import os
from loguru import logger
import time
import traceback
from typing import Dict, Any
import whisperx
import torch
from core.config import (
    WHISPER_MODEL, COMPUTE_TYPE, OUTPUT_DIR,
    BATCH_SIZE, NUM_WORKERS, LANGUAGE, NAS_PATH
)
from torch.serialization import add_safe_globals
from omegaconf.listconfig import ListConfig
from huggingface_hub import hf_hub_download
from pyannote.audio import Model

# Add omegaconf.ListConfig to safe globals for PyTorch 2.6+
add_safe_globals([ListConfig])

def get_current_job():
    try:
        from rq import get_current_job as rq_get_current_job
        return rq_get_current_job()
    except:
        return None

def run_whisperx(video_path: str) -> Dict[str, Any]:
    """Run WhisperX transcription on a video file using the Python API"""
    try:
        logger.info(f"Starting transcription of {video_path}")
        
        # Get current job for progress updates
        current_job = get_current_job()
        if current_job:
            current_job.meta.update({
                'start_time': time.time(),
                'progress': 0,
                'status_message': 'Initializing transcription...',
                'error_details': None
            })
            current_job.save_meta()

        # Validate input file
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Check file size
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise ValueError(f"Video file is empty: {video_path}")
            
        # Check file permissions
        if not os.access(video_path, os.R_OK):
            raise PermissionError(f"No read permission for file: {video_path}")

        # Use OUTPUT_DIR for output files
        if not os.access(OUTPUT_DIR, os.W_OK):
            raise PermissionError(f"No write permission for output directory: {OUTPUT_DIR}")

        # Get relative path structure
        rel_path = os.path.relpath(video_path, NAS_PATH)
        output_subdir = os.path.dirname(rel_path)
        output_path = os.path.join(OUTPUT_DIR, output_subdir)
        os.makedirs(output_path, exist_ok=True)

        # Update status
        if current_job:
            current_job.meta['status_message'] = 'Loading WhisperX model...'
            current_job.save_meta()

        # Load model with updated configuration
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "float32"
        
        # Set the target directory
        target_dir = "/opt/Archivist/.venv/lib/python3.11/site-packages/whisperx/assets"
        os.makedirs(target_dir, exist_ok=True)

        # Download the model file directly
        model_path = hf_hub_download(
            repo_id="pyannote/segmentation",
            filename="pytorch_model.bin",
            token="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",
            cache_dir=target_dir
        )

        # Verify the downloaded file
        if os.path.exists(model_path):
            file_size = os.path.getsize(model_path)
            if file_size == 0:
                raise ValueError('Downloaded model file is empty. Please check the download process.')
            elif file_size < 1000:  # Arbitrary size check, adjust as needed
                raise ValueError('Downloaded model file is too small. Please check the download process.')
            else:
                print(f'Model file downloaded successfully with size: {file_size} bytes.')
        else:
            raise FileNotFoundError('Model file was not downloaded. Please check the download process.')

        # Now load the model to verify it works
        model = Model.from_pretrained(
            "pyannote/segmentation",
            use_auth_token="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",
            cache_dir=target_dir
        )
        print("Model loaded successfully!")

        if current_job:
            current_job.meta['status_message'] = 'Transcribing audio...'
            current_job.save_meta()

        # Transcribe audio
        result = model.transcribe(video_path)
        
        if current_job:
            current_job.meta['status_message'] = 'Aligning timestamps...'
            current_job.save_meta()

        # Align whisper output
        model_a, metadata = whisperx.load_align_model(
            language_code=LANGUAGE,
            device=device
        )
        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            video_path,
            device
        )

        # Save results
        output_file = os.path.join(output_path, f"{os.path.basename(video_path)}.srt")
        with open(output_file, "w", encoding="utf-8") as f:
            for segment in result["segments"]:
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"].strip()
                f.write(f"{segment['id']}\n{start} --> {end}\n{text}\n\n")

        if current_job:
            current_job.meta.update({
                'progress': 100,
                'status_message': f'Completed! Generated transcript with {len(result["segments"])} segments',
                'time_remaining': 0
            })
            current_job.save_meta()

        return {
            'srt_path': output_file,
            'segments': len(result["segments"]),
            'duration': result["segments"][-1]["end"] if result["segments"] else 0
        }

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        error_details = {
            'type': error_type,
            'message': error_msg,
            'traceback': traceback.format_exc()
        }
        
        logger.error(f"Transcription error ({error_type}): {error_msg}")
        if current_job:
            current_job.meta.update({
                'error_details': error_details,
                'status_message': f"Error ({error_type}): {error_msg}",
                'failed_at': time.time()
            })
            current_job.save_meta()
        raise

def format_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",") 
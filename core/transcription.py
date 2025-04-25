import subprocess
import os
import torch
from loguru import logger
from typing import Tuple
from config import (
    WHISPER_MODEL, COMPUTE_TYPE, OUTPUT_DIR,
    BATCH_SIZE, NUM_WORKERS, LANGUAGE
)

def run_whisperx(video_path: str) -> Tuple[bool, str]:
    """
    Transcribes a video file using WhisperX and returns the path to the generated SRT file.
    
    Args:
        video_path (str): Path to the video file to transcribe
        
    Returns:
        Tuple[bool, str]: (success, srt_path)
            - success: True if transcription was successful
            - srt_path: Path to the generated SRT file, or error message if failed
    """
    try:
        # Validate input file
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Prepare output paths
        video_name = os.path.basename(video_path)
        srt_name = os.path.splitext(video_name)[0] + ".srt"
        srt_path = os.path.join(OUTPUT_DIR, srt_name)
        
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Build WhisperX command
        command = [
            "whisperx",
            video_path,
            "--model", WHISPER_MODEL,
            "--output_dir", OUTPUT_DIR,
            "--output_format", "srt",
            "--compute_type", COMPUTE_TYPE,
            "--batch_size", str(BATCH_SIZE),
            "--language", LANGUAGE,
            "--device", "cpu",
            "--threads", str(NUM_WORKERS)
        ]
            
        # Run WhisperX
        logger.info(f"Starting transcription of {video_path}")
        logger.info(f"Using command: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Log the output for debugging
        if result.stdout:
            logger.info(f"WhisperX output: {result.stdout}")
        if result.stderr:
            logger.warning(f"WhisperX warnings: {result.stderr}")
        
        # Verify output
        if not os.path.exists(srt_path):
            raise FileNotFoundError(f"SRT file not generated at expected location: {srt_path}")
            
        logger.info(f"Transcription completed successfully: {srt_path}")
        return True, srt_path
        
    except subprocess.CalledProcessError as e:
        error_msg = f"WhisperX failed: {e.stderr if e.stderr else str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Transcription error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg 
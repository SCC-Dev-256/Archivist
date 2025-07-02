import subprocess
import os
import torch
from core.services import TranscriptionService


def run_whisper_transcription(video_path: str) -> str:
    """
    Transcribes the given video file using faster-whisper library and returns the path to the generated SRT file.
    
    Args:
        video_path (str): Path to the video file
        
    Returns:
        str: Path to the generated SRT file
        
    Raises:
        RuntimeError: If transcription fails
    """
    try:
        result = TranscriptionService().transcribe_file(video_path)
        return result['srt_path']
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")

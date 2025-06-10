import subprocess
import os
import torch


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
    # Import the actual transcription function
    from core.transcription import run_whisper_transcription as transcribe
    
    try:
        result = transcribe(video_path)
        return result['srt_path']
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")

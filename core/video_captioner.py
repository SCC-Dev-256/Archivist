import subprocess
import os
import torch


def run_whisperx(video_path: str) -> str:
    """
    Transcribes the given video file using WhisperX and returns the path to the generated SRT file.
    """
    video_dir = os.path.dirname(video_path)
    video_name = os.path.basename(video_path)
    srt_name = os.path.splitext(video_name)[0] + ".srt"
    srt_path = os.path.join(video_dir, srt_name)

    command = [
        "whisperx", video_path,
        "--output_dir", video_dir,
        "--output_format", "srt"
    ]

    compute_type = "float16" if torch.cuda.is_available() else "int8"
    command.extend(["--compute_type", compute_type])

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"WhisperX failed: {e}")

    if not os.path.exists(srt_path):
        raise FileNotFoundError(f"SRT file not found at expected location: {srt_path}")

    return srt_path

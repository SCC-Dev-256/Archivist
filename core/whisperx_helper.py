from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger


from core.config import (
    WHISPER_MODEL,
    USE_GPU,
    COMPUTE_TYPE,
    BATCH_SIZE,
    LANGUAGE,
    OUTPUT_DIR,
)

# Mapping used to decode SCC files in scc_summarizer.py
_HEX_TO_CHAR = {
    '20': ' ', '21': '!', '22': '"', '23': '#', '24': '$', '25': '%', '26': '&', '27': "'",
    '28': '(', '29': ')', '2A': '*', '2B': '+', '2C': ',', '2D': '-', '2E': '.', '2F': '/',
    '30': '0', '31': '1', '32': '2', '33': '3', '34': '4', '35': '5', '36': '6', '37': '7',
    '38': '8', '39': '9', '3A': ':', '3B': ';', '3C': '<', '3D': '=', '3E': '>', '3F': '?',
    '40': '@', '41': 'A', '42': 'B', '43': 'C', '44': 'D', '45': 'E', '46': 'F', '47': 'G',
    '48': 'H', '49': 'I', '4A': 'J', '4B': 'K', '4C': 'L', '4D': 'M', '4E': 'N', '4F': 'O',
    '50': 'P', '51': 'Q', '52': 'R', '53': 'S', '54': 'T', '55': 'U', '56': 'V', '57': 'W',
    '58': 'X', '59': 'Y', '5A': 'Z', '5B': '[', '5C': '\\', '5D': ']', '5E': '^', '5F': '_',
    '60': '`', '61': 'a', '62': 'b', '63': 'c', '64': 'd', '65': 'e', '66': 'f', '67': 'g',
    '68': 'h', '69': 'i', '6A': 'j', '6B': 'k', '6C': 'l', '6D': 'm', '6E': 'n', '6F': 'o',
    '70': 'p', '71': 'q', '72': 'r', '73': 's', '74': 't', '75': 'u', '76': 'v', '77': 'w',
    '78': 'x', '79': 'y', '7A': 'z', '7B': '{', '7C': '|', '7D': '}', '7E': '~',
}
_CHAR_TO_HEX = {v: k for k, v in _HEX_TO_CHAR.items()}

_PREFIX = "9420 9420 94ae 94ae 9452 9452 97a2 97a2"
_SUFFIX = "9420 9420 942c 942c 8080 8080"


def _seconds_to_smpte(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int(round((seconds - int(seconds)) * 30))
    return f"{hours:02d}:{minutes:02d}:{secs:02d};{frames:02d}"


def _encode_text(text: str) -> str:
    return " ".join(_CHAR_TO_HEX.get(ch, '20') for ch in text)


def save_scc_file(segments: List[Dict[str, Any]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("Scenarist_SCC V1.0\n\n")
        for seg in segments:
            ts = _seconds_to_smpte(float(seg.get('start', 0)))
            text_hex = _encode_text(str(seg.get('text', '')))
            line = f"{ts}\t{_PREFIX} {text_hex} {_SUFFIX}\n"
            f.write(line + "\n")
    logger.debug(f"Saved SCC file: {output_path}")


def transcribe_with_whisperx(file_path: str, output_dir: str | None = None) -> Dict[str, Any]:
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    from faster_whisper import WhisperModel

    device = "cuda" if USE_GPU else "cpu"
    logger.info(f"Loading Whisper model {WHISPER_MODEL} on {device}")
    model = WhisperModel(WHISPER_MODEL, device=device, compute_type=COMPUTE_TYPE)
    segments_gen, info = model.transcribe(file_path, batch_size=BATCH_SIZE, language=LANGUAGE)
    segments = [
        {"start": seg.start, "end": seg.end, "text": seg.text.strip()} for seg in segments_gen
    ]
    duration = getattr(info, 'duration', 0)
    scc_path = os.path.join(output_dir, Path(file_path).stem + '.scc')
    save_scc_file(segments, scc_path)
    logger.info(f"Transcription complete: {scc_path}")
    return {"output_path": scc_path, "segments": len(segments), "duration": duration}

__all__ = ["transcribe_with_whisperx", "save_scc_file"]

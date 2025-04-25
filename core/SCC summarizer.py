import os
import json
from typing import List, Dict

# Placeholder - connect llama.cpp or another summarization backend later
def dummy_summarize_segment(text: str) -> str:
    return f"Summary of: {text[:60]}..."

def parse_srt(file_path: str) -> List[Dict]:
    segments = []
    with open(file_path, 'r') as f:
        lines = f.read().splitlines()
    
    block = []
    for line in lines:
        if line.strip():
            block.append(line.strip())
        else:
            if len(block) >= 3:
                segments.append({
                    "index": block[0],
                    "time": block[1],
                    "text": " ".join(block[2:])
                })
            block = []
    return segments

def summarize_srt(srt_path: str):
    segments = parse_srt(srt_path)
    summary = []
    for seg in segments:
        summary.append({
            "speaker": "Unknown",  # Optional: add speaker ID logic
            "start": seg["time"].split(" --> ")[0],
            "text": dummy_summarize_segment(seg["text"])
        })
    
    summary_path = srt_path.replace(".srt", "_minutes.json")
    with open(summary_path, 'w') as f:
        json.dump({"summary": summary}, f, indent=2)

    return summary_path

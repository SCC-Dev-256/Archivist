import os
import json
from typing import List, Dict
from transformers import AutoModelForCausalLM, AutoTokenizer
from loguru import logger

class SummaryModel:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """Lazy loading of the model to save memory when not in use"""
        if self.model is None:
            logger.info("Loading slim-summary model...")
            self.model = AutoModelForCausalLM.from_pretrained("llmware/slim-summary")
            self.tokenizer = AutoTokenizer.from_pretrained("llmware/slim-summary")
            logger.info("Model loaded successfully")

    def summarize_text(self, text: str, num_points: int = 3) -> str:
        """Summarize text using the slim-summary model"""
        self.load_model()
        
        function = "summarize"
        params = f"key points ({num_points})"
        prompt = f"<human>: {text}\n<{function}> {params} </{function}>\n<bot>:"
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        start_of_input = len(inputs.input_ids[0])
        
        outputs = self.model.generate(
            inputs.input_ids.to('cpu'),
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.3,
            max_new_tokens=100
        )
        
        summary = self.tokenizer.decode(outputs[0][start_of_input:], skip_special_tokens=True)
        return summary.strip()

# Create a singleton instance
summarizer = SummaryModel()

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
    
    # Group segments into chunks for better context
    chunk_size = 5  # Summarize 5 segments at a time
    for i in range(0, len(segments), chunk_size):
        chunk = segments[i:i + chunk_size]
        combined_text = " ".join(seg["text"] for seg in chunk)
        
        # Get timestamp of first segment in chunk
        start_time = chunk[0]["time"].split(" --> ")[0]
        
        summary.append({
            "speaker": "Unknown",  # Optional: add speaker ID logic
            "start": start_time,
            "text": summarizer.summarize_text(combined_text, num_points=1)
        })
    
    summary_path = srt_path.replace(".srt", "_minutes.json")
    with open(summary_path, 'w') as f:
        json.dump({"summary": summary}, f, indent=2)

    return summary_path

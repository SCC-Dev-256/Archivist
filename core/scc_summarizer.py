"""
SCC Transcript Summarizer Module

This module provides functionality to summarize SCC (Scenarist Closed Caption) files
using local transformer models for extracting key points from transcribed content.

Key Features:
- SCC file parsing and text extraction
- Local model-based summarization
- Conversion to meeting minutes format
- Structured output with timestamps
- CPU-optimized processing

Example:
    >>> from core.scc_summarizer import summarize_scc
    >>> summary_path = summarize_scc('transcript.scc')
    >>> print(f"Summary saved to: {summary_path}")
"""

import json
import re
import os
from typing import List, Dict, Any, Optional
from loguru import logger
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
from core.config import (
    SUMMARIZATION_MODEL, SUMMARIZATION_MAX_LENGTH, 
    SUMMARIZATION_MIN_LENGTH, SUMMARIZATION_CHUNK_SIZE
)

# Force CPU-only mode for consistency with transcription system
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
torch.cuda.is_available = lambda: False

class LocalSummaryModel:
    """Local transformer model interface for text summarization."""
    
    def __init__(self):
        """Initialize the local model."""
        self.device = "cpu"
        self.model_name = SUMMARIZATION_MODEL
        self.max_length = SUMMARIZATION_MAX_LENGTH
        self.min_length = SUMMARIZATION_MIN_LENGTH
        
        try:
            # Initialize the summarization pipeline
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                device=0 if torch.cuda.is_available() else -1,
                torch_dtype=torch.float32
            )
            logger.info(f"Successfully loaded local summarization model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load summarization model: {e}")
            # Fallback to a simpler approach
            self.summarizer = None
    
    def summarize_text(self, text: str, num_points: int = 3) -> str:
        """
        Summarize text using local transformer model.
        
        Args:
            text: Text to summarize
            num_points: Number of key points to extract (used for guidance)
            
        Returns:
            Summarized text
        """
        if not self.summarizer:
            # Fallback to simple text truncation if model fails
            return self._simple_summarize(text, num_points)
        
        try:
            # Truncate text if too long
            if len(text) > 1024:
                text = text[:1024]
            
            # Generate summary
            summary_result = self.summarizer(
                text,
                max_length=self.max_length,
                min_length=self.min_length,
                do_sample=False,
                truncation=True
            )
            
            if summary_result and len(summary_result) > 0:
                summary = summary_result[0]['summary_text']
                logger.debug(f"Generated summary: {summary}")
                return summary
            else:
                return self._simple_summarize(text, num_points)
                
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self._simple_summarize(text, num_points)
    
    def _simple_summarize(self, text: str, num_points: int) -> str:
        """
        Simple fallback summarization using text processing.
        
        Args:
            text: Text to summarize
            num_points: Number of key points to extract
            
        Returns:
            Simple summary
        """
        # Split into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if not sentences:
            return "No content to summarize"
        
        # Take first few sentences as summary
        summary_sentences = sentences[:min(num_points, len(sentences))]
        summary = '. '.join(summary_sentences)
        
        # Ensure it ends with a period
        if not summary.endswith('.'):
            summary += '.'
        
        logger.debug(f"Simple summary generated: {summary}")
        return summary

# Create a singleton instance
summarizer = LocalSummaryModel()

def parse_scc(file_path: str) -> List[Dict]:
    """
    Parse SCC (Scenarist Closed Caption) file and extract text segments.
    
    Args:
        file_path: Path to the SCC file
        
    Returns:
        List of dictionaries with segment information
    """
    segments = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into lines and process
        lines = content.strip().split('\n')
        current_segment = None
        segment_index = 1
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and header
            if not line or line.startswith('Scenarist_SCC'):
                continue
            
            # Check if line contains a timestamp
            if re.match(r'\d{2}:\d{2}:\d{2}[:;]\d{2}', line):
                # Extract timestamp and hex data
                parts = line.split('\t', 1)
                if len(parts) >= 2:
                    timestamp = parts[0]
                    hex_data = parts[1]
                    
                    # Extract readable text from hex data
                    text = extract_text_from_hex(hex_data)
                    
                    if text and text.strip():
                        # Parse SMPTE timestamp to seconds
                        start_seconds = parse_smpte_timestamp(timestamp)
                        
                        # Create new segment
                        segments.append({
                            "index": str(segment_index),
                            "start": start_seconds,
                            "end": start_seconds + 3.0,  # Default 3 second duration
                            "time": timestamp,
                            "text": text.strip()
                        })
                        segment_index += 1
        
        logger.info(f"Parsed {len(segments)} segments from SCC file")
        return segments
        
    except Exception as e:
        logger.error(f"Error parsing SCC file {file_path}: {e}")
        return []

def parse_smpte_timestamp(timestamp: str) -> float:
    """
    Parse SMPTE timestamp (HH:MM:SS;FF or HH:MM:SS:FF) to seconds.
    
    Args:
        timestamp: SMPTE timestamp string
        
    Returns:
        Time in seconds
    """
    try:
        # Handle both semicolon and colon separators
        if ';' in timestamp:
            time_part, frames = timestamp.split(';')
        elif ':' in timestamp and timestamp.count(':') == 3:
            parts = timestamp.split(':')
            time_part = ':'.join(parts[:3])
            frames = parts[3]
        else:
            # No frames, treat as regular time
            time_part = timestamp
            frames = '0'
        
        # Parse time components
        hours, minutes, seconds = map(int, time_part.split(':'))
        frame_num = int(frames)
        
        # Convert to total seconds (assume 29.97 fps)
        total_seconds = hours * 3600 + minutes * 60 + seconds + (frame_num / 29.97)
        
        return total_seconds
        
    except Exception as e:
        logger.error(f"Error parsing SMPTE timestamp {timestamp}: {e}")
        return 0.0

def extract_text_from_hex(hex_data: str) -> str:
    """
    Extract readable text from SCC hexadecimal data.
    
    Args:
        hex_data: Hexadecimal string from SCC file
        
    Returns:
        Extracted text string
    """
    # CEA-608 hex to character mapping (basic implementation)
    hex_to_char = {
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
        '78': 'x', '79': 'y', '7A': 'z', '7B': '{', '7C': '|', '7D': '}', '7E': '~'
    }
    
    # Skip control codes and extract text
    control_codes = {'94ae', '9420', '942c', '942f', '8080', '947a', '94f2', '9452', '97a2'}
    
    text_parts = []
    hex_words = hex_data.split()
    
    for hex_word in hex_words:
        if hex_word.lower() in control_codes:
            continue
            
        # Process word in pairs of hex characters
        for i in range(0, len(hex_word), 2):
            if i + 1 < len(hex_word):
                hex_char = hex_word[i:i+2].upper()
                if hex_char in hex_to_char:
                    text_parts.append(hex_to_char[hex_char])
    
    return ''.join(text_parts)

def summarize_scc(scc_path: str) -> str:
    """
    Summarize an SCC (Scenarist Closed Caption) file.
    
    Args:
        scc_path: Path to the SCC file
        
    Returns:
        Path to the generated summary file
    """
    try:
        logger.info(f"Starting summarization of SCC file: {scc_path}")
        
        # Parse SCC file
        segments = parse_scc(scc_path)
        
        if not segments:
            logger.warning(f"No segments found in SCC file: {scc_path}")
            return None
        
        summary = []
        
        # Group segments into chunks for better context
        chunk_size = SUMMARIZATION_CHUNK_SIZE
        for i in range(0, len(segments), chunk_size):
            chunk = segments[i:i + chunk_size]
            combined_text = " ".join(seg["text"] for seg in chunk)
            
            # Skip empty chunks
            if not combined_text.strip():
                continue
            
            # Get timestamp of first segment in chunk
            start_time = chunk[0]["time"]
            
            # Generate summary for this chunk
            chunk_summary = summarizer.summarize_text(combined_text, num_points=1)
            
            summary.append({
                "speaker": "Unknown",  # Optional: add speaker ID logic
                "start": start_time,
                "text": chunk_summary
            })
        
        # Create output file path
        summary_path = scc_path.replace(".scc", "_minutes.json")
        
        # Save summary
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({"summary": summary}, f, indent=2)
        
        logger.info(f"Summary saved to: {summary_path}")
        return summary_path
        
    except Exception as e:
        logger.error(f"Error summarizing SCC file {scc_path}: {e}")
        return None

# Legacy function name for backward compatibility
def summarize_srt(srt_path: str) -> str:
    """
    Legacy function that redirects to SCC summarization.
    
    Args:
        srt_path: Path to the file (should be SCC format)
        
    Returns:
        Path to the generated summary file
    """
    logger.warning("summarize_srt is deprecated. Use summarize_scc instead.")
    return summarize_scc(srt_path)

#!/usr/bin/env python3
"""
Complete SCC Pipeline Test

This script tests the complete SCC transcription pipeline using a real video file:
1. Video transcription to SCC format
2. SCC file validation
3. Local model summarization
4. End-to-end verification
"""

import os
import sys
import time
from datetime import datetime
from loguru import logger
from core.transcription import run_whisper_transcription
from core.scc_summarizer import summarize_scc, parse_scc
from core.services.transcription import TranscriptionService

# Configure logging for the test
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")

def find_test_video():
    """Find a suitable test video file."""
    # List of potential video files to test with (member city content)
    potential_files = [
        "/mnt/flex-5/14221-1-North St Paul City Council (20190402).mp4",  # Spare Record Storage 1
        "/mnt/flex-2/10845-1-Birchwood City Council (20160614).mpeg",     # Dellwood Grant Willernie
        "/mnt/nas/test_video.mp4"
    ]
    
    for video_path in potential_files:
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
            logger.info(f"Found video: {video_path} ({file_size:.1f} MB)")
            return video_path
    
    logger.error("No test video files found")
    return None

def validate_scc_file(scc_path):
    """Validate that the SCC file is correctly formatted."""
    if not os.path.exists(scc_path):
        logger.error(f"SCC file does not exist: {scc_path}")
        return False
    
    file_size = os.path.getsize(scc_path)
    if file_size == 0:
        logger.error("SCC file is empty")
        return False
    
    logger.info(f"SCC file size: {file_size} bytes")
    
    # Read and validate SCC content
    try:
        with open(scc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.strip().split('\n')
        
        # Check header
        if not lines[0].startswith('Scenarist_SCC V1.0'):
            logger.error("Invalid SCC header")
            return False
        
        # Count timecode lines
        timecode_lines = [line for line in lines if ';' in line and '\t' in line]
        logger.info(f"SCC segments found: {len(timecode_lines)}")
        
        if len(timecode_lines) == 0:
            logger.error("No SCC segments found")
            return False
        
        # Show sample content
        if timecode_lines:
            logger.info(f"First SCC segment: {timecode_lines[0][:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating SCC file: {e}")
        return False

def test_scc_parsing(scc_path):
    """Test SCC file parsing."""
    logger.info("Testing SCC parsing...")
    
    segments = parse_scc(scc_path)
    
    if not segments:
        logger.error("Failed to parse SCC file")
        return False
    
    logger.info(f"Successfully parsed {len(segments)} segments")
    
    # Show sample parsed content
    for i, segment in enumerate(segments[:3]):
        logger.info(f"Segment {i+1}: [{segment.get('time', 'N/A')}] {segment.get('text', '')[:100]}...")
    
    return True

def test_summarization(scc_path):
    """Test SCC summarization with local model."""
    logger.info("Testing SCC summarization...")
    
    try:
        summary_path = summarize_scc(scc_path)
        
        if not summary_path:
            logger.error("Summarization failed - no output file")
            return False
        
        if not os.path.exists(summary_path):
            logger.error(f"Summary file was not created: {summary_path}")
            return False
        
        # Validate summary content
        import json
        with open(summary_path, 'r') as f:
            summary_data = json.load(f)
        
        if 'summary' not in summary_data:
            logger.error("Summary data missing 'summary' key")
            return False
        
        summary_items = summary_data['summary']
        logger.info(f"Generated {len(summary_items)} summary items")
        
        # Show sample summary
        for i, item in enumerate(summary_items[:2]):
            logger.info(f"Summary {i+1}: [{item.get('start', 'N/A')}] {item.get('text', '')[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Summarization test failed: {e}")
        return False

def run_complete_pipeline():
    """Run the complete SCC transcription pipeline."""
    logger.info("🚀 Starting Complete SCC Pipeline Test")
    logger.info("=" * 60)
    
    # Step 1: Find test video
    video_path = find_test_video()
    if not video_path:
        return False
    
    logger.info(f"Using video: {video_path}")
    
    # Step 2: Run transcription
    logger.info("\n📹 Step 1: Running WhisperX Transcription to SCC")
    logger.info("-" * 50)
    
    start_time = time.time()
    
    try:
        # Use the service layer for cleaner interface
        transcription_service = TranscriptionService()
        result = transcription_service.transcribe_file(video_path)
        
        if not result or result.get('status') != 'completed':
            logger.error(f"Transcription failed: {result}")
            return False
        
        scc_path = result.get('output_path')
        if not scc_path:
            logger.error("No SCC output path returned")
            return False
        
        transcription_time = time.time() - start_time
        logger.info(f"✅ Transcription completed in {transcription_time/60:.2f} minutes")
        logger.info(f"✅ SCC file: {scc_path}")
        logger.info(f"✅ Segments: {result.get('segments', 0)}")
        logger.info(f"✅ Duration: {result.get('duration', 0):.1f} seconds")
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return False
    
    # Step 3: Validate SCC file
    logger.info("\n📄 Step 2: Validating SCC File Format")
    logger.info("-" * 50)
    
    if not validate_scc_file(scc_path):
        return False
    
    logger.info("✅ SCC file validation passed")
    
    # Step 4: Test SCC parsing
    logger.info("\n🔍 Step 3: Testing SCC Parsing")
    logger.info("-" * 50)
    
    if not test_scc_parsing(scc_path):
        return False
    
    logger.info("✅ SCC parsing test passed")
    
    # Step 5: Test summarization
    logger.info("\n🧠 Step 4: Testing Local Model Summarization")
    logger.info("-" * 50)
    
    if not test_summarization(scc_path):
        return False
    
    logger.info("✅ Summarization test passed")
    
    # Final summary
    total_time = time.time() - start_time
    logger.info("\n🎉 COMPLETE PIPELINE TEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"✅ Video file: {video_path}")
    logger.info(f"✅ SCC file: {scc_path}")
    logger.info(f"✅ Total time: {total_time/60:.2f} minutes")
    logger.info(f"✅ All tests passed! SCC pipeline is working correctly.")
    
    return True

if __name__ == "__main__":
    success = run_complete_pipeline()
    
    if success:
        logger.info("\n🎉 Complete SCC pipeline test PASSED!")
        sys.exit(0)
    else:
        logger.error("\n❌ Complete SCC pipeline test FAILED!")
        sys.exit(1) 
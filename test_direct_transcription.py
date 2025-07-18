#!/usr/bin/env python3
"""
Test script to test transcription directly without Celery.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.transcription import run_whisper_transcription
from loguru import logger

def test_direct_transcription():
    """Test transcription directly without Celery."""
    print("🎤 Testing Direct WhisperX Transcription...")
    
    # Test video file path
    test_video = "/mnt/flex-8/White Bear Lake Shortest Marathon.mp4"
    
    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        return False
    
    print(f"✅ Found test video: {test_video}")
    print(f"📊 File size: {os.path.getsize(test_video) / (1024*1024):.1f} MB")
    
    try:
        # Run transcription directly
        print("🚀 Starting direct transcription...")
        result = run_whisper_transcription(video_path=test_video)
        
        print("✅ Transcription completed!")
        print(f"📄 Output path: {result.get('output_path')}")
        print(f"⏱️ Duration: {result.get('duration', 'Unknown')}")
        print(f"📝 Segments: {result.get('segments', 'Unknown')}")
        print(f"📊 Status: {result.get('status', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_transcription()
    sys.exit(0 if success else 1) 
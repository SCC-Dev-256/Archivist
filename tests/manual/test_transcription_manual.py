#!/usr/bin/env python3
"""
Test script to directly test WhisperX transcription on a video file.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tasks import celery_app
from core.tasks.transcription import run_whisper_transcription
from loguru import logger

def test_transcription():
    """Test transcription on a video file."""
    print("🎤 Testing WhisperX Transcription...")
    
    # Test video file path
    test_video = "/mnt/flex-8/White Bear Lake Shortest Marathon.mp4"
    
    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        return False
    
    print(f"✅ Found test video: {test_video}")
    print(f"📊 File size: {os.path.getsize(test_video) / (1024*1024):.1f} MB")
    
    try:
        # Trigger transcription task
        print("🚀 Starting transcription...")
        result = run_whisper_transcription.delay(test_video)
        
        print(f"✅ Task queued: {result.id}")
        print("⏳ Waiting for completion...")
        
        # Wait for result (with timeout)
        transcription_data = result.get(timeout=300)  # 5 minute timeout
        
        print("✅ Transcription completed!")
        print(f"📄 Output path: {transcription_data.get('output_path')}")
        print(f"⏱️ Duration: {transcription_data.get('duration', 'Unknown')}")
        print(f"📝 Status: {transcription_data.get('status')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return False

if __name__ == "__main__":
    success = test_transcription()
    sys.exit(0 if success else 1) 
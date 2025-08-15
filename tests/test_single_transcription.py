#!/usr/bin/env python3
"""Test script for single video transcription on surface-level flex servers.

This script tests the transcription system by processing a single video file
from one of the flex servers to verify the surface-level structure works correctly.
"""

import os
import sys
import time
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_single_transcription():
    """Test transcription of a single video file."""
    print("🎬 Testing Single Video Transcription")
    print("=" * 50)
    
    # Find a suitable test video (smaller file for faster testing)
    test_video = None
    test_server = None
    
    # Check flex servers for a suitable test video
    flex_servers = {
        'flex1': '/mnt/flex-1',
        'flex2': '/mnt/flex-2', 
        'flex3': '/mnt/flex-3',
        'flex4': '/mnt/flex-4',
        'flex5': '/mnt/flex-5',
        'flex6': '/mnt/flex-6',
        'flex7': '/mnt/flex-7',
        'flex8': '/mnt/flex-8'
    }
    
    print("🔍 Searching for suitable test video...")
    
    for server_id, mount_path in flex_servers.items():
        if not os.path.ismount(mount_path):
            continue
            
        if not os.access(mount_path, os.R_OK):
            continue
        
        # Look for a smaller video file (under 100MB for faster testing)
        import glob
        video_files = glob.glob(os.path.join(mount_path, "*.mp4"))
        
        for video_file in video_files:
            if os.path.isfile(video_file):
                file_size = os.path.getsize(video_file)
                file_size_mb = file_size / (1024 * 1024)
                
                # Check if this video already has an SCC file
                base_name = os.path.splitext(os.path.basename(video_file))[0]
                scc_path = os.path.join(mount_path, f"{base_name}.scc")
                
                # Prefer a smaller file that doesn't already have transcription
                if file_size_mb < 100 and not os.path.exists(scc_path):
                    test_video = video_file
                    test_server = server_id
                    print(f"✅ Found test video: {os.path.basename(video_file)} ({file_size_mb:.1f} MB)")
                    break
        
        if test_video:
            break
    
    if not test_video:
        print("❌ No suitable test video found (small file without existing transcription)")
        return False
    
    print(f"\n📹 Test Video Details:")
    print(f"  File: {os.path.basename(test_video)}")
    print(f"  Path: {test_video}")
    print(f"  Server: {test_server}")
    print(f"  Size: {os.path.getsize(test_video) / (1024 * 1024):.1f} MB")
    
    # Check if file is accessible
    if not os.path.exists(test_video):
        print("❌ Test video file not found")
        return False
    
    print(f"\n🚀 Starting Transcription...")
    start_time = time.time()
    
    try:
        # Import and use the transcription service
        from core.services.transcription import TranscriptionService
        
        service = TranscriptionService()
        
        print(f"  📝 Transcribing: {os.path.basename(test_video)}")
        
        # Perform transcription
        result = service.transcribe_file(test_video)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Transcription Completed!")
        print(f"  Duration: {duration:.1f} seconds")
        print(f"  Output: {result.get('output_path', 'N/A')}")
        print(f"  Segments: {result.get('segments', 0)}")
        print(f"  Status: {result.get('status', 'N/A')}")
        
        # Verify the SCC file was created
        base_name = os.path.splitext(os.path.basename(test_video))[0]
        expected_scc_path = os.path.join(os.path.dirname(test_video), f"{base_name}.scc")
        
        if os.path.exists(expected_scc_path):
            scc_size = os.path.getsize(expected_scc_path)
            print(f"  SCC File: {os.path.basename(expected_scc_path)} ({scc_size} bytes)")
            
            # Show first few lines of SCC file
            try:
                with open(expected_scc_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]  # First 10 lines
                    print(f"  SCC Preview:")
                    for i, line in enumerate(lines, 1):
                        print(f"    {i:2d}: {line.strip()}")
                    if len(lines) == 10:
                        print(f"    ... (truncated)")
            except Exception as e:
                print(f"  ⚠️  Could not read SCC file: {e}")
        else:
            print(f"  ❌ SCC file not found at expected location: {expected_scc_path}")
            return False
        
        print(f"\n🎉 Transcription test successful!")
        print(f"  Surface-level structure working correctly")
        print(f"  SCC file generated in same directory as video")
        
        return True
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_files():
    """Clean up any test files created during testing."""
    print("\n🧹 Cleaning up test files...")
    
    # This would remove any test SCC files if needed
    # For now, we'll keep them as proof of successful transcription
    print("  Test files preserved for verification")

if __name__ == "__main__":
    print("🚀 Starting Single Video Transcription Test")
    print("=" * 60)
    
    # Test single transcription
    success = test_single_transcription()
    
    # Cleanup
    cleanup_test_files()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Single transcription test completed successfully!")
        print("✅ Surface-level flex server transcription is working correctly")
    else:
        print("❌ Single transcription test failed")
        print("⚠️  Check the output above for error details")
    
    print("\n📋 Test Summary:")
    print(f"  Single Transcription: {'✅' if success else '❌'}")
    print(f"  Surface-Level Structure: {'✅' if success else '❌'}")
    print(f"  SCC Generation: {'✅' if success else '❌'}") 
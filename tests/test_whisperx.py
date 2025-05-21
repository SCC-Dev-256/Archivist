import os
import pytest
from core.transcription import run_whisperx
from core.config import OUTPUT_DIR, NAS_PATH
import tempfile
import shutil

@pytest.fixture
def test_video():
    """Create a temporary test video file"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    test_video_path = os.path.join(temp_dir, "test_video.mp4")
    
    # Create a simple test video file (1 second of silence with video)
    os.system(f"ffmpeg -f lavfi -i testsrc=duration=1:size=1280x720:rate=30 -f lavfi -i anullsrc=r=44100:cl=mono -c:v libx264 -c:a aac -shortest {test_video_path}")
    
    # Verify the file was created and has content
    if not os.path.exists(test_video_path) or os.path.getsize(test_video_path) == 0:
        pytest.skip("Failed to create test video file")
    
    yield test_video_path
    
    # Cleanup
    shutil.rmtree(temp_dir)

def test_whisperx_transcription(test_video):
    """Test the WhisperX transcription functionality"""
    # Run transcription
    result = run_whisperx(test_video)
    
    # Verify result structure
    assert isinstance(result, dict)
    assert 'srt_path' in result
    assert 'segments' in result
    assert 'duration' in result
    
    # Verify output file exists
    assert os.path.exists(result['srt_path'])
    
    # Verify SRT file content
    with open(result['srt_path'], 'r', encoding='utf-8') as f:
        content = f.read()
        assert content.strip()  # File should not be empty
        assert '-->' in content  # Should contain timestamp markers

def test_whisperx_error_handling():
    """Test error handling for non-existent file"""
    with pytest.raises(FileNotFoundError):
        run_whisperx("nonexistent_video.mp4")

def test_whisperx_empty_file():
    """Test handling of empty video file"""
    # Create empty file
    temp_dir = tempfile.mkdtemp()
    empty_video = os.path.join(temp_dir, "empty_video.mp4")
    open(empty_video, 'w').close()
    
    try:
        with pytest.raises(ValueError):
            run_whisperx(empty_video)
    finally:
        shutil.rmtree(temp_dir)

def test_whisperx_permissions():
    """Test handling of permission errors"""
    # Create a file with no read permissions
    temp_dir = tempfile.mkdtemp()
    no_perms_video = os.path.join(temp_dir, "no_perms_video.mp4")
    
    # Create a valid video file first
    os.system(f"ffmpeg -f lavfi -i testsrc=duration=1:size=1280x720:rate=30 -f lavfi -i anullsrc=r=44100:cl=mono -c:v libx264 -c:a aac -shortest {no_perms_video}")
    
    # Then remove permissions
    os.chmod(no_perms_video, 0o000)
    
    try:
        with pytest.raises(PermissionError):
            run_whisperx(no_perms_video)
    finally:
        os.chmod(no_perms_video, 0o644)
        shutil.rmtree(temp_dir) 
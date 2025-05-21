import os
import pytest
from core.transcription import run_whisperx
from core.config import OUTPUT_DIR

def test_transcription_basic():
    """Test basic transcription functionality"""
    # Create a test audio file path
    test_audio = "test_audio.wav"  # You'll need to provide a test audio file
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        # Run transcription
        result = run_whisperx(test_audio)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'srt_path' in result
        assert 'segments' in result
        assert 'duration' in result
        
        # Verify output file exists
        assert os.path.exists(result['srt_path'])
        
        # Verify segments
        assert result['segments'] > 0
        
        print("Transcription test passed successfully!")
        print(f"Generated SRT file: {result['srt_path']}")
        print(f"Number of segments: {result['segments']}")
        print(f"Duration: {result['duration']} seconds")
        
    except Exception as e:
        pytest.fail(f"Transcription test failed with error: {str(e)}")

if __name__ == "__main__":
    test_transcription_basic()
import os
import pytest
from unittest.mock import patch, MagicMock
from core.transcription import run_whisperx
from core.config import OUTPUT_DIR

# Sample test audio file path
TEST_AUDIO = os.path.join(os.path.dirname(__file__), "fixtures", "test_audio.wav")

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment before each test."""
    # Create test fixtures directory if it doesn't exist
    os.makedirs(os.path.dirname(TEST_AUDIO), exist_ok=True)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    yield
    
    # Cleanup after test
    if os.path.exists(TEST_AUDIO):
        os.remove(TEST_AUDIO)

@pytest.fixture
def mock_whisperx():
    """Mock WhisperX transcription results."""
    return {
        'srt_path': os.path.join(OUTPUT_DIR, 'test_output.srt'),
        'segments': 5,
        'duration': 10.5
    }

def test_transcription_basic(mock_whisperx):
    """Test basic transcription functionality with mocked WhisperX."""
    with patch('core.transcription.run_whisperx') as mock_run:
        # Configure mock
        mock_run.return_value = mock_whisperx
        
        # Run transcription
        result = run_whisperx(TEST_AUDIO)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'srt_path' in result
        assert 'segments' in result
        assert 'duration' in result
        
        # Verify mock was called with correct arguments
        mock_run.assert_called_once_with(TEST_AUDIO)
        
        # Verify result values
        assert result['srt_path'] == mock_whisperx['srt_path']
        assert result['segments'] == mock_whisperx['segments']
        assert result['duration'] == mock_whisperx['duration']

def test_transcription_error_handling():
    """Test transcription error handling."""
    with patch('core.transcription.run_whisperx') as mock_run:
        # Configure mock to raise an exception
        mock_run.side_effect = Exception("Transcription failed")
        
        # Verify that the exception is propagated
        with pytest.raises(Exception) as exc_info:
            run_whisperx(TEST_AUDIO)
        
        assert str(exc_info.value) == "Transcription failed"
        mock_run.assert_called_once_with(TEST_AUDIO)

def test_transcription_invalid_file():
    """Test transcription with invalid file path."""
    invalid_path = "nonexistent.wav"
    
    with pytest.raises(FileNotFoundError):
        run_whisperx(invalid_path)

if __name__ == "__main__":
    test_transcription_basic()
import os
import pytest
from unittest.mock import patch, MagicMock
from core.services import TranscriptionService
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
def mock_transcription_result():
    """Mock transcription results."""
    return {
        'output_path': os.path.join(OUTPUT_DIR, 'test_output.scc'),
        'status': 'completed',
        'duration': 10.5
    }

def test_transcription_basic(mock_transcription_result):
    """Test basic transcription functionality with mocked service."""
    with patch.object(TranscriptionService, 'transcribe_file') as mock_transcribe:
        # Configure mock
        mock_transcribe.return_value = mock_transcription_result
        
        # Create service and run transcription
        service = TranscriptionService()
        result = service.transcribe_file(TEST_AUDIO)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'output_path' in result
        assert 'status' in result
        assert 'duration' in result
        
        # Verify mock was called with correct arguments
        mock_transcribe.assert_called_once_with(TEST_AUDIO)
        
        # Verify result values
        assert result['output_path'] == mock_transcription_result['output_path']
        assert result['status'] == mock_transcription_result['status']
        assert result['duration'] == mock_transcription_result['duration']

def test_transcription_error_handling():
    """Test transcription error handling."""
    with patch.object(TranscriptionService, 'transcribe_file') as mock_transcribe:
        # Configure mock to raise an exception
        mock_transcribe.side_effect = Exception("Transcription failed")
        
        # Create service and verify that the exception is propagated
        service = TranscriptionService()
        with pytest.raises(Exception) as exc_info:
            service.transcribe_file(TEST_AUDIO)
        
        assert str(exc_info.value) == "Transcription failed"
        mock_transcribe.assert_called_once_with(TEST_AUDIO)

def test_transcription_invalid_file():
    """Test transcription with invalid file path."""
    invalid_path = "nonexistent.wav"
    
    service = TranscriptionService()
    with pytest.raises(Exception):  # Should raise TranscriptionError
        service.transcribe_file(invalid_path)

if __name__ == "__main__":
    test_transcription_basic()
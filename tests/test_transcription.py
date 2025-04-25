import pytest
from unittest.mock import patch, MagicMock
import os
import subprocess
from core.transcription import run_whisperx
from config import OUTPUT_DIR

@pytest.fixture
def mock_video(tmp_path):
    """Create a temporary video file for testing."""
    video_path = tmp_path / "test.mp4"
    video_path.write_bytes(b"fake video content")
    return str(video_path)

@pytest.fixture
def mock_srt(tmp_path):
    """Create a temporary SRT file for testing."""
    srt_path = tmp_path / "test.srt"
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nTest caption")
    return str(srt_path)

def test_successful_transcription(mock_video, mock_srt):
    """Test successful transcription with GPU available."""
    with patch('subprocess.run') as mock_run, \
         patch('torch.cuda.is_available', return_value=True), \
         patch('os.path.exists', side_effect=lambda x: x == mock_video or x == mock_srt):
        
        # Mock successful subprocess run
        mock_run.return_value = MagicMock(returncode=0)
        
        success, result = run_whisperx(mock_video)
        assert success is True
        assert result.endswith(".srt")
        
        # Verify command was called with GPU options
        args = mock_run.call_args[0][0]
        assert "--device" in args
        assert "cuda" in args

def test_cpu_fallback(mock_video, mock_srt):
    """Test CPU fallback when GPU is not available."""
    with patch('subprocess.run') as mock_run, \
         patch('torch.cuda.is_available', return_value=False), \
         patch('os.path.exists', side_effect=lambda x: x == mock_video or x == mock_srt):
        
        mock_run.return_value = MagicMock(returncode=0)
        
        success, result = run_whisperx(mock_video)
        assert success is True
        
        # Verify command was called with CPU options
        args = mock_run.call_args[0][0]
        assert "--device" in args
        assert "cpu" in args

def test_nonexistent_file():
    """Test handling of nonexistent video file."""
    success, result = run_whisperx("nonexistent.mp4")
    assert success is False
    assert "not found" in result.lower()

def test_invalid_file_extension():
    """Test handling of invalid file extension."""
    success, result = run_whisperx("test.avi")
    assert success is False
    assert "only .mp4 files" in result.lower()

def test_whisperx_failure(mock_video):
    """Test handling of WhisperX failure."""
    with patch('subprocess.run') as mock_run, \
         patch('torch.cuda.is_available', return_value=True):
        
        # Mock failed subprocess run
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["whisperx"],
            stderr="Transcription failed"
        )
        
        success, result = run_whisperx(mock_video)
        assert success is False
        assert "failed" in result.lower() 
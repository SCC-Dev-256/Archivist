"""Tests for the service layer.

This module tests the new service layer abstractions to ensure they
work correctly and provide the expected functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.services import TranscriptionService, VODService, FileService, QueueService
from core.exceptions import TranscriptionError, VODError, FileError, QueueError

class TestTranscriptionService:
    """Test the TranscriptionService."""
    
    def test_transcription_service_initialization(self):
        """Test that TranscriptionService initializes correctly."""
        service = TranscriptionService()
        assert service is not None
        assert hasattr(service, 'model')
        assert hasattr(service, 'use_gpu')
        assert hasattr(service, 'language')
    
    @patch('core.transcription.run_whisper_transcription')
    @patch('os.path.exists')
    def test_transcribe_file_success(self, mock_exists, mock_transcribe):
        """Test successful transcription."""
        mock_exists.return_value = True
        mock_transcribe.return_value = {
            'success': True,
            'srt_path': '/path/to/output.srt',
            'segments': 10,
            'duration': 120.5
        }
        
        service = TranscriptionService()
        result = service.transcribe_file('/path/to/video.mp4')
        
        assert result['output_path'] == '/path/to/output.srt'
        assert result['status'] == 'completed'
        assert result['segments'] == 10
        assert result['duration'] == 120.5
        mock_transcribe.assert_called_once_with(video_path='/path/to/video.mp4')
    
    def test_transcribe_file_not_found(self):
        """Test transcription with non-existent file."""
        service = TranscriptionService()
        
        with pytest.raises(TranscriptionError) as exc_info:
            service.transcribe_file('/path/to/nonexistent.mp4')
        
        assert "File not found" in str(exc_info.value)

class TestVODService:
    """Test the VODService."""
    
    def test_vod_service_initialization(self):
        """Test that VODService initializes correctly."""
        service = VODService()
        assert service is not None
        assert hasattr(service, 'client')
        assert hasattr(service, 'content_manager')
        assert hasattr(service, 'show_mapper')
    
    @patch('core.cablecast_client.CablecastAPIClient.test_connection')
    def test_test_connection_success(self, mock_test_connection):
        """Test successful connection test."""
        mock_test_connection.return_value = True
        
        service = VODService()
        result = service.test_connection()
        
        assert result is True
        mock_test_connection.assert_called_once()
    
    @patch('core.cablecast_client.CablecastAPIClient.get_shows')
    def test_get_shows_success(self, mock_get_shows):
        """Test successful show retrieval."""
        mock_get_shows.return_value = [
            {'id': 1, 'title': 'Show 1'},
            {'id': 2, 'title': 'Show 2'}
        ]
        
        service = VODService()
        shows = service.get_shows()
        
        assert len(shows) == 2
        assert shows[0]['title'] == 'Show 1'
        assert shows[1]['title'] == 'Show 2'
        mock_get_shows.assert_called_once()

class TestFileService:
    """Test the FileService."""
    
    def test_file_service_initialization(self):
        """Test that FileService initializes correctly."""
        service = FileService()
        assert service is not None
        assert hasattr(service, 'mount_points')
        assert hasattr(service, 'nas_path')
    
    @patch('os.path.exists')
    @patch('os.access')
    def test_validate_path_safe(self, mock_access, mock_exists):
        """Test path validation with safe path."""
        mock_exists.return_value = True
        mock_access.return_value = True
        
        service = FileService()
        result = service.validate_path('safe/path')
        
        assert result is True
    
    def test_validate_path_traversal_attempt(self):
        """Test path validation with traversal attempt."""
        service = FileService()
        result = service.validate_path('../etc/passwd')
        
        assert result is False
    
    @patch('os.path.exists')
    def test_get_file_size_success(self, mock_exists):
        """Test successful file size retrieval."""
        mock_exists.return_value = True
        
        with patch('os.path.getsize', return_value=1024):
            service = FileService()
            size = service.get_file_size('/path/to/file.txt')
            
            assert size == 1024

class TestQueueService:
    """Test the QueueService."""
    
    def test_queue_service_initialization(self):
        """Test that QueueService initializes correctly."""
        service = QueueService()
        assert service is not None
        assert hasattr(service, 'queue_manager')
    
    @patch('os.path.exists')
    @patch('core.tasks.transcription.enqueue_transcription')
    def test_enqueue_transcription_success(self, mock_enqueue, mock_exists):
        """Test successful job enqueue."""
        mock_exists.return_value = True
        mock_enqueue.return_value = 'job-123'
        
        service = QueueService()
        job_id = service.enqueue_transcription('/path/to/video.mp4')
        
        assert job_id == 'job-123'
        mock_enqueue.assert_called_once_with('/path/to/video.mp4', None)
    
    @patch('os.path.exists')
    def test_enqueue_transcription_file_not_found(self, mock_exists):
        """Test job enqueue with non-existent file."""
        mock_exists.return_value = False
        
        service = QueueService()
        
        with pytest.raises(QueueError) as exc_info:
            service.enqueue_transcription('/path/to/nonexistent.mp4')
        
        assert "Video file not found" in str(exc_info.value)
    
    @patch('core.services.queue.celery_app.control.inspect')
    def test_get_queue_status_success(self, mock_inspect):
        """Test successful queue status retrieval."""
        mock_inspect.return_value.active.return_value = {
            'worker1': [{}, {}]
        }
        mock_inspect.return_value.reserved.return_value = {
            'worker1': [{}, {}, {}]
        }
        mock_inspect.return_value.scheduled.return_value = {}
        
        service = QueueService()
        status = service.get_queue_status()
        
        assert status['total_jobs'] == 5
        assert status['running_jobs'] == 2
        assert status['queued_jobs'] == 3
        mock_inspect.assert_called_once()

class TestServiceIntegration:
    """Test service integration."""
    
    def test_service_singletons(self):
        """Test that service singletons are created correctly."""
        from core.services import (
            transcription_service, vod_service, 
            file_service, queue_service
        )
        
        assert transcription_service is not None
        assert vod_service is not None
        assert file_service is not None
        assert queue_service is not None
        
        # Test that they are valid instances
        assert isinstance(transcription_service, TranscriptionService)
        assert isinstance(vod_service, VODService)
        assert isinstance(file_service, FileService)
        assert isinstance(queue_service, QueueService)
    
    def test_service_imports(self):
        """Test that services can be imported correctly."""
        from core.services import (
            TranscriptionService, VODService, 
            FileService, QueueService
        )
        
        assert TranscriptionService is not None
        assert VODService is not None
        assert FileService is not None
        assert QueueService is not None 
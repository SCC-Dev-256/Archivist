"""Tests for the service layer.

This module tests the new service layer abstractions to ensure they
work correctly and provide the expected functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.services import TranscriptionService, VODService, FileService, QueueService
from core.exceptions import TranscriptionError, VODError, FileError, QueueError
from core.config import OUTPUT_DIR
import os

class TestTranscriptionService:
    """Test the TranscriptionService."""
    
    def test_transcription_service_initialization(self):
        """Test that TranscriptionService initializes correctly."""
        service = TranscriptionService()
        assert service is not None
        assert hasattr(service, 'model')
        assert hasattr(service, 'use_gpu')
        assert hasattr(service, 'language')
    
    @patch('core.services.transcription.TranscriptionService._transcribe_with_faster_whisper')
    @patch('os.path.exists')
    def test_transcribe_file_success(self, mock_exists, mock_transcribe):
        """Test successful transcription."""
        mock_exists.return_value = True
        mock_transcribe.return_value = {
            'output_path': '/path/to/output.srt',
            'segments': 10,
            'duration': 120.5,
            'language': 'en',
            'model_used': 'base'
        }
        
        service = TranscriptionService()
        result = service.transcribe_file('/path/to/video.mp4')
        
        assert result['output_path'] == '/path/to/output.srt'
        assert result['status'] == 'completed'
        assert result['segments'] == 10
        assert result['duration'] == 120.5
        assert result['language'] == 'en'
        assert result['model_used'] == 'base'
        mock_transcribe.assert_called_once_with('/path/to/video.mp4')
    
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
        """Test path validation for safe paths."""
        mock_exists.return_value = True
        mock_access.return_value = True
        
        service = FileService()
        result = service.validate_path('/mnt/nas/safe/path')
        
        assert result is True
        mock_exists.assert_called_once_with('/mnt/nas/safe/path')
        mock_access.assert_called_once_with('/mnt/nas/safe/path', os.R_OK)
    
    def test_validate_path_traversal_attempt(self):
        """Test path validation rejects directory traversal attempts."""
        service = FileService()
        
        with pytest.raises(FileError):
            service.validate_path('/mnt/nas/../../../etc/passwd')
    
    @patch('os.path.exists')
    def test_get_file_size_success(self, mock_exists):
        """Test successful file size retrieval."""
        mock_exists.return_value = True
        
        service = FileService()
        with patch('os.path.getsize', return_value=1024):
            size = service.get_file_size('/path/to/file.mp4')
            assert size == 1024

class TestQueueService:
    """Test the QueueService."""
    
    def test_queue_service_initialization(self):
        """Test that QueueService initializes correctly."""
        service = QueueService()
        assert service is not None
        assert hasattr(service, 'celery_app')
    
    @patch('os.path.exists')
    @patch('core.services.queue.run_whisper_transcription.delay')
    def test_enqueue_transcription_success(self, mock_enqueue, mock_exists):
        """Test successful transcription enqueue."""
        mock_exists.return_value = True
        mock_job = MagicMock()
        mock_job.id = 'job-123'
        mock_enqueue.return_value = mock_job
        
        service = QueueService()
        result = service.enqueue_transcription('/path/to/video.mp4')
        
        assert result == 'job-123'
        mock_enqueue.assert_called_once_with('/path/to/video.mp4')
    
    @patch('os.path.exists')
    def test_enqueue_transcription_file_not_found(self, mock_exists):
        """Test transcription enqueue with non-existent file."""
        mock_exists.return_value = False
        
        service = QueueService()
        
        with pytest.raises(FileError) as exc_info:
            service.enqueue_transcription('/path/to/nonexistent.mp4')
        
        assert "File not found" in str(exc_info.value)
    
    @patch('core.services.queue.celery_app.control.inspect')
    def test_get_queue_status_success(self, mock_inspect):
        """Test successful queue status retrieval."""
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        
        # Mock the inspect methods to match actual implementation
        mock_inspector.stats.return_value = {'worker1': {'pid': 12345}}
        mock_inspector.ping.return_value = {'worker1': 'pong'}
        
        service = QueueService()
        status = service.get_queue_status()
        
        # Check for the actual keys returned by the implementation
        assert 'active_workers' in status
        assert 'total_workers' in status
        assert 'worker_status' in status
        assert 'queue_length' in status
        assert 'completed_jobs' in status
        assert 'status' in status
        assert status['active_workers'] == 1
        assert status['total_workers'] == 1
        assert status['worker_status'] == 'healthy'
        assert status['status'] == 'operational'

class TestServiceIntegration:
    """Test service integration and singletons."""
    
    def test_service_singletons(self):
        """Test that service singletons work correctly."""
        from core.services import transcription_service, vod_service, file_service, queue_service
        
        assert transcription_service is not None
        assert vod_service is not None
        assert file_service is not None
        assert queue_service is not None
        
        # Test that they're the same instances
        assert transcription_service is TranscriptionService()
        assert vod_service is VODService()
        assert file_service is FileService()
        assert queue_service is QueueService()
    
    def test_service_imports(self):
        """Test that all services can be imported."""
        from core.services import (
            TranscriptionService, VODService, FileService, QueueService,
            transcription_service, vod_service, file_service, queue_service
        )
        
        assert TranscriptionService is not None
        assert VODService is not None
        assert FileService is not None
        assert QueueService is not None 
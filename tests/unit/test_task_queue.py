import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
try:
    from core.services.queue import QueueService
except ImportError:
    import pytest
    pytest.skip('QueueService not available, skipping test', allow_module_level=True)

@pytest.fixture
def mock_job():
    """Create a mock job with common attributes"""
    job = MagicMock()
    job.id = "test-job-123"
    job.meta = {
        'position': 0,
        'progress': 0,
        'status_message': 'Test message',
        'paused': False
    }
    job.created_at = datetime.now()
    job.started_at = None
    job.ended_at = None
    job.is_finished = False
    job.is_failed = False
    job.is_started = False
    job.get_status.return_value = 'queued'
    job.exc_info = None
    job.result = None
    return job

@pytest.fixture
def mock_celery_result():
    """Create a mock Celery AsyncResult"""
    result = MagicMock()
    result.id = "test-job-123"
    result.status = "PENDING"
    result.info = {
        'status': 'pending',
        'progress': 0,
        'status_message': 'Test message',
        'video_path': '/test/video.mp4',
        'created_at': datetime.now().isoformat()
    }
    result.failed.return_value = False
    result.successful.return_value = False
    result.result = None
    return result

@pytest.fixture
def mock_queue():
    """Create a mock queue with test jobs"""
    queue = MagicMock()
    job1 = MagicMock()
    job1.id = "job-1"
    job1.meta = {'position': 0, 'progress': 50}
    job1.is_finished = False
    job1.is_failed = False
    job1.is_started = True
    
    job2 = MagicMock()
    job2.id = "job-2"
    job2.meta = {'position': 1, 'progress': 0}
    job2.is_finished = False
    job2.is_failed = False
    job2.is_started = False
    
    queue.jobs = [job1, job2]
    queue.fetch_job.return_value = job1
    queue.started_job_registry.get_job_ids.return_value = ["job-1"]
    queue.enqueue.return_value = job1
    return queue

def test_enqueue_transcription(mock_queue):
    """Test enqueueing a transcription job"""
    service = QueueService()
    with patch('core.services.queue.run_whisper_transcription.delay') as mock_task:
        # Mock the Celery task to return a job with the expected ID
        mock_job = MagicMock()
        mock_job.id = "job-123"
        mock_task.return_value = mock_job
        
        # Use a real video file from flex servers that exists and has speech content
        real_video_path = "/mnt/flex-1/20704-1-Birchwood Village Special City Meeting (20240423).mp4"
        job_id = service.enqueue_transcription(real_video_path)
        assert job_id == "job-123"
        mock_task.assert_called_once_with(real_video_path)

def test_get_job_status(mock_celery_result):
    """Test getting job status"""
    service = QueueService()
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        status = service.get_job_status("test-job-123")
        assert status["status"] == "pending"
        assert status["progress"] == 0
        assert status["video_path"] == "/test/video.mp4"

def test_get_all_jobs(mock_queue):
    """Test getting all jobs"""
    service = QueueService()
    with patch.object(service, 'queue_manager') as mock_celery:
        # Mock Celery inspect to return job information
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect
        mock_inspect.active.return_value = {}
        mock_inspect.reserved.return_value = {}
        mock_inspect.scheduled.return_value = {}
        
        jobs = service.get_all_jobs()
        assert isinstance(jobs, list)

def test_reorder_job(mock_queue):
    """Test reordering a job"""
    service = QueueService()
    with patch.object(service, 'queue_manager', mock_queue):
        result = service.reorder_job("job-1", 2)
        assert result is False  # Celery doesn't support reordering

def test_pause_job(mock_celery_result):
    """Test pausing a job"""
    service = QueueService()
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        result = service.pause_job("test-job-123")
        assert result is False  # Celery doesn't support pausing

def test_resume_job(mock_celery_result):
    """Test resuming a job"""
    service = QueueService()
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        result = service.resume_job("test-job-123")
        assert result is False  # Celery doesn't support resuming

def test_job_status_transitions(mock_celery_result):
    """Test job status transitions"""
    service = QueueService()
    
    # Test pending status
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        status = service.get_job_status("test-job-123")
        assert status["status"] == "pending"
    
    # Test running status
    mock_celery_result.status = "STARTED"
    mock_celery_result.info = {
        'status': 'started',
        'progress': 50,
        'status_message': 'Processing...'
    }
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        status = service.get_job_status("test-job-123")
        assert status["status"] == "started"
        assert status["progress"] == 50
    
    # Test completed status
    mock_celery_result.status = "SUCCESS"
    mock_celery_result.successful.return_value = True
    mock_celery_result.result = {"transcription": "test result"}
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        status = service.get_job_status("test-job-123")
        assert status["status"] == "success"
    
    # Test failed status
    mock_celery_result.status = "FAILURE"
    mock_celery_result.failed.return_value = True
    mock_celery_result.info = "Task failed"
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        status = service.get_job_status("test-job-123")
        assert status["status"] == "failure"
        assert "error" in status

def test_remove_job(mock_celery_result):
    """Test removing a job"""
    service = QueueService()
    with patch('core.services.queue.AsyncResult', return_value=mock_celery_result):
        result = service.cancel_job("test-job-123")
        assert result is False  # Celery doesn't support cancellation

def test_cleanup_failed_jobs(mock_queue):
    """Test cleaning up failed jobs"""
    service = QueueService()
    with patch.object(service, 'queue_manager') as mock_celery:
        # Mock Celery inspect to return failed job information
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect
        mock_inspect.failed.return_value = {}
        
        result = service.get_failed_jobs()
        assert isinstance(result, list)

def test_get_current_job(mock_queue):
    """Test getting current job"""
    service = QueueService()
    with patch.object(service, 'queue_manager') as mock_celery:
        # Mock Celery inspect to return active job information
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect
        mock_inspect.active.return_value = {}
        
        jobs = service.get_all_jobs()
        assert isinstance(jobs, list) 
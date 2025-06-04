import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from core.task_queue import (
    enqueue_transcription,
    get_job_status,
    get_all_jobs,
    reorder_job,
    stop_job,
    pause_job,
    resume_job,
    remove_job,
    cleanup_failed_jobs,
    get_current_job,
    queue_manager
)

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
    with patch.object(queue_manager, '_queue', mock_queue):
        job_id = enqueue_transcription("/path/to/video.mp4")
        assert job_id == "job-1"
        mock_queue.enqueue.assert_called_once()

def test_get_job_status(mock_job):
    """Test getting job status"""
    with patch.object(queue_manager, '_queue') as mock_queue:
        mock_queue.fetch_job.return_value = mock_job
        status = get_job_status("test-job-123")
        assert status["status"] == "queued"
        assert status["progress"] == 0
        assert status["position"] == 0

def test_get_all_jobs(mock_queue):
    """Test getting all jobs"""
    with patch.object(queue_manager, '_queue', mock_queue):
        jobs = get_all_jobs()
        assert len(jobs) == 2
        assert jobs[0]["id"] == "job-1"
        assert jobs[1]["id"] == "job-2"

def test_reorder_job(mock_queue):
    """Test reordering a job"""
    with patch.object(queue_manager, '_queue', mock_queue):
        result = reorder_job("job-1", 2)
        assert result is True
        mock_queue.fetch_job.return_value.meta["position"] = 2
        mock_queue.fetch_job.return_value.save_meta.assert_called()

def test_stop_job(mock_job):
    """Test stopping a job"""
    with patch.object(queue_manager, '_queue') as mock_queue:
        mock_queue.fetch_job.return_value = mock_job
        mock_job.get_status.return_value = 'queued'
        
        result = stop_job("test-job-123")
        assert result is True
        assert mock_job.meta["status"] == "cancelled"

def test_pause_job(mock_job):
    """Test pausing a job"""
    with patch.object(queue_manager, '_queue') as mock_queue:
        mock_queue.fetch_job.return_value = mock_job
        mock_job.get_status.return_value = 'started'
        
        result = pause_job("test-job-123")
        assert result is True
        assert mock_job.meta["paused"] is True

def test_resume_job(mock_job):
    """Test resuming a job"""
    with patch.object(queue_manager, '_queue') as mock_queue:
        mock_queue.fetch_job.return_value = mock_job
        mock_job.meta["paused"] = True
        
        result = resume_job("test-job-123")
        assert result is True
        assert mock_job.meta["paused"] is False

def test_remove_job(mock_job):
    """Test removing a job"""
    with patch.object(queue_manager, '_queue') as mock_queue:
        mock_queue.fetch_job.return_value = mock_job
        
        result = remove_job("test-job-123")
        assert result is True
        mock_job.delete.assert_called_once()

def test_cleanup_failed_jobs(mock_queue):
    """Test cleaning up failed jobs"""
    with patch.object(queue_manager, '_queue', mock_queue):
        # Mock a failed job that's older than 24 hours
        old_job = MagicMock()
        old_job.ended_at = datetime.now() - timedelta(days=2)
        mock_queue.fetch_job.return_value = old_job
        mock_queue.failed_job_registry.get_job_ids.return_value = ["failed-job-1"]
        mock_queue.failed_job_registry.remove = MagicMock()
        
        cleanup_failed_jobs()
        mock_queue.failed_job_registry.remove.assert_called_with("failed-job-1")

def test_get_current_job(mock_queue):
    """Test getting current job"""
    with patch.object(queue_manager, '_queue', mock_queue):
        current_job = get_current_job()
        assert current_job is not None
        assert current_job.id == "job-1"

def test_job_status_transitions(mock_job):
    """Test job status transitions"""
    with patch.object(queue_manager, '_queue') as mock_queue:
        mock_queue.fetch_job.return_value = mock_job
        
        # Test queued status
        mock_job.is_finished = False
        mock_job.is_failed = False
        mock_job.is_started = False
        status = get_job_status("test-job-123")
        assert status["status"] == "queued"
        
        # Test processing status
        mock_job.is_started = True
        status = get_job_status("test-job-123")
        assert status["status"] == "processing"
        
        # Test paused status
        mock_job.meta["paused"] = True
        status = get_job_status("test-job-123")
        assert status["status"] == "paused"
        
        # Test completed status
        mock_job.is_finished = True
        mock_job.result = {"transcription": "test"}
        status = get_job_status("test-job-123")
        assert status["status"] == "completed"
        assert "transcription" in status
        
        # Test failed status
        mock_job.is_finished = False
        mock_job.is_failed = True
        mock_job.exc_info = "Test error"
        status = get_job_status("test-job-123")
        assert status["status"] == "failed"
        assert "error" in status 
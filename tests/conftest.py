import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
try:
    from core.app import create_app
except ImportError:  # pragma: no cover - fallback for missing deps
    from unittest.mock import MagicMock

    def create_app(*args, **kwargs):
        return MagicMock()

try:
    from core.logging_config import setup_logging
except ImportError:
    import logging

    def setup_logging(*args, **kwargs):
        """Fallback logging configuration for tests."""
        level = logging.DEBUG if kwargs.get("log_level") == "DEBUG" or kwargs.get("testing") else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            stream=sys.stdout,
        )

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set test environment variables
os.environ["TESTING"] = "true"
os.environ["NAS_PATH"] = "/tmp/test_nas"
os.environ["OUTPUT_DIR"] = "/tmp/test_output"
os.environ["HF_HOME"] = "/tmp/test_hf_home"  # Set HuggingFace cache directory for tests
os.environ["TRANSFORMERS_CACHE"] = "/tmp/test_transformers_cache"  # Set transformers cache directory
os.environ["REDIS_URL"] = "redis://localhost:6379/0"  # Set Redis URL for tests

# Create test directories
os.makedirs(os.environ["NAS_PATH"], exist_ok=True)
os.makedirs(os.environ["OUTPUT_DIR"], exist_ok=True)
os.makedirs(os.environ["HF_HOME"], exist_ok=True)
os.makedirs(os.environ["TRANSFORMERS_CACHE"], exist_ok=True)

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables and logging"""
    # Set testing environment
    os.environ["TESTING"] = "true"
    
    # Configure minimal logging for tests
    setup_logging(testing=True, log_level="DEBUG")
    
    yield
    
    # Cleanup
    os.environ.pop("TESTING", None)

@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return app.test_client()

@pytest.fixture(autouse=True)
def mock_heavy_imports(monkeypatch):
    """Mock heavy imports to speed up tests and prevent PyTorch loading"""
    
    # Use sys.modules to mock modules before they're imported
    import sys
    from unittest.mock import MagicMock
    
    # Mock PyTorch and transformers
    mock_torch = MagicMock()
    mock_transformers = MagicMock()
    mock_faster_whisper = MagicMock()

    # Mock WhisperModel
    mock_whisper_model = MagicMock()
    mock_whisper_model.transcribe.return_value = ([], {'language': 'en'})
    mock_faster_whisper.WhisperModel.return_value = mock_whisper_model

    # Mock transformers pipeline
    mock_pipeline = MagicMock()
    mock_transformers.pipeline.return_value = mock_pipeline

    # Mock Celery and related modules
    mock_celery = MagicMock()
    mock_celery_app = MagicMock()
    mock_celery_app.control.inspect.return_value = MagicMock()
    mock_celery.Celery.return_value = mock_celery_app
    
    # Mock Celery result
    mock_async_result = MagicMock()
    mock_async_result.status = "PENDING"
    mock_async_result.info = {}
    mock_async_result.failed.return_value = False
    mock_async_result.successful.return_value = False
    mock_celery.result.AsyncResult.return_value = mock_async_result

    # Mock tasks module
    mock_tasks = MagicMock()
    mock_tasks.celery_app = mock_celery_app
    mock_tasks.get_celery_app.return_value = mock_celery_app
    
    # Mock transcription tasks
    mock_transcription_task = MagicMock()
    mock_transcription_task.delay.return_value = mock_async_result
    mock_tasks.transcription = MagicMock()
    mock_tasks.transcription.run_whisper_transcription = mock_transcription_task

    # Mock services module
    mock_services = MagicMock()
    mock_queue_service = MagicMock()
    mock_transcription_service = MagicMock()
    mock_vod_service = MagicMock()
    mock_file_service = MagicMock()
    
    # Mock service classes
    mock_services.QueueService = MagicMock(return_value=mock_queue_service)
    mock_services.TranscriptionService = MagicMock(return_value=mock_transcription_service)
    mock_services.VODService = MagicMock(return_value=mock_vod_service)
    mock_services.FileService = MagicMock(return_value=mock_file_service)
    
    # Mock service getter functions
    mock_services.get_queue_service = MagicMock(return_value=mock_queue_service)
    mock_services.get_transcription_service = MagicMock(return_value=mock_transcription_service)
    mock_services.get_vod_service = MagicMock(return_value=mock_vod_service)
    mock_services.get_file_service = MagicMock(return_value=mock_file_service)

    # Apply mocks using sys.modules
    sys.modules['torch'] = mock_torch
    sys.modules['transformers'] = mock_transformers
    sys.modules['faster_whisper'] = mock_faster_whisper
    sys.modules['celery'] = mock_celery
    sys.modules['core.tasks'] = mock_tasks
    sys.modules['core.tasks.transcription'] = mock_tasks.transcription
    sys.modules['core.services'] = mock_services
    
    # Mock specific submodules
    mock_torch.cuda = MagicMock()
    mock_torch.device = MagicMock()
    mock_transformers.pipeline = mock_pipeline
    mock_transformers.AutoTokenizer = MagicMock()
    mock_transformers.AutoModelForCausalLM = MagicMock()
    
    yield
    
    # Cleanup
    for module_name in ['torch', 'transformers', 'faster_whisper', 'celery', 'core.tasks', 'core.tasks.transcription', 'core.services']:
        sys.modules.pop(module_name, None)

@pytest.fixture(autouse=True)
def mock_transformers(monkeypatch):
    """Mock transformers to avoid downloading models during tests"""
    import transformers
    from unittest.mock import MagicMock
    
    # Mock the AutoModelForCausalLM and AutoTokenizer
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    
    monkeypatch.setattr(transformers, "AutoModelForCausalLM", MagicMock(return_value=mock_model))
    monkeypatch.setattr(transformers, "AutoTokenizer", MagicMock(return_value=mock_tokenizer))

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Mock Redis connection for tests"""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    
    # Mock redis.from_url
    monkeypatch.setattr("redis.from_url", MagicMock(return_value=mock_redis))
    
    # Mock RQ Queue
    mock_queue = MagicMock()
    monkeypatch.setattr("rq.Queue", MagicMock(return_value=mock_queue)) 
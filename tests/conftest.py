
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Ensure project root is on the Python path **before** importing application modules
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.app import create_app
from core.logging_config import setup_logging

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
    """Provide a fake Redis module so tests run without the real dependency."""
    mock_instance = MagicMock()
    mock_instance.ping.return_value = True

    import types, sys

    fake_redis = types.ModuleType("redis")
    fake_redis.from_url = MagicMock(return_value=mock_instance)
    monkeypatch.setitem(sys.modules, "redis", fake_redis)
    
    # Mock RQ Queue
    mock_queue = MagicMock()
    monkeypatch.setattr("rq.Queue", MagicMock(return_value=mock_queue)) 
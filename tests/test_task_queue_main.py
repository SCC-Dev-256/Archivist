try:
    from core.services.queue import QueueService
except ImportError:
    import pytest
    pytest.skip('QueueService not available, skipping test', allow_module_level=True) 
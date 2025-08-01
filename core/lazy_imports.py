"""
Lazy import utilities for core modules.

This module provides lazy loading capabilities to prevent heavy imports
from causing hanging during module initialization. It allows deferring
the import of heavy modules until they are actually needed.

Example:
    >>> from core.lazy_imports import get_celery_app
    >>> celery_app = get_celery_app()  # Only imported when called
"""

import importlib
import time
from typing import Any, Optional, Callable
from loguru import logger

class LazyModule:
    """Lazy loading wrapper for modules."""
    
    def __init__(self, module_name: str, timeout: int = 5):
        self.module_name = module_name
        self.timeout = timeout
        self._module: Optional[Any] = None
        self._import_time: Optional[float] = None
        self._import_error: Optional[str] = None
    
    def __getattr__(self, name: str):
        """Lazy load the module and return the requested attribute."""
        if self._module is None:
            self._import_module()
        
        if self._module is None:
            raise ImportError(f"Failed to import {self.module_name}: {self._import_error}")
        
        return getattr(self._module, name)
    
    def _import_module(self):
        """Import the module with timeout protection."""
        start_time = time.time()
        
        try:
            logger.debug(f"Lazy importing {self.module_name}")
            self._module = importlib.import_module(self.module_name)
            self._import_time = time.time() - start_time
            logger.debug(f"Successfully imported {self.module_name} in {self._import_time:.3f}s")
            
        except Exception as e:
            self._import_error = str(e)
            self._import_time = time.time() - start_time
            logger.error(f"Failed to import {self.module_name} after {self._import_time:.3f}s: {e}")
            self._module = None
    
    def is_loaded(self) -> bool:
        """Check if the module has been loaded."""
        return self._module is not None
    
    def get_import_time(self) -> Optional[float]:
        """Get the time it took to import the module."""
        return self._import_time
    
    def get_import_error(self) -> Optional[str]:
        """Get the import error if any."""
        return self._import_error

class LazyService:
    """Lazy loading wrapper for service instances."""
    
    def __init__(self, service_class_path: str, timeout: int = 5):
        self.service_class_path = service_class_path
        self.timeout = timeout
        self._instance: Optional[Any] = None
        self._init_time: Optional[float] = None
        self._init_error: Optional[str] = None
    
    def get_instance(self) -> Any:
        """Get the service instance, creating it if necessary."""
        if self._instance is None:
            self._create_instance()
        
        if self._instance is None:
            raise RuntimeError(f"Failed to create service instance: {self._init_error}")
        
        return self._instance
    
    def _create_instance(self):
        """Create the service instance with timeout protection."""
        start_time = time.time()
        
        try:
            logger.debug(f"Creating service instance: {self.service_class_path}")
            
            # Parse the class path (e.g., "core.services.TranscriptionService")
            module_path, class_name = self.service_class_path.rsplit('.', 1)
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the class
            service_class = getattr(module, class_name)
            
            # Create the instance
            self._instance = service_class()
            
            self._init_time = time.time() - start_time
            logger.debug(f"Successfully created {self.service_class_path} in {self._init_time:.3f}s")
            
        except Exception as e:
            self._init_error = str(e)
            self._init_time = time.time() - start_time
            logger.error(f"Failed to create {self.service_class_path} after {self._init_time:.3f}s: {e}")
            self._instance = None
    
    def is_initialized(self) -> bool:
        """Check if the service has been initialized."""
        return self._instance is not None
    
    def get_init_time(self) -> Optional[float]:
        """Get the time it took to initialize the service."""
        return self._init_time
    
    def get_init_error(self) -> Optional[str]:
        """Get the initialization error if any."""
        return self._init_error

# Lazy module instances for heavy imports
tasks_module = LazyModule('core.tasks', timeout=5)
monitoring_module = LazyModule('core.monitoring.integrated_dashboard', timeout=5)
admin_ui_module = LazyModule('core.admin_ui', timeout=5)
services_module = LazyModule('core.services', timeout=5)

# Lazy service instances
transcription_service = LazyService('core.services.TranscriptionService', timeout=5)
vod_service = LazyService('core.services.VODService', timeout=5)
file_service = LazyService('core.services.FileService', timeout=5)
queue_service = LazyService('core.services.QueueService', timeout=5)

# Convenience functions for common lazy imports
def get_celery_app():
    """Get the Celery app instance."""
    return tasks_module.get_celery_app

def get_integrated_dashboard():
    """Get the IntegratedDashboard class."""
    return monitoring_module.IntegratedDashboard

def get_admin_ui():
    """Get the AdminUI class."""
    return admin_ui_module.AdminUI

def get_start_admin_ui():
    """Get the start_admin_ui function."""
    return admin_ui_module.start_admin_ui

def get_unified_queue_manager():
    """Get the UnifiedQueueManager class."""
    # This is imported from a different module
    unified_queue_module = LazyModule('core.unified_queue_manager', timeout=5)
    return unified_queue_module.UnifiedQueueManager

def get_vod_content_manager():
    """Get the VODContentManager class."""
    vod_content_module = LazyModule('core.vod_content_manager', timeout=5)
    return vod_content_module.VODContentManager

def get_transcription_service():
    """Get the transcription service instance."""
    return transcription_service.get_instance()

def get_vod_service():
    """Get the VOD service instance."""
    return vod_service.get_instance()

def get_file_service():
    """Get the file service instance."""
    return file_service.get_instance()

def get_queue_service():
    """Get the queue service instance."""
    return queue_service.get_instance()

# Health check functions
def check_lazy_imports_health() -> dict:
    """Check the health of all lazy imports."""
    health_status = {
        'modules': {},
        'services': {},
        'overall_status': 'healthy'
    }
    
    # Check modules
    for name, module in [
        ('tasks', tasks_module),
        ('monitoring', monitoring_module),
        ('admin_ui', admin_ui_module),
        ('services', services_module)
    ]:
        health_status['modules'][name] = {
            'loaded': module.is_loaded(),
            'import_time': module.get_import_time(),
            'error': module.get_import_error()
        }
        
        if module.get_import_error():
            health_status['overall_status'] = 'degraded'
    
    # Check services
    for name, service in [
        ('transcription', transcription_service),
        ('vod', vod_service),
        ('file', file_service),
        ('queue', queue_service)
    ]:
        health_status['services'][name] = {
            'initialized': service.is_initialized(),
            'init_time': service.get_init_time(),
            'error': service.get_init_error()
        }
        
        if service.get_init_error():
            health_status['overall_status'] = 'degraded'
    
    return health_status

def preload_critical_modules():
    """Preload critical modules in the background."""
    import threading
    
    def preload_module(module, name):
        """Preload a module in a separate thread."""
        try:
            logger.info(f"Preloading {name} module...")
            # Access any attribute to trigger import
            if hasattr(module, '__name__'):
                _ = module.__name__
            logger.info(f"Successfully preloaded {name} module")
        except Exception as e:
            logger.warning(f"Failed to preload {name} module: {e}")
    
    # Start preloading in background threads
    threads = []
    for name, module in [
        ('tasks', tasks_module),
        ('services', services_module)
    ]:
        thread = threading.Thread(target=preload_module, args=(module, name))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    return threads

# Export the main functions
__all__ = [
    'LazyModule',
    'LazyService',
    'get_celery_app',
    'get_integrated_dashboard',
    'get_admin_ui',
    'get_start_admin_ui',
    'get_unified_queue_manager',
    'get_vod_content_manager',
    'get_transcription_service',
    'get_vod_service',
    'get_file_service',
    'get_queue_service',
    'check_lazy_imports_health',
    'preload_critical_modules'
] 
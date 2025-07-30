"""
Health check system for core services.

This module provides comprehensive health monitoring for all core services,
including import performance, connection status, and system availability.
It helps detect and diagnose hanging issues and service failures.

Example:
    >>> from core.health_check import health_checker
    >>> status = health_checker.check_all()
    >>> print(status)
"""

import time
import threading
import socket
from typing import Dict, Any, Optional, Callable
from loguru import logger

class HealthChecker:
    """Comprehensive health checker for core services."""
    
    def __init__(self):
        self.checks = {}
        self.last_check = {}
        self.check_history = {}
        self.max_history_size = 100
    
    def register_check(self, name: str, check_func: Callable, timeout: int = 5, 
                      critical: bool = False, description: str = ""):
        """Register a health check function.
        
        Args:
            name: Name of the health check
            check_func: Function that performs the health check
            timeout: Maximum time to wait for check to complete
            critical: Whether this check is critical for system health
            description: Description of what this check does
        """
        self.checks[name] = {
            'func': check_func,
            'timeout': timeout,
            'critical': critical,
            'description': description
        }
    
    def check_service(self, name: str) -> Dict[str, Any]:
        """Check a specific service with timeout protection."""
        if name not in self.checks:
            return {
                "status": "unknown",
                "error": "Service not registered",
                "elapsed": 0,
                "timestamp": time.time()
            }
        
        check_info = self.checks[name]
        check_func = check_info['func']
        timeout = check_info['timeout']
        
        result = {
            "status": "unknown",
            "elapsed": 0,
            "timestamp": time.time(),
            "error": None,
            "details": None
        }
        
        def run_check():
            """Run the health check in a separate thread."""
            try:
                start_time = time.time()
                check_result = check_func()
                elapsed = time.time() - start_time
                
                result["status"] = "healthy"
                result["elapsed"] = elapsed
                result["details"] = check_result
                
            except Exception as e:
                result["status"] = "unhealthy"
                result["error"] = str(e)
                result["elapsed"] = time.time() - start_time
        
        # Run check in separate thread with timeout
        check_thread = threading.Thread(target=run_check)
        check_thread.daemon = True
        check_thread.start()
        
        # Wait for completion or timeout
        check_thread.join(timeout=timeout)
        
        if check_thread.is_alive():
            result["status"] = "timeout"
            result["error"] = f"Health check timed out after {timeout} seconds"
            result["elapsed"] = timeout
        
        # Store result
        self.last_check[name] = result
        
        # Add to history
        if name not in self.check_history:
            self.check_history[name] = []
        
        self.check_history[name].append(result)
        
        # Trim history if too long
        if len(self.check_history[name]) > self.max_history_size:
            self.check_history[name] = self.check_history[name][-self.max_history_size:]
        
        return result
    
    def check_all(self) -> Dict[str, Any]:
        """Check all registered services."""
        results = {}
        overall_status = "healthy"
        critical_failures = []
        
        for name in self.checks:
            result = self.check_service(name)
            results[name] = result
            
            # Check if critical service failed
            if self.checks[name]['critical'] and result['status'] != 'healthy':
                critical_failures.append(name)
                overall_status = "critical"
            elif result['status'] != 'healthy' and overall_status == "healthy":
                overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "critical_failures": critical_failures,
            "services": results,
            "timestamp": time.time(),
            "total_checks": len(results)
        }
    
    def get_service_history(self, name: str, limit: int = 10) -> list:
        """Get recent health check history for a service."""
        if name not in self.check_history:
            return []
        
        return self.check_history[name][-limit:]
    
    def get_overall_history(self, limit: int = 10) -> Dict[str, list]:
        """Get recent health check history for all services."""
        history = {}
        for name in self.checks:
            history[name] = self.get_service_history(name, limit)
        return history

# Global health checker instance
health_checker = HealthChecker()

# Core health check functions
def check_redis_connectivity():
    """Check Redis connectivity."""
    import redis
    from core.config import REDIS_HOST, REDIS_PORT, REDIS_TIMEOUT
    
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        socket_timeout=REDIS_TIMEOUT,
        socket_connect_timeout=REDIS_TIMEOUT
    )
    
    # Test basic operations
    r.ping()
    r.set('health_check', 'ok')
    r.delete('health_check')
    
    return {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "operations": ["ping", "set", "delete"]
    }

def check_database_connectivity():
    """Check database connectivity."""
    from core.database import db
    
    # Test basic query
    result = db.engine.execute("SELECT 1 as test").scalar()
    
    return {
        "test_query": result,
        "engine_info": str(db.engine)
    }

def check_file_system_access():
    """Check file system access."""
    import os
    from core.config import MOUNT_POINTS
    
    results = {}
    
    for mount_name, mount_path in MOUNT_POINTS.items():
        try:
            # Check if mount point exists and is accessible
            if os.path.exists(mount_path):
                # Try to list directory
                files = os.listdir(mount_path)
                results[mount_name] = {
                    "status": "accessible",
                    "path": mount_path,
                    "file_count": len(files)
                }
            else:
                results[mount_name] = {
                    "status": "not_found",
                    "path": mount_path
                }
        except Exception as e:
            results[mount_name] = {
                "status": "error",
                "path": mount_path,
                "error": str(e)
            }
    
    return results

def check_import_performance():
    """Check import performance for core modules."""
    import time
    import sys
    
    results = {}
    
    # Test import times for critical modules
    modules_to_test = [
        'core.exceptions',
        'core.models',
        'core.config',
        'core.tasks',
        'core.services'
    ]
    
    for module in modules_to_test:
        try:
            # Clear module cache
            if module in sys.modules:
                del sys.modules[module]
            
            start_time = time.time()
            __import__(module)
            elapsed = time.time() - start_time
            
            results[module] = {
                "import_time": elapsed,
                "status": "success"
            }
            
        except Exception as e:
            results[module] = {
                "import_time": None,
                "status": "error",
                "error": str(e)
            }
    
    return results

def check_celery_workers():
    """Check Celery worker status."""
    try:
        from core.tasks import celery_app
        
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        ping = inspect.ping()
        
        return {
            "active_workers": len(ping) if ping else 0,
            "total_workers": len(stats) if stats else 0,
            "worker_status": "healthy" if (ping and len(ping) > 0) else "unhealthy"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "worker_status": "error"
        }

def check_network_connectivity():
    """Check network connectivity to external services."""
    from core.config import CABLECAST_BASE_URL
    
    results = {}
    
    # Test Cablecast connectivity
    try:
        import requests
        from core.config import REQUEST_TIMEOUT
        
        response = requests.get(
            CABLECAST_BASE_URL,
            timeout=REQUEST_TIMEOUT,
            verify=False  # Skip SSL verification for health check
        )
        
        results['cablecast'] = {
            "status": "reachable",
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds()
        }
        
    except Exception as e:
        results['cablecast'] = {
            "status": "unreachable",
            "error": str(e)
        }
    
    return results

def check_system_resources():
    """Check system resource usage."""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "load_average": psutil.getloadavg()
    }

def check_lazy_imports():
    """Check lazy import system health."""
    try:
        from core.lazy_imports import check_lazy_imports_health
        return check_lazy_imports_health()
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

# Register all health checks
health_checker.register_check(
    "redis",
    check_redis_connectivity,
    timeout=5,
    critical=True,
    description="Check Redis connectivity and basic operations"
)

health_checker.register_check(
    "database",
    check_database_connectivity,
    timeout=5,
    critical=True,
    description="Check database connectivity and basic queries"
)

health_checker.register_check(
    "file_system",
    check_file_system_access,
    timeout=10,
    critical=False,
    description="Check file system access to mount points"
)

health_checker.register_check(
    "import_performance",
    check_import_performance,
    timeout=15,
    critical=False,
    description="Check import performance for core modules"
)

health_checker.register_check(
    "celery_workers",
    check_celery_workers,
    timeout=5,
    critical=False,
    description="Check Celery worker status and availability"
)

health_checker.register_check(
    "network_connectivity",
    check_network_connectivity,
    timeout=10,
    critical=False,
    description="Check network connectivity to external services"
)

health_checker.register_check(
    "system_resources",
    check_system_resources,
    timeout=3,
    critical=False,
    description="Check system resource usage (CPU, memory, disk)"
)

health_checker.register_check(
    "lazy_imports",
    check_lazy_imports,
    timeout=5,
    critical=False,
    description="Check lazy import system health"
)

# Convenience functions
def quick_health_check() -> Dict[str, Any]:
    """Perform a quick health check of critical services."""
    critical_checks = [name for name, info in health_checker.checks.items() 
                      if info['critical']]
    
    results = {}
    overall_status = "healthy"
    
    for name in critical_checks:
        result = health_checker.check_service(name)
        results[name] = result
        
        if result['status'] != 'healthy':
            overall_status = "unhealthy"
    
    return {
        "overall_status": overall_status,
        "services": results,
        "timestamp": time.time()
    }

def get_health_summary() -> str:
    """Get a human-readable health summary."""
    status = health_checker.check_all()
    
    summary = []
    summary.append(f"System Health: {status['overall_status'].upper()}")
    summary.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['timestamp']))}")
    summary.append(f"Total Checks: {status['total_checks']}")
    
    if status['critical_failures']:
        summary.append(f"Critical Failures: {', '.join(status['critical_failures'])}")
    
    summary.append("\nService Status:")
    for name, result in status['services'].items():
        status_icon = "✅" if result['status'] == 'healthy' else "❌"
        summary.append(f"  {status_icon} {name}: {result['status']} ({result['elapsed']:.3f}s)")
    
    return "\n".join(summary)

# Export the main components
__all__ = [
    'HealthChecker',
    'health_checker',
    'quick_health_check',
    'get_health_summary',
    'check_redis_connectivity',
    'check_database_connectivity',
    'check_file_system_access',
    'check_import_performance',
    'check_celery_workers',
    'check_network_connectivity',
    'check_system_resources',
    'check_lazy_imports'
] 
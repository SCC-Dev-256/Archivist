"""
Health Check System for VOD Processing

This module provides comprehensive health checks for all system components
including storage, API connectivity, and system resources.
"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import psutil

from core.cablecast_client import CablecastAPIClient
from core.config import MEMBER_CITIES
from core.monitoring.metrics import get_metrics_collector
from loguru import logger


@dataclass
class HealthCheckResult:
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time: Optional[float] = None


class StorageHealthChecker:
    """Health checker for storage systems."""

    def __init__(self):
        self.metrics = get_metrics_collector()

    def check_mount_availability(self, mount_path: str) -> HealthCheckResult:
        """Check if a mount point is available and writable."""
        start_time = time.time()

        try:
            # Check if path exists
            if not os.path.exists(mount_path):
                return HealthCheckResult(
                    component=f"storage:{mount_path}",
                    status="unhealthy",
                    message=f"Mount path does not exist: {mount_path}",
                    details={"exists": False, "writable": False},
                    timestamp=datetime.now(),
                    response_time=time.time() - start_time,
                )

            # Check if it's a mount point
            if not os.path.ismount(mount_path):
                return HealthCheckResult(
                    component=f"storage:{mount_path}",
                    status="degraded",
                    message=f"Path is not a mount point: {mount_path}",
                    details={
                        "exists": True,
                        "is_mount": False,
                        "writable": os.access(mount_path, os.W_OK),
                    },
                    timestamp=datetime.now(),
                    response_time=time.time() - start_time,
                )

            # Check write permissions
            writable = os.access(mount_path, os.W_OK)

            # Try to create a test file
            test_file = os.path.join(mount_path, ".health_check_test")
            test_success = False

            try:
                with open(test_file, "w") as f:
                    f.write("health_check")
                test_success = True
                os.remove(test_file)
            except Exception as e:
                test_success = False
                logger.warning(f"Write test failed for {mount_path}: {e}")

            status = "healthy" if writable and test_success else "degraded"
            message = f"Storage {mount_path} is {'healthy' if status == 'healthy' else 'has issues'}"

            self.metrics.increment("storage_checks_total")
            if status != "healthy":
                self.metrics.increment("storage_checks_failed")

            return HealthCheckResult(
                component=f"storage:{mount_path}",
                status=status,
                message=message,
                details={
                    "exists": True,
                    "is_mount": True,
                    "writable": writable,
                    "test_write": test_success,
                    "free_space": self._get_free_space(mount_path),
                },
                timestamp=datetime.now(),
                response_time=time.time() - start_time,
            )

        except Exception as e:
            self.metrics.increment("storage_checks_failed")
            return HealthCheckResult(
                component=f"storage:{mount_path}",
                status="unhealthy",
                message=f"Storage check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                response_time=time.time() - start_time,
            )

    def _get_free_space(self, path: str) -> Optional[float]:
        """Get free space in GB for the given path."""
        try:
            stat = os.statvfs(path)
            free_bytes = stat.f_frsize * stat.f_bavail
            return free_bytes / (1024**3)  # Convert to GB
        except Exception:
            return None

    def check_all_storage(self) -> List[HealthCheckResult]:
        """Check health of all storage mounts."""
        results = []

        # Check flex mounts
        for i in range(1, 10):  # flex-1 through flex-9
            mount_path = f"/mnt/flex-{i}"
            results.append(self.check_mount_availability(mount_path))

        # Check temp directory
        temp_path = "/tmp"
        results.append(self.check_mount_availability(temp_path))

        return results


class APIHealthChecker:
    """Health checker for API connectivity."""

    def __init__(self):
        self.metrics = get_metrics_collector()
        self.circuit_breaker = self.metrics.get_circuit_breaker("cablecast_api")

    def check_cablecast_api(self) -> HealthCheckResult:
        """Check Cablecast API connectivity."""
        start_time = time.time()

        try:
            # Use circuit breaker for API calls
            def api_test():
                client = CablecastAPIClient()
                return client.test_connection()

            result = self.circuit_breaker.call(api_test)

            response_time = time.time() - start_time

            if result:
                status = "healthy"
                message = "Cablecast API is responding normally"
            else:
                status = "degraded"
                message = "Cablecast API test returned False"

            return HealthCheckResult(
                component="api:cablecast",
                status=status,
                message=message,
                details={
                    "response_time": response_time,
                    "circuit_breaker_state": self.circuit_breaker.state,
                    "test_result": result,
                },
                timestamp=datetime.now(),
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component="api:cablecast",
                status="unhealthy",
                message=f"Cablecast API check failed: {str(e)}",
                details={
                    "error": str(e),
                    "circuit_breaker_state": self.circuit_breaker.state,
                    "response_time": response_time,
                },
                timestamp=datetime.now(),
                response_time=response_time,
            )


class SystemHealthChecker:
    """Health checker for system resources."""

    def check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent()

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage for root
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # Load average
            load_avg = psutil.getloadavg()

            # Determine overall status
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = "degraded"
                message = "System resources are under high load"
            elif cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
                status = "degraded"
                message = "System resources are under moderate load"
            else:
                status = "healthy"
                message = "System resources are normal"

            return HealthCheckResult(
                component="system:resources",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "load_average": load_avg,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_free_gb": disk.free / (1024**3),
                },
                timestamp=datetime.now(),
            )

        except Exception as e:
            return HealthCheckResult(
                component="system:resources",
                status="unhealthy",
                message=f"System resource check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
            )

    def check_celery_workers(self) -> HealthCheckResult:
        """Check Celery worker status."""
        try:
            # Check if Celery processes are running
            celery_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if "celery" in proc.info["name"].lower():
                        cmdline = " ".join(proc.info["cmdline"] or [])
                        if "worker" in cmdline:
                            celery_processes.append(
                                {"pid": proc.info["pid"], "cmdline": cmdline}
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if celery_processes:
                status = "healthy"
                message = f"Found {len(celery_processes)} Celery worker processes"
            else:
                status = "unhealthy"
                message = "No Celery worker processes found"

            return HealthCheckResult(
                component="system:celery_workers",
                status=status,
                message=message,
                details={
                    "worker_count": len(celery_processes),
                    "workers": celery_processes,
                },
                timestamp=datetime.now(),
            )

        except Exception as e:
            return HealthCheckResult(
                component="system:celery_workers",
                status="unhealthy",
                message=f"Celery worker check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
            )


class HealthCheckManager:
    """Main health check manager."""

    def __init__(self):
        self.storage_checker = StorageHealthChecker()
        self.api_checker = APIHealthChecker()
        self.system_checker = SystemHealthChecker()
        self.metrics = get_metrics_collector()

    def run_all_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive results."""
        start_time = time.time()

        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {},
            "summary": {},
        }

        # Storage checks
        storage_results = self.storage_checker.check_all_storage()
        results["checks"]["storage"] = [r.__dict__ for r in storage_results]

        # API checks
        api_result = self.api_checker.check_cablecast_api()
        results["checks"]["api"] = [api_result.__dict__]

        # System checks
        system_resources = self.system_checker.check_system_resources()
        celery_workers = self.system_checker.check_celery_workers()
        results["checks"]["system"] = [
            system_resources.__dict__,
            celery_workers.__dict__,
        ]

        # Calculate overall status
        all_results = storage_results + [api_result, system_resources, celery_workers]
        unhealthy_count = sum(1 for r in all_results if r.status == "unhealthy")
        degraded_count = sum(1 for r in all_results if r.status == "degraded")

        if unhealthy_count > 0:
            results["overall_status"] = "unhealthy"
        elif degraded_count > 0:
            results["overall_status"] = "degraded"

        # Summary
        results["summary"] = {
            "total_checks": len(all_results),
            "healthy": sum(1 for r in all_results if r.status == "healthy"),
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "response_time": time.time() - start_time,
        }

        return results

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status (cached for performance)."""
        # For now, run checks directly. In production, you might want to cache results
        return self.run_all_health_checks()

    def run_all_checks(self) -> Dict[str, Any]:
        """Alias for run_all_health_checks for backward compatibility."""
        return self.run_all_health_checks()


# Global health check manager
_health_manager: Optional[HealthCheckManager] = None


def get_health_manager() -> HealthCheckManager:
    """Get the global health check manager instance."""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    return _health_manager

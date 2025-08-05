#!/usr/bin/env python3
"""
Unified Startup Manager for Archivist System

This module consolidates all startup functionality into a single, configurable system,
eliminating the duplication across multiple startup scripts.
"""

import os
import sys
import time
import signal
import threading
import subprocess
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import importlib.util

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from .startup_config import StartupConfig, StartupMode, ServiceConfig

class ServiceManager:
    """Manages individual services with health checks and restart capabilities."""
    
    def __init__(self, config: StartupConfig):
        self.config = config
        self.processes: Dict[str, subprocess.Popen] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.restart_attempts: Dict[str, int] = {}
        self.health_checkers: Dict[str, Callable] = {}
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize health checkers
        self._setup_health_checkers()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.stop_all_services()
        sys.exit(0)
    
    def _setup_health_checkers(self):
        """Setup health check functions for each service."""
        self.health_checkers = {
            "redis": self._check_redis_health,
            "postgresql": self._check_postgresql_health,
            "celery_worker": self._check_celery_worker_health,
            "celery_beat": self._check_celery_beat_health,
            "admin_ui": self._check_admin_ui_health,
            "monitoring_dashboard": self._check_dashboard_health,
            "vod_sync_monitor": self._check_vod_sync_health,
        }
    
    def _check_redis_health(self) -> bool:
        """Check Redis health."""
        try:
            result = subprocess.run(
                ['redis-cli', 'ping'], 
                capture_output=True, 
                text=True, 
                timeout=self.config.health_checks.timeout
            )
            return result.returncode == 0 and 'PONG' in result.stdout
        except Exception:
            return False
    
    def _check_postgresql_health(self) -> bool:
        """Check PostgreSQL health."""
        try:
            result = subprocess.run(
                ['pg_isready'], 
                capture_output=True, 
                text=True, 
                timeout=self.config.health_checks.timeout
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_celery_worker_health(self) -> bool:
        """Check Celery worker health."""
        try:
            # Check for any Python or Celery process running celery worker
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if ((proc.info['name'] == 'python' or proc.info['name'] == 'celery') and 
                    proc.info['cmdline'] and 
                    any('celery' in arg for arg in proc.info['cmdline']) and
                    any('worker' in arg for arg in proc.info['cmdline']) and
                    proc.is_running()):
                    logger.debug(f"Found Celery worker process: {proc.info['pid']}")
                    return True
            
            # If no process found, try the inspect method as fallback
            try:
                from core.tasks import celery_app
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                if stats:
                    logger.debug(f"Found Celery workers via inspect: {list(stats.keys())}")
                    return True
            except Exception as e:
                logger.debug(f"Celery inspect failed: {e}")
            
            return False
        except Exception as e:
            logger.debug(f"Celery worker health check failed: {e}")
            return False
    
    def _check_celery_beat_health(self) -> bool:
        """Check Celery beat health."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if (proc.info['cmdline'] and 
                    any('celery' in arg for arg in proc.info['cmdline']) and
                    any('beat' in arg for arg in proc.info['cmdline']) and
                    proc.is_running()):
                    logger.debug(f"Found Celery beat process: {proc.info['pid']}")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Celery beat health check failed: {e}")
            return False
    
    def _check_admin_ui_health(self) -> bool:
        """Check Admin UI health."""
        try:
            import requests
            response = requests.get(
                f'http://localhost:{self.config.ports.admin_ui}/api/admin/status', 
                timeout=self.config.health_checks.timeout
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _check_port_availability(self, port: int) -> bool:
        """Check if a port is available."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def _find_available_port(self, preferred_port: int) -> int:
        """Find an available port starting from preferred_port."""
        port = preferred_port
        while port < preferred_port + 100:  # Try next 100 ports
            if self._check_port_availability(port):
                return port
            port += 1
        raise RuntimeError(f"No available ports found starting from {preferred_port}")
    
    def _check_dashboard_health(self) -> bool:
        """Check monitoring dashboard health."""
        try:
            import requests
            response = requests.get(
                f'http://localhost:{self.config.ports.dashboard}/api/health', 
                timeout=self.config.health_checks.timeout
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _check_vod_sync_health(self) -> bool:
        """Check VOD sync monitor health."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'vod_sync_monitor.py' in ' '.join(proc.info['cmdline']):
                    return proc.is_running()
            return False
        except Exception:
            return False
    
    def start_service(self, service_name: str) -> bool:
        """Start a specific service."""
        if not self.config.get_service_config(service_name).enabled:
            logger.info(f"Service {service_name} is disabled, skipping")
            return True
        
        logger.info(f"Starting {service_name}...")
        
        try:
            if service_name == "redis":
                return self._start_redis()
            elif service_name == "postgresql":
                return self._start_postgresql()
            elif service_name == "celery_worker":
                return self._start_celery_worker()
            elif service_name == "celery_beat":
                return self._start_celery_beat()
            elif service_name == "admin_ui":
                return self._start_admin_ui()
            elif service_name == "monitoring_dashboard":
                return self._start_monitoring_dashboard()
            elif service_name == "vod_sync_monitor":
                return self._start_vod_sync_monitor()
            else:
                logger.error(f"Unknown service: {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            return False
    
    def _start_redis(self) -> bool:
        """Start Redis service."""
        if self._check_redis_health():
            logger.info("✅ Redis is already running")
            return True
        
        try:
            # Try systemctl first with full path
            systemctl_paths = ['/usr/bin/systemctl', '/bin/systemctl', 'systemctl']
            systemctl_found = False
            
            for systemctl_path in systemctl_paths:
                try:
                    result = subprocess.run([systemctl_path, 'start', 'redis'], capture_output=True, text=True)
                    if result.returncode == 0:
                        time.sleep(2)
                        if self._check_redis_health():
                            logger.info(f"✅ Redis started via {systemctl_path}")
                            return True
                        systemctl_found = True
                        break
                except FileNotFoundError:
                    continue
            
            if not systemctl_found:
                logger.warning("⚠️ systemctl not found, trying direct Redis start")
            
            # Fallback to direct start
            try:
                subprocess.run(['redis-server', '--daemonize', 'yes'], check=True, capture_output=True)
                time.sleep(2)
                
                if self._check_redis_health():
                    logger.info("✅ Redis started directly")
                    return True
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.warning(f"⚠️ Direct Redis start failed: {e}")
            
            # Final fallback - check if Redis is already running
            if self._check_redis_health():
                logger.info("✅ Redis is already running")
                return True
            
            logger.error("❌ Failed to start Redis")
            return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start Redis: {e}")
            return False
    
    def _start_postgresql(self) -> bool:
        """Start PostgreSQL service."""
        if self._check_postgresql_health():
            logger.info("✅ PostgreSQL is already running")
            return True
        
        try:
            # Try systemctl first with full path
            systemctl_paths = ['/usr/bin/systemctl', '/bin/systemctl', 'systemctl']
            systemctl_found = False
            
            for systemctl_path in systemctl_paths:
                try:
                    result = subprocess.run([systemctl_path, 'start', 'postgresql'], capture_output=True, text=True)
                    if result.returncode == 0:
                        time.sleep(3)
                        if self._check_postgresql_health():
                            logger.info(f"✅ PostgreSQL started via {systemctl_path}")
                            return True
                        systemctl_found = True
                        break
                except FileNotFoundError:
                    continue
            
            if not systemctl_found:
                logger.warning("⚠️ systemctl not found, trying direct PostgreSQL start")
            
            # Fallback to pg_ctl
            try:
                subprocess.run(['pg_ctl', '-D', '/var/lib/postgresql/data', 'start'], check=True, capture_output=True)
                time.sleep(3)
                
                if self._check_postgresql_health():
                    logger.info("✅ PostgreSQL started via pg_ctl")
                    return True
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.warning(f"⚠️ Direct PostgreSQL start failed: {e}")
            
            # Final fallback - check if PostgreSQL is already running
            if self._check_postgresql_health():
                logger.info("✅ PostgreSQL is already running")
                return True
            
            logger.error("❌ Failed to start PostgreSQL")
            return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start PostgreSQL: {e}")
            return False
    
    def _start_celery_worker(self) -> bool:
        """Start Celery worker."""
        try:
            # Check if worker is already running
            if self._check_celery_worker_health():
                logger.info("✅ Celery worker is already running")
                return True
            
            # Use direct celery command with virtual environment activation
            logger.info("Using direct Celery command with venv activation")
            venv_celery = os.path.join(self.config.project_root, "venv_py311", "bin", "celery")
            worker_cmd = [
                venv_celery, "-A", "core.tasks", "worker",
                "--loglevel=info",
                f"--concurrency={self.config.celery.concurrency}",
                f"--hostname={self.config.celery.hostname}",
                "--queues=" + ",".join(self.config.celery.queues)
            ]
            
            worker_process = subprocess.Popen(
                worker_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=self.config.project_root
            )
            
            logger.info(f"Starting Celery worker with command: {' '.join(worker_cmd)}")
            
            self.processes["celery_worker"] = worker_process
            
            # Wait for worker to start with multiple checks
            for attempt in range(30):  # Try for up to 30 seconds (increased for ML model loading)
                time.sleep(1)
                if self._check_celery_worker_health():
                    logger.info("✅ Celery worker started successfully")
                    return True
                
                # Check if process is still running
                if worker_process.poll() is not None:
                    # Process died
                    logger.error(f"❌ Celery worker process died with exit code: {worker_process.returncode}")
                    return False
            
            logger.error("❌ Celery worker failed to start within timeout")
            return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start Celery worker: {e}")
            return False
    
    def _start_celery_beat(self) -> bool:
        """Start Celery beat scheduler."""
        try:
            # Check if beat is already running
            if self._check_celery_beat_health():
                logger.info("✅ Celery beat scheduler is already running")
                return True
            
            # Use direct celery command with virtual environment activation
            logger.info("Using direct Celery beat command with venv activation")
            venv_celery = os.path.join(self.config.project_root, "venv_py311", "bin", "celery")
            beat_cmd = [
                venv_celery, "-A", "core.tasks", "beat",
                "--loglevel=info",
                f"--scheduler={self.config.celery.scheduler}"
            ]
            
            beat_process = subprocess.Popen(
                beat_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=self.config.project_root
            )
            
            logger.info(f"Starting Celery beat with command: {' '.join(beat_cmd)}")
            
            self.processes["celery_beat"] = beat_process
            
            # Wait for beat to start with multiple checks
            for attempt in range(10):  # Try for up to 10 seconds
                time.sleep(1)
                if self._check_celery_beat_health():
                    logger.info("✅ Celery beat scheduler started successfully")
                    return True
                
                # Check if process is still running
                if beat_process.poll() is not None:
                    # Process died
                    logger.error(f"❌ Celery beat process died with exit code: {beat_process.returncode}")
                    return False
            
            logger.error("❌ Celery beat scheduler failed to start within timeout")
            return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start Celery beat: {e}")
            return False
    
    def _start_admin_ui(self) -> bool:
        """Start Admin UI."""
        try:
            # Check and resolve port conflicts
            admin_port = self.config.ports.admin_ui
            if not self._check_port_availability(admin_port):
                logger.warning(f"⚠️ Port {admin_port} is in use, finding alternative...")
                admin_port = self._find_available_port(admin_port)
                logger.info(f"✅ Using alternative port {admin_port} for Admin UI")
                self.config.ports.admin_ui = admin_port
            
            def run_admin_ui():
                try:
                    from core.admin_ui import start_admin_ui
                    start_admin_ui(
                        host="0.0.0.0",
                        port=self.config.ports.admin_ui,
                        dashboard_port=self.config.ports.dashboard
                    )
                except Exception as e:
                    logger.error(f"Admin UI error: {e}")
            
            admin_thread = threading.Thread(target=run_admin_ui, daemon=True)
            admin_thread.start()
            self.threads["admin_ui"] = admin_thread
            
            # Wait for admin UI to start
            for attempt in range(30):
                time.sleep(1)
                if self._check_admin_ui_health():
                    logger.info("✅ Admin UI started successfully")
                    return True
            
            logger.error("❌ Admin UI failed to start")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to start Admin UI: {e}")
            return False
    
    def _start_monitoring_dashboard(self) -> bool:
        """Start monitoring dashboard."""
        try:
            # Check and resolve port conflicts
            dashboard_port = self.config.ports.dashboard
            if not self._check_port_availability(dashboard_port):
                logger.warning(f"⚠️ Port {dashboard_port} is in use, finding alternative...")
                dashboard_port = self._find_available_port(dashboard_port)
                logger.info(f"✅ Using alternative port {dashboard_port} for Dashboard")
                self.config.ports.dashboard = dashboard_port
            
            def run_dashboard():
                try:
                    from core.monitoring.integrated_dashboard import start_integrated_dashboard
                    start_integrated_dashboard(
                        port=self.config.ports.dashboard
                    )
                except Exception as e:
                    logger.error(f"Dashboard error: {e}")
            
            dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            dashboard_thread.start()
            self.threads["monitoring_dashboard"] = dashboard_thread
            
            # Wait for dashboard to start
            for attempt in range(30):
                time.sleep(1)
                if self._check_dashboard_health():
                    logger.info("✅ Monitoring dashboard started successfully")
                    return True
            
            logger.error("❌ Monitoring dashboard failed to start")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring dashboard: {e}")
            return False
    
    def _start_vod_sync_monitor(self) -> bool:
        """Start VOD sync monitor."""
        try:
            vod_cmd = [
                "python3", "scripts/monitoring/vod_sync_monitor.py", "--single-run"
            ]
            
            vod_process = subprocess.Popen(
                vod_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.config.project_root
            )
            
            self.processes["vod_sync_monitor"] = vod_process
            
            # Wait for VOD sync monitor to start
            time.sleep(2)
            if self._check_vod_sync_health():
                logger.info("✅ VOD sync monitor started successfully")
                return True
            else:
                logger.warning("⚠️ VOD sync monitor may not have started properly")
                return True  # Don't fail startup for this
                
        except Exception as e:
            logger.error(f"❌ Failed to start VOD sync monitor: {e}")
            return True  # Don't fail startup for this
    
    def stop_service(self, service_name: str):
        """Stop a specific service."""
        logger.info(f"Stopping {service_name}...")
        
        # Stop process if running
        if service_name in self.processes:
            process = self.processes[service_name]
            try:
                process.terminate()
                process.wait(timeout=10)
                logger.info(f"✅ {service_name} stopped successfully")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {service_name}")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        # Stop thread if running
        if service_name in self.threads:
            # Threads are daemon, they'll stop when main thread stops
            logger.info(f"✅ {service_name} thread stopped")
    
    def stop_all_services(self):
        """Stop all services."""
        logger.info("Stopping all services...")
        
        # Stop in reverse order
        service_order = [
            "vod_sync_monitor", "monitoring_dashboard", "admin_ui", 
            "celery_beat", "celery_worker", "postgresql", "redis"
        ]
        
        for service_name in reversed(service_order):
            self.stop_service(service_name)
        
        logger.info("✅ All services stopped")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        status = {}
        
        for service_name in self.config.services.keys():
            is_healthy = False
            if service_name in self.health_checkers:
                is_healthy = self.health_checkers[service_name]()
            
            is_running = (
                service_name in self.processes and 
                self.processes[service_name].poll() is None
            ) or service_name in self.threads
            
            status[service_name] = {
                "enabled": self.config.get_service_config(service_name).enabled,
                "running": is_running,
                "healthy": is_healthy,
                "restart_attempts": self.restart_attempts.get(service_name, 0)
            }
        
        return status

class StartupManager:
    """Main startup manager that orchestrates the entire system startup."""
    
    def __init__(self, config: StartupConfig):
        self.config = config
        self.service_manager = ServiceManager(config)
        self.running = True
        
        # Setup logging
        self._setup_logging()
        
        # Create necessary directories
        self._create_directories()
    
    def _setup_logging(self):
        """Setup comprehensive logging."""
        logger.remove()  # Remove default handler
        
        # Add console handler with color
        logger.add(
            sys.stdout,
            format=self.config.logging.format,
            level=self.config.logging.level,
            colorize=True
        )
        
        # Add file handler
        log_dir = self.config.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            log_dir / f"{self.config.mode.value}_system.log",
            format=self.config.logging.file_format,
            level=self.config.logging.file_level,
            rotation=self.config.logging.rotation,
            retention=self.config.logging.retention
        )
    
    def _create_directories(self):
        """Create necessary directories."""
        directories = [
            "logs",
            "output", 
            "core/templates",
            "core/static",
            "pids"
        ]
        
        for directory in directories:
            dir_path = self.config.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def check_dependencies(self) -> bool:
        """Check system dependencies."""
        logger.info("Checking system dependencies...")
        
        # Check Python environment
        try:
            import core.tasks
            import core.admin_ui
            import core.monitoring.integrated_dashboard
            logger.info("✅ Python modules loaded successfully")
        except ImportError as e:
            logger.error(f"❌ Python module import failed: {e}")
            return False
        
        # Check Redis
        if self.service_manager._check_redis_health():
            logger.info("✅ Redis connection successful")
        else:
            logger.warning("⚠️ Redis not running, will start it")
        
        # Check PostgreSQL
        if self.service_manager._check_postgresql_health():
            logger.info("✅ PostgreSQL connection successful")
        else:
            logger.warning("⚠️ PostgreSQL not running, will start it")
        
        # Check flex mounts
        flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', '/mnt/flex-5']
        for mount in flex_mounts:
            if os.path.ismount(mount):
                logger.info(f"✅ Flex mount {mount} available")
            else:
                logger.warning(f"⚠️ Flex mount {mount} not mounted")
        
        return True
    
    def start_services(self) -> bool:
        """Start all services in the correct order."""
        logger.info("Starting all services in order...")
        
        # Service startup order
        service_order = [
            "redis",
            "postgresql", 
            "celery_worker",
            "celery_beat",
            "vod_sync_monitor",
            "admin_ui",
            "monitoring_dashboard"
        ]
        
        for service_name in service_order:
            if not self.service_manager.start_service(service_name):
                logger.error(f"Failed to start {service_name}, stopping startup")
                return False
            
            # Wait between services
            time.sleep(2)
        
        logger.info("✅ All services started successfully")
        return True
    
    def start_health_monitoring(self):
        """Start background health monitoring."""
        if not self.config.health_checks.enabled:
            return
        
        def health_monitor():
            """Background health monitoring service."""
            while self.running:
                try:
                    status = self.service_manager.get_service_status()
                    
                    for service_name, service_status in status.items():
                        if (not service_status['running'] and 
                            service_status['restart_attempts'] < self.config.health_checks.max_failures):
                            logger.warning(f"Service {service_name} is not running, attempting restart")
                            self._handle_service_failure(service_name)
                    
                    time.sleep(self.config.health_checks.interval)
                    
                except Exception as e:
                    logger.error(f"Error in health monitoring: {e}")
                    time.sleep(60)
        
        health_thread = threading.Thread(target=health_monitor, daemon=True)
        health_thread.start()
        logger.info("✅ Background health monitoring started")
    
    def _handle_service_failure(self, service_name: str):
        """Handle service failure with restart logic."""
        if service_name not in self.service_manager.restart_attempts:
            self.service_manager.restart_attempts[service_name] = 0
        
        self.service_manager.restart_attempts[service_name] += 1
        
        if self.service_manager.restart_attempts[service_name] <= self.config.health_checks.max_failures:
            logger.warning(f"Restarting {service_name} (attempt {self.service_manager.restart_attempts[service_name]}/{self.config.health_checks.max_failures})")
            time.sleep(self.config.get_service_config(service_name).restart_delay)
            self.service_manager.start_service(service_name)
        else:
            logger.error(f"Service {service_name} failed too many times, giving up")
    
    def run(self) -> bool:
        """Main startup orchestration."""
        logger.info(f"Starting Archivist system in {self.config.mode.value} mode")
        
        # Check dependencies
        if not self.check_dependencies():
            logger.error("Dependency check failed. Exiting.")
            return False
        
        # Start services
        if not self.start_services():
            logger.error("Failed to start all services. Exiting.")
            return False
        
        # Start health monitoring
        self.start_health_monitoring()
        
        # Print status
        self._print_startup_summary()
        
        return True
    
    def _print_startup_summary(self):
        """Print startup summary."""
        print(f"\n🎉 Archivist System Started Successfully!")
        print("=" * 60)
        print(f"📊 Admin UI: http://0.0.0.0:{self.config.ports.admin_ui}")
        print(f"📈 Monitoring Dashboard: http://localhost:{self.config.ports.dashboard}")
        print(f"📚 API Documentation: http://0.0.0.0:{self.config.ports.admin_ui}/api/docs")
        print(f"🔗 Unified Queue API: http://0.0.0.0:{self.config.ports.admin_ui}/api/unified-queue/docs")
        print(f"⏰ VOD Processing Schedule: {self.config.get_environment_var('VOD_PROCESSING_TIME', '19:00')} daily")
        print(f"🔄 Celery Workers: {self.config.celery.concurrency} concurrent workers active")
        print(f"📅 Scheduled Tasks: Daily caption check, VOD processing, cleanup")
        print(f"🎬 Flex Server Integration: Direct file access enabled")
        print(f"📋 Sequential Processing: Videos processed one at a time")
        print(f"🔄 Auto-restart: {'Enabled' if self.config.features['auto_restart'] else 'Disabled'}")
        print("=" * 60)
    
    def stop(self):
        """Stop the startup manager."""
        logger.info("Stopping startup manager...")
        self.running = False
        self.service_manager.stop_all_services()
        logger.info("Startup manager stopped") 
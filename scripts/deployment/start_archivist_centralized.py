#!/usr/bin/env python3
"""
Centralized Archivist System Startup Script

This script starts ALL services in the correct order with proper integration:
- Redis and PostgreSQL
- Celery workers and beat scheduler
- Admin UI and monitoring dashboard (fully integrated)
- VOD sync monitor (integrated into dashboard)
- VOD automation features (accessible through GUIs)
- Unified task queue management (RQ + Celery)

Features:
- Service startup order management
- Automatic restart capabilities
- Cross-linked GUI interfaces
- Unified task management
- Health monitoring and alerts
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
from typing import Dict, List, Optional, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

class ServiceManager:
    """Manages all Archivist services with startup order and restart capabilities."""
    
    def __init__(self):
        self.services = {}
        self.processes = {}
        self.running = True
        self.restart_attempts = {}
        self.max_restart_attempts = 3
        self.restart_delay = 10  # seconds
        
        # Service startup order
        self.startup_order = [
            'redis',
            'postgresql', 
            'celery_worker',
            'celery_beat',
            'vod_sync_monitor',
            'admin_ui',
            'monitoring_dashboard'
        ]
        
        # Service configurations
        self.service_configs = {
            'redis': {
                'name': 'Redis',
                'check_cmd': ['redis-cli', 'ping'],
                'start_cmd': ['redis-server', '--daemonize', 'yes'],
                'stop_cmd': ['redis-cli', 'shutdown'],
                'port': 6379,
                'health_check': self._check_redis_health
            },
            'postgresql': {
                'name': 'PostgreSQL',
                'check_cmd': ['pg_isready'],
                'start_cmd': ['pg_ctl', '-D', '/var/lib/postgresql/data', 'start'],
                'stop_cmd': ['pg_ctl', '-D', '/var/lib/postgresql/data', 'stop'],
                'port': 5432,
                'health_check': self._check_postgresql_health
            },
            'celery_worker': {
                'name': 'Celery Worker',
                'check_cmd': None,  # Will check via Celery inspect
                'start_cmd': ['celery', '-A', 'core.tasks', 'worker', '--loglevel=info', '--concurrency=2'],
                'stop_cmd': None,
                'port': None,
                'health_check': self._check_celery_worker_health,
                'python_env': True
            },
            'celery_beat': {
                'name': 'Celery Beat Scheduler',
                'check_cmd': None,
                'start_cmd': ['celery', '-A', 'core.tasks', 'beat', '--loglevel=info'],
                'stop_cmd': None,
                'port': None,
                'health_check': self._check_celery_beat_health,
                'python_env': True
            },
            'vod_sync_monitor': {
                'name': 'VOD Sync Monitor',
                'check_cmd': None,
                'start_cmd': ['python3', 'scripts/monitoring/vod_sync_monitor.py', '--single-run'],
                'stop_cmd': None,
                'port': None,
                'health_check': self._check_vod_sync_health,
                'python_env': True,
                'background': True
            },
            'admin_ui': {
                'name': 'Admin UI',
                'check_cmd': None,
                'start_cmd': ['python3', '-m', 'core.admin_ui'],
                'stop_cmd': None,
                'port': 8080,
                'health_check': self._check_admin_ui_health,
                'python_env': True
            },
            'monitoring_dashboard': {
                'name': 'Monitoring Dashboard',
                'check_cmd': None,
                'start_cmd': ['python3', '-m', 'core.monitoring.integrated_dashboard'],
                'stop_cmd': None,
                'port': 5051,
                'health_check': self._check_dashboard_health,
                'python_env': True
            }
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.stop_all_services()
        sys.exit(0)
    
    def setup_logging(self):
        """Setup comprehensive logging."""
        logger.remove()  # Remove default handler
        
        # Add console handler with color
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True
        )
        
        # Add file handler
        os.makedirs("logs", exist_ok=True)
        logger.add(
            "logs/centralized_system.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days"
        )
    
    def _check_redis_health(self) -> bool:
        """Check Redis health."""
        try:
            result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and 'PONG' in result.stdout
        except:
            return False
    
    def _check_postgresql_health(self) -> bool:
        """Check PostgreSQL health."""
        try:
            result = subprocess.run(['pg_isready'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_celery_worker_health(self) -> bool:
        """Check Celery worker health."""
        try:
            from core.tasks import celery_app
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            return bool(stats)
        except:
            return False
    
    def _check_celery_beat_health(self) -> bool:
        """Check Celery beat health."""
        try:
            # Check if beat process is running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'celery' in proc.info['cmdline'] and 'beat' in proc.info['cmdline']:
                    return proc.is_running()
            return False
        except:
            return False
    
    def _check_vod_sync_health(self) -> bool:
        """Check VOD sync monitor health."""
        try:
            # Check if VOD sync monitor process is running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'vod_sync_monitor.py' in ' '.join(proc.info['cmdline']):
                    return proc.is_running()
            return False
        except:
            return False
    
    def _check_admin_ui_health(self) -> bool:
        """Check Admin UI health."""
        try:
            import requests
            response = requests.get('http://localhost:8080/api/admin/status', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _check_dashboard_health(self) -> bool:
        """Check monitoring dashboard health."""
        try:
            import requests
            response = requests.get('http://localhost:5051/api/health', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_dependencies(self) -> bool:
        """Check system dependencies."""
        logger.info("Checking system dependencies...")
        
        # Check Python environment
        try:
            import core.tasks
            import core.task_queue
            import core.monitoring.integrated_dashboard
            import core.admin_ui
            logger.info("✅ Python modules loaded successfully")
        except ImportError as e:
            logger.error(f"❌ Python module import failed: {e}")
            return False
        
        # Check Redis
        if self._check_redis_health():
            logger.info("✅ Redis connection successful")
        else:
            logger.warning("⚠️ Redis not running, will start it")
        
        # Check flex mounts
        flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', '/mnt/flex-5']
        for mount in flex_mounts:
            if os.path.ismount(mount):
                logger.info(f"✅ Flex mount {mount} available")
            else:
                logger.warning(f"⚠️ Flex mount {mount} not mounted")
        
        return True
    
    def start_service(self, service_name: str) -> bool:
        """Start a specific service."""
        if service_name not in self.service_configs:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        config = self.service_configs[service_name]
        logger.info(f"Starting {config['name']}...")
        
        try:
            # Check if already running
            if config['health_check'] and config['health_check']():
                logger.info(f"{config['name']} is already running")
                return True
            
            # Prepare command
            cmd = config['start_cmd']
            if config.get('python_env'):
                # Activate virtual environment
                venv_path = project_root / "venv_py311"
                if venv_path.exists():
                    cmd = [str(venv_path / "bin" / "python3")] + cmd[1:]
                else:
                    cmd = ["python3"] + cmd[1:]
            
            # Start service
            if config.get('background'):
                # Start in background
                process = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
                self.processes[service_name] = process
                logger.info(f"Started {config['name']} in background (PID: {process.pid})")
            else:
                # Start in foreground with threading
                def run_service():
                    process = subprocess.Popen(
                        cmd,
                        cwd=project_root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    self.processes[service_name] = process
                    logger.info(f"Started {config['name']} (PID: {process.pid})")
                    
                    # Monitor process
                    while self.running and process.poll() is None:
                        time.sleep(1)
                    
                    if process.returncode is not None and self.running:
                        logger.error(f"{config['name']} exited with code {process.returncode}")
                        self._handle_service_failure(service_name)
                
                thread = threading.Thread(target=run_service, daemon=True)
                thread.start()
                self.services[service_name] = thread
            
            # Wait for service to be healthy
            if config['health_check']:
                for attempt in range(30):  # Wait up to 30 seconds
                    time.sleep(1)
                    if config['health_check']():
                        logger.info(f"✅ {config['name']} started successfully")
                        return True
                
                logger.error(f"❌ {config['name']} failed to start (health check failed)")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start {config['name']}: {e}")
            return False
    
    def _handle_service_failure(self, service_name: str):
        """Handle service failure with restart logic."""
        if service_name not in self.restart_attempts:
            self.restart_attempts[service_name] = 0
        
        self.restart_attempts[service_name] += 1
        
        if self.restart_attempts[service_name] <= self.max_restart_attempts:
            logger.warning(f"Restarting {service_name} (attempt {self.restart_attempts[service_name]}/{self.max_restart_attempts})")
            time.sleep(self.restart_delay)
            self.start_service(service_name)
        else:
            logger.error(f"Service {service_name} failed too many times, giving up")
    
    def start_all_services(self) -> bool:
        """Start all services in the correct order."""
        logger.info("Starting all services in order...")
        
        for service_name in self.startup_order:
            if not self.start_service(service_name):
                logger.error(f"Failed to start {service_name}, stopping startup")
                return False
            
            # Wait between services
            time.sleep(2)
        
        logger.info("✅ All services started successfully")
        return True
    
    def stop_service(self, service_name: str):
        """Stop a specific service."""
        if service_name not in self.service_configs:
            return
        
        config = self.service_configs[service_name]
        logger.info(f"Stopping {config['name']}...")
        
        # Stop process if running
        if service_name in self.processes:
            process = self.processes[service_name]
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                
                # Wait for graceful shutdown
                process.wait(timeout=10)
                logger.info(f"✅ {config['name']} stopped successfully")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {config['name']}")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {config['name']}: {e}")
        
        # Use stop command if available
        if config['stop_cmd']:
            try:
                subprocess.run(config['stop_cmd'], timeout=10, capture_output=True)
            except Exception as e:
                logger.error(f"Error running stop command for {config['name']}: {e}")
    
    def stop_all_services(self):
        """Stop all services."""
        logger.info("Stopping all services...")
        
        # Stop in reverse order
        for service_name in reversed(self.startup_order):
            self.stop_service(service_name)
        
        logger.info("✅ All services stopped")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        status = {}
        
        for service_name, config in self.service_configs.items():
            is_healthy = config['health_check']() if config['health_check'] else False
            is_running = service_name in self.processes and self.processes[service_name].poll() is None
            
            status[service_name] = {
                'name': config['name'],
                'running': is_running,
                'healthy': is_healthy,
                'restart_attempts': self.restart_attempts.get(service_name, 0)
            }
        
        return status
    
    def monitor_services(self):
        """Monitor all services and restart failed ones."""
        logger.info("Starting service monitoring...")
        
        while self.running:
            try:
                status = self.get_service_status()
                
                for service_name, service_status in status.items():
                    if not service_status['running'] and service_status['restart_attempts'] < self.max_restart_attempts:
                        logger.warning(f"Service {service_name} is not running, attempting restart")
                        self._handle_service_failure(service_name)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in service monitoring: {e}")
                time.sleep(60)

def main():
    """Main startup function."""
    print("🚀 Starting Centralized Archivist System")
    print("=" * 60)
    
    # Initialize service manager
    manager = ServiceManager()
    manager.setup_logging()
    
    logger.info("Starting Centralized Archivist System")
    
    # Check dependencies
    if not manager.check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Start all services
    if not manager.start_all_services():
        logger.error("Failed to start all services. Exiting.")
        sys.exit(1)
    
    # Start service monitoring in background
    monitor_thread = threading.Thread(target=manager.monitor_services, daemon=True)
    monitor_thread.start()
    
    # Print status
    print(f"\n🎉 Centralized Archivist System Started Successfully!")
    print("=" * 60)
    print(f"📊 Admin UI: http://0.0.0.0:8080")
    print(f"📈 Monitoring Dashboard: http://localhost:5051")
    print(f"📚 API Documentation: http://0.0.0.0:8080/api/docs")
    print(f"🔗 Unified Queue API: http://0.0.0.0:8080/api/unified-queue/docs")
    print(f"⏰ VOD Processing Schedule: {os.getenv('VOD_PROCESSING_TIME', '19:00')} daily")
    print(f"🔄 Celery Workers: 2 concurrent workers active")
    print(f"📅 Scheduled Tasks: Daily caption check, VOD processing, cleanup")
    print(f"🎬 Flex Server Integration: Direct file access enabled")
    print(f"📋 Sequential Processing: Videos processed one at a time")
    print(f"🔄 Auto-restart: Enabled (max 3 attempts)")
    print("=" * 60)
    
    try:
        # Keep main thread alive
        while manager.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down gracefully...")
    finally:
        manager.stop_all_services()

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Complete VOD Processing System Startup Script

This script starts the complete integrated system including:
- Main Admin UI with embedded monitoring dashboard
- Celery workers for VOD processing
- Celery beat scheduler for automated tasks
- Unified queue management
- Health checks and metrics collection
- Automatic GUI interface posting
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger
from core.exceptions import (
    ConnectionError,
    DatabaseError,
    FileError,
    ConfigurationError
)

def setup_logging():
    """Setup logging configuration."""
    logger.remove()  # Remove default handler
    
    # Add console handler with color
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Add file handler
    logger.add(
        "logs/complete_system.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )

def check_dependencies():
    """Check if all required dependencies are available."""
    logger.info("Checking system dependencies...")
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        logger.info("✅ Redis connection successful")
    except ConnectionError as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False
    
    # Check PostgreSQL
    try:
        from core.config import DATABASE_URL
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        logger.info("✅ PostgreSQL connection successful")
    except ConnectionError as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        return False
    except DatabaseError as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        return False
    
    # Check Celery
    try:
        from core.tasks import celery_app
        logger.info("✅ Celery app loaded successfully")
    except ImportError as e:
        logger.error(f"❌ Celery app import failed: {e}")
        return False
    except ConfigurationError as e:
        logger.error(f"❌ Celery app configuration failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Celery app loading failed: {e}")
        return False
    
    # Check flex mounts
    flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', '/mnt/flex-5']
    for mount in flex_mounts:
        if os.path.ismount(mount):
            logger.info(f"✅ Flex mount {mount} available")
        else:
            logger.warning(f"⚠️ Flex mount {mount} not available")
    
    return True

def check_environment():
    """Check environment configuration."""
    logger.info("Checking environment configuration...")
    
    required_vars = [
        'REDIS_URL',
        'DATABASE_URL',
        'CABLECAST_API_URL',
        'CABLECAST_API_KEY'
    ]
    
    for var in required_vars:
        if os.getenv(var):
            logger.info(f"✅ {var} configured")
        else:
            logger.warning(f"⚠️ {var} not configured")
    
    # Check VOD processing time
    vod_time = os.getenv("VOD_PROCESSING_TIME", "19:00")
    logger.info(f"✅ VOD processing scheduled for {vod_time}")

def start_celery_worker():
    """Start Celery worker for VOD processing."""
    logger.info("Starting Celery worker...")
    
    try:
        # Start Celery worker in background
        worker_cmd = [
            "celery", "-A", "core.tasks", "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--hostname=vod_worker@%h",
            "--queues=vod_processing,default"
        ]
        
        worker_process = subprocess.Popen(
            worker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_root
        )
        
        # Wait a moment to check if worker started successfully
        time.sleep(3)
        if worker_process.poll() is None:
            logger.info("✅ Celery worker started successfully")
            return worker_process
        else:
            logger.error("❌ Celery worker failed to start")
            return None
            
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Subprocess error starting Celery worker: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"❌ Celery command not found: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error starting Celery worker: {e}")
        return None

def start_celery_beat():
    """Start Celery beat scheduler."""
    logger.info("Starting Celery beat scheduler...")
    
    try:
        # Start Celery beat in background
        beat_cmd = [
            "celery", "-A", "core.tasks", "beat",
            "--loglevel=info",
            "--scheduler=celery.beat.PersistentScheduler"
        ]
        
        beat_process = subprocess.Popen(
            beat_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_root
        )
        
        # Wait a moment to check if beat started successfully
        time.sleep(3)
        if beat_process.poll() is None:
            logger.info("✅ Celery beat scheduler started successfully")
            return beat_process
        else:
            logger.error("❌ Celery beat scheduler failed to start")
            return None
            
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Subprocess error starting Celery beat: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"❌ Celery command not found: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error starting Celery beat: {e}")
        return None

def start_background_services():
    """Start background monitoring and health check services."""
    logger.info("Starting background services...")
    
    def health_monitor():
        """Background health monitoring service."""
        while True:
            try:
                # Check Redis
                import redis
                r = redis.Redis(host='localhost', port=6379, db=0)
                r.ping()
                
                # Check Celery workers
                from core.tasks import celery_app
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                
                if stats:
                    logger.debug(f"Celery workers active: {len(stats)}")
                else:
                    logger.warning("No Celery workers detected")
                
                time.sleep(60)  # Check every minute
                
            except ConnectionError as e:
                logger.error(f"Connection error in health check: {e}")
                time.sleep(60)
            except ImportError as e:
                logger.error(f"Import error in health check: {e}")
                time.sleep(60)
            except Exception as e:
                logger.error(f"Unexpected error in health check: {e}")
                time.sleep(60)
    
    # Start health monitoring in background
    health_thread = threading.Thread(target=health_monitor, daemon=True)
    health_thread.start()
    logger.info("✅ Background health monitoring started")

def test_vod_processing():
    """Test VOD processing system."""
    logger.info("Testing VOD processing system...")
    
    try:
        from core.tasks import celery_app
        
        # Check if VOD processing tasks are registered
        registered_tasks = celery_app.tasks.keys()
        vod_tasks = [task for task in registered_tasks if 'vod_processing' in task]
        
        expected_tasks = [
            'vod_processing.process_recent_vods',
            'vod_processing.process_single_vod',
            'vod_processing.download_vod_content',
            'vod_processing.generate_vod_captions',
            'vod_processing.retranscode_vod_with_captions',
            'vod_processing.upload_captioned_vod',
            'vod_processing.validate_vod_quality',
            'vod_processing.cleanup_temp_files'
        ]
        
        missing_tasks = [task for task in expected_tasks if task not in vod_tasks]
        
        if missing_tasks:
            logger.error(f"❌ Missing VOD processing tasks: {missing_tasks}")
            return False
        
        logger.info(f"✅ All {len(vod_tasks)} VOD processing tasks registered")
        
        # Test task triggering
        from core.tasks.vod_processing import cleanup_temp_files
        test_task = cleanup_temp_files.delay()
        logger.info(f"✅ Test task triggered: {test_task.id}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error in VOD processing test: {e}")
        return False
    except ConnectionError as e:
        logger.error(f"❌ Connection error in VOD processing test: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in VOD processing test: {e}")
        return False

def start_gui_interfaces():
    """Start all GUI interfaces."""
    logger.info("Starting GUI interfaces...")
    
    try:
        # Import and start admin UI
        from core.admin_ui import start_admin_ui
        
        # Configuration
        admin_host = os.getenv("ADMIN_HOST", "0.0.0.0")
        admin_port = int(os.getenv("ADMIN_PORT", "8080"))
        dashboard_port = int(os.getenv("DASHBOARD_PORT", "5051"))
        
        logger.info(f"Starting Admin UI on {admin_host}:{admin_port}")
        logger.info(f"Embedded dashboard on port {dashboard_port}")
        
        # Start admin UI in a separate thread
        def run_admin_ui():
            try:
                start_admin_ui(admin_host, admin_port, dashboard_port)
            except ImportError as e:
                logger.error(f"Import error in Admin UI: {e}")
            except ConnectionError as e:
                logger.error(f"Connection error in Admin UI: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in Admin UI: {e}")
        
        admin_thread = threading.Thread(target=run_admin_ui, daemon=True)
        admin_thread.start()
        
        # Wait for services to start
        time.sleep(5)
        
        logger.info("✅ GUI interfaces started successfully")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error starting GUI interfaces: {e}")
        return False
    except ConnectionError as e:
        logger.error(f"❌ Connection error starting GUI interfaces: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error starting GUI interfaces: {e}")
        return False

def main():
    """Main startup function."""
    print("🚀 Starting Complete VOD Processing System")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    logger.info("Starting Complete VOD Processing System")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Check environment
    check_environment()
    
    # Start background services
    start_background_services()
    
    # Start Celery worker
    worker_process = start_celery_worker()
    if not worker_process:
        logger.error("Failed to start Celery worker. Exiting.")
        sys.exit(1)
    
    # Start Celery beat scheduler
    beat_process = start_celery_beat()
    if not beat_process:
        logger.error("Failed to start Celery beat. Exiting.")
        sys.exit(1)
    
    # Test VOD processing
    if not test_vod_processing():
        logger.error("VOD processing test failed. Exiting.")
        sys.exit(1)
    
    # Start GUI interfaces
    if not start_gui_interfaces():
        logger.error("Failed to start GUI interfaces. Exiting.")
        sys.exit(1)
    
    # Configuration
    admin_host = os.getenv("ADMIN_HOST", "0.0.0.0")
    admin_port = int(os.getenv("ADMIN_PORT", "8080"))
    dashboard_port = int(os.getenv("DASHBOARD_PORT", "5051"))
    
    print(f"\n🎉 Complete VOD Processing System Started Successfully!")
    print("=" * 60)
    print(f"📊 Admin UI: http://{admin_host}:{admin_port}")
    print(f"📈 Monitoring Dashboard: http://localhost:{dashboard_port}")
    print(f"📚 API Documentation: http://{admin_host}:{admin_port}/api/docs")
    print(f"🔗 Unified Queue API: http://{admin_host}:{admin_port}/api/unified-queue/docs")
    print(f"⏰ VOD Processing Schedule: {os.getenv('VOD_PROCESSING_TIME', '19:00')} daily")
    print(f"🔄 Celery Workers: 4 concurrent workers active")
    print(f"📅 Scheduled Tasks: Daily caption check, VOD processing, cleanup")
    print("\n" + "=" * 60)
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(60)
            
            # Check if processes are still running
            if worker_process.poll() is not None:
                logger.error("Celery worker process died. Restarting...")
                worker_process = start_celery_worker()
                
            if beat_process.poll() is not None:
                logger.error("Celery beat process died. Restarting...")
                beat_process = start_celery_beat()
                
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down gracefully...")
        
        # Stop processes
        if worker_process:
            worker_process.terminate()
        if beat_process:
            beat_process.terminate()
            
        logger.info("System shutdown complete.")
    except ConnectionError as e:
        logger.error(f"Connection error in main: {e}")
        sys.exit(1)
    except ImportError as e:
        logger.error(f"Import error in main: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
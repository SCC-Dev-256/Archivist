#!/usr/bin/env python3
"""
Simplified VOD Processing System Startup Script

This script starts the VOD processing system with focus on:
- Celery workers for VOD processing
- GUI interfaces
- Flex server integration
- Sequential video processing
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

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
        "logs/vod_system.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )

def check_basic_dependencies():
    """Check basic system dependencies."""
    logger.info("Checking basic system dependencies...")
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        logger.info("✅ Redis connection successful")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False
    
    # Check Celery
    try:
        from core.tasks import celery_app
        logger.info("✅ Celery app loaded successfully")
    except Exception as e:
        logger.error(f"❌ Celery app loading failed: {e}")
        return False
    
    # Check flex mounts (optional)
    flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', '/mnt/flex-5']
    for mount in flex_mounts:
        if os.path.ismount(mount):
            logger.info(f"✅ Flex mount {mount} available")
        else:
            logger.warning(f"⚠️ Flex mount {mount} not available")
    
    return True

def start_celery_worker():
    """Start Celery worker for VOD processing."""
    logger.info("Starting Celery worker...")
    
    try:
        # Start Celery worker in background
        worker_cmd = [
            "celery", "-A", "core.tasks", "worker",
            "--loglevel=info",
            "--concurrency=2",
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
            
    except Exception as e:
        logger.error(f"❌ Failed to start Celery worker: {e}")
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
            
    except Exception as e:
        logger.error(f"❌ Failed to start Celery beat: {e}")
        return None

def start_gui_interfaces():
    """Start GUI interfaces."""
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
            except Exception as e:
                logger.error(f"Admin UI error: {e}")
        
        admin_thread = threading.Thread(target=run_admin_ui, daemon=True)
        admin_thread.start()
        
        # Wait for services to start
        time.sleep(5)
        
        logger.info("✅ GUI interfaces started successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to start GUI interfaces: {e}")
        return False

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
        
    except Exception as e:
        logger.error(f"❌ VOD processing test failed: {e}")
        return False

def main():
    """Main startup function."""
    print("🚀 Starting Simplified VOD Processing System")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    logger.info("Starting Simplified VOD Processing System")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Check basic dependencies
    if not check_basic_dependencies():
        logger.error("Basic dependency check failed. Exiting.")
        sys.exit(1)
    
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
    
    print(f"\n🎉 Simplified VOD Processing System Started Successfully!")
    print("=" * 60)
    print(f"📊 Admin UI: http://{admin_host}:{admin_port}")
    print(f"📈 Monitoring Dashboard: http://localhost:{dashboard_port}")
    print(f"📚 API Documentation: http://{admin_host}:{admin_port}/api/docs")
    print(f"🔗 Unified Queue API: http://{admin_host}:{admin_port}/api/unified-queue/docs")
    print(f"⏰ VOD Processing Schedule: {os.getenv('VOD_PROCESSING_TIME', '19:00')} daily")
    print(f"🔄 Celery Workers: 2 concurrent workers active")
    print(f"📅 Scheduled Tasks: Daily caption check, VOD processing, cleanup")
    print(f"🎬 Flex Server Integration: Direct file access enabled")
    print(f"📋 Sequential Processing: Videos processed one at a time")
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
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
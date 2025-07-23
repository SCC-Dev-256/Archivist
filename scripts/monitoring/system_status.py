#!/usr/bin/env python3
"""System status monitoring script for VOD processing system."""

import os
import sys
from datetime import datetime

import psutil
from loguru import logger

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.services import VODService


def check_flex_mounts():
    """Check status of flex server mounts."""
    logger.info("🔍 Checking Flex Mounts...")
    
    flex_mounts = [
        '/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4',
        '/mnt/flex-5', '/mnt/flex-6', '/mnt/flex-7', '/mnt/flex-8', '/mnt/flex-9'
    ]
    
    working_mounts = 0
    total_mounts = len(flex_mounts)
    
    for mount in flex_mounts:
        try:
            if os.path.ismount(mount):
                # Test write access
                test_file = os.path.join(mount, '.test_write')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    logger.success(f"{mount}: Working")
                    working_mounts += 1
                except (OSError, IOError):
                    logger.warning(f"{mount}: Mounted but no write access")
            else:
                logger.error(f"{mount}: Not mounted")
        except Exception as e:
            logger.error(f"{mount}: Error - {e}")
    
    return working_mounts, total_mounts


def check_celery():
    """Check Celery and Redis status."""
    logger.info("🔍 Checking Celery...")
    
    try:
        from core.tasks import celery_app
        from celery import current_app
        
        # Check Redis connection
        redis_client = current_app.connection()
        redis_client.ensure_connection()
        logger.success("Redis: Connected")
        
        # Check Celery workers
        i = current_app.control.inspect()
        workers = i.active()
        if workers:
            logger.success(f"Celery Workers: {len(workers)} active")
        else:
            logger.warning("Celery Workers: No active workers found")
        
        # Check recent tasks
        task_keys = redis_client.client.keys('celery-task-meta-*')
        logger.info(f"Recent Tasks: {len(task_keys)} found")
        
        return True
        
    except Exception as e:
        logger.error(f"Celery/Redis Error: {e}")
        return False


def check_cablecast_api():
    """Check Cablecast API connection."""
    logger.info("🔍 Checking Cablecast API...")
    
    try:
        vod_service = VODService()
        if vod_service.test_connection():
            logger.success("Cablecast API: Connected")
            return True
        else:
            logger.error("Cablecast API: Connection failed")
            return False
    except Exception as e:
        logger.error(f"Cablecast API Error: {e}")
        return False


def check_system_resources():
    """Check system resource usage."""
    logger.info("🔍 Checking System Resources...")
    
    try:
        # CPU usage
        cpu = psutil.cpu_percent(interval=1)
        logger.info(f"CPU Usage: {cpu}%")
        
        # Memory usage
        memory = psutil.virtual_memory()
        logger.info(f"Memory Usage: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        logger.info(f"Disk Usage: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
        
        # Check if resources are within acceptable limits
        if cpu < 80 and memory.percent < 85 and disk.percent < 90:
            logger.success("System Resources: Within acceptable limits")
            return True
        else:
            logger.warning("System Resources: Some metrics above thresholds")
            return True  # Still operational, just warning
            
    except Exception as e:
        logger.error(f"System Resources Error: {e}")
        return False


def main():
    """Main status check function."""
    logger.info("🚀 VOD Processing System Status Check")
    logger.info("=" * 50)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Run all checks
    try:
        working_mounts, total_mounts = check_flex_mounts()
        celery_ok = check_celery()
        cablecast_ok = check_cablecast_api()
        system_ok = check_system_resources()
        
        # Calculate overall status
        mount_ratio = working_mounts / total_mounts if total_mounts > 0 else 0
        operational_components = sum([mount_ratio >= 0.5, celery_ok, cablecast_ok, system_ok])
        
        logger.info("")
        logger.info("=" * 50)
        logger.info("📊 STATUS SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Flex Mounts: {working_mounts}/{total_mounts} working")
        logger.info(f"Celery/Redis: {'✅ OK' if celery_ok else '❌ FAILED'}")
        logger.info(f"Cablecast API: {'✅ OK' if cablecast_ok else '❌ FAILED'}")
        logger.info(f"System Resources: {'✅ OK' if system_ok else '❌ FAILED'}")
        
        # Determine overall status
        if operational_components >= 3:
            logger.success("🎉 SYSTEM STATUS: OPERATIONAL")
            logger.info("   VOD processing system is ready for production use.")
        elif operational_components >= 2:
            logger.warning("⚠️  SYSTEM STATUS: PARTIALLY OPERATIONAL")
            logger.info("   System can process VODs but some components need attention.")
        else:
            logger.error("❌ SYSTEM STATUS: DEGRADED")
            logger.info("   System needs immediate attention before production use.")
        
        logger.info("")
        logger.info(f"📊 Dashboard: http://localhost:5051")
        logger.info(f"📋 Logs: /opt/Archivist/logs/archivist.log")
        
        return 0 if operational_components >= 3 else 1
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

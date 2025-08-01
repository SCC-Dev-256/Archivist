#!/usr/bin/env python3
"""
Test Celery integration and task functionality.
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logging for tests
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

def test_celery_app():
    """Test Celery application."""
    logger.info("📋 Testing Celery Application...")
    
    try:
        from core.tasks import celery_app
        
        logger.info("✅ Celery app imported successfully")
        
        # Test app configuration
        if hasattr(celery_app, 'conf'):
            logger.info("✅ Celery app has configuration")
        else:
            logger.error("❌ Celery app missing configuration")
            return False
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import Celery app: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing Celery app: {e}")
        return False

def test_task_registration():
    """Test task registration."""
    logger.info("📝 Testing Task Registration...")
    
    try:
        from core.tasks import celery_app
        
        # Get registered tasks
        registered_tasks = list(celery_app.tasks.keys())
        
        # Look for transcription tasks
        transcription_tasks = [task for task in registered_tasks if 'transcription' in task.lower()]
        
        if transcription_tasks:
            logger.info(f"✅ Found {len(transcription_tasks)} transcription tasks")
            for task in transcription_tasks:
                logger.info(f"   - {task}")
        else:
            logger.warning("⚠️ No transcription tasks found")
        
        # Look for VOD tasks
        vod_tasks = [task for task in registered_tasks if 'vod' in task.lower()]
        
        if vod_tasks:
            logger.info(f"✅ Found {len(vod_tasks)} VOD tasks")
            for task in vod_tasks:
                logger.info(f"   - {task}")
        else:
            logger.warning("⚠️ No VOD tasks found")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import tasks: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing task registration: {e}")
        return False

def test_transcription_task():
    """Test transcription task."""
    logger.info("🎤 Testing Transcription Task...")
    
    try:
        from core.tasks.transcription import run_whisper_transcription
        
        logger.info("✅ Transcription task imported")
        
        # Test task function
        if callable(run_whisper_transcription):
            logger.info("✅ Transcription task is callable")
        else:
            logger.error("❌ Transcription task is not callable")
            return False
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import transcription task: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing transcription task: {e}")
        return False

def test_vod_task():
    """Test VOD processing task."""
    logger.info("📺 Testing VOD Processing Task...")
    
    try:
        from core.tasks.vod_processing import process_single_vod
        
        logger.info("✅ VOD processing task imported")
        
        # Test task function
        if callable(process_single_vod):
            logger.info("✅ VOD processing task is callable")
        else:
            logger.error("❌ VOD processing task is not callable")
            return False
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import VOD processing task: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing VOD processing task: {e}")
        return False

def test_celery_configuration():
    """Test Celery configuration."""
    logger.info("⚙️ Testing Celery Configuration...")
    
    try:
        from core.config import Config
        
        config = Config()
        
        # Check required Celery configs
        required_configs = [
            'CELERY_BROKER_URL',
            'CELERY_RESULT_BACKEND'
        ]
        
        missing_configs = []
        for config_name in required_configs:
            if not hasattr(config, config_name):
                missing_configs.append(config_name)
        
        if missing_configs:
            logger.warning(f"⚠️ Missing Celery configs: {missing_configs}")
        else:
            logger.info("✅ All required Celery configurations present")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import configuration: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing Celery configuration: {e}")
        return False

def main():
    """Run all Celery integration tests."""
    logger.info("🚀 Starting Celery Integration Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Celery App", test_celery_app),
        ("Task Registration", test_task_registration),
        ("Transcription Task", test_transcription_task),
        ("VOD Task", test_vod_task),
        ("Celery Configuration", test_celery_configuration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("=" * 50)
    logger.info("📊 Celery Integration Test Results:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Celery integration tests passed!")
        return True
    else:
        logger.error("❌ Some Celery integration tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
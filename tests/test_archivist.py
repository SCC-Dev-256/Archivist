#!/usr/bin/env python3
"""
Test script for the Archivist application.
Tests core functionality and integration.
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

def test_core_imports():
    """Test core module imports."""
    logger.info("🔧 Testing Core Imports...")
    
    core_modules = [
        'core.config',
        'core.app',
        'core.services',
        'core.tasks',
        'core.api',
        'core.monitoring',
        'core.security',
        'core.exceptions'
    ]
    
    success_count = 0
    total_count = len(core_modules)
    
    for module_name in core_modules:
        try:
            __import__(module_name)
            logger.info(f"✅ {module_name} imported successfully")
            success_count += 1
        except ImportError as e:
            logger.error(f"❌ Failed to import {module_name}: {e}")
    
    logger.info(f"📊 Import Results: {success_count}/{total_count} modules imported")
    return success_count == total_count

def test_service_layer():
    """Test service layer functionality."""
    logger.info("🎯 Testing Service Layer...")
    
    try:
        from core.services import TranscriptionService, QueueService
        
        # Test TranscriptionService
        transcription_service = TranscriptionService()
        logger.info("✅ TranscriptionService instantiated")
        
        # Test QueueService
        queue_service = QueueService()
        logger.info("✅ QueueService instantiated")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Service import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Service instantiation error: {e}")
        return False

def test_configuration():
    """Test configuration system."""
    logger.info("⚙️ Testing Configuration...")
    
    try:
        from core.config import Config
        
        config = Config()
        logger.info("✅ Configuration loaded")
        
        # Test essential config values
        required_configs = [
            'SQLALCHEMY_DATABASE_URI',
            'SECRET_KEY',
            'CELERY_BROKER_URL'
        ]
        
        missing_configs = []
        for config_name in required_configs:
            if not hasattr(config, config_name):
                missing_configs.append(config_name)
        
        if missing_configs:
            logger.warning(f"⚠️ Missing configs: {missing_configs}")
        else:
            logger.info("✅ All required configurations present")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Configuration import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        return False

def test_file_system():
    """Test file system access."""
    logger.info("📁 Testing File System...")
    
    # Test flex mounts
    flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4']
    available_mounts = 0
    
    for mount in flex_mounts:
        if os.path.ismount(mount):
            logger.info(f"✅ {mount} available")
            available_mounts += 1
        else:
            logger.warning(f"⚠️ {mount} not available")
    
    if available_mounts > 0:
        logger.info(f"✅ {available_mounts} flex mounts available")
        return True
    else:
        logger.error("❌ No flex mounts available")
        return False

def test_dependencies():
    """Test required dependencies."""
    logger.info("📦 Testing Dependencies...")
    
    dependencies = [
        ('faster_whisper', 'Faster Whisper'),
        ('torch', 'PyTorch'),
        ('transformers', 'Transformers'),
        ('celery', 'Celery'),
        ('flask', 'Flask'),
        ('loguru', 'Loguru'),
        ('requests', 'Requests'),
        ('sqlalchemy', 'SQLAlchemy')
    ]
    
    success_count = 0
    total_count = len(dependencies)
    
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            logger.info(f"✅ {display_name} available")
            success_count += 1
        except ImportError:
            logger.error(f"❌ {display_name} not available")
    
    logger.info(f"📊 Dependency Results: {success_count}/{total_count} dependencies available")
    return success_count == total_count

def main():
    """Run all Archivist tests."""
    logger.info("🚀 Starting Archivist Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Core Imports", test_core_imports),
        ("Service Layer", test_service_layer),
        ("Configuration", test_configuration),
        ("File System", test_file_system),
        ("Dependencies", test_dependencies)
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
    logger.info("📊 Test Results Summary:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Archivist tests passed!")
        return True
    else:
        logger.error("❌ Some Archivist tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
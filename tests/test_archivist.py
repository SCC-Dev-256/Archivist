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
    assert success_count == total_count, f"Only {success_count}/{total_count} modules imported successfully"

def test_service_layer():
    """Test service layer functionality."""
    logger.info("🎯 Testing Service Layer...")
    
    try:
        from core.services import TranscriptionService, QueueService
        
        # Test TranscriptionService
        transcription_service = TranscriptionService()
        logger.info("✅ TranscriptionService instantiated")
        assert transcription_service is not None
        
        # Test QueueService
        queue_service = QueueService()
        logger.info("✅ QueueService instantiated")
        assert queue_service is not None
        
    except ImportError as e:
        logger.error(f"❌ Service import error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Service instantiation error: {e}")
        raise

def test_configuration():
    """Test configuration system."""
    logger.info("⚙️ Testing Configuration...")
    
    try:
        from core.config import MOUNT_POINTS, MEMBER_CITIES, NAS_PATH, OUTPUT_DIR
        
        logger.info("✅ Configuration loaded")
        assert MOUNT_POINTS is not None
        assert MEMBER_CITIES is not None
        assert NAS_PATH is not None
        assert OUTPUT_DIR is not None
        
        # Test essential config values
        required_configs = [
            'NAS_PATH',
            'MOUNT_POINTS', 
            'MEMBER_CITIES',
            'OUTPUT_DIR'
        ]
        
        missing_configs = []
        for config_name in required_configs:
            if config_name not in globals():
                missing_configs.append(config_name)
        
        if missing_configs:
            logger.error(f"❌ Missing required configs: {missing_configs}")
            assert False, f"Missing required configs: {missing_configs}"
        
        logger.info("✅ All required configurations present")
        
    except ImportError as e:
        logger.error(f"❌ Configuration import error: {e}")
        assert False, f"Configuration import failed: {e}"
    except Exception as e:
        logger.error(f"❌ Configuration test error: {e}")
        assert False, f"Configuration test failed: {e}"

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
    
    logger.info(f"📊 Mount Results: {available_mounts}/{len(flex_mounts)} mounts available")
    
    # Test NAS path
    nas_path = os.environ.get('NAS_PATH', '/mnt/nas')
    if os.path.exists(nas_path):
        logger.info(f"✅ NAS path {nas_path} exists")
        assert os.access(nas_path, os.R_OK), f"NAS path {nas_path} not readable"
    else:
        logger.warning(f"⚠️ NAS path {nas_path} does not exist")
    
    # Test output directory
    output_dir = os.environ.get('OUTPUT_DIR', '/tmp/output')
    if os.path.exists(output_dir):
        logger.info(f"✅ Output directory {output_dir} exists")
        assert os.access(output_dir, os.W_OK), f"Output directory {output_dir} not writable"
    else:
        logger.warning(f"⚠️ Output directory {output_dir} does not exist")
    
    # Assert that at least some mounts are available
    assert available_mounts > 0, "No flex mounts available"

def test_dependencies():
    """Test required dependencies."""
    logger.info("📦 Testing Dependencies...")
    
    required_packages = [
        'flask',
        'celery',
        'redis',
        'sqlalchemy',
        'loguru',
        'requests',
        'pydantic'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package} available")
        except ImportError:
            logger.error(f"❌ {package} not available")
            missing_packages.append(package)
    
    logger.info(f"📊 Dependency Results: {len(required_packages) - len(missing_packages)}/{len(required_packages)} packages available")
    assert len(missing_packages) == 0, f"Missing packages: {missing_packages}"

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
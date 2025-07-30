#!/usr/bin/env python3
"""
Debug Import Chain Test

This script tests each import step to identify exactly where the hanging occurs.
"""

import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_import_step(step_name, import_func):
    """Test a single import step with timing."""
    print(f"🔍 Testing: {step_name}")
    start_time = time.time()
    
    try:
        result = import_func()
        end_time = time.time()
        duration = end_time - start_time
        print(f"✅ {step_name}: SUCCESS ({duration:.2f}s)")
        return True, duration
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ {step_name}: FAILED ({duration:.2f}s) - {e}")
        return False, duration

def test_basic_imports():
    """Test basic Python imports."""
    print("\n=== Testing Basic Imports ===")
    
    # Test 1: Basic Python modules
    test_import_step("os module", lambda: __import__('os'))
    test_import_step("sys module", lambda: __import__('sys'))
    test_import_step("pathlib module", lambda: __import__('pathlib'))
    test_import_step("time module", lambda: __import__('time'))

def test_core_exceptions():
    """Test core exceptions import."""
    print("\n=== Testing Core Exceptions ===")
    
    test_import_step("core.exceptions", lambda: __import__('core.exceptions'))

def test_core_models():
    """Test core models import."""
    print("\n=== Testing Core Models ===")
    
    test_import_step("core.models", lambda: __import__('core.models'))

def test_core_file_manager():
    """Test core file manager import."""
    print("\n=== Testing Core File Manager ===")
    
    test_import_step("core.file_manager", lambda: __import__('core.file_manager'))

def test_core_security():
    """Test core security import."""
    print("\n=== Testing Core Security ===")
    
    test_import_step("core.security", lambda: __import__('core.security'))

def test_core_vod_content_manager():
    """Test core VOD content manager import."""
    print("\n=== Testing Core VOD Content Manager ===")
    
    test_import_step("core.vod_content_manager", lambda: __import__('core.vod_content_manager'))

def test_core_config():
    """Test core config import."""
    print("\n=== Testing Core Config ===")
    
    test_import_step("core.config", lambda: __import__('core.config'))

def test_core_tasks():
    """Test core tasks import (likely to hang)."""
    print("\n=== Testing Core Tasks (Potential Hang) ===")
    
    test_import_step("core.tasks", lambda: __import__('core.tasks'))

def test_core_unified_queue_manager():
    """Test core unified queue manager import (likely to hang)."""
    print("\n=== Testing Core Unified Queue Manager (Potential Hang) ===")
    
    test_import_step("core.unified_queue_manager", lambda: __import__('core.unified_queue_manager'))

def test_core_monitoring():
    """Test core monitoring import (likely to hang)."""
    print("\n=== Testing Core Monitoring (Potential Hang) ===")
    
    test_import_step("core.monitoring.integrated_dashboard", lambda: __import__('core.monitoring.integrated_dashboard'))

def test_core_services():
    """Test core services import."""
    print("\n=== Testing Core Services ===")
    
    test_import_step("core.services", lambda: __import__('core.services'))

def test_core_admin_ui():
    """Test core admin UI import (likely to hang)."""
    print("\n=== Testing Core Admin UI (Potential Hang) ===")
    
    test_import_step("core.admin_ui", lambda: __import__('core.admin_ui'))

def test_core_app():
    """Test core app import."""
    print("\n=== Testing Core App ===")
    
    test_import_step("core.app", lambda: __import__('core.app'))

def test_full_core_import():
    """Test full core import (likely to hang)."""
    print("\n=== Testing Full Core Import (Potential Hang) ===")
    
    test_import_step("core", lambda: __import__('core'))

def main():
    """Run all import tests."""
    print("🔍 DEBUGGING IMPORT CHAIN")
    print("=" * 50)
    
    # Test basic imports first
    test_basic_imports()
    
    # Test core components in order
    test_core_exceptions()
    test_core_models()
    test_core_file_manager()
    test_core_security()
    test_core_vod_content_manager()
    test_core_config()
    
    # Test potentially problematic imports
    print("\n⚠️  WARNING: Next tests may hang!")
    print("Press Ctrl+C if any test hangs for more than 10 seconds")
    
    try:
        test_core_tasks()
    except KeyboardInterrupt:
        print("⏹️  core.tasks import was interrupted (likely hanging)")
    
    try:
        test_core_unified_queue_manager()
    except KeyboardInterrupt:
        print("⏹️  core.unified_queue_manager import was interrupted (likely hanging)")
    
    try:
        test_core_monitoring()
    except KeyboardInterrupt:
        print("⏹️  core.monitoring import was interrupted (likely hanging)")
    
    # Test services
    test_core_services()
    
    try:
        test_core_admin_ui()
    except KeyboardInterrupt:
        print("⏹️  core.admin_ui import was interrupted (likely hanging)")
    
    # Test app
    test_core_app()
    
    try:
        test_full_core_import()
    except KeyboardInterrupt:
        print("⏹️  Full core import was interrupted (likely hanging)")
    
    print("\n" + "=" * 50)
    print("🔍 IMPORT CHAIN DEBUGGING COMPLETE")

if __name__ == "__main__":
    main() 
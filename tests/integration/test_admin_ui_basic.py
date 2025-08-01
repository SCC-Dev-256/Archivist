#!/usr/bin/env python3
"""
Basic Admin UI Tests

This module contains very basic tests that verify Admin UI file structure
and imports without instantiating the AdminUI class to avoid hanging issues.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def test_admin_ui_file_exists():
    """Test that admin_ui.py file exists and has content."""
    logger.info("Testing Admin UI file existence")
    
    admin_ui_file = Path("core/admin_ui.py")
    assert admin_ui_file.exists(), "admin_ui.py should exist"
    
    # Check file size
    file_size = admin_ui_file.stat().st_size
    assert file_size > 1000, f"admin_ui.py should be substantial (current: {file_size} bytes)"
    logger.info(f"✅ AdminUI file exists and has {file_size} bytes")
    
    return True


def test_admin_ui_file_content():
    """Test that admin_ui.py contains expected content."""
    logger.info("Testing Admin UI file content")
    
    admin_ui_file = Path("core/admin_ui.py")
    
    with open(admin_ui_file, 'r') as f:
        content = f.read()
    
    # Verify key components exist in the file
    required_elements = [
        'class AdminUI:',
        'def __init__',
        'def _register_routes',
        'def _render_admin_dashboard',
        'def _get_system_status',
        'def _start_embedded_dashboard',
        'def run',
        'Flask',
        'CORS',
        'UnifiedQueueManager'
    ]
    
    for element in required_elements:
        assert element in content, f"admin_ui.py should contain '{element}'"
    
    logger.info("✅ AdminUI file contains all required elements")
    return True


def test_admin_ui_imports():
    """Test that admin_ui.py can be imported without errors."""
    logger.info("Testing Admin UI imports")
    
    try:
        # Test basic import
        import core.admin_ui
        assert core.admin_ui is not None, "core.admin_ui should import successfully"
        logger.info("✅ core.admin_ui import successful")
        
        # Test class import
        from core.admin_ui import AdminUI
        assert AdminUI is not None, "AdminUI class should be available"
        logger.info("✅ AdminUI class import successful")
        
        # Test function import
        from core.admin_ui import start_admin_ui
        assert start_admin_ui is not None, "start_admin_ui function should be available"
        logger.info("✅ start_admin_ui function import successful")
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        raise
    
    return True


def test_admin_ui_dependencies():
    """Test that AdminUI dependencies are available."""
    logger.info("Testing Admin UI dependencies")
    
    try:
        # Test Flask
        import flask
        assert flask is not None, "Flask should be available"
        logger.info("✅ Flask import successful")
        
        # Test Flask-CORS
        import flask_cors
        assert flask_cors is not None, "Flask-CORS should be available"
        logger.info("✅ Flask-CORS import successful")
        
        # Test core dependencies
        from core import MEMBER_CITIES, IntegratedDashboard, UnifiedQueueManager, celery_app
        assert MEMBER_CITIES is not None, "MEMBER_CITIES should be available"
        assert IntegratedDashboard is not None, "IntegratedDashboard should be available"
        assert UnifiedQueueManager is not None, "UnifiedQueueManager should be available"
        assert celery_app is not None, "celery_app should be available"
        logger.info("✅ Core dependencies import successful")
        
    except ImportError as e:
        logger.error(f"❌ Dependency import failed: {e}")
        raise
    
    return True


def test_admin_ui_template_exists():
    """Test that admin UI template file exists."""
    logger.info("Testing Admin UI template existence")
    
    template_file = Path("core/templates/index.html")
    assert template_file.exists(), "index.html template should exist"
    
    # Check file size
    file_size = template_file.stat().st_size
    assert file_size > 1000, f"index.html should be substantial (current: {file_size} bytes)"
    logger.info(f"✅ Admin UI template exists and has {file_size} bytes")
    
    return True


def test_admin_ui_template_content():
    """Test that admin UI template contains expected content."""
    logger.info("Testing Admin UI template content")
    
    template_file = Path("core/templates/index.html")
    
    with open(template_file, 'r') as f:
        content = f.read()
    
    # Verify key elements exist in the template
    required_elements = [
        '<!DOCTYPE html>',
        '<html',
        '<head>',
        '<body>',
        'Archivist',
        'Video Transcription',
        'tailwind.min.css',
        'socket.io'
    ]
    
    for element in required_elements:
        assert element in content, f"index.html should contain '{element}'"
    
    logger.info("✅ Admin UI template contains all required elements")
    return True


def test_admin_ui_static_files():
    """Test that admin UI static files exist."""
    logger.info("Testing Admin UI static files")
    
    static_dir = Path("core/static")
    assert static_dir.exists(), "static directory should exist"
    assert static_dir.is_dir(), "static should be a directory"
    
    # Check for CSS directory
    css_dir = static_dir / "css"
    assert css_dir.exists(), "css directory should exist"
    assert css_dir.is_dir(), "css should be a directory"
    
    # Check for favicon
    favicon_file = static_dir / "favicon.ico"
    assert favicon_file.exists(), "favicon.ico should exist"
    
    logger.info("✅ Admin UI static files exist")
    return True


def run_admin_ui_basic_tests():
    """Run all basic admin UI tests."""
    logger.info("Starting Basic Admin UI Tests")
    
    # Define test functions
    test_functions = [
        test_admin_ui_file_exists,
        test_admin_ui_file_content,
        test_admin_ui_imports,
        test_admin_ui_dependencies,
        test_admin_ui_template_exists,
        test_admin_ui_template_content,
        test_admin_ui_static_files
    ]
    
    results = []
    for test_func in test_functions:
        try:
            success = test_func()
            results.append((test_func.__name__, success, "Passed"))
            logger.info(f"✅ {test_func.__name__}: PASSED")
        except Exception as e:
            results.append((test_func.__name__, False, str(e)))
            logger.error(f"❌ {test_func.__name__}: FAILED - {e}")
    
    # Generate summary
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    logger.info(f"\n📊 Basic Admin UI Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_admin_ui_basic_tests()
    sys.exit(0 if success else 1) 
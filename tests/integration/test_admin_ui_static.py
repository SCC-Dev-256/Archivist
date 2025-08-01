#!/usr/bin/env python3
"""
Static Admin UI Tests

This module performs static analysis of Admin UI files without importing
any modules to avoid hanging issues.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def test_admin_ui_file_structure():
    """Test Admin UI file structure without importing."""
    logger.info("Testing Admin UI file structure (static analysis)")
    
    # Test main admin UI file
    admin_ui_file = Path("core/admin_ui.py")
    assert admin_ui_file.exists(), "admin_ui.py should exist"
    
    file_size = admin_ui_file.stat().st_size
    assert file_size > 1000, f"admin_ui.py should be substantial (current: {file_size} bytes)"
    logger.info(f"✅ AdminUI file exists and has {file_size} bytes")
    
    # Read file content
    with open(admin_ui_file, 'r') as f:
        content = f.read()
    
    # Verify key components exist
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


def test_admin_ui_template_structure():
    """Test Admin UI template structure."""
    logger.info("Testing Admin UI template structure")
    
    template_file = Path("core/templates/index.html")
    assert template_file.exists(), "index.html template should exist"
    
    file_size = template_file.stat().st_size
    assert file_size > 1000, f"index.html should be substantial (current: {file_size} bytes)"
    logger.info(f"✅ Admin UI template exists and has {file_size} bytes")
    
    # Read template content
    with open(template_file, 'r') as f:
        content = f.read()
    
    # Verify key elements
    required_elements = [
        '<!DOCTYPE html>',
        '<html',
        '<head>',
        '<body>',
        'Archivist',
        'Video Transcription'
    ]
    
    for element in required_elements:
        assert element in content, f"index.html should contain '{element}'"
    
    logger.info("✅ Admin UI template contains all required elements")
    return True


def test_admin_ui_static_files():
    """Test Admin UI static files exist."""
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


def test_admin_ui_code_quality():
    """Test Admin UI code quality indicators."""
    logger.info("Testing Admin UI code quality")
    
    admin_ui_file = Path("core/admin_ui.py")
    
    with open(admin_ui_file, 'r') as f:
        content = f.read()
    
    # Check for good practices
    quality_indicators = [
        '"""',  # Docstrings
        'logger',  # Logging
        'try:',  # Error handling
        'except',  # Exception handling
        'def ',  # Function definitions
        'class ',  # Class definitions
    ]
    
    for indicator in quality_indicators:
        assert indicator in content, f"admin_ui.py should contain '{indicator}' for good code quality"
    
    logger.info("✅ Admin UI code quality indicators present")
    return True


def test_admin_ui_routes_structure():
    """Test Admin UI routes structure."""
    logger.info("Testing Admin UI routes structure")
    
    admin_ui_file = Path("core/admin_ui.py")
    
    with open(admin_ui_file, 'r') as f:
        content = f.read()
    
    # Check for route definitions
    route_indicators = [
        '@self.app.route',
        'def api_admin_status',
        'def api_admin_cities',
        'def api_admin_queue_summary',
        'def api_admin_celery_summary',
        'def api_admin_trigger_task',
        'def api_admin_queue_cleanup'
    ]
    
    for indicator in route_indicators:
        assert indicator in content, f"admin_ui.py should contain '{indicator}' for API routes"
    
    logger.info("✅ Admin UI routes structure verified")
    return True


def run_admin_ui_static_tests():
    """Run all static admin UI tests."""
    logger.info("Starting Static Admin UI Tests")
    
    # Define test functions
    test_functions = [
        test_admin_ui_file_structure,
        test_admin_ui_template_structure,
        test_admin_ui_static_files,
        test_admin_ui_code_quality,
        test_admin_ui_routes_structure
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
    
    logger.info(f"\n📊 Static Admin UI Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_admin_ui_static_tests()
    sys.exit(0 if success else 1) 
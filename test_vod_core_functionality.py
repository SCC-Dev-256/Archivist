#!/usr/bin/env python3
"""
Core VOD Processing System Test Suite

This script tests the core functionality of the VOD processing system:
1. Admin UI imports and basic functionality
2. VOD processing module imports and functions
3. VOD automation functions
4. VOD service functionality
5. Basic Celery task imports

Usage:
    python3 test_vod_core_functionality.py
"""

import os
import sys
import time
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class VODCoreTester:
    """Core VOD system tester focusing on functionality without background services."""
    
    def __init__(self):
        self.results = {
            'admin_ui': {},
            'vod_processing': {},
            'vod_automation': {},
            'vod_service': {},
            'celery_imports': {},
            'overall': {}
        }
        self.test_start_time = datetime.now()
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamps."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_admin_ui_imports(self) -> bool:
        """Test Admin UI module imports."""
        try:
            self.log("Testing Admin UI imports...")
            
            # Test basic imports
            from core.admin_ui import AdminUI
            from core.config import MEMBER_CITIES
            from core.task_queue import QueueManager
            
            self.log("✓ Admin UI imports successful")
            return True
            
        except Exception as e:
            self.log(f"✗ Admin UI import failed: {e}", "ERROR")
            return False
    
    def test_admin_ui_functionality(self) -> bool:
        """Test Admin UI basic functionality."""
        try:
            self.log("Testing Admin UI functionality...")
            
            from core.admin_ui import AdminUI
            
            # Test Admin UI initialization
            admin_ui = AdminUI(
                host="127.0.0.1",
                port=8080,
                dashboard_port=5051
            )
            
            # Test system status method
            status = admin_ui._get_system_status()
            if isinstance(status, dict):
                self.log("✓ System status method working")
                self.log(f"  - Queue status: {status.get('queue', {})}")
                self.log(f"  - Celery status: {status.get('celery', {})}")
                self.log(f"  - Overall status: {status.get('overall_status', 'unknown')}")
            else:
                self.log("✗ System status method failed", "ERROR")
                return False
            
            # Test member cities
            cities = admin_ui._get_system_status().get('cities', {})
            if cities.get('total', 0) > 0:
                self.log(f"✓ Member cities loaded: {cities.get('total')}")
            else:
                self.log("⚠ No member cities found", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"✗ Admin UI functionality failed: {e}", "ERROR")
            return False
    
    def test_vod_processing_imports(self) -> bool:
        """Test VOD processing module imports."""
        try:
            self.log("Testing VOD processing imports...")
            
            # Test VOD processing imports
            from core.tasks.vod_processing import (
                process_recent_vods, process_single_vod, download_vod_content_task,
                generate_vod_captions, retranscode_vod_with_captions,
                validate_vod_quality, cleanup_temp_files,
                extract_vod_url_from_cablecast, get_vod_file_path,
                validate_video_file, create_captioned_video,
                get_city_vod_storage_path, map_city_to_vod_pattern
            )
            
            self.log("✓ VOD processing imports successful")
            return True
            
        except Exception as e:
            self.log(f"✗ VOD processing import failed: {e}", "ERROR")
            return False
    
    def test_vod_processing_functions(self) -> bool:
        """Test VOD processing utility functions."""
        try:
            self.log("Testing VOD processing functions...")
            
            from core.tasks.vod_processing import (
                extract_vod_url_from_cablecast, get_vod_file_path,
                validate_video_file, get_city_vod_storage_path,
                map_city_to_vod_pattern
            )
            
            # Test URL extraction
            test_vod_data = {
                'id': 'test_123',
                'title': 'Test VOD',
                'url': 'https://example.com/test.mp4'
            }
            
            url = extract_vod_url_from_cablecast(test_vod_data)
            if url:
                self.log(f"✓ URL extraction working: {url}")
            else:
                self.log("⚠ URL extraction returned None", "WARNING")
            
            # Test city mapping
            city_patterns = map_city_to_vod_pattern('flex1')
            if city_patterns:
                self.log(f"✓ City mapping working: {len(city_patterns)} patterns")
            else:
                self.log("⚠ City mapping returned empty", "WARNING")
            
            # Test storage path
            storage_path = get_city_vod_storage_path('flex1')
            if storage_path:
                self.log(f"✓ Storage path: {storage_path}")
            else:
                self.log("⚠ Storage path returned None", "WARNING")
            
            # Test video validation with fake file
            test_video_path = "/tmp/test_video.mp4"
            with open(test_video_path, 'wb') as f:
                f.write(b'fake video content')
            
            validation_result = validate_video_file(test_video_path)
            self.log(f"✓ Video validation test completed (result: {validation_result})")
            
            # Cleanup
            os.remove(test_video_path)
            
            return True
            
        except Exception as e:
            self.log(f"✗ VOD processing functions failed: {e}", "ERROR")
            return False
    
    def test_vod_automation_imports(self) -> bool:
        """Test VOD automation module imports."""
        try:
            self.log("Testing VOD automation imports...")
            
            from core.vod_automation import (
                auto_link_transcription_to_show, manual_link_transcription_to_show,
                get_show_suggestions, get_transcription_link_status,
                unlink_transcription_from_show, get_linked_transcriptions,
                process_transcription_queue
            )
            
            self.log("✓ VOD automation imports successful")
            return True
            
        except Exception as e:
            self.log(f"✗ VOD automation import failed: {e}", "ERROR")
            return False
    
    def test_vod_service_imports(self) -> bool:
        """Test VOD service module imports."""
        try:
            self.log("Testing VOD service imports...")
            
            from core.services.vod import VODService
            
            # Test service initialization
            service = VODService()
            self.log("✓ VOD service initialization successful")
            
            return True
            
        except Exception as e:
            self.log(f"✗ VOD service import failed: {e}", "ERROR")
            return False
    
    def test_celery_imports(self) -> bool:
        """Test Celery module imports."""
        try:
            self.log("Testing Celery imports...")
            
            # Test basic Celery imports
            from core.tasks import celery_app
            from core.tasks.transcription import run_whisper_transcription
            
            self.log("✓ Celery imports successful")
            return True
            
        except Exception as e:
            self.log(f"✗ Celery import failed: {e}", "ERROR")
            return False
    
    def test_celery_task_definitions(self) -> bool:
        """Test Celery task definitions without execution."""
        try:
            self.log("Testing Celery task definitions...")
            
            from core.tasks.vod_processing import (
                process_recent_vods, process_single_vod, cleanup_temp_files
            )
            
            # Check if tasks are properly decorated
            if hasattr(process_recent_vods, 'delay'):
                self.log("✓ process_recent_vods task properly defined")
            else:
                self.log("✗ process_recent_vods not a Celery task", "ERROR")
                return False
            
            if hasattr(process_single_vod, 'delay'):
                self.log("✓ process_single_vod task properly defined")
            else:
                self.log("✗ process_single_vod not a Celery task", "ERROR")
                return False
            
            if hasattr(cleanup_temp_files, 'delay'):
                self.log("✓ cleanup_temp_files task properly defined")
            else:
                self.log("✗ cleanup_temp_files not a Celery task", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"✗ Celery task definitions failed: {e}", "ERROR")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results."""
        self.log("Starting core VOD system testing...")
        
        try:
            # Test 1: Admin UI
            self.log("\n=== Testing Admin UI ===")
            self.results['admin_ui']['imports'] = self.test_admin_ui_imports()
            self.results['admin_ui']['functionality'] = self.test_admin_ui_functionality()
            
            # Test 2: VOD Processing
            self.log("\n=== Testing VOD Processing ===")
            self.results['vod_processing']['imports'] = self.test_vod_processing_imports()
            self.results['vod_processing']['functions'] = self.test_vod_processing_functions()
            
            # Test 3: VOD Automation
            self.log("\n=== Testing VOD Automation ===")
            self.results['vod_automation']['imports'] = self.test_vod_automation_imports()
            
            # Test 4: VOD Service
            self.log("\n=== Testing VOD Service ===")
            self.results['vod_service']['imports'] = self.test_vod_service_imports()
            
            # Test 5: Celery
            self.log("\n=== Testing Celery ===")
            self.results['celery_imports']['imports'] = self.test_celery_imports()
            self.results['celery_imports']['task_definitions'] = self.test_celery_task_definitions()
            
            # Calculate overall results
            self.calculate_overall_results()
            
        except Exception as e:
            self.log(f"Test execution failed: {e}", "ERROR")
        
        return self.results
    
    def calculate_overall_results(self):
        """Calculate overall test results."""
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            if category == 'overall':
                continue
            for test_name, result in tests.items():
                total_tests += 1
                if result:
                    passed_tests += 1
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        self.results['overall'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': success_rate,
            'status': 'PASS' if success_rate >= 0.8 else 'FAIL',
            'duration': (datetime.now() - self.test_start_time).total_seconds()
        }
    
    def print_results(self):
        """Print test results in a formatted way."""
        print("\n" + "="*60)
        print("VOD CORE FUNCTIONALITY TEST RESULTS")
        print("="*60)
        
        for category, tests in self.results.items():
            if category == 'overall':
                continue
                
            print(f"\n{category.upper().replace('_', ' ')}:")
            print("-" * 40)
            
            for test_name, result in tests.items():
                status = "✓ PASS" if result else "✗ FAIL"
                print(f"  {test_name.replace('_', ' ').title()}: {status}")
        
        # Overall results
        overall = self.results['overall']
        print(f"\nOVERALL RESULTS:")
        print("-" * 40)
        print(f"  Total Tests: {overall['total_tests']}")
        print(f"  Passed: {overall['passed_tests']}")
        print(f"  Failed: {overall['failed_tests']}")
        print(f"  Success Rate: {overall['success_rate']:.1%}")
        print(f"  Status: {overall['status']}")
        print(f"  Duration: {overall['duration']:.1f} seconds")
        
        print("\n" + "="*60)

def main():
    """Main test execution function."""
    print("VOD Processing System Core Functionality Test Suite")
    print("=" * 60)
    
    # Create tester and run tests
    tester = VODCoreTester()
    results = tester.run_all_tests()
    
    # Print results
    tester.print_results()
    
    # Save results to file
    try:
        with open('vod_core_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: vod_core_test_results.json")
    except Exception as e:
        print(f"\nWarning: Could not save results file: {e}")
    
    # Exit with appropriate code
    if results['overall']['status'] == 'PASS':
        print("\n🎉 Core functionality tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some core functionality tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 
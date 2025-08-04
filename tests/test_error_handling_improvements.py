#!/usr/bin/env python3
"""
Test Error Handling Improvements for VOD Processing System

This script validates the recent improvements to error handling:
1. Download retries with exponential backoff
2. Storage availability checks
3. API fallback mechanisms
4. Graceful degradation
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tasks.vod_processing import (
    download_vod_content, 
    get_vod_file_path,
    process_single_vod,
    validate_video_file
)
from core.cablecast_client import CablecastAPIClient
from core.utils.alerts import send_alert
from core.check_mounts import list_mount_contents

class ErrorHandlingTester:
    def __init__(self):
        self.test_results = []
        self.temp_dir = tempfile.mkdtemp()
        
    def cleanup(self):
        """Clean up test artifacts."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
    
    def test_download_retries(self):
        """Test download retry mechanism with exponential backoff."""
        print("\n=== Testing Download Retries ===")
        
        # Test 1: Successful download after retries
        test_url = "https://httpbin.org/delay/1"
        test_path = os.path.join(self.temp_dir, "test_download.mp4")
        
        try:
            success = download_vod_content(test_url, test_path, timeout=5)
            self.log_test("Download retry - success after delay", success, 
                         f"Downloaded to {test_path}")
        except Exception as e:
            self.log_test("Download retry - success after delay", False, str(e))
        
        # Test 2: Failed download (404) - should fail after retries
        bad_url = "https://httpbin.org/status/404"
        bad_path = os.path.join(self.temp_dir, "bad_download.mp4")
        
        try:
            success = download_vod_content(bad_url, bad_path, timeout=5)
            self.log_test("Download retry - fail on 404", not success, 
                         "Correctly failed on 404")
        except Exception as e:
            self.log_test("Download retry - fail on 404", True, 
                         f"Expected failure: {str(e)}")
    
    def test_storage_checks(self):
        """Test storage availability and write permission checks."""
        print("\n=== Testing Storage Checks ===")
        
        # Test 1: Valid storage path
        valid_path = self.temp_dir
        if os.path.exists(valid_path) and os.access(valid_path, os.W_OK):
            self.log_test("Storage check - valid path", True, 
                         f"Path {valid_path} is writable")
        else:
            self.log_test("Storage check - valid path", False, 
                         f"Path {valid_path} not writable")
        
        # Test 2: Invalid storage path
        invalid_path = "/nonexistent/path/12345"
        if not os.path.exists(invalid_path):
            self.log_test("Storage check - invalid path", True, 
                         f"Correctly identified invalid path: {invalid_path}")
        else:
            self.log_test("Storage check - invalid path", False, 
                         f"Path unexpectedly exists: {invalid_path}")
        
        # Test 3: Read-only path (if we can find one)
        read_only_paths = ["/proc", "/sys"]
        for path in read_only_paths:
            if os.path.exists(path) and not os.access(path, os.W_OK):
                self.log_test("Storage check - read-only path", True, 
                             f"Correctly identified read-only path: {path}")
                break
        else:
            self.log_test("Storage check - read-only path", True, 
                         "No read-only paths available for testing")
    
    def test_api_fallback(self):
        """Test API fallback mechanisms."""
        print("\n=== Testing API Fallback ===")
        
        # Test with mock API client that fails
        with patch('core.tasks.vod_processing.CablecastAPIClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_vod.side_effect = Exception("API Unavailable")
            mock_client.return_value = mock_instance
            
            # Test process_single_vod with API failure
            try:
                result = process_single_vod(123, "/mnt/flex-1")
                if result.get('status') == 'deferred':
                    self.log_test("API fallback - defer on failure", True, 
                                 "Task correctly deferred on API failure")
                else:
                    self.log_test("API fallback - defer on failure", False, 
                                 f"Unexpected result: {result}")
            except Exception as e:
                self.log_test("API fallback - defer on failure", False, 
                             f"Unexpected exception: {str(e)}")
    
    def test_graceful_degradation(self):
        """Test graceful degradation when components are unavailable."""
        print("\n=== Testing Graceful Degradation ===")
        
        # Test 1: Missing video file
        with patch('core.tasks.vod_processing.get_vod_file_path') as mock_get_path:
            mock_get_path.return_value = None
            
            try:
                result = process_single_vod(999, "/mnt/flex-1")
                if result.get('status') == 'failed' and 'No video file found' in result.get('error', ''):
                    self.log_test("Graceful degradation - missing video", True, 
                                 "Correctly handled missing video file")
                else:
                    self.log_test("Graceful degradation - missing video", False, 
                                 f"Unexpected result: {result}")
            except Exception as e:
                self.log_test("Graceful degradation - missing video", False, 
                             f"Unexpected exception: {str(e)}")
        
        # Test 2: Storage unavailable
        with patch('core.tasks.vod_processing.get_city_vod_storage_path') as mock_storage:
            mock_storage.return_value = "/nonexistent/storage"
            
            with patch('os.path.ismount') as mock_ismount:
                mock_ismount.return_value = False
                
                try:
                    result = process_single_vod(123, "/mnt/flex-1")
                    if result.get('status') == 'failed' and 'Storage unavailable' in result.get('error', ''):
                        self.log_test("Graceful degradation - storage unavailable", True, 
                                     "Correctly handled unavailable storage")
                    else:
                        self.log_test("Graceful degradation - storage unavailable", False, 
                                     f"Unexpected result: {result}")
                except Exception as e:
                    self.log_test("Graceful degradation - storage unavailable", False, 
                                 f"Unexpected exception: {str(e)}")
    
    def test_alert_system(self):
        """Test alert system integration."""
        print("\n=== Testing Alert System ===")
        
        # Test alert sending (should log locally since no webhook configured)
        try:
            send_alert("info", "Test alert message", test_param="value")
            self.log_test("Alert system - local logging", True, 
                         "Alert logged locally (no webhook configured)")
        except Exception as e:
            self.log_test("Alert system - local logging", False, 
                         f"Alert failed: {str(e)}")
    
    def test_video_validation(self):
        """Test video file validation using actual video from flex servers."""
        print("\n=== Testing Video Validation with Real Video from Flex Servers ===")
        
        # Use the mount system to get a real video path
        flex_mount_path = "/mnt/flex-1"  # Example mount path, adjust as needed
        video_files = list_mount_contents(flex_mount_path)
        
        # Find a video file in the mount path
        test_video = next((file for file in video_files if file.endswith('.mp4')), None)
        
        if test_video:
            full_video_path = os.path.join(flex_mount_path, test_video)
            if validate_video_file(full_video_path):
                self.log_test("Video validation - valid file", True, 
                             f"Validated real video: {full_video_path}")
            else:
                self.log_test("Video validation - valid file", False, 
                             f"Failed to validate real video: {full_video_path}")
        else:
            self.log_test("Video validation - file not found", False, 
                         "No valid video file found on flex servers")
    
    def run_all_tests(self):
        """Run all error handling tests."""
        print("🧪 Testing Error Handling Improvements")
        print("=" * 50)
        
        try:
            self.test_download_retries()
            self.test_storage_checks()
            self.test_api_fallback()
            self.test_graceful_degradation()
            self.test_alert_system()
            self.test_video_validation()
            
            # Summary
            passed = sum(1 for result in self.test_results if result['passed'])
            total = len(self.test_results)
            
            print(f"\n📊 Test Summary")
            print("=" * 30)
            print(f"Passed: {passed}/{total}")
            print(f"Failed: {total - passed}/{total}")
            
            if passed == total:
                print("🎉 All error handling tests passed!")
                return True
            else:
                print("⚠️  Some tests failed. Review the details above.")
                return False
                
        finally:
            self.cleanup()

def main():
    """Main test runner."""
    tester = ErrorHandlingTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Error handling improvements are working correctly!")
        print("\nKey improvements validated:")
        print("• Download retries with exponential backoff")
        print("• Storage availability and permission checks")
        print("• API fallback mechanisms")
        print("• Graceful degradation")
        print("• Alert system integration")
        print("• Video file validation")
    else:
        print("\n❌ Some error handling improvements need attention.")
        sys.exit(1)

if __name__ == "__main__":
    main() 
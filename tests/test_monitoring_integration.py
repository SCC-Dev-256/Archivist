#!/usr/bin/env python3
"""
Test Monitoring System Integration

This script validates the comprehensive monitoring system integration including:
1. Metrics collection and tracking
2. Health checks for storage, API, and system
3. Circuit breaker functionality
4. Dashboard functionality
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.monitoring.metrics import get_metrics_collector, CircuitBreaker
from core.monitoring.health_checks import get_health_manager
from core.monitoring.dashboard import MonitoringDashboard
from core.tasks.vod_processing import download_vod_content, process_single_vod

class MonitoringIntegrationTester:
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
    
    def test_metrics_collection(self):
        """Test metrics collection functionality."""
        print("\n=== Testing Metrics Collection ===")
        
        metrics = get_metrics_collector()
        
        # Test counter metrics
        metrics.increment("test_counter")
        metrics.increment("test_counter", 5)
        
        summary = metrics.get_metrics_summary(time_window=3600)
        if "test_counter" in summary and summary["test_counter"] == 6:
            self.log_test("Metrics collection - counter", True, 
                         f"Counter value: {summary['test_counter']}")
        else:
            self.log_test("Metrics collection - counter", False, 
                         f"Expected 6, got {summary.get('test_counter', 'missing')}")
        
        # Test gauge metrics
        metrics.gauge("test_gauge", 42.5)
        summary = metrics.get_metrics_summary(time_window=3600)
        if "test_gauge" in summary and summary["test_gauge"] == 42.5:
            self.log_test("Metrics collection - gauge", True, 
                         f"Gauge value: {summary['test_gauge']}")
        else:
            self.log_test("Metrics collection - gauge", False, 
                         f"Expected 42.5, got {summary.get('test_gauge', 'missing')}")
        
        # Test histogram metrics
        metrics.histogram("test_histogram", 10.5)
        metrics.histogram("test_histogram", 20.3)
        metrics.histogram("test_histogram", 15.7)
        
        summary = metrics.get_metrics_summary(time_window=3600)
        if "test_histogram" in summary:
            hist_data = summary["test_histogram"]
            if hist_data["count"] == 3 and hist_data["avg"] > 15:
                self.log_test("Metrics collection - histogram", True, 
                             f"Histogram: count={hist_data['count']}, avg={hist_data['avg']:.1f}")
            else:
                self.log_test("Metrics collection - histogram", False, 
                             f"Unexpected histogram data: {hist_data}")
        else:
            self.log_test("Metrics collection - histogram", False, "Histogram not found")
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        print("\n=== Testing Circuit Breaker ===")
        
        # Test successful calls
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
        
        def successful_func():
            return "success"
        
        try:
            result = cb.call(successful_func)
            if result == "success":
                self.log_test("Circuit breaker - successful call", True, 
                             f"Result: {result}")
            else:
                self.log_test("Circuit breaker - successful call", False, 
                             f"Expected 'success', got {result}")
        except Exception as e:
            self.log_test("Circuit breaker - successful call", False, 
                         f"Unexpected exception: {e}")
        
        # Test failure handling
        def failing_func():
            raise Exception("Test failure")
        
        failure_count = 0
        for i in range(4):  # Should trigger circuit breaker
            try:
                cb.call(failing_func)
            except (ConnectionError, TimeoutError):
                failure_count += 1
        
        status = cb.get_status()
        if status["state"] == "OPEN" and failure_count >= 3:
            self.log_test("Circuit breaker - failure handling", True, 
                         f"State: {status['state']}, failures: {failure_count}")
        else:
            self.log_test("Circuit breaker - failure handling", False, 
                         f"State: {status['state']}, failures: {failure_count}")
    
    def test_health_checks(self):
        """Test health check functionality."""
        print("\n=== Testing Health Checks ===")
        
        health_manager = get_health_manager()
        
        # Test storage health checks
        storage_results = health_manager.storage_checker.check_all_storage()
        if storage_results:
            healthy_storage = sum(1 for r in storage_results if r.status == "healthy")
            total_storage = len(storage_results)
            self.log_test("Health checks - storage", True, 
                         f"Storage: {healthy_storage}/{total_storage} healthy")
        else:
            self.log_test("Health checks - storage", False, "No storage results")
        
        # Test system health checks
        system_resources = health_manager.system_checker.check_system_resources()
        if system_resources.status in ["healthy", "degraded", "unhealthy"]:
            self.log_test("Health checks - system resources", True, 
                         f"Status: {system_resources.status}")
        else:
            self.log_test("Health checks - system resources", False, 
                         f"Unexpected status: {system_resources.status}")
        
        # Test overall health status
        health_status = health_manager.get_health_status()
        if "overall_status" in health_status and "summary" in health_status:
            self.log_test("Health checks - overall status", True, 
                         f"Overall: {health_status['overall_status']}")
        else:
            self.log_test("Health checks - overall status", False, 
                         "Missing required fields in health status")
    
    def test_vod_processing_integration(self):
        """Test VOD processing integration with metrics."""
        print("\n=== Testing VOD Processing Integration ===")
        
        metrics = get_metrics_collector()
        
        # Test download metrics integration
        test_url = "https://httpbin.org/delay/1"
        test_path = os.path.join(self.temp_dir, "test_download.mp4")
        
        try:
            success = download_vod_content(test_url, test_path, timeout=5)
            if success:
                self.log_test("VOD processing integration - download", True, 
                             "Download completed with metrics tracking")
            else:
                self.log_test("VOD processing integration - download", False, 
                             "Download failed")
        except Exception as e:
            self.log_test("VOD processing integration - download", False, 
                         f"Download exception: {e}")
        
        # Check if metrics were recorded
        summary = metrics.get_metrics_summary(time_window=3600)
        if "vod_download_total" in summary and summary["vod_download_total"] > 0:
            self.log_test("VOD processing integration - metrics tracking", True, 
                         f"Download metrics recorded: {summary['vod_download_total']}")
        else:
            self.log_test("VOD processing integration - metrics tracking", False, 
                         "No download metrics found")
    
    def test_dashboard_functionality(self):
        """Test dashboard functionality."""
        print("\n=== Testing Dashboard Functionality ===")
        
        # Test dashboard initialization
        try:
            dashboard = MonitoringDashboard(host="127.0.0.1", port=8081)
            self.log_test("Dashboard functionality - initialization", True, 
                         "Dashboard initialized successfully")
        except Exception as e:
            self.log_test("Dashboard functionality - initialization", False, 
                         f"Dashboard init failed: {e}")
            return
        
        # Test dashboard routes
        with dashboard.app.test_client() as client:
            # Test metrics endpoint
            response = client.get('/api/metrics')
            if response.status_code == 200:
                self.log_test("Dashboard functionality - metrics endpoint", True, 
                             "Metrics endpoint responding")
            else:
                self.log_test("Dashboard functionality - metrics endpoint", False, 
                             f"Status code: {response.status_code}")
            
            # Test health endpoint
            response = client.get('/api/health')
            if response.status_code == 200:
                self.log_test("Dashboard functionality - health endpoint", True, 
                             "Health endpoint responding")
            else:
                self.log_test("Dashboard functionality - health endpoint", False, 
                             f"Status code: {response.status_code}")
            
            # Test main dashboard page
            response = client.get('/')
            if response.status_code == 200:
                self.log_test("Dashboard functionality - main page", True, 
                             "Main dashboard page responding")
            else:
                self.log_test("Dashboard functionality - main page", False, 
                             f"Status code: {response.status_code}")
    
    def test_error_handling_improvements(self):
        """Test the improved error handling with monitoring."""
        print("\n=== Testing Error Handling Improvements ===")
        
        # Test with fixed alert level
        try:
            from core.utils.alerts import send_alert
            send_alert("info", "Test alert message", test_param="value")
            self.log_test("Error handling improvements - alert levels", True, 
                         "Alert sent with correct level")
        except Exception as e:
            self.log_test("Error handling improvements - alert levels", False, 
                         f"Alert failed: {e}")
        
        # Test storage unavailable scenario with monitoring
        with patch('core.tasks.vod_processing.get_city_vod_storage_path') as mock_storage:
            mock_storage.return_value = "/nonexistent/storage"
            
            with patch('os.path.ismount') as mock_ismount:
                mock_ismount.return_value = False
                
                try:
                    result = process_single_vod(123, "/mnt/flex-1")
                    if result.get('status') == 'failed' and 'Storage unavailable' in result.get('error', ''):
                        self.log_test("Error handling improvements - storage monitoring", True, 
                                     "Storage unavailable handled with monitoring")
                    else:
                        self.log_test("Error handling improvements - storage monitoring", False, 
                                     f"Unexpected result: {result}")
                except Exception as e:
                    self.log_test("Error handling improvements - storage monitoring", False, 
                                 f"Unexpected exception: {e}")
    
    def run_all_tests(self):
        """Run all monitoring integration tests."""
        print("🧪 Testing Monitoring System Integration")
        print("=" * 50)
        
        try:
            self.test_metrics_collection()
            self.test_circuit_breaker()
            self.test_health_checks()
            self.test_vod_processing_integration()
            self.test_dashboard_functionality()
            self.test_error_handling_improvements()
            
            # Summary
            passed = sum(1 for result in self.test_results if result['passed'])
            total = len(self.test_results)
            
            print(f"\n📊 Test Summary")
            print("=" * 30)
            print(f"Passed: {passed}/{total}")
            print(f"Failed: {total - passed}/{total}")
            
            if passed == total:
                print("🎉 All monitoring integration tests passed!")
                return True
            else:
                print("⚠️  Some tests failed. Review the details above.")
                return False
                
        finally:
            self.cleanup()

def main():
    """Main test runner."""
    tester = MonitoringIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Monitoring system integration is working correctly!")
        print("\nKey improvements validated:")
        print("• Metrics collection and tracking")
        print("• Circuit breaker functionality")
        print("• Health checks for all components")
        print("• VOD processing integration")
        print("• Dashboard functionality")
        print("• Error handling improvements")
        print("\n🚀 Ready to start monitoring dashboard!")
        print("Run: python -m core.monitoring.dashboard")
    else:
        print("\n❌ Some monitoring integration tests need attention.")
        sys.exit(1)

if __name__ == "__main__":
    main() 
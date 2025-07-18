#!/usr/bin/env python3
"""
Integrated System Test Script

This script tests the complete integrated VOD processing system including:
- Admin UI with embedded monitoring dashboard
- Unified queue management (RQ + Celery)
- API endpoints and functionality
- Health checks and metrics
"""

import os
import sys
import time
import requests
import json
import threading
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

class IntegratedSystemTester:
    """Test suite for the integrated VOD processing system."""
    
    def __init__(self):
        self.admin_url = "http://localhost:8080"
        self.dashboard_url = "http://localhost:5051"
        self.test_results = []
        self.session = requests.Session()
        self.session.timeout = 10
    
    def log_test(self, test_name: str, success: bool, message: str = "", details: dict = None):
        """Log test result."""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details or {},
            'timestamp': time.time()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
        
        if details:
            logger.debug(f"Details: {json.dumps(details, indent=2)}")
    
    def test_admin_ui_availability(self):
        """Test if the admin UI is accessible."""
        try:
            response = self.session.get(f"{self.admin_url}/")
            if response.status_code == 200:
                self.log_test("Admin UI Availability", True, "Admin UI is accessible")
            else:
                self.log_test("Admin UI Availability", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Admin UI Availability", False, f"Connection failed: {str(e)}")
    
    def test_dashboard_availability(self):
        """Test if the monitoring dashboard is accessible."""
        try:
            response = self.session.get(f"{self.dashboard_url}/")
            if response.status_code == 200:
                self.log_test("Dashboard Availability", True, "Monitoring dashboard is accessible")
            else:
                self.log_test("Dashboard Availability", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Dashboard Availability", False, f"Connection failed: {str(e)}")
    
    def test_admin_api_endpoints(self):
        """Test admin API endpoints."""
        endpoints = [
            ("/api/admin/status", "Admin Status API"),
            ("/api/admin/cities", "Admin Cities API"),
            ("/api/admin/queue/summary", "Admin Queue Summary API"),
            ("/api/admin/celery/summary", "Admin Celery Summary API"),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.admin_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"{name} Endpoint", True, f"Endpoint accessible", data)
                else:
                    self.log_test(f"{name} Endpoint", False, f"Status code: {response.status_code}")
            except Exception as e:
                self.log_test(f"{name} Endpoint", False, f"Request failed: {str(e)}")
    
    def test_unified_queue_api(self):
        """Test unified queue management API."""
        endpoints = [
            ("/api/unified-queue/tasks/", "Unified Queue Tasks API"),
            ("/api/unified-queue/tasks/summary", "Unified Queue Summary API"),
            ("/api/unified-queue/workers/", "Unified Queue Workers API"),
            ("/api/unified-queue/workers/cached-data", "Unified Queue Cached Data API"),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.admin_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"{name} Endpoint", True, f"Endpoint accessible", data)
                else:
                    self.log_test(f"{name} Endpoint", False, f"Status code: {response.status_code}")
            except Exception as e:
                self.log_test(f"{name} Endpoint", False, f"Request failed: {str(e)}")
    
    def test_dashboard_api_endpoints(self):
        """Test monitoring dashboard API endpoints."""
        endpoints = [
            ("/api/metrics", "Dashboard Metrics API"),
            ("/api/health", "Dashboard Health API"),
            ("/api/queue/jobs", "Dashboard Queue Jobs API"),
            ("/api/celery/tasks", "Dashboard Celery Tasks API"),
            ("/api/celery/workers", "Dashboard Celery Workers API"),
            ("/api/unified/tasks", "Dashboard Unified Tasks API"),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.dashboard_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"{name} Endpoint", True, f"Endpoint accessible", data)
                else:
                    self.log_test(f"{name} Endpoint", False, f"Status code: {response.status_code}")
            except Exception as e:
                self.log_test(f"{name} Endpoint", False, f"Request failed: {str(e)}")
    
    def test_celery_task_trigger(self):
        """Test triggering a Celery task."""
        try:
            # Test triggering a simple task
            payload = {
                "task_name": "cleanup_temp_files",
                "kwargs": {}
            }
            response = self.session.post(
                f"{self.admin_url}/api/admin/tasks/trigger/cleanup_temp_files",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("Celery Task Trigger", True, "Task triggered successfully", data)
                else:
                    self.log_test("Celery Task Trigger", False, f"Task trigger failed: {data.get('error')}")
            else:
                self.log_test("Celery Task Trigger", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Celery Task Trigger", False, f"Request failed: {str(e)}")
    
    def test_queue_cleanup(self):
        """Test queue cleanup functionality."""
        try:
            response = self.session.post(f"{self.admin_url}/api/admin/queue/cleanup")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Queue Cleanup", True, "Queue cleanup completed", data)
            else:
                self.log_test("Queue Cleanup", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Queue Cleanup", False, f"Request failed: {str(e)}")
    
    def test_unified_queue_task_management(self):
        """Test unified queue task management."""
        try:
            # Test triggering a Celery task through unified API
            payload = {
                "task_name": "cleanup_temp_files",
                "kwargs": {}
            }
            response = self.session.post(
                f"{self.admin_url}/api/unified-queue/tasks/trigger-celery",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("Unified Queue Task Trigger", True, "Task triggered via unified API", data)
                else:
                    self.log_test("Unified Queue Task Trigger", False, f"Task trigger failed: {data.get('error')}")
            else:
                self.log_test("Unified Queue Task Trigger", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Unified Queue Task Trigger", False, f"Request failed: {str(e)}")
    
    def test_health_checks(self):
        """Test health check endpoints."""
        try:
            response = self.session.get(f"{self.dashboard_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                overall_status = data.get('overall_status', 'unknown')
                self.log_test("Health Checks", True, f"Overall status: {overall_status}", data)
            else:
                self.log_test("Health Checks", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Health Checks", False, f"Request failed: {str(e)}")
    
    def test_metrics_collection(self):
        """Test metrics collection."""
        try:
            response = self.session.get(f"{self.dashboard_url}/api/metrics")
            if response.status_code == 200:
                data = response.json()
                counters = data.get('counters', {})
                timers = data.get('timers', {})
                self.log_test("Metrics Collection", True, f"Collected {len(counters)} counters, {len(timers)} timers", data)
            else:
                self.log_test("Metrics Collection", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Metrics Collection", False, f"Request failed: {str(e)}")
    
    def test_iframe_embedding(self):
        """Test if the dashboard is properly embedded in the admin UI."""
        try:
            response = self.session.get(f"{self.admin_url}/")
            if response.status_code == 200:
                content = response.text
                if 'iframe' in content.lower() and 'localhost:5051' in content:
                    self.log_test("Iframe Embedding", True, "Dashboard iframe found in admin UI")
                else:
                    self.log_test("Iframe Embedding", False, "Dashboard iframe not found in admin UI")
            else:
                self.log_test("Iframe Embedding", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Iframe Embedding", False, f"Request failed: {str(e)}")
    
    def test_api_documentation(self):
        """Test API documentation endpoints."""
        endpoints = [
            ("/api/docs", "Main API Documentation"),
            ("/api/unified-queue/docs", "Unified Queue API Documentation"),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.admin_url}{endpoint}")
                if response.status_code == 200:
                    self.log_test(f"{name} Documentation", True, "API documentation accessible")
                else:
                    self.log_test(f"{name} Documentation", False, f"Status code: {response.status_code}")
            except Exception as e:
                self.log_test(f"{name} Documentation", False, f"Request failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests."""
        logger.info("🚀 Starting Integrated System Tests")
        logger.info("=" * 50)
        
        # Test basic availability
        self.test_admin_ui_availability()
        self.test_dashboard_availability()
        
        # Test API endpoints
        self.test_admin_api_endpoints()
        self.test_unified_queue_api()
        self.test_dashboard_api_endpoints()
        
        # Test functionality
        self.test_celery_task_trigger()
        self.test_queue_cleanup()
        self.test_unified_queue_task_management()
        
        # Test monitoring
        self.test_health_checks()
        self.test_metrics_collection()
        
        # Test integration
        self.test_iframe_embedding()
        self.test_api_documentation()
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary."""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        logger.info("=" * 50)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    logger.error(f"  - {result['test']}: {result['message']}")
        
        # Save results to file
        with open("test_results_integrated_system.json", "w") as f:
            json.dump({
                'timestamp': time.time(),
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'success_rate': (passed_tests/total_tests*100)
                },
                'results': self.test_results
            }, f, indent=2)
        
        logger.info(f"\n📄 Detailed results saved to: test_results_integrated_system.json")
        
        if failed_tests == 0:
            logger.info("🎉 All tests passed! Integrated system is working correctly.")
        else:
            logger.warning(f"⚠️  {failed_tests} tests failed. Please check the system configuration.")

def main():
    """Main test function."""
    tester = IntegratedSystemTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 
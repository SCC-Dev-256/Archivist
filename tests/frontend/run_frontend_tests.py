#!/usr/bin/env python3
"""
Frontend Testing Runner

This module orchestrates all frontend testing including:
- GUI Testing (Selenium-based)
- WebSocket Functionality Testing
- Integration Testing
- Performance Testing
- Accessibility Testing

It provides a unified interface for running all frontend tests
and generating comprehensive reports.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# PURPOSE: Comprehensive frontend testing orchestration and reporting
# DEPENDENCIES: Selenium, Socket.IO, Flask test client, pytest
# MODIFICATION NOTES: v1.0 - Initial frontend testing runner implementation


class FrontendTestRunner:
    """Comprehensive frontend testing runner."""
    
    def __init__(self, base_url="http://localhost:5050"):
        self.base_url = base_url
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def log_test_suite(self, suite_name: str, success: bool, message: str = "", details: dict = None):
        """Log test suite result."""
        result = {
            'suite': suite_name,
            'success': success,
            'message': message,
            'details': details or {},
            'timestamp': time.time()
        }
        self.test_results[suite_name] = result
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {suite_name}: {message}")
        
        if details:
            logger.debug(f"Details: {json.dumps(details, indent=2)}")
    
    def check_prerequisites(self):
        """Check if all prerequisites are met for frontend testing."""
        logger.info("Checking Frontend Testing Prerequisites")
        
        try:
            # Check if web server is running
            import requests
            try:
                response = requests.get(self.base_url, timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Web server is running and accessible")
                else:
                    logger.warning(f"⚠️ Web server responded with status {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Web server is not accessible: {str(e)}")
                return False
            
            # Check if Chrome/Chromium is available for Selenium
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                driver = webdriver.Chrome(options=chrome_options)
                driver.quit()
                logger.info("✅ Chrome/Chromium is available for Selenium testing")
            except Exception as e:
                logger.error(f"❌ Chrome/Chromium not available: {str(e)}")
                return False
            
            # Check if required Python packages are installed
            required_packages = [
                'selenium',
                'socketio',
                'pytest',
                'requests',
                'loguru'
            ]
            
            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)
            
            if missing_packages:
                logger.error(f"❌ Missing required packages: {', '.join(missing_packages)}")
                return False
            else:
                logger.info("✅ All required Python packages are installed")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Prerequisites check failed: {str(e)}")
            return False
    
    def run_gui_tests(self):
        """Run GUI testing suite."""
        logger.info("Starting GUI Testing Suite")
        
        try:
            from tests.frontend.test_frontend_gui import FrontendGUITester
            
            tester = FrontendGUITester(self.base_url)
            results = tester.run_all_frontend_tests(headless=True)
            
            passed = sum(1 for result in results if result['success'])
            total = len(results)
            
            success = passed == total
            message = f"GUI Testing: {passed}/{total} tests passed"
            
            details = {
                'passed': passed,
                'total': total,
                'results': results
            }
            
            self.log_test_suite("GUI Testing", success, message, details)
            return success
            
        except Exception as e:
            self.log_test_suite("GUI Testing", False, f"GUI testing failed: {str(e)}")
            return False
    
    def run_websocket_tests(self):
        """Run WebSocket functionality testing suite."""
        logger.info("Starting WebSocket Testing Suite")
        
        try:
            from tests.frontend.test_websocket_functionality import WebSocketFunctionalityTester
            
            tester = WebSocketFunctionalityTester(self.base_url)
            results = tester.run_all_websocket_tests()
            
            passed = sum(1 for result in results if result['success'])
            total = len(results)
            
            success = passed == total
            message = f"WebSocket Testing: {passed}/{total} tests passed"
            
            details = {
                'passed': passed,
                'total': total,
                'results': results
            }
            
            self.log_test_suite("WebSocket Testing", success, message, details)
            return success
            
        except Exception as e:
            self.log_test_suite("WebSocket Testing", False, f"WebSocket testing failed: {str(e)}")
            return False
    
    def run_integration_tests(self):
        """Run frontend integration tests."""
        logger.info("Starting Frontend Integration Testing")
        
        try:
            # Import and run integration tests that focus on frontend
            from tests.integration.test_admin_ui_integration import TestAdminUIIntegration
            
            # Create test instance and run frontend-focused tests
            test_instance = TestAdminUIIntegration()
            
            # Run specific frontend integration tests
            frontend_tests = [
                'test_admin_dashboard_rendering',
                'test_admin_api_endpoints',
                'test_real_time_updates_websocket',
                'test_ui_interactions_form_validation'
            ]
            
            passed = 0
            total = len(frontend_tests)
            results = []
            
            for test_name in frontend_tests:
                try:
                    test_method = getattr(test_instance, test_name)
                    test_method()
                    passed += 1
                    results.append({'test': test_name, 'success': True, 'message': 'Test passed'})
                except Exception as e:
                    results.append({'test': test_name, 'success': False, 'message': str(e)})
            
            success = passed == total
            message = f"Frontend Integration Testing: {passed}/{total} tests passed"
            
            details = {
                'passed': passed,
                'total': total,
                'results': results
            }
            
            self.log_test_suite("Frontend Integration Testing", success, message, details)
            return success
            
        except Exception as e:
            self.log_test_suite("Frontend Integration Testing", False, f"Integration testing failed: {str(e)}")
            return False
    
    def run_performance_tests(self):
        """Run frontend performance tests."""
        logger.info("Starting Frontend Performance Testing")
        
        try:
            import requests
            import time
            
            # Test page load performance
            load_times = []
            for i in range(5):
                start_time = time.time()
                response = requests.get(self.base_url, timeout=10)
                load_time = time.time() - start_time
                load_times.append(load_time)
                
                if response.status_code != 200:
                    raise Exception(f"Page load failed with status {response.status_code}")
            
            avg_load_time = sum(load_times) / len(load_times)
            max_load_time = max(load_times)
            
            # Performance thresholds
            success = avg_load_time < 3.0 and max_load_time < 5.0
            message = f"Performance Testing: Avg load time {avg_load_time:.2f}s, Max {max_load_time:.2f}s"
            
            details = {
                'average_load_time': avg_load_time,
                'max_load_time': max_load_time,
                'load_times': load_times,
                'thresholds': {
                    'avg_threshold': 3.0,
                    'max_threshold': 5.0
                }
            }
            
            self.log_test_suite("Performance Testing", success, message, details)
            return success
            
        except Exception as e:
            self.log_test_suite("Performance Testing", False, f"Performance testing failed: {str(e)}")
            return False
    
    def run_visual_regression_tests(self):
        """Run visual regression testing suite."""
        logger.info("Running Visual Regression Testing")
        
        try:
            # Import visual regression testing module
            from tests.frontend.test_visual_regression import run_visual_regression_tests
            
            # Run visual regression tests
            results = run_visual_regression_tests()
            
            # Analyze results
            if results:
                passed = sum(1 for _, result in results if result)
                total = len(results)
                success_rate = (passed / total) * 100 if total > 0 else 0
                
                success = success_rate >= 80  # 80% threshold
                message = f"{passed}/{total} visual regression tests passed ({success_rate:.1f}%)"
                
                details = {
                    'passed': passed,
                    'total': total,
                    'success_rate': success_rate,
                    'results': results
                }
                
                self.log_test_suite("Visual Regression Testing", success, message, details)
            else:
                self.log_test_suite("Visual Regression Testing", False, "No visual regression test results")
                
        except ImportError:
            self.log_test_suite("Visual Regression Testing", False, "Visual regression testing module not available")
        except Exception as e:
            self.log_test_suite("Visual Regression Testing", False, f"Visual regression testing failed: {str(e)}")

    def run_accessibility_tests(self):
        """Run accessibility testing."""
        logger.info("Starting Accessibility Testing")
        
        try:
            # Basic accessibility checks
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(self.base_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            accessibility_issues = []
            
            # Check for proper heading structure
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if not headings:
                accessibility_issues.append("No headings found")
            
            # Check for alt text on images
            images = soup.find_all('img')
            for img in images:
                if not img.get('alt'):
                    accessibility_issues.append(f"Image missing alt text: {img.get('src', 'unknown')}")
            
            # Check for form labels
            forms = soup.find_all('form')
            for form in forms:
                inputs = form.find_all(['input', 'textarea', 'select'])
                for input_elem in inputs:
                    if input_elem.get('type') not in ['hidden', 'submit', 'button']:
                        input_id = input_elem.get('id')
                        if input_id:
                            label = soup.find('label', {'for': input_id})
                            if not label:
                                accessibility_issues.append(f"Input missing label: {input_id}")
            
            # Check for semantic HTML
            semantic_elements = ['nav', 'main', 'section', 'article', 'aside', 'header', 'footer']
            found_semantic = [elem for elem in semantic_elements if soup.find(elem)]
            if not found_semantic:
                accessibility_issues.append("No semantic HTML elements found")
            
            success = len(accessibility_issues) == 0
            message = f"Accessibility Testing: {len(accessibility_issues)} issues found"
            
            details = {
                'issues': accessibility_issues,
                'semantic_elements_found': found_semantic,
                'total_images': len(images),
                'total_forms': len(forms),
                'total_headings': len(headings)
            }
            
            self.log_test_suite("Accessibility Testing", success, message, details)
            return success
            
        except Exception as e:
            self.log_test_suite("Accessibility Testing", False, f"Accessibility testing failed: {str(e)}")
            return False
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("Generating Frontend Test Report")
        
        if not self.end_time:
            self.end_time = time.time()
        
        total_duration = self.end_time - self.start_time
        
        # Calculate overall statistics
        total_suites = len(self.test_results)
        passed_suites = sum(1 for result in self.test_results.values() if result['success'])
        
        # Generate detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration': total_duration,
            'overall_success': passed_suites == total_suites,
            'summary': {
                'total_suites': total_suites,
                'passed_suites': passed_suites,
                'failed_suites': total_suites - passed_suites,
                'success_rate': (passed_suites / total_suites * 100) if total_suites > 0 else 0
            },
            'test_suites': self.test_results,
            'recommendations': self.generate_recommendations()
        }
        
        # Save report to file
        report_file = f"frontend_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to: {report_file}")
        return report
    
    def generate_recommendations(self):
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_suites = [name for name, result in self.test_results.items() if not result['success']]
        
        if 'GUI Testing' in failed_suites:
            recommendations.append("Fix GUI rendering issues and ensure all UI elements are properly displayed")
        
        if 'WebSocket Testing' in failed_suites:
            recommendations.append("Check WebSocket server configuration and ensure real-time updates are working")
        
        if 'Performance Testing' in failed_suites:
            recommendations.append("Optimize page load times and reduce server response latency")
        
        if 'Accessibility Testing' in failed_suites:
            recommendations.append("Add missing alt text, labels, and semantic HTML elements for better accessibility")
        
        if not failed_suites:
            recommendations.append("All frontend tests passed! Consider adding more comprehensive test coverage")
        
        return recommendations
    
    def run_all_frontend_tests(self):
        """Run all frontend testing suites."""
        logger.info("Starting Comprehensive Frontend Testing")
        
        self.start_time = time.time()
        
        try:
            # Check prerequisites first
            if not self.check_prerequisites():
                logger.error("Prerequisites check failed. Please fix issues before running tests.")
                return False
            
            # Run all test suites
            test_suites = [
                ("GUI Testing", self.run_gui_tests),
                ("WebSocket Testing", self.run_websocket_tests),
                ("Frontend Integration Testing", self.run_integration_tests),
                ("Visual Regression Testing", self.run_visual_regression_tests),
                ("Performance Testing", self.run_performance_tests),
                ("Accessibility Testing", self.run_accessibility_tests)
            ]
            
            for suite_name, test_method in test_suites:
                try:
                    logger.info(f"Running {suite_name}...")
                    test_method()
                except Exception as e:
                    logger.error(f"{suite_name} failed with exception: {str(e)}")
                    self.log_test_suite(suite_name, False, f"Exception: {str(e)}")
            
            # Generate final report
            report = self.generate_test_report()
            
            # Print summary
            self.print_summary(report)
            
            return report['overall_success']
            
        except Exception as e:
            logger.error(f"Frontend testing failed: {str(e)}")
            return False
        finally:
            self.end_time = time.time()
    
    def print_summary(self, report):
        """Print test summary to console."""
        print("\n" + "="*80)
        print("FRONTEND TESTING SUMMARY")
        print("="*80)
        
        summary = report['summary']
        print(f"Total Test Suites: {summary['total_suites']}")
        print(f"Passed: {summary['passed_suites']}")
        print(f"Failed: {summary['failed_suites']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Duration: {report['duration']:.2f} seconds")
        
        print("\nTest Suite Results:")
        print("-" * 40)
        
        for suite_name, result in report['test_suites'].items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} {suite_name}: {result['message']}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            print("-" * 20)
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"{i}. {rec}")
        
        print("\n" + "="*80)


def run_frontend_tests():
    """Main function to run all frontend tests."""
    # Set testing environment variable for rate limiting
    os.environ['TESTING'] = 'true'
    
    logger.info("Starting Frontend Testing Suite")
    
    runner = FrontendTestRunner()
    success = runner.run_all_frontend_tests()
    
    return success


if __name__ == "__main__":
    run_frontend_tests()

# NEXT STEP: Integrate with CI/CD pipeline and add automated test scheduling 
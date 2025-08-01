#!/usr/bin/env python3
"""
Frontend Performance Testing

This module tests frontend performance metrics including load times, memory usage,
and responsiveness to ensure the UI remains fast and efficient.
"""

import os
import sys
import time
import json
import psutil
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger

# PURPOSE: Performance testing for frontend responsiveness and efficiency
# DEPENDENCIES: Selenium, psutil
# MODIFICATION NOTES: v1.0 - Initial performance testing implementation


class PerformanceTester:
    """Performance testing for frontend UI."""
    
    def __init__(self, base_url="http://localhost:5050"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.performance_results = []
        
    def setup_driver(self):
        """Set up Selenium WebDriver with performance logging."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--v=1")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def teardown_driver(self):
        """Clean up WebDriver."""
        if self.driver:
            self.driver.quit()
    
    def measure_page_load_time(self):
        """Measure page load time and performance metrics."""
        logger.info("Measuring page load performance")
        
        try:
            # Clear logs
            self.driver.get_log('performance')
            
            # Navigate to page and measure time
            start_time = time.time()
            self.driver.get(self.base_url)
            
            # Wait for page to be fully loaded
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Wait for key elements
            self.wait.until(EC.presence_of_element_located((By.ID, "live-metrics")))
            self.wait.until(EC.presence_of_element_located((By.ID, "file-list")))
            
            load_time = time.time() - start_time
            
            # Get performance logs
            logs = self.driver.get_log('performance')
            
            # Analyze performance data
            performance_data = {
                'load_time': load_time,
                'dom_content_loaded': None,
                'first_paint': None,
                'first_contentful_paint': None,
                'largest_contentful_paint': None
            }
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    if 'message' in message:
                        method = message['message']['method']
                        params = message['message'].get('params', {})
                        
                        if method == 'Performance.metrics':
                            metrics = params.get('metrics', [])
                            for metric in metrics:
                                if metric['name'] == 'DomContentLoaded':
                                    performance_data['dom_content_loaded'] = metric['value']
                                elif metric['name'] == 'FirstPaint':
                                    performance_data['first_paint'] = metric['value']
                                elif metric['name'] == 'FirstContentfulPaint':
                                    performance_data['first_contentful_paint'] = metric['value']
                                elif metric['name'] == 'LargestContentfulPaint':
                                    performance_data['largest_contentful_paint'] = metric['value']
                except:
                    continue
            
            # Check performance thresholds
            thresholds = {
                'load_time': 3.0,  # 3 seconds
                'dom_content_loaded': 2000,  # 2 seconds
                'first_paint': 1000,  # 1 second
                'first_contentful_paint': 1500,  # 1.5 seconds
                'largest_contentful_paint': 2500  # 2.5 seconds
            }
            
            passed = True
            issues = []
            
            for metric, value in performance_data.items():
                if value is not None and metric in thresholds:
                    if value > thresholds[metric]:
                        passed = False
                        issues.append(f"{metric}: {value:.2f}ms (threshold: {thresholds[metric]}ms)")
            
            result = {
                'test': 'Page Load Performance',
                'passed': passed,
                'data': performance_data,
                'issues': issues,
                'message': f"Load time: {load_time:.2f}s"
            }
            
            self.performance_results.append(result)
            
            if passed:
                logger.info(f"✅ Page load performance acceptable: {load_time:.2f}s")
            else:
                logger.warning(f"❌ Page load performance issues: {', '.join(issues)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Page load performance test failed: {str(e)}")
            return {'test': 'Page Load Performance', 'passed': False, 'error': str(e)}
    
    def measure_memory_usage(self):
        """Measure memory usage during UI interactions."""
        logger.info("Measuring memory usage")
        
        try:
            # Get initial memory usage
            initial_memory = psutil.virtual_memory().percent
            
            # Perform UI interactions
            interactions = [
                ("Navigate to Analytics tab", lambda: self.driver.find_element(By.CSS_SELECTOR, '[data-tab="tab-analytics"]').click()),
                ("Navigate to Real-Time tab", lambda: self.driver.find_element(By.CSS_SELECTOR, '[data-tab="tab-realtime"]').click()),
                ("Navigate to Controls tab", lambda: self.driver.find_element(By.CSS_SELECTOR, '[data-tab="tab-controls"]').click()),
                ("Navigate back to File Browser", lambda: self.driver.find_element(By.CSS_SELECTOR, '[data-tab="tab-browser"]').click()),
                ("Refresh page", lambda: self.driver.refresh())
            ]
            
            memory_readings = [initial_memory]
            
            for interaction_name, interaction_func in interactions:
                try:
                    interaction_func()
                    time.sleep(1)  # Wait for interaction to complete
                    memory_readings.append(psutil.virtual_memory().percent)
                    logger.debug(f"Memory after {interaction_name}: {memory_readings[-1]:.1f}%")
                except Exception as e:
                    logger.warning(f"Interaction {interaction_name} failed: {str(e)}")
            
            # Analyze memory usage
            max_memory = max(memory_readings)
            avg_memory = sum(memory_readings) / len(memory_readings)
            memory_increase = max_memory - initial_memory
            
            # Check thresholds
            memory_threshold = 80  # 80% memory usage
            increase_threshold = 20  # 20% increase
            
            passed = max_memory < memory_threshold and memory_increase < increase_threshold
            issues = []
            
            if max_memory >= memory_threshold:
                issues.append(f"High memory usage: {max_memory:.1f}%")
            if memory_increase >= increase_threshold:
                issues.append(f"Large memory increase: {memory_increase:.1f}%")
            
            result = {
                'test': 'Memory Usage',
                'passed': passed,
                'data': {
                    'initial_memory': initial_memory,
                    'max_memory': max_memory,
                    'avg_memory': avg_memory,
                    'memory_increase': memory_increase,
                    'readings': memory_readings
                },
                'issues': issues,
                'message': f"Max memory: {max_memory:.1f}%, Increase: {memory_increase:.1f}%"
            }
            
            self.performance_results.append(result)
            
            if passed:
                logger.info(f"✅ Memory usage acceptable: max {max_memory:.1f}%, increase {memory_increase:.1f}%")
            else:
                logger.warning(f"❌ Memory usage issues: {', '.join(issues)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Memory usage test failed: {str(e)}")
            return {'test': 'Memory Usage', 'passed': False, 'error': str(e)}
    
    def measure_responsiveness(self):
        """Measure UI responsiveness and interaction times."""
        logger.info("Measuring UI responsiveness")
        
        try:
            response_times = []
            
            # Test tab switching responsiveness
            tabs = ["tab-browser", "tab-analytics", "tab-realtime", "tab-controls"]
            
            for tab_id in tabs:
                try:
                    start_time = time.time()
                    tab_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-tab="{tab_id}"]')))
                    tab_btn.click()
                    
                    # Wait for tab content to be visible
                    self.wait.until(EC.visibility_of_element_located((By.ID, tab_id)))
                    
                    response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    response_times.append(response_time)
                    logger.debug(f"Tab {tab_id} response time: {response_time:.2f}ms")
                    
                except Exception as e:
                    logger.warning(f"Tab {tab_id} responsiveness test failed: {str(e)}")
            
            # Test button click responsiveness
            buttons_to_test = [
                ("Refresh Files", "button[onclick='loadFiles()']"),
                ("Refresh Analytics", "#refresh-analytics-btn"),
                ("Refresh Flex Servers", "button[onclick='loadFlexServers()']")
            ]
            
            for button_name, selector in buttons_to_test:
                try:
                    start_time = time.time()
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    button.click()
                    time.sleep(0.5)  # Wait for any immediate response
                    
                    response_time = (time.time() - start_time) * 1000
                    response_times.append(response_time)
                    logger.debug(f"Button {button_name} response time: {response_time:.2f}ms")
                    
                except Exception as e:
                    logger.warning(f"Button {button_name} responsiveness test failed: {str(e)}")
            
            # Analyze responsiveness
            if response_times:
                avg_response = sum(response_times) / len(response_times)
                max_response = max(response_times)
                min_response = min(response_times)
                
                # Check thresholds
                avg_threshold = 500  # 500ms average
                max_threshold = 2000  # 2s maximum
                
                passed = avg_response < avg_threshold and max_response < max_threshold
                issues = []
                
                if avg_response >= avg_threshold:
                    issues.append(f"Slow average response: {avg_response:.2f}ms")
                if max_response >= max_threshold:
                    issues.append(f"Slow maximum response: {max_response:.2f}ms")
                
                result = {
                    'test': 'UI Responsiveness',
                    'passed': passed,
                    'data': {
                        'avg_response': avg_response,
                        'max_response': max_response,
                        'min_response': min_response,
                        'response_times': response_times
                    },
                    'issues': issues,
                    'message': f"Avg: {avg_response:.2f}ms, Max: {max_response:.2f}ms"
                }
            else:
                result = {
                    'test': 'UI Responsiveness',
                    'passed': False,
                    'error': 'No response times measured',
                    'message': 'Failed to measure responsiveness'
                }
            
            self.performance_results.append(result)
            
            if result['passed']:
                logger.info(f"✅ UI responsiveness acceptable: avg {avg_response:.2f}ms, max {max_response:.2f}ms")
            else:
                logger.warning(f"❌ UI responsiveness issues: {', '.join(issues) if 'issues' in result else result.get('error', 'Unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"UI responsiveness test failed: {str(e)}")
            return {'test': 'UI Responsiveness', 'passed': False, 'error': str(e)}
    
    def measure_network_performance(self):
        """Measure network performance and API response times."""
        logger.info("Measuring network performance")
        
        try:
            # Enable network logging
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # Clear network logs
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            self.driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
            
            # Navigate to page and collect network data
            self.driver.get(self.base_url)
            time.sleep(3)  # Wait for all resources to load
            
            # Get network logs
            logs = self.driver.get_log('performance')
            
            network_requests = []
            api_responses = []
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    if 'message' in message:
                        method = message['message']['method']
                        params = message['message'].get('params', {})
                        
                        if method == 'Network.responseReceived':
                            request_id = params.get('requestId')
                            response = params.get('response', {})
                            url = response.get('url', '')
                            
                            if '/api/' in url:
                                api_responses.append({
                                    'url': url,
                                    'status': response.get('status'),
                                    'request_id': request_id
                                })
                        
                        elif method == 'Network.loadingFinished':
                            request_id = params.get('requestId')
                            timestamp = params.get('timestamp', 0)
                            
                            # Find corresponding request
                            for api_response in api_responses:
                                if api_response['request_id'] == request_id:
                                    api_response['load_time'] = timestamp
                                    break
                            
                            network_requests.append({
                                'request_id': request_id,
                                'load_time': timestamp
                            })
                            
                except:
                    continue
            
            # Analyze API performance
            api_times = []
            for api_response in api_responses:
                if 'load_time' in api_response:
                    api_times.append(api_response['load_time'])
            
            if api_times:
                avg_api_time = sum(api_times) / len(api_times)
                max_api_time = max(api_times)
                
                # Check thresholds
                api_threshold = 1000  # 1 second
                
                passed = avg_api_time < api_threshold
                issues = []
                
                if avg_api_time >= api_threshold:
                    issues.append(f"Slow API responses: {avg_api_time:.2f}ms average")
                
                result = {
                    'test': 'Network Performance',
                    'passed': passed,
                    'data': {
                        'avg_api_time': avg_api_time,
                        'max_api_time': max_api_time,
                        'api_requests': len(api_responses),
                        'total_requests': len(network_requests)
                    },
                    'issues': issues,
                    'message': f"API avg: {avg_api_time:.2f}ms, {len(api_responses)} API calls"
                }
            else:
                result = {
                    'test': 'Network Performance',
                    'passed': False,
                    'error': 'No API requests detected',
                    'message': 'No network data collected'
                }
            
            self.performance_results.append(result)
            
            if result['passed']:
                logger.info(f"✅ Network performance acceptable: API avg {avg_api_time:.2f}ms")
            else:
                logger.warning(f"❌ Network performance issues: {', '.join(issues) if 'issues' in result else result.get('error', 'Unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Network performance test failed: {str(e)}")
            return {'test': 'Network Performance', 'passed': False, 'error': str(e)}
    
    def run_performance_tests(self):
        """Run all performance tests."""
        logger.info("Starting performance tests")
        
        try:
            self.setup_driver()
            
            tests = [
                self.measure_page_load_time,
                self.measure_memory_usage,
                self.measure_responsiveness,
                self.measure_network_performance
            ]
            
            for test_func in tests:
                try:
                    test_func()
                except Exception as e:
                    logger.error(f"Performance test failed: {str(e)}")
            
            # Generate summary
            passed = sum(1 for result in self.performance_results if result.get('passed', False))
            total = len(self.performance_results)
            
            logger.info(f"Performance tests complete: {passed}/{total} passed")
            
            return self.performance_results
            
        except Exception as e:
            logger.error(f"Performance tests failed: {str(e)}")
            return []
        finally:
            self.teardown_driver()


def run_performance_tests():
    """Main function to run performance tests."""
    logger.info("Starting Performance Testing")
    
    tester = PerformanceTester()
    results = tester.run_performance_tests()
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE TESTING RESULTS")
    print("="*60)
    
    passed = 0
    for result in results:
        status = "✅ PASS" if result.get('passed', False) else "❌ FAIL"
        print(f"{status} {result['test']}: {result.get('message', 'No message')}")
        if result.get('passed', False):
            passed += 1
        
        if 'issues' in result and result['issues']:
            for issue in result['issues']:
                print(f"    ⚠️  {issue}")
    
    print(f"\nSummary: {passed}/{len(results)} tests passed")
    
    return results


if __name__ == "__main__":
    run_performance_tests()

# NEXT STEP: Integrate performance monitoring into CI/CD pipeline and set up alerts for performance regressions 
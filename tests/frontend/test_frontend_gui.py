#!/usr/bin/env python3
"""
Frontend GUI Testing Suite

This module contains comprehensive frontend testing for the Archivist web interface.
It covers UI interactions, real-time updates, form validation, and user experience testing.

Test Categories:
1. UI Rendering and Layout
2. Navigation and Tab Functionality
3. Real-time Updates and WebSocket
4. Form Validation and User Input
5. File Browser Functionality
6. Analytics Dashboard
7. Queue Management Interface
8. Error Handling and User Feedback
9. Responsive Design Testing
10. Accessibility Testing
"""

import os
import sys
import time
import json
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from loguru import logger

# PURPOSE: Frontend GUI testing suite for Archivist web interface
# DEPENDENCIES: Selenium WebDriver, Flask test client, Socket.IO
# MODIFICATION NOTES: v1.0 - Initial comprehensive frontend testing implementation


class FrontendGUITester:
    """Comprehensive frontend GUI testing suite."""
    
    def __init__(self, base_url="http://localhost:5050"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.test_results = []
        
    def setup_driver(self, headless=True):
        """Set up Selenium WebDriver with Chrome options."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def teardown_driver(self):
        """Clean up WebDriver."""
        if self.driver:
            self.driver.quit()
            
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
    
    def test_ui_rendering_and_layout(self):
        """Test UI rendering and layout structure."""
        logger.info("Testing UI Rendering and Layout")
        
        try:
            # Navigate to the main page
            self.driver.get(self.base_url)
            
            # Test page title
            title = self.driver.title
            assert "Archivist" in title, f"Expected 'Archivist' in title, got: {title}"
            
            # Test main header
            header = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            assert "Archivist" in header.text, "Main header should contain 'Archivist'"
            
            # Test navigation tabs
            tabs = self.driver.find_elements(By.CSS_SELECTOR, "#main-tabs .tab-btn")
            expected_tabs = ["File Browser", "Analytics", "Real-Time Tasks", "Controls"]
            
            for i, tab in enumerate(tabs):
                assert tab.text == expected_tabs[i], f"Tab {i} should be '{expected_tabs[i]}', got: '{tab.text}'"
            
            # Test live metrics panel
            metrics_panel = self.driver.find_element(By.ID, "live-metrics")
            assert metrics_panel.is_displayed(), "Live metrics panel should be visible"
            
            # Test CSS classes for styling
            body = self.driver.find_element(By.TAG_NAME, "body")
            assert "bg-gray-900" in body.get_attribute("class"), "Body should have dark background"
            
            self.log_test("UI Rendering and Layout", True, "All UI elements rendered correctly")
            
        except Exception as e:
            self.log_test("UI Rendering and Layout", False, f"UI rendering failed: {str(e)}")
    
    def test_navigation_and_tab_functionality(self):
        """Test navigation between tabs and tab content switching."""
        logger.info("Testing Navigation and Tab Functionality")
        
        try:
            self.driver.get(self.base_url)
            
            # Test tab switching
            tabs = {
                "tab-browser": "File Browser",
                "tab-analytics": "Analytics", 
                "tab-realtime": "Real-Time Tasks",
                "tab-controls": "Controls"
            }
            
            for tab_id, tab_name in tabs.items():
                # Click tab button
                tab_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-tab="{tab_id}"]')))
                tab_btn.click()
                
                # Wait for tab content to be visible
                tab_content = self.wait.until(EC.visibility_of_element_located((By.ID, tab_id)))
                assert tab_content.is_displayed(), f"Tab content for {tab_name} should be visible"
                
                # Verify other tabs are hidden
                for other_id in tabs.keys():
                    if other_id != tab_id:
                        other_content = self.driver.find_element(By.ID, other_id)
                        assert "hidden" in other_content.get_attribute("class"), f"Other tab {other_id} should be hidden"
                
                # Test tab button active state
                assert "active" in tab_btn.get_attribute("class"), f"Tab button for {tab_name} should be active"
            
            self.log_test("Navigation and Tab Functionality", True, "All tabs switch correctly")
            
        except Exception as e:
            self.log_test("Navigation and Tab Functionality", False, f"Tab navigation failed: {str(e)}")
    
    def test_file_browser_functionality(self):
        """Test file browser interface and interactions."""
        logger.info("Testing File Browser Functionality")
        
        try:
            self.driver.get(self.base_url)
            
            # Ensure we're on the file browser tab
            browser_tab = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-tab="tab-browser"]')))
            browser_tab.click()
            
            # Test search functionality
            search_input = self.wait.until(EC.presence_of_element_located((By.ID, "search-input")))
            search_input.clear()
            search_input.send_keys("test")
            
            # Test search type dropdown
            search_type = self.driver.find_element(By.ID, "search-type")
            search_type.click()
            files_option = self.driver.find_element(By.CSS_SELECTOR, "#search-type option[value='files']")
            assert files_option.is_selected(), "Files option should be selected by default"
            
            # Test file list container
            file_list = self.driver.find_element(By.ID, "file-list")
            assert file_list.is_displayed(), "File list should be visible"
            
            # Test current path display
            current_path = self.driver.find_element(By.ID, "current-path")
            assert current_path.is_displayed(), "Current path should be visible"
            
            # Test navigation buttons
            up_button = self.driver.find_element(By.CSS_SELECTOR, "button[onclick='navigateUp()']")
            assert up_button.is_displayed(), "Up navigation button should be visible"
            
            # Test queue button
            queue_button = self.driver.find_element(By.ID, "queue-selected-btn")
            assert queue_button.is_displayed(), "Queue selected button should be visible"
            assert "Queue Selected for Transcription" in queue_button.text
            
            self.log_test("File Browser Functionality", True, "File browser interface works correctly")
            
        except Exception as e:
            self.log_test("File Browser Functionality", False, f"File browser testing failed: {str(e)}")
    
    def test_analytics_dashboard(self):
        """Test analytics dashboard functionality."""
        logger.info("Testing Analytics Dashboard")
        
        try:
            self.driver.get(self.base_url)
            
            # Switch to analytics tab
            analytics_tab = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-tab="tab-analytics"]')))
            analytics_tab.click()
            
            # Test analytics content
            analytics_content = self.wait.until(EC.visibility_of_element_located((By.ID, "tab-analytics")))
            assert analytics_content.is_displayed(), "Analytics content should be visible"
            
            # Test system metrics chart
            chart_canvas = self.driver.find_element(By.ID, "system-metrics-chart")
            assert chart_canvas.is_displayed(), "System metrics chart should be visible"
            
            # Test system info sections
            system_info = self.driver.find_element(By.ID, "system-info")
            assert system_info.is_displayed(), "System info should be visible"
            
            # Test service status section
            service_status = self.driver.find_element(By.ID, "service-status")
            assert service_status.is_displayed(), "Service status should be visible"
            
            # Test queue metrics section
            queue_metrics = self.driver.find_element(By.ID, "queue-metrics")
            assert queue_metrics.is_displayed(), "Queue metrics should be visible"
            
            self.log_test("Analytics Dashboard", True, "Analytics dashboard renders correctly")
            
        except Exception as e:
            self.log_test("Analytics Dashboard", False, f"Analytics dashboard testing failed: {str(e)}")
    
    def test_realtime_tasks_interface(self):
        """Test real-time tasks interface."""
        logger.info("Testing Real-Time Tasks Interface")
        
        try:
            self.driver.get(self.base_url)
            
            # Switch to real-time tasks tab
            realtime_tab = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-tab="tab-realtime"]')))
            realtime_tab.click()
            
            # Test real-time tasks content
            realtime_content = self.wait.until(EC.visibility_of_element_located((By.ID, "tab-realtime")))
            assert realtime_content.is_displayed(), "Real-time tasks content should be visible"
            
            # Test real-time tasks list
            tasks_list = self.driver.find_element(By.ID, "realtime-tasks-list")
            assert tasks_list.is_displayed(), "Real-time tasks list should be visible"
            
            # Check for initial message
            assert "Waiting for updates" in tasks_list.text, "Should show waiting message initially"
            
            self.log_test("Real-Time Tasks Interface", True, "Real-time tasks interface works correctly")
            
        except Exception as e:
            self.log_test("Real-Time Tasks Interface", False, f"Real-time tasks testing failed: {str(e)}")
    
    def test_controls_interface(self):
        """Test controls interface."""
        logger.info("Testing Controls Interface")
        
        try:
            self.driver.get(self.base_url)
            
            # Switch to controls tab
            controls_tab = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-tab="tab-controls"]')))
            controls_tab.click()
            
            # Test controls content
            controls_content = self.wait.until(EC.visibility_of_element_located((By.ID, "tab-controls")))
            assert controls_content.is_displayed(), "Controls content should be visible"
            
            # Test controls placeholder
            placeholder = self.driver.find_element(By.ID, "controls-placeholder")
            assert placeholder.is_displayed(), "Controls placeholder should be visible"
            assert "Coming Soon" in placeholder.text, "Should show coming soon message"
            
            self.log_test("Controls Interface", True, "Controls interface works correctly")
            
        except Exception as e:
            self.log_test("Controls Interface", False, f"Controls testing failed: {str(e)}")
    
    def test_live_metrics_display(self):
        """Test live metrics display functionality."""
        logger.info("Testing Live Metrics Display")
        
        try:
            self.driver.get(self.base_url)
            
            # Test live metrics panel
            metrics_panel = self.wait.until(EC.presence_of_element_located((By.ID, "live-metrics")))
            assert metrics_panel.is_displayed(), "Live metrics panel should be visible"
            
            # Test individual metric elements
            cpu_metric = self.driver.find_element(By.ID, "metric-cpu")
            mem_metric = self.driver.find_element(By.ID, "metric-mem")
            disk_metric = self.driver.find_element(By.ID, "metric-disk")
            redis_metric = self.driver.find_element(By.ID, "metric-redis")
            
            # Check that metrics are displayed
            assert cpu_metric.is_displayed(), "CPU metric should be visible"
            assert mem_metric.is_displayed(), "Memory metric should be visible"
            assert disk_metric.is_displayed(), "Disk metric should be visible"
            assert redis_metric.is_displayed(), "Redis metric should be visible"
            
            # Check initial values (should be "-" initially)
            assert cpu_metric.text == "-" or cpu_metric.text.isdigit(), "CPU metric should show dash or number"
            assert mem_metric.text == "-" or mem_metric.text.isdigit(), "Memory metric should show dash or number"
            assert disk_metric.text == "-" or disk_metric.text.isdigit(), "Disk metric should show dash or number"
            assert redis_metric.text in ["-", "OK", "Error"], "Redis metric should show dash, OK, or Error"
            
            self.log_test("Live Metrics Display", True, "Live metrics display works correctly")
            
        except Exception as e:
            self.log_test("Live Metrics Display", False, f"Live metrics testing failed: {str(e)}")
    
    def test_flex_servers_panel(self):
        """Test Flex servers panel functionality."""
        logger.info("Testing Flex Servers Panel")
        
        try:
            self.driver.get(self.base_url)
            
            # Test flex servers panel
            flex_panel = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".bg-gray-800.rounded-lg.p-6")))
            assert flex_panel.is_displayed(), "Flex servers panel should be visible"
            
            # Test flex servers list
            flex_list = self.driver.find_element(By.ID, "flex-servers-list")
            assert flex_list.is_displayed(), "Flex servers list should be visible"
            
            # Test refresh button
            refresh_btn = self.driver.find_element(By.CSS_SELECTOR, "button[onclick='loadFlexServers()']")
            assert refresh_btn.is_displayed(), "Refresh button should be visible"
            assert "Refresh" in refresh_btn.text, "Refresh button should have correct text"
            
            self.log_test("Flex Servers Panel", True, "Flex servers panel works correctly")
            
        except Exception as e:
            self.log_test("Flex Servers Panel", False, f"Flex servers testing failed: {str(e)}")
    
    def test_responsive_design(self):
        """Test responsive design across different viewport sizes."""
        logger.info("Testing Responsive Design")
        
        try:
            self.driver.get(self.base_url)
            
            # Test different viewport sizes
            viewports = [
                (1920, 1080),  # Desktop
                (1366, 768),   # Laptop
                (768, 1024),   # Tablet
                (375, 667)     # Mobile
            ]
            
            for width, height in viewports:
                self.driver.set_window_size(width, height)
                time.sleep(1)  # Allow layout to adjust
                
                # Check that main elements are still visible
                header = self.driver.find_element(By.TAG_NAME, "h1")
                assert header.is_displayed(), f"Header should be visible at {width}x{height}"
                
                # Check navigation tabs
                tabs = self.driver.find_elements(By.CSS_SELECTOR, "#main-tabs .tab-btn")
                assert len(tabs) > 0, f"Navigation tabs should be visible at {width}x{height}"
                
                # Check container responsiveness
                container = self.driver.find_element(By.CSS_SELECTOR, ".container")
                assert container.is_displayed(), f"Container should be visible at {width}x{height}"
            
            self.log_test("Responsive Design", True, "Responsive design works across viewport sizes")
            
        except Exception as e:
            self.log_test("Responsive Design", False, f"Responsive design testing failed: {str(e)}")
    
    def test_accessibility_features(self):
        """Test basic accessibility features."""
        logger.info("Testing Accessibility Features")
        
        try:
            self.driver.get(self.base_url)
            
            # Test semantic HTML structure
            header = self.driver.find_element(By.TAG_NAME, "h1")
            assert header.is_displayed(), "Main heading should be present"
            
            # Test navigation structure
            nav = self.driver.find_element(By.TAG_NAME, "nav")
            assert nav.is_displayed(), "Navigation should be present"
            
            # Test form elements have proper labels/placeholders
            search_input = self.driver.find_element(By.ID, "search-input")
            placeholder = search_input.get_attribute("placeholder")
            assert placeholder, "Search input should have placeholder text"
            
            # Test button accessibility
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                # Buttons should be clickable or have proper ARIA attributes
                assert button.is_enabled() or button.get_attribute("aria-disabled"), "Buttons should be accessible"
            
            # Test color contrast (basic check)
            body = self.driver.find_element(By.TAG_NAME, "body")
            bg_color = body.value_of_css_property("background-color")
            assert "rgb(17, 24, 39)" in bg_color or "rgba(17, 24, 39" in bg_color, "Should have dark background"
            
            self.log_test("Accessibility Features", True, "Basic accessibility features are present")
            
        except Exception as e:
            self.log_test("Accessibility Features", False, f"Accessibility testing failed: {str(e)}")
    
    def test_error_handling_and_feedback(self):
        """Test error handling and user feedback mechanisms."""
        logger.info("Testing Error Handling and User Feedback")
        
        try:
            self.driver.get(self.base_url)
            
            # Test file details modal functionality
            details_btn = self.driver.find_element(By.CSS_SELECTOR, "button[onclick='showFileDetails()']")
            assert details_btn.is_displayed(), "File details button should be present"
            
            # Check if modal exists and is hidden initially
            modal = self.driver.find_element(By.ID, "file-details-modal")
            assert "hidden" in modal.get_attribute("class"), "Modal should be hidden initially"
            
            # Test modal close button exists (even when hidden)
            close_btn = self.driver.find_element(By.CSS_SELECTOR, "button[onclick='closeFileDetails()']")
            assert close_btn is not None, "Modal close button should exist"
            
            # Test CSRF token handling - look for it in any script tag
            scripts = self.driver.find_elements(By.CSS_SELECTOR, "script")
            csrf_found = False
            for script in scripts:
                if script.get_attribute("innerHTML") and "csrfToken" in script.get_attribute("innerHTML"):
                    csrf_found = True
                    break
            assert csrf_found, "CSRF token handling should be present in page scripts"
            
            self.log_test("Error Handling and User Feedback", True, "Error handling mechanisms are in place")
            
        except Exception as e:
            self.log_test("Error Handling and User Feedback", False, f"Error handling testing failed: {str(e)}")
    
    def run_all_frontend_tests(self, headless=True):
        """Run all frontend GUI tests."""
        logger.info("Starting Frontend GUI Testing Suite")
        
        try:
            self.setup_driver(headless)
            
            # Run all test methods
            test_methods = [
                self.test_ui_rendering_and_layout,
                self.test_navigation_and_tab_functionality,
                self.test_file_browser_functionality,
                self.test_analytics_dashboard,
                self.test_realtime_tasks_interface,
                self.test_controls_interface,
                self.test_live_metrics_display,
                self.test_flex_servers_panel,
                self.test_responsive_design,
                self.test_accessibility_features,
                self.test_error_handling_and_feedback
            ]
            
            for test_method in test_methods:
                try:
                    test_method()
                except Exception as e:
                    logger.error(f"Test {test_method.__name__} failed: {str(e)}")
            
            # Generate test summary
            passed = sum(1 for result in self.test_results if result['success'])
            total = len(self.test_results)
            
            logger.info(f"Frontend GUI Testing Complete: {passed}/{total} tests passed")
            
            return self.test_results
            
        finally:
            self.teardown_driver()


def run_frontend_gui_tests():
    """Main function to run frontend GUI tests."""
    logger.info("Starting Frontend GUI Testing")
    
    tester = FrontendGUITester()
    results = tester.run_all_frontend_tests(headless=True)
    
    # Print summary
    print("\n" + "="*60)
    print("FRONTEND GUI TESTING RESULTS")
    print("="*60)
    
    passed = 0
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} {result['test']}: {result['message']}")
        if result['success']:
            passed += 1
    
    print(f"\nSummary: {passed}/{len(results)} tests passed")
    
    return results


if __name__ == "__main__":
    run_frontend_gui_tests()

# NEXT STEP: Add Selenium WebDriver setup instructions and integrate with CI/CD pipeline 
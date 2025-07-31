#!/usr/bin/env python3
"""
Visual Regression Testing

This module captures screenshots of the frontend and compares them to baseline images
to detect visual changes that might indicate bugs or unintended UI changes.
"""

import os
import sys
import time
import json
import hashlib
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
from PIL import Image, ImageChops
import numpy as np
from loguru import logger

# PURPOSE: Visual regression testing for frontend UI consistency
# DEPENDENCIES: Selenium, Pillow, numpy
# MODIFICATION NOTES: v1.0 - Initial visual regression testing implementation


class VisualRegressionTester:
    """Visual regression testing for frontend UI."""
    
    def __init__(self, base_url="http://localhost:5050"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.screenshot_dir = Path("tests/frontend/screenshots")
        self.baseline_dir = self.screenshot_dir / "baseline"
        self.current_dir = self.screenshot_dir / "current"
        self.diff_dir = self.screenshot_dir / "diff"
        
        # Create directories
        for dir_path in [self.baseline_dir, self.current_dir, self.diff_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def setup_driver(self):
        """Set up Selenium WebDriver for visual testing."""
        chrome_options = Options()
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
    
    def capture_screenshot(self, name, element_selector=None):
        """Capture a screenshot of the page or specific element."""
        try:
            # Wait for page to load
            time.sleep(2)
            
            if element_selector:
                try:
                    # Wait for element and capture it
                    element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, element_selector)))
                    screenshot = element.screenshot_as_png
                except Exception as e:
                    logger.warning(f"Element {element_selector} not found, capturing full page instead: {str(e)}")
                    screenshot = self.driver.get_screenshot_as_png()
            else:
                # Capture full page
                screenshot = self.driver.get_screenshot_as_png()
            
            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.current_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(screenshot)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot {name}: {str(e)}")
            return None
    
    def compare_screenshots(self, current_path, baseline_path, threshold=0.95):
        """Compare current screenshot with baseline."""
        try:
            if not baseline_path.exists():
                logger.warning(f"Baseline not found: {baseline_path}")
                return False, 0.0, "No baseline found"
            
            # Load images
            current_img = Image.open(current_path)
            baseline_img = Image.open(baseline_path)
            
            # Ensure same size
            if current_img.size != baseline_img.size:
                current_img = current_img.resize(baseline_img.size)
            
            # Convert to RGB if needed
            if current_img.mode != 'RGB':
                current_img = current_img.convert('RGB')
            if baseline_img.mode != 'RGB':
                baseline_img = baseline_img.convert('RGB')
            
            # Calculate difference
            diff = ImageChops.difference(current_img, baseline_img)
            
            # Calculate similarity percentage
            total_pixels = diff.size[0] * diff.size[1]
            diff_pixels = np.sum(np.array(diff) > 0)
            similarity = 1 - (diff_pixels / total_pixels)
            
            # Save diff image if significant difference
            if similarity < threshold:
                diff_filename = f"diff_{current_path.stem}_{baseline_path.stem}.png"
                diff_path = self.diff_dir / diff_filename
                diff.save(diff_path)
                return False, similarity, f"Visual difference detected. Diff saved to {diff_path}"
            
            return True, similarity, "Screenshots match"
            
        except Exception as e:
            logger.error(f"Failed to compare screenshots: {str(e)}")
            return False, 0.0, f"Comparison error: {str(e)}"
    
    def test_main_page_layout(self):
        """Test main page layout consistency."""
        logger.info("Testing main page layout")
        
        try:
            self.driver.get(self.base_url)
            time.sleep(2)  # Wait for page to load
            
            # Capture full page screenshot
            current_path = self.capture_screenshot("main_page")
            if not current_path:
                return False
            
            # Compare with baseline
            baseline_path = self.baseline_dir / "main_page_baseline.png"
            matches, similarity, message = self.compare_screenshots(current_path, baseline_path)
            
            if matches:
                logger.info(f"✅ Main page layout matches baseline (similarity: {similarity:.2%})")
                return True
            else:
                logger.warning(f"❌ Main page layout differs: {message}")
                return False
                
        except Exception as e:
            logger.error(f"Main page layout test failed: {str(e)}")
            return False
    
    def test_navigation_tabs(self):
        """Test navigation tabs visual consistency."""
        logger.info("Testing navigation tabs")
        
        try:
            self.driver.get(self.base_url)
            time.sleep(2)
            
            # Test each tab
            tabs = ["tab-browser", "tab-analytics", "tab-realtime", "tab-controls"]
            results = []
            
            for tab_id in tabs:
                # Click tab
                tab_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-tab="{tab_id}"]')))
                tab_btn.click()
                time.sleep(1)
                
                # Capture tab content screenshot
                current_path = self.capture_screenshot(f"tab_{tab_id}")
                if current_path:
                    baseline_path = self.baseline_dir / f"tab_{tab_id}_baseline.png"
                    matches, similarity, message = self.compare_screenshots(current_path, baseline_path)
                    results.append((tab_id, matches, similarity, message))
            
            # Report results
            all_passed = all(matches for _, matches, _, _ in results)
            for tab_id, matches, similarity, message in results:
                if matches:
                    logger.info(f"✅ Tab {tab_id} matches baseline (similarity: {similarity:.2%})")
                else:
                    logger.warning(f"❌ Tab {tab_id} differs: {message}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Navigation tabs test failed: {str(e)}")
            return False
    
    def test_responsive_design(self):
        """Test responsive design across different viewport sizes."""
        logger.info("Testing responsive design")
        
        try:
            viewports = [
                (1920, 1080, "desktop"),
                (1366, 768, "laptop"),
                (768, 1024, "tablet"),
                (375, 667, "mobile")
            ]
            
            results = []
            
            for width, height, name in viewports:
                self.driver.set_window_size(width, height)
                time.sleep(1)
                
                self.driver.get(self.base_url)
                time.sleep(2)
                
                # Capture screenshot
                current_path = self.capture_screenshot(f"responsive_{name}")
                if current_path:
                    baseline_path = self.baseline_dir / f"responsive_{name}_baseline.png"
                    matches, similarity, message = self.compare_screenshots(current_path, baseline_path)
                    results.append((name, matches, similarity, message))
            
            # Report results
            all_passed = all(matches for _, matches, _, _ in results)
            for name, matches, similarity, message in results:
                if matches:
                    logger.info(f"✅ {name} viewport matches baseline (similarity: {similarity:.2%})")
                else:
                    logger.warning(f"❌ {name} viewport differs: {message}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Responsive design test failed: {str(e)}")
            return False
    
    def test_ui_components(self):
        """Test individual UI components."""
        logger.info("Testing UI components")
        
        try:
            self.driver.get(self.base_url)
            time.sleep(2)
            
            components = [
                ("live_metrics", "#live-metrics"),
                ("file_browser", "#file-list"),
                ("queue_status", "#queue-list"),
                ("flex_servers", "#flex-servers-list")
            ]
            
            results = []
            
            for component_name, selector in components:
                try:
                    # Wait for component to be present
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    time.sleep(0.5)
                    
                    # Capture component screenshot
                    current_path = self.capture_screenshot(f"component_{component_name}", selector)
                    if current_path:
                        baseline_path = self.baseline_dir / f"component_{component_name}_baseline.png"
                        matches, similarity, message = self.compare_screenshots(current_path, baseline_path)
                        results.append((component_name, matches, similarity, message))
                except Exception as e:
                    logger.warning(f"Component {component_name} not found: {str(e)}")
                    results.append((component_name, False, 0.0, f"Component not found: {str(e)}"))
            
            # Report results
            all_passed = all(matches for _, matches, _, _ in results)
            for component_name, matches, similarity, message in results:
                if matches:
                    logger.info(f"✅ Component {component_name} matches baseline (similarity: {similarity:.2%})")
                else:
                    logger.warning(f"❌ Component {component_name} differs: {message}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"UI components test failed: {str(e)}")
            return False
    
    def create_baseline(self):
        """Create baseline screenshots for comparison."""
        logger.info("Creating baseline screenshots")
        
        try:
            self.setup_driver()
            
            # Main page
            self.driver.get(self.base_url)
            time.sleep(3)
            self.capture_screenshot("main_page")
            
            # Navigation tabs
            tabs = ["tab-browser", "tab-analytics", "tab-realtime", "tab-controls"]
            for tab_id in tabs:
                try:
                    tab_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-tab="{tab_id}"]')))
                    tab_btn.click()
                    time.sleep(2)
                    self.capture_screenshot(f"tab_{tab_id}")
                except Exception as e:
                    logger.warning(f"Tab {tab_id} not clickable: {str(e)}")
                    self.capture_screenshot(f"tab_{tab_id}")
            
            # Responsive design
            viewports = [
                (1920, 1080, "desktop"),
                (1366, 768, "laptop"),
                (768, 1024, "tablet"),
                (375, 667, "mobile")
            ]
            
            for width, height, name in viewports:
                try:
                    self.driver.set_window_size(width, height)
                    time.sleep(2)
                    self.driver.get(self.base_url)
                    time.sleep(3)
                    self.capture_screenshot(f"responsive_{name}")
                except Exception as e:
                    logger.warning(f"Viewport {name} failed: {str(e)}")
            
            # UI components - capture full page for each component
            components = [
                ("live_metrics", "#live-metrics"),
                ("file_browser", "#file-list"),
                ("queue_status", "#queue-list"),
                ("flex_servers", "#flex-servers-list")
            ]
            
            self.driver.get(self.base_url)
            time.sleep(3)
            
            for component_name, selector in components:
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    time.sleep(1)
                    self.capture_screenshot(f"component_{component_name}", selector)
                except Exception as e:
                    logger.warning(f"Component {component_name} not found, capturing full page: {str(e)}")
                    self.capture_screenshot(f"component_{component_name}")
            
            # Move current screenshots to baseline
            for file_path in self.current_dir.glob("*.png"):
                baseline_path = self.baseline_dir / file_path.name.replace(".png", "_baseline.png")
                file_path.rename(baseline_path)
            
            logger.info("✅ Baseline screenshots created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create baseline: {str(e)}")
        finally:
            self.teardown_driver()
    
    def run_visual_tests(self):
        """Run all visual regression tests."""
        logger.info("Starting visual regression tests")
        
        try:
            self.setup_driver()
            
            tests = [
                ("Main Page Layout", self.test_main_page_layout),
                ("Navigation Tabs", self.test_navigation_tabs),
                ("Responsive Design", self.test_responsive_design),
                ("UI Components", self.test_ui_components)
            ]
            
            results = []
            for test_name, test_func in tests:
                try:
                    result = test_func()
                    results.append((test_name, result))
                except Exception as e:
                    logger.error(f"Test {test_name} failed: {str(e)}")
                    results.append((test_name, False))
            
            # Generate report
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            logger.info(f"Visual regression tests complete: {passed}/{total} passed")
            
            return results
            
        except Exception as e:
            logger.error(f"Visual regression tests failed: {str(e)}")
            return []
        finally:
            self.teardown_driver()


def run_visual_regression_tests():
    """Main function to run visual regression tests."""
    logger.info("Starting Visual Regression Testing")
    
    tester = VisualRegressionTester()
    results = tester.run_visual_tests()
    
    # Print summary
    print("\n" + "="*60)
    print("VISUAL REGRESSION TESTING RESULTS")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nSummary: {passed}/{len(results)} tests passed")
    
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "create-baseline":
        tester = VisualRegressionTester()
        tester.create_baseline()
    else:
        run_visual_regression_tests()

# NEXT STEP: Run with "python3 tests/frontend/test_visual_regression.py create-baseline" to create baseline images 
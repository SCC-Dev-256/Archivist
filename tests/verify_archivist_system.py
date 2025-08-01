#!/usr/bin/env python3
"""
Comprehensive Archivist system verification script.
Tests all major components of the Archivist application.
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logging for tests
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

class ArchivistSystemVerifier:
    """Comprehensive Archivist system verification."""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result with consistent formatting."""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if details:
            logger.info(f"   Details: {details}")
        self.results[test_name] = passed
    
    def test_core_imports(self):
        """Test core module imports."""
        logger.info("\n🔧 Testing Core Module Imports...")
        
        core_modules = [
            ('core.config', 'Configuration'),
            ('core.app', 'Application Factory'),
            ('core.services', 'Services'),
            ('core.tasks', 'Tasks'),
            ('core.api', 'API Routes'),
            ('core.monitoring', 'Monitoring'),
            ('core.security', 'Security'),
            ('core.exceptions', 'Exceptions')
        ]
        
        for module_name, display_name in core_modules:
            try:
                __import__(module_name)
                self.log_test(display_name, True, f"{display_name} imported successfully")
            except ImportError as e:
                self.log_test(display_name, False, f"Import error: {e}")
    
    def test_service_layer(self):
        """Test service layer functionality."""
        logger.info("\n🎯 Testing Service Layer...")
        
        services = [
            ('TranscriptionService', 'core.services'),
            ('QueueService', 'core.services'),
            ('FileService', 'core.services'),
            ('CablecastService', 'core.services')
        ]
        
        for service_name, module_name in services:
            try:
                module = __import__(module_name, fromlist=[service_name])
                service_class = getattr(module, service_name, None)
                
                if service_class:
                    # Try to instantiate the service
                    try:
                        service = service_class()
                        self.log_test(service_name, True, f"{service_name} instantiated successfully")
                    except Exception as e:
                        self.log_test(service_name, False, f"Instantiation error: {e}")
                else:
                    self.log_test(service_name, False, f"{service_name} not found in {module_name}")
                    
            except ImportError as e:
                self.log_test(service_name, False, f"Import error: {e}")
    
    def test_task_system(self):
        """Test task system functionality."""
        logger.info("\n📋 Testing Task System...")
        
        try:
            from celery import current_app
            
            if current_app:
                self.log_test("Celery App", True, "Celery application available")
                
                # Test task registration
                registered_tasks = current_app.tasks.keys()
                transcription_tasks = [task for task in registered_tasks if 'transcription' in task.lower()]
                
                if transcription_tasks:
                    self.log_test("Task Registration", True, f"Found {len(transcription_tasks)} transcription tasks")
                else:
                    self.log_test("Task Registration", False, "No transcription tasks found")
            else:
                self.log_test("Celery App", False, "Celery application not available")
                
        except ImportError:
            self.log_test("Celery App", False, "Celery not available")
        except Exception as e:
            self.log_test("Task System", False, f"Unexpected error: {e}")
    
    def test_api_endpoints(self):
        """Test API endpoints."""
        logger.info("\n🌐 Testing API Endpoints...")
        
        base_url = "http://localhost:5000"
        timeout = 10
        
        endpoints = [
            ("/health", "Health Check"),
            ("/api/transcribe", "Transcription API"),
            ("/api/queue", "Queue API"),
            ("/api/cablecast/shows", "Cablecast API"),
            ("/api/vod", "VOD API")
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=timeout)
                
                if response.status_code in [200, 405, 401]:  # OK, Method Not Allowed, Unauthorized
                    self.log_test(name, True, f"Endpoint responding (status: {response.status_code})")
                elif response.status_code == 404:
                    self.log_test(name, False, "Endpoint not found")
                else:
                    self.log_test(name, False, f"Unexpected status: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                self.log_test(name, False, "Could not connect to API")
            except Exception as e:
                self.log_test(name, False, f"Error: {e}")
    
    def test_database_connection(self):
        """Test database connectivity."""
        logger.info("\n🗄️ Testing Database Connection...")
        
        try:
            from core.config import Config
            
            config = Config()
            if hasattr(config, 'SQLALCHEMY_DATABASE_URI'):
                self.log_test("Database Config", True, "Database URI configured")
                
                # Test database connection
                try:
                    from sqlalchemy import create_engine
                    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
                    with engine.connect() as conn:
                        conn.execute("SELECT 1")
                    self.log_test("Database Connection", True, "Database connection successful")
                except Exception as e:
                    self.log_test("Database Connection", False, f"Connection error: {e}")
            else:
                self.log_test("Database Config", False, "Database URI not configured")
                
        except ImportError as e:
            self.log_test("Database Config", False, f"Import error: {e}")
        except Exception as e:
            self.log_test("Database", False, f"Unexpected error: {e}")
    
    def test_file_system_access(self):
        """Test file system access."""
        logger.info("\n📁 Testing File System Access...")
        
        # Test flex mounts
        flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4']
        available_mounts = 0
        
        for mount in flex_mounts:
            if os.path.ismount(mount):
                available_mounts += 1
                self.log_test(f"Mount {mount}", True, "Mount available")
            else:
                self.log_test(f"Mount {mount}", False, "Mount not available")
        
        if available_mounts > 0:
            self.log_test("File System Access", True, f"{available_mounts} flex mounts available")
        else:
            self.log_test("File System Access", False, "No flex mounts available")
        
        # Test critical directories
        critical_dirs = ['/tmp', '/var/log', '/opt/Archivist']
        for directory in critical_dirs:
            if os.path.exists(directory):
                if os.access(directory, os.R_OK):
                    self.log_test(f"Directory {directory}", True, "Directory readable")
                else:
                    self.log_test(f"Directory {directory}", False, "Directory not readable")
            else:
                self.log_test(f"Directory {directory}", False, "Directory does not exist")
    
    def test_security_features(self):
        """Test security features."""
        logger.info("\n🔒 Testing Security Features...")
        
        try:
            from core.security import SecurityManager
            
            security = SecurityManager()
            self.log_test("Security Manager", True, "SecurityManager instantiated")
            
            # Test security methods
            if hasattr(security, 'validate_path'):
                self.log_test("Path Validation", True, "Path validation method available")
            else:
                self.log_test("Path Validation", False, "Path validation method not found")
                
        except ImportError as e:
            self.log_test("Security Manager", False, f"Import error: {e}")
        except Exception as e:
            self.log_test("Security Features", False, f"Unexpected error: {e}")
    
    def test_monitoring_system(self):
        """Test monitoring system."""
        logger.info("\n📊 Testing Monitoring System...")
        
        try:
            from core.monitoring import get_metrics_collector
            
            metrics = get_metrics_collector()
            self.log_test("Metrics Collector", True, "Metrics collector available")
            
            # Test metrics functionality
            if hasattr(metrics, 'increment'):
                self.log_test("Metrics Methods", True, "Metrics methods available")
            else:
                self.log_test("Metrics Methods", False, "Metrics methods not found")
                
        except ImportError as e:
            self.log_test("Metrics Collector", False, f"Import error: {e}")
        except Exception as e:
            self.log_test("Monitoring System", False, f"Unexpected error: {e}")
    
    def test_exception_system(self):
        """Test exception handling system."""
        logger.info("\n⚠️ Testing Exception System...")
        
        try:
            from core.exceptions import (
                ArchivistException, TranscriptionError, FileError,
                create_error_response, map_exception_to_http_status
            )
            
            self.log_test("Exception Classes", True, "Exception classes imported")
            
            # Test exception utilities
            if callable(create_error_response):
                self.log_test("Error Response Utility", True, "Error response utility available")
            else:
                self.log_test("Error Response Utility", False, "Error response utility not found")
                
            if callable(map_exception_to_http_status):
                self.log_test("Status Mapping Utility", True, "Status mapping utility available")
            else:
                self.log_test("Status Mapping Utility", False, "Status mapping utility not found")
                
        except ImportError as e:
            self.log_test("Exception Classes", False, f"Import error: {e}")
        except Exception as e:
            self.log_test("Exception System", False, f"Unexpected error: {e}")
    
    def generate_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "="*60)
        logger.info("📊 ARCHIVIST SYSTEM VERIFICATION REPORT")
        logger.info("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            logger.info("\n❌ Failed Tests:")
            for test_name, result in self.results.items():
                if not result:
                    logger.info(f"   - {test_name}")
        
        logger.info(f"\n⏱️  Verification completed in: {datetime.now() - self.start_time}")
        
        if failed_tests == 0:
            logger.info("🎉 All Archivist system tests passed!")
            return True
        else:
            logger.warning(f"⚠️  {failed_tests} tests failed. Please review the issues above.")
            return False
    
    def run_all_tests(self):
        """Run all verification tests."""
        logger.info("🚀 Starting Archivist System Verification")
        logger.info("="*60)
        
        # Run all test categories
        self.test_core_imports()
        self.test_service_layer()
        self.test_task_system()
        self.test_api_endpoints()
        self.test_database_connection()
        self.test_file_system_access()
        self.test_security_features()
        self.test_monitoring_system()
        self.test_exception_system()
        
        # Generate report
        return self.generate_report()

def main():
    """Main verification function."""
    verifier = ArchivistSystemVerifier()
    success = verifier.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
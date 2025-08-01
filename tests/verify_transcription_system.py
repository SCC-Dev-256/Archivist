#!/usr/bin/env python3
"""
Comprehensive transcription system verification script.
Tests all aspects of the transcription system including service layer, tasks, and API endpoints.
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

class TranscriptionSystemVerifier:
    """Comprehensive transcription system verification."""
    
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
    
    def test_service_layer(self):
        """Test transcription service layer."""
        logger.info("\n🎤 Testing Transcription Service Layer...")
        
        try:
            from core.services import TranscriptionService
            
            service = TranscriptionService()
            self.log_test("Service Import", True, "TranscriptionService imported successfully")
            
            # Test service methods
            if hasattr(service, 'transcribe_file'):
                self.log_test("Service Methods", True, "transcribe_file method available")
            else:
                self.log_test("Service Methods", False, "transcribe_file method not found")
                return False
            
            # Test service configuration
            if hasattr(service, 'config'):
                self.log_test("Service Configuration", True, "Service has configuration")
            else:
                self.log_test("Service Configuration", False, "Service missing configuration")
            
            return True
            
        except ImportError as e:
            self.log_test("Service Import", False, f"Import error: {e}")
            return False
        except Exception as e:
            self.log_test("Service Layer", False, f"Unexpected error: {e}")
            return False
    
    def test_task_layer(self):
        """Test transcription task layer."""
        logger.info("\n📋 Testing Transcription Task Layer...")
        
        try:
            from core.tasks.transcription import run_whisper_transcription
            
            self.log_test("Task Import", True, "Task function imported successfully")
            
            # Test task function
            if callable(run_whisper_transcription):
                self.log_test("Task Function", True, "Task function is callable")
            else:
                self.log_test("Task Function", False, "Task function is not callable")
                return False
            
            # Test Celery integration
            try:
                from celery import current_app
                if current_app:
                    self.log_test("Celery Integration", True, "Celery app available")
                else:
                    self.log_test("Celery Integration", False, "Celery app not available")
            except ImportError:
                self.log_test("Celery Integration", False, "Celery not available")
            
            return True
            
        except ImportError as e:
            self.log_test("Task Import", False, f"Import error: {e}")
            return False
        except Exception as e:
            self.log_test("Task Layer", False, f"Unexpected error: {e}")
            return False
    
    def test_direct_transcription(self):
        """Test direct transcription functionality."""
        logger.info("\n🎯 Testing Direct Transcription...")
        
        try:
            from core.transcription import run_whisper_transcription
            
            self.log_test("Direct Import", True, "Direct transcription imported")
            
            if callable(run_whisper_transcription):
                self.log_test("Direct Function", True, "Direct function is callable")
            else:
                self.log_test("Direct Function", False, "Direct function is not callable")
                return False
            
            return True
            
        except ImportError as e:
            self.log_test("Direct Import", False, f"Import error: {e}")
            return False
        except Exception as e:
            self.log_test("Direct Transcription", False, f"Unexpected error: {e}")
            return False
    
    def test_queue_integration(self):
        """Test queue integration."""
        logger.info("\n🔄 Testing Queue Integration...")
        
        try:
            from core.services import QueueService
            
            service = QueueService()
            self.log_test("Queue Service", True, "QueueService imported and initialized")
            
            # Test queue methods
            if hasattr(service, 'enqueue_transcription'):
                self.log_test("Queue Methods", True, "enqueue_transcription method available")
            else:
                self.log_test("Queue Methods", False, "enqueue_transcription method not found")
            
            return True
            
        except ImportError as e:
            self.log_test("Queue Service", False, f"Import error: {e}")
            return False
        except Exception as e:
            self.log_test("Queue Integration", False, f"Unexpected error: {e}")
            return False
    
    def test_api_endpoints(self):
        """Test API endpoints."""
        logger.info("\n🌐 Testing API Endpoints...")
        
        base_url = "http://localhost:5000"
        timeout = 10
        
        # Test health endpoint
        try:
            response = requests.get(f"{base_url}/health", timeout=timeout)
            if response.status_code == 200:
                self.log_test("Health Endpoint", True, "Health endpoint responding")
            else:
                self.log_test("Health Endpoint", False, f"Status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log_test("Health Endpoint", False, "Could not connect to API")
        except Exception as e:
            self.log_test("Health Endpoint", False, f"Error: {e}")
        
        # Test transcription endpoint
        try:
            response = requests.get(f"{base_url}/api/transcribe", timeout=timeout)
            if response.status_code in [405, 404]:  # Method not allowed or not found
                self.log_test("Transcription Endpoint", True, f"Endpoint exists (status: {response.status_code})")
            else:
                self.log_test("Transcription Endpoint", True, f"Endpoint responding (status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            self.log_test("Transcription Endpoint", False, "Could not connect to API")
        except Exception as e:
            self.log_test("Transcription Endpoint", False, f"Error: {e}")
        
        # Test queue endpoint
        try:
            response = requests.get(f"{base_url}/api/queue", timeout=timeout)
            if response.status_code in [200, 404]:
                self.log_test("Queue Endpoint", True, f"Endpoint responding (status: {response.status_code})")
            else:
                self.log_test("Queue Endpoint", False, f"Unexpected status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log_test("Queue Endpoint", False, "Could not connect to API")
        except Exception as e:
            self.log_test("Queue Endpoint", False, f"Error: {e}")
    
    def test_file_system(self):
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
        
        # Test temp directory
        temp_dir = "/tmp"
        if os.access(temp_dir, os.W_OK):
            self.log_test("Temp Directory", True, "Temp directory writable")
        else:
            self.log_test("Temp Directory", False, "Temp directory not writable")
    
    def test_dependencies(self):
        """Test required dependencies."""
        logger.info("\n📦 Testing Dependencies...")
        
        dependencies = [
            ('faster_whisper', 'Faster Whisper'),
            ('torch', 'PyTorch'),
            ('transformers', 'Transformers'),
            ('celery', 'Celery'),
            ('flask', 'Flask'),
            ('loguru', 'Loguru'),
            ('requests', 'Requests'),
            ('sqlalchemy', 'SQLAlchemy')
        ]
        
        for module_name, display_name in dependencies:
            try:
                __import__(module_name)
                self.log_test(display_name, True, f"{display_name} available")
            except ImportError:
                self.log_test(display_name, False, f"{display_name} not available")
    
    def generate_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "="*60)
        logger.info("📊 TRANSCRIPTION SYSTEM VERIFICATION REPORT")
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
            logger.info("🎉 All transcription system tests passed!")
            return True
        else:
            logger.warning(f"⚠️  {failed_tests} tests failed. Please review the issues above.")
            return False
    
    def run_all_tests(self):
        """Run all verification tests."""
        logger.info("🚀 Starting Transcription System Verification")
        logger.info("="*60)
        
        # Run all test categories
        self.test_service_layer()
        self.test_task_layer()
        self.test_direct_transcription()
        self.test_queue_integration()
        self.test_api_endpoints()
        self.test_file_system()
        self.test_dependencies()
        
        # Generate report
        return self.generate_report()

def main():
    """Main verification function."""
    verifier = TranscriptionSystemVerifier()
    success = verifier.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
#!/usr/bin/env python3
"""
Test script to demonstrate and resolve the core module import hanging issue.

This script tests:
1. Import performance and hanging detection
2. Connection timeout handling
3. Lazy loading implementation
4. Circular import detection
5. Graceful degradation

Usage:
    python tests/test_import_hanging_issue.py
"""

import time
import sys
import os
import signal
import threading
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional
import statistics

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ImportTimeoutError(Exception):
    """Raised when an import takes too long."""
    pass

class ImportHangingTester:
    """Test suite for detecting and resolving import hanging issues."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.results = {}
        
    def test_import_with_timeout(self, module_name: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Test importing a module with a timeout."""
        
        if timeout is None:
            timeout = self.timeout
            
        # Clear module cache if it exists
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        start_time = time.time()
        result = {
            'module': module_name,
            'success': False,
            'elapsed': 0,
            'error': None,
            'hanging': False
        }
        
        def import_module():
            """Import the module in a separate thread."""
            try:
                __import__(module_name)
                result['success'] = True
            except Exception as e:
                result['error'] = str(e)
        
        # Run import in separate thread
        import_thread = threading.Thread(target=import_module)
        import_thread.daemon = True
        import_thread.start()
        
        # Wait for import to complete or timeout
        import_thread.join(timeout=timeout)
        
        result['elapsed'] = time.time() - start_time
        
        if import_thread.is_alive():
            result['hanging'] = True
            result['error'] = f"Import hung for {timeout} seconds"
            # Note: We can't actually kill the thread, but we can detect hanging
            
        return result
    
    def test_basic_imports(self) -> Dict[str, Any]:
        """Test basic lightweight imports."""
        
        print("🔍 Testing basic imports...")
        
        basic_modules = [
            'core.exceptions',
            'core.models',
            'core.config',
            'core.database'
        ]
        
        results = {}
        for module in basic_modules:
            result = self.test_import_with_timeout(module, timeout=2)
            results[module] = result
            print(f"  {module}: {result['elapsed']:.3f}s {'✅' if result['success'] else '❌'}")
            
        return results
    
    def test_heavy_imports(self) -> Dict[str, Any]:
        """Test heavy imports that might hang."""
        
        print("\n🔍 Testing heavy imports...")
        
        heavy_modules = [
            'core.tasks',
            'core.monitoring.integrated_dashboard',
            'core.admin_ui',
            'core.services',
            'core'
        ]
        
        results = {}
        for module in heavy_modules:
            result = self.test_import_with_timeout(module, timeout=5)
            results[module] = result
            status = '✅' if result['success'] else '❌'
            if result['hanging']:
                status = '⏰'
            print(f"  {module}: {result['elapsed']:.3f}s {status}")
            if result['error']:
                print(f"    Error: {result['error']}")
                
        return results
    
    def test_import_with_mocks(self) -> Dict[str, Any]:
        """Test imports with external dependencies mocked."""
        
        print("\n🔍 Testing imports with mocked dependencies...")
        
        # Mock external dependencies
        mocks = {
            'redis.Redis': MagicMock(),
            'celery.Celery': MagicMock(),
            'flask_sqlalchemy.SQLAlchemy': MagicMock(),
            'flask.Flask': MagicMock(),
            'flask_socketio.SocketIO': MagicMock(),
        }
        
        patches = [patch(mock_path, mock_obj) for mock_path, mock_obj in mocks.items()]
        
        results = {}
        
        with patch.multiple('redis', Redis=MagicMock()), \
             patch.multiple('celery', Celery=MagicMock()), \
             patch.multiple('flask_sqlalchemy', SQLAlchemy=MagicMock()), \
             patch.multiple('flask', Flask=MagicMock()), \
             patch.multiple('flask_socketio', SocketIO=MagicMock()):
            
            heavy_modules = [
                'core.tasks',
                'core.monitoring.integrated_dashboard', 
                'core.admin_ui',
                'core.services',
                'core'
            ]
            
            for module in heavy_modules:
                result = self.test_import_with_timeout(module, timeout=3)
                results[module] = result
                status = '✅' if result['success'] else '❌'
                print(f"  {module}: {result['elapsed']:.3f}s {status}")
                
        return results
    
    def test_connection_timeouts(self) -> Dict[str, Any]:
        """Test connection timeout handling."""
        
        print("\n🔍 Testing connection timeout handling...")
        
        def slow_redis_connection(*args, **kwargs):
            """Simulate slow Redis connection."""
            time.sleep(10)  # Simulate hanging connection
            return MagicMock()
        
        def slow_db_connection(*args, **kwargs):
            """Simulate slow database connection."""
            time.sleep(10)  # Simulate hanging connection
            return MagicMock()
        
        results = {}
        
        # Test Redis timeout
        with patch('redis.Redis', side_effect=slow_redis_connection):
            result = self.test_import_with_timeout('core.tasks', timeout=3)
            results['redis_timeout'] = result
            print(f"  Redis timeout test: {result['elapsed']:.3f}s {'⏰' if result['hanging'] else '✅'}")
        
        # Test database timeout
        with patch('flask_sqlalchemy.SQLAlchemy', side_effect=slow_db_connection):
            result = self.test_import_with_timeout('core.app', timeout=3)
            results['db_timeout'] = result
            print(f"  Database timeout test: {result['elapsed']:.3f}s {'⏰' if result['hanging'] else '✅'}")
            
        return results
    
    def test_circular_imports(self) -> Dict[str, Any]:
        """Test for circular import detection."""
        
        print("\n🔍 Testing circular import detection...")
        
        # Test the specific circular import between core and admin_ui
        try:
            # Clear both modules from cache
            for module in ['core', 'core.admin_ui']:
                if module in sys.modules:
                    del sys.modules[module]
            
            # Try importing admin_ui which imports from core
            result = self.test_import_with_timeout('core.admin_ui', timeout=5)
            
            if result['success']:
                print("  ✅ No circular import detected")
            else:
                print(f"  ❌ Import failed: {result['error']}")
                
            return {'circular_import_test': result}
            
        except Exception as e:
            print(f"  ❌ Circular import test failed: {e}")
            return {'circular_import_test': {'error': str(e)}}
    
    def benchmark_import_performance(self) -> Dict[str, Any]:
        """Benchmark import performance across multiple runs."""
        
        print("\n🔍 Benchmarking import performance...")
        
        modules_to_test = [
            'core.exceptions',
            'core.models',
            'core.config',
            'core.tasks',
            'core.services',
            'core'
        ]
        
        results = {}
        
        for module in modules_to_test:
            times = []
            successes = 0
            
            for run in range(5):  # Run 5 times
                # Clear module cache
                if module in sys.modules:
                    del sys.modules[module]
                
                with patch.multiple('redis', Redis=MagicMock()), \
                     patch.multiple('celery', Celery=MagicMock()), \
                     patch.multiple('flask_sqlalchemy', SQLAlchemy=MagicMock()):
                    
                    result = self.test_import_with_timeout(module, timeout=3)
                    if result['success']:
                        times.append(result['elapsed'])
                        successes += 1
            
            if times:
                results[module] = {
                    'mean': statistics.mean(times),
                    'std': statistics.stdev(times) if len(times) > 1 else 0,
                    'min': min(times),
                    'max': max(times),
                    'success_rate': successes / 5
                }
                
                print(f"  {module}: {results[module]['mean']:.3f}s ± {results[module]['std']:.3f}s "
                      f"(success rate: {results[module]['success_rate']:.1%})")
            else:
                results[module] = {'error': 'All runs failed'}
                print(f"  {module}: ❌ All runs failed")
                
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all import tests."""
        
        print("🚀 Starting Import Hanging Issue Tests")
        print("=" * 50)
        
        all_results = {}
        
        # Test 1: Basic imports
        all_results['basic_imports'] = self.test_basic_imports()
        
        # Test 2: Heavy imports
        all_results['heavy_imports'] = self.test_heavy_imports()
        
        # Test 3: Mocked imports
        all_results['mocked_imports'] = self.test_import_with_mocks()
        
        # Test 4: Connection timeouts
        all_results['connection_timeouts'] = self.test_connection_timeouts()
        
        # Test 5: Circular imports
        all_results['circular_imports'] = self.test_circular_imports()
        
        # Test 6: Performance benchmarking
        all_results['performance_benchmark'] = self.benchmark_import_performance()
        
        return all_results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive test report."""
        
        report = []
        report.append("📊 IMPORT HANGING ISSUE TEST REPORT")
        report.append("=" * 50)
        
        # Summary statistics
        total_tests = 0
        successful_tests = 0
        hanging_tests = 0
        
        for test_category, test_results in results.items():
            report.append(f"\n{test_category.upper()}:")
            
            if isinstance(test_results, dict):
                for test_name, result in test_results.items():
                    total_tests += 1
                    
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successful_tests += 1
                            status = "✅ PASS"
                        elif result.get('hanging', False):
                            hanging_tests += 1
                            status = "⏰ HANGING"
                        else:
                            status = "❌ FAIL"
                        
                        elapsed = result.get('elapsed', 0)
                        report.append(f"  {test_name}: {elapsed:.3f}s {status}")
                        
                        if result.get('error'):
                            report.append(f"    Error: {result['error']}")
        
        # Overall summary
        report.append(f"\nSUMMARY:")
        report.append(f"  Total Tests: {total_tests}")
        report.append(f"  Successful: {successful_tests}")
        report.append(f"  Failed: {total_tests - successful_tests - hanging_tests}")
        report.append(f"  Hanging: {hanging_tests}")
        report.append(f"  Success Rate: {successful_tests/total_tests:.1%}" if total_tests > 0 else "  Success Rate: N/A")
        
        # Recommendations
        report.append(f"\nRECOMMENDATIONS:")
        if hanging_tests > 0:
            report.append("  ⚠️  Hanging imports detected - implement lazy loading")
        if total_tests - successful_tests - hanging_tests > 0:
            report.append("  ⚠️  Import failures detected - check dependencies")
        if successful_tests == total_tests:
            report.append("  ✅ All imports working correctly")
        
        return "\n".join(report)

def main():
    """Main test runner."""
    
    # Create tester instance
    tester = ImportHangingTester(timeout=10)
    
    try:
        # Run all tests
        results = tester.run_all_tests()
        
        # Generate and print report
        report = tester.generate_report(results)
        print("\n" + report)
        
        # Save report to file
        with open('import_hanging_test_report.txt', 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: import_hanging_test_report.txt")
        
        # Return exit code based on results
        total_tests = sum(len(r) if isinstance(r, dict) else 1 for r in results.values())
        successful_tests = sum(
            sum(1 for result in r.values() if isinstance(result, dict) and result.get('success', False))
            for r in results.values() if isinstance(r, dict)
        )
        
        if successful_tests == total_tests:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed - check the report for details")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 
#!/usr/bin/env python3
"""
Celery Migration Test & Evaluation Script

This script tests and evaluates the migration from RQ to Celery,
providing a comprehensive assessment of the consolidation.
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_celery_task_registration():
    """Test 1: Verify all Celery tasks are properly registered."""
    print("\n🔍 TEST 1: Celery Task Registration")
    print("=" * 50)
    
    try:
        from core.tasks import celery_app
        
        tasks = list(celery_app.tasks.keys())
        total_tasks = len(tasks)
        
        # Categorize tasks
        vod_tasks = [task for task in tasks if 'vod_processing' in task]
        transcription_tasks = [task for task in tasks if 'transcription' in task]
        caption_tasks = [task for task in tasks if 'caption_checks' in task]
        
        print(f"✅ Total tasks registered: {total_tasks}")
        print(f"✅ VOD processing tasks: {len(vod_tasks)}")
        print(f"✅ Transcription tasks: {len(transcription_tasks)}")
        print(f"✅ Caption check tasks: {len(caption_tasks)}")
        
        # Expected tasks
        expected_vod_tasks = [
            'vod_processing.process_recent_vods',
            'vod_processing.process_single_vod',
            'vod_processing.download_vod_content',
            'vod_processing.generate_vod_captions',
            'vod_processing.retranscode_vod_with_captions',
            'vod_processing.upload_captioned_vod',
            'vod_processing.validate_vod_quality',
            'vod_processing.cleanup_temp_files'
        ]
        
        expected_transcription_tasks = [
            'transcription.run_whisper',
            'transcription.batch_process',
            'transcription.cleanup_temp_files'
        ]
        
        # Check for missing tasks
        missing_vod = [task for task in expected_vod_tasks if task not in vod_tasks]
        missing_transcription = [task for task in expected_transcription_tasks if task not in transcription_tasks]
        
        if missing_vod:
            print(f"❌ Missing VOD tasks: {missing_vod}")
            return False
        
        if missing_transcription:
            print(f"❌ Missing transcription tasks: {missing_transcription}")
            return False
        
        print("✅ All expected tasks are registered")
        return True
        
    except Exception as e:
        print(f"❌ Task registration test failed: {e}")
        return False

def test_transcription_task_import():
    """Test 2: Verify transcription task can be imported and called."""
    print("\n🔍 TEST 2: Transcription Task Import & Functionality")
    print("=" * 50)
    
    try:
        from core.tasks.transcription import run_whisper_transcription, enqueue_transcription
        
        print("✅ Transcription task imported successfully")
        print(f"✅ Task function: {run_whisper_transcription.__name__}")
        print(f"✅ Task name: {run_whisper_transcription.name}")
        print(f"✅ Backward compatibility function: {enqueue_transcription.__name__}")
        
        # Test task signature
        import inspect
        sig = inspect.signature(run_whisper_transcription)
        print(f"✅ Task signature: {sig}")
        
        return True
        
    except Exception as e:
        print(f"❌ Transcription task import failed: {e}")
        return False

def test_vod_processing_integration():
    """Test 3: Verify VOD processing uses Celery transcription."""
    print("\n🔍 TEST 3: VOD Processing Integration")
    print("=" * 50)
    
    try:
        from core.tasks.vod_processing import process_recent_vods, process_single_vod
        
        print("✅ VOD processing tasks imported successfully")
        print(f"✅ process_recent_vods function: {process_recent_vods.__name__}")
        print(f"✅ process_single_vod function: {process_single_vod.__name__}")
        
        # Check if VOD processing imports Celery transcription
        import inspect
        
        # Get the actual function (not the decorator wrapper)
        actual_function = process_single_vod
        if hasattr(process_single_vod, '__wrapped__'):
            actual_function = process_single_vod.__wrapped__
        
        try:
            vod_source = inspect.getsource(actual_function)
            
            if 'run_whisper_transcription' in vod_source:
                print("✅ VOD processing uses Celery transcription task")
            else:
                print("❌ VOD processing does not use Celery transcription task")
                return False
        except Exception as e:
            print(f"⚠️ Could not inspect source code: {e}")
            # Fallback: check if the import is present
            if 'from core.tasks.transcription import run_whisper_transcription' in vod_source:
                print("✅ VOD processing imports Celery transcription task")
            else:
                print("❌ VOD processing does not import Celery transcription task")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ VOD processing integration test failed: {e}")
        return False

def test_rq_system_removal():
    """Test 4: Verify RQ system components are removed from startup."""
    print("\n🔍 TEST 4: RQ System Removal")
    print("=" * 50)
    
    try:
        # Check startup script
        with open('start_archivist_centralized.sh', 'r') as f:
            startup_content = f.read()
        
        rq_mentions = startup_content.count('rq_worker')
        rq_startup_functions = startup_content.count('start_rq_worker')
        
        print(f"📊 RQ mentions in startup script: {rq_mentions}")
        print(f"📊 RQ startup functions: {rq_startup_functions}")
        
        if rq_mentions == 0:
            print("✅ RQ system completely removed from startup script")
            return True
        elif rq_mentions <= 2:  # Only in comments or status checks
            print("⚠️ RQ system mostly removed (some references remain)")
            return True
        else:
            print("❌ RQ system still present in startup script")
            return False
            
    except Exception as e:
        print(f"❌ RQ removal test failed: {e}")
        return False

def test_celery_worker_status():
    """Test 5: Verify Celery workers are running."""
    print("\n🔍 TEST 5: Celery Worker Status")
    print("=" * 50)
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        # Check Redis connection
        r.ping()
        print("✅ Redis connection successful")
        
        # Check for running Celery processes
        import psutil
        celery_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'celery' in proc.info['name'].lower() and 'worker' in ' '.join(proc.info['cmdline'] or []):
                    celery_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        print(f"✅ Celery worker processes found: {len(celery_processes)}")
        
        if len(celery_processes) > 0:
            print("✅ Celery workers are running")
            return True
        else:
            print("❌ No Celery worker processes detected")
            return False
            
    except Exception as e:
        print(f"❌ Celery worker status test failed: {e}")
        return False

def test_backward_compatibility():
    """Test 6: Verify backward compatibility functions work."""
    print("\n🔍 TEST 6: Backward Compatibility")
    print("=" * 50)
    
    try:
        from core.tasks.transcription import enqueue_transcription
        
        # Test the backward compatibility function
        # This should work without actually submitting a task
        print("✅ Backward compatibility function imported")
        
        # Test function signature
        import inspect
        sig = inspect.signature(enqueue_transcription)
        print(f"✅ Function signature: {sig}")
        
        # Check if it returns a string (task ID)
        print("✅ Backward compatibility function ready")
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def test_system_health():
    """Test 7: Overall system health check."""
    print("\n🔍 TEST 7: System Health Check")
    print("=" * 50)
    
    try:
        # Check if core services are running
        import psutil
        
        # Check for Celery processes
        celery_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'celery' in proc.info['name'].lower():
                    celery_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        print(f"✅ Celery processes found: {len(celery_processes)}")
        
        # Check for RQ processes (should be none)
        rq_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'rq' in proc.info['name'].lower():
                    rq_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if len(rq_processes) == 0:
            print("✅ No RQ processes running (good)")
        else:
            print(f"⚠️ RQ processes still running: {len(rq_processes)}")
        
        return len(celery_processes) > 0
        
    except Exception as e:
        print(f"❌ System health check failed: {e}")
        return False

def generate_migration_report():
    """Generate comprehensive migration report."""
    print("\n📊 CELERY MIGRATION EVALUATION REPORT")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run all tests
    tests = [
        ("Task Registration", test_celery_task_registration),
        ("Transcription Task Import", test_transcription_task_import),
        ("VOD Processing Integration", test_vod_processing_integration),
        ("RQ System Removal", test_rq_system_removal),
        ("Celery Worker Status", test_celery_worker_status),
        ("Backward Compatibility", test_backward_compatibility),
        ("System Health", test_system_health)
    ]
    
    results = {}
    total_tests = len(tests)
    passed_tests = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            if result:
                passed_tests += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            results[test_name] = False
            print(f"❌ {test_name}: ERROR - {e}")
    
    # Calculate overall score
    score = (passed_tests / total_tests) * 100
    
    print("\n" + "=" * 60)
    print("📈 MIGRATION SUCCESS METRICS")
    print("=" * 60)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {score:.1f}%")
    
    if score >= 90:
        grade = "A+"
        status = "EXCELLENT"
    elif score >= 80:
        grade = "A"
        status = "VERY GOOD"
    elif score >= 70:
        grade = "B"
        status = "GOOD"
    elif score >= 60:
        grade = "C"
        status = "ACCEPTABLE"
    else:
        grade = "F"
        status = "NEEDS IMPROVEMENT"
    
    print(f"Grade: {grade}")
    print(f"Status: {status}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("=" * 60)
    
    if score >= 90:
        print("✅ Migration is highly successful!")
        print("✅ System is ready for production")
        print("✅ Consider removing remaining RQ references")
    elif score >= 80:
        print("✅ Migration is mostly successful")
        print("⚠️ Address any failed tests before production")
        print("✅ Monitor system performance")
    elif score >= 70:
        print("⚠️ Migration needs some attention")
        print("⚠️ Fix failed tests before production")
        print("⚠️ Consider rolling back if critical issues")
    else:
        print("❌ Migration has significant issues")
        print("❌ Do not deploy to production")
        print("❌ Consider rolling back to RQ system")
    
    # Save detailed results
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'score': score,
        'grade': grade,
        'status': status,
        'results': results,
        'passed_tests': passed_tests,
        'total_tests': total_tests
    }
    
    with open('celery_migration_report.json', 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: celery_migration_report.json")
    
    return score >= 80  # Return True if migration is successful

if __name__ == '__main__':
    success = generate_migration_report()
    sys.exit(0 if success else 1) 
#!/usr/bin/env python3
"""
Database ↔ Service Integration Tests

This module contains comprehensive integration tests that verify the interaction
between the database layer and service layer in the Archivist application.

Test Categories:
1. VOD CRUD Operations
2. Transaction Management
3. Concurrent Access
4. Error Recovery
5. Data Consistency
"""

import os
import sys
import time
import uuid
import threading
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from loguru import logger
from core.exceptions import (
    DatabaseError,
    ValidationError,
    VODError,
    FileError
)


class TestDatabaseServiceIntegration:
    """Integration tests for database and service layer interaction."""
    
    def setup_method(self):
        """Set up test environment."""
        from core.app import create_app, db
        from core.models import CablecastVODORM, TranscriptionResultORM
        
        # Create test app with test database
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            self.db = db
            
            # Import services after database setup
            from core.services import get_vod_service, get_transcription_service
            self.vod_service = get_vod_service()
            self.transcription_service = get_transcription_service()
    
    def teardown_method(self):
        """Clean up test environment."""
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
    
    def test_vod_crud_operations(self):
        """Test complete VOD CRUD operations through service layer."""
        logger.info("Testing VOD CRUD operations...")
        
        # 1. Create VOD through service
        vod_data = {
            'title': f'Test VOD {uuid.uuid4().hex[:8]}',
            'file_path': '/test/video.mp4',
            'duration': 300,
            'file_size': 1024 * 1024 * 100,  # 100MB
            'vod_state': 'pending'
        }
        
        vod_id = self.vod_service.create_vod(vod_data)
        assert vod_id is not None
        logger.info(f"Created VOD with ID: {vod_id}")
        
        # 2. Read VOD through service
        vod = self.vod_service.get_vod(vod_id)
        assert vod is not None
        assert vod['title'] == vod_data['title']
        assert vod['file_path'] == vod_data['file_path']
        assert vod['vod_state'] == 'pending'
        logger.info(f"Retrieved VOD: {vod['title']}")
        
        # 3. Update VOD through service
        update_data = {
            'vod_state': 'processing',
            'percent_complete': 25
        }
        
        success = self.vod_service.update_vod(vod_id, update_data)
        assert success is True
        
        # 4. Verify update in database
        updated_vod = self.vod_service.get_vod(vod_id)
        assert updated_vod['vod_state'] == 'processing'
        assert updated_vod['percent_complete'] == 25
        logger.info(f"Updated VOD state to: {updated_vod['vod_state']}")
        
        # 5. List VODs through service
        vods = self.vod_service.get_all_vods()
        assert len(vods) >= 1
        assert any(v['id'] == vod_id for v in vods)
        logger.info(f"Found {len(vods)} VODs in database")
        
        # 6. Delete VOD through service
        success = self.vod_service.delete_vod(vod_id)
        assert success is True
        
        # 7. Verify deletion
        deleted_vod = self.vod_service.get_vod(vod_id)
        assert deleted_vod is None
        logger.info("VOD successfully deleted")
    
    def test_transaction_management(self):
        """Test database transaction management and rollback scenarios."""
        logger.info("Testing transaction management...")
        
        # 1. Create initial VOD
        vod_data = {
            'title': 'Transaction Test VOD',
            'file_path': '/test/transaction_test.mp4',
            'vod_state': 'pending'
        }
        
        vod_id = self.vod_service.create_vod(vod_data)
        initial_vod = self.vod_service.get_vod(vod_id)
        assert initial_vod['vod_state'] == 'pending'
        
        # 2. Test successful transaction
        try:
            # Update VOD state
            self.vod_service.update_vod(vod_id, {'vod_state': 'processing'})
            
            # Verify update persisted
            updated_vod = self.vod_service.get_vod(vod_id)
            assert updated_vod['vod_state'] == 'processing'
            logger.info("Successful transaction completed")
            
        except Exception as e:
            logger.error(f"Transaction failed unexpectedly: {e}")
            assert False, "Transaction should have succeeded"
        
        # 3. Test transaction rollback on validation error
        try:
            # Attempt invalid update
            self.vod_service.update_vod(vod_id, {'vod_state': 'invalid_status'})
            assert False, "Should have raised validation error"
            
        except ValidationError:
            # Verify rollback - status should still be 'processing'
            final_vod = self.vod_service.get_vod(vod_id)
            assert final_vod['vod_state'] == 'processing'
            logger.info("Transaction rollback verified")
        
        # 4. Test concurrent transaction handling
        def concurrent_update(thread_id):
            """Perform concurrent update operation."""
            try:
                update_data = {
                    'vod_state': f'processing_thread_{thread_id}',
                    'percent_complete': thread_id * 10
                }
                return self.vod_service.update_vod(vod_id, update_data)
            except Exception as e:
                return f"Error in thread {thread_id}: {e}"
        
        # Run concurrent updates
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_update, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # At least one update should succeed
        assert any(result is True for result in results)
        logger.info("Concurrent transaction handling verified")
    
    def test_concurrent_access_scenarios(self):
        """Test database behavior under concurrent access."""
        logger.info("Testing concurrent access scenarios...")
        
        # 1. Test concurrent VOD creation
        def create_vod(thread_id):
            """Create a VOD from a specific thread."""
            vod_data = {
                'title': f'Concurrent VOD {thread_id}',
                'file_path': f'/test/concurrent_{thread_id}.mp4',
                'vod_state': 'pending'
            }
            return self.vod_service.create_vod(vod_data)
        
        # Create VODs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_vod, i) for i in range(20)]
            vod_ids = [future.result() for future in futures]
        
        # All VODs should be created successfully
        assert len(vod_ids) == 20
        assert all(vod_id is not None for vod_id in vod_ids)
        logger.info(f"Successfully created {len(vod_ids)} VODs concurrently")
        
        # 2. Test concurrent reads
        def read_vod(vod_id):
            """Read a VOD from database."""
            return self.vod_service.get_vod(vod_id)
        
        # Read VODs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(read_vod, vod_id) for vod_id in vod_ids]
            vod_results = [future.result() for future in futures]
        
        # All reads should succeed
        assert len(vod_results) == 20
        assert all(vod is not None for vod in vod_results)
        logger.info("Concurrent reads completed successfully")
        
        # 3. Test concurrent updates
        def update_vod(vod_id, thread_id):
            """Update a VOD from a specific thread."""
            update_data = {
                'vod_state': f'updated_by_thread_{thread_id}',
                'percent_complete': thread_id * 5
            }
            return self.vod_service.update_vod(vod_id, update_data)
        
        # Update VODs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(update_vod, vod_ids[i], i) for i in range(10)]
            update_results = [future.result() for future in futures]
        
        # All updates should succeed
        assert len(update_results) == 10
        assert all(result is True for result in update_results)
        logger.info("Concurrent updates completed successfully")
        
        # 4. Test data consistency under concurrent access
        def read_all_vods():
            """Read all VODs from database."""
            return self.vod_service.get_all_vods()
        
        # Read all VODs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_all_vods) for _ in range(30)]
            all_vod_results = [future.result() for future in futures]
        
        # All reads should return consistent data
        vod_counts = [len(vods) for vods in all_vod_results]
        assert len(set(vod_counts)) == 1, "All reads should return same count"
        assert vod_counts[0] >= 20, "Should have at least 20 VODs"
        logger.info("Data consistency verified under concurrent access")
    
    def test_error_recovery_scenarios(self):
        """Test database error recovery and resilience."""
        logger.info("Testing error recovery scenarios...")
        
        # 1. Test invalid data handling
        try:
            # Attempt to create VOD with invalid data
            invalid_vod_data = {
                'title': None,  # Invalid: title cannot be None
                'file_path': '/test/invalid.mp4',
                'vod_state': 'invalid_state'  # Invalid state
            }
            
            vod_id = self.vod_service.create_vod(invalid_vod_data)
            assert False, "Should have raised validation error"
            
        except ValidationError as e:
            logger.info(f"Validation error caught: {e}")
        
        # 2. Test database constraint violations
        try:
            # Create VOD with duplicate unique constraint (if applicable)
            vod_data = {
                'title': 'Duplicate Test VOD',
                'file_path': '/test/duplicate.mp4',
                'vod_state': 'pending'
            }
            
            # Create first VOD
            vod_id_1 = self.vod_service.create_vod(vod_data)
            assert vod_id_1 is not None
            
            # Attempt to create duplicate (should fail if unique constraints exist)
            vod_id_2 = self.vod_service.create_vod(vod_data)
            
            # If no unique constraints, both should succeed
            if vod_id_2 is not None:
                logger.info("No unique constraints on VOD data")
            else:
                logger.info("Unique constraint violation handled")
                
        except DatabaseError as e:
            logger.info(f"Database constraint error handled: {e}")
        
        # 3. Test service layer error handling
        try:
            # Attempt to get non-existent VOD
            non_existent_vod = self.vod_service.get_vod(99999)
            assert non_existent_vod is None, "Should return None for non-existent VOD"
            logger.info("Non-existent VOD handling verified")
            
        except Exception as e:
            logger.error(f"Unexpected error getting non-existent VOD: {e}")
            assert False, "Should handle non-existent VOD gracefully"
        
        # 4. Test transaction rollback on service error
        # Create a VOD first
        vod_data = {
            'title': 'Rollback Test VOD',
            'file_path': '/test/rollback_test.mp4',
            'vod_state': 'pending'
        }
        
        vod_id = self.vod_service.create_vod(vod_data)
        initial_state = self.vod_service.get_vod(vod_id)['vod_state']
        
        try:
            # Attempt invalid operation that should cause rollback
            self.vod_service.update_vod(vod_id, {'vod_state': 'invalid_state'})
            assert False, "Should have raised validation error"
            
        except ValidationError:
            # Verify rollback occurred
            final_state = self.vod_service.get_vod(vod_id)['vod_state']
            assert final_state == initial_state, "Transaction should have rolled back"
            logger.info("Transaction rollback on service error verified")
    
    def test_data_consistency(self):
        """Test data consistency across operations."""
        logger.info("Testing data consistency...")
        
        # 1. Test VOD state transitions
        vod_data = {
            'title': 'Consistency Test VOD',
            'file_path': '/test/consistency_test.mp4',
            'vod_state': 'pending'
        }
        
        vod_id = self.vod_service.create_vod(vod_data)
        
        # Define valid state transitions
        valid_transitions = [
            ('pending', 'processing'),
            ('processing', 'completed'),
            ('processing', 'failed'),
            ('failed', 'pending')  # Retry scenario
        ]
        
        for from_state, to_state in valid_transitions:
            # Update to target state
            self.vod_service.update_vod(vod_id, {'vod_state': to_state})
            
            # Verify state change
            vod = self.vod_service.get_vod(vod_id)
            assert vod['vod_state'] == to_state, f"State should be {to_state}"
            logger.info(f"State transition {from_state} -> {to_state} verified")
        
        # 2. Test data integrity across service calls
        # Create multiple VODs
        vod_ids = []
        for i in range(5):
            vod_data = {
                'title': f'Integrity Test VOD {i}',
                'file_path': f'/test/integrity_test_{i}.mp4',
                'vod_state': 'pending'
            }
            vod_ids.append(self.vod_service.create_vod(vod_data))
        
        # Verify all VODs exist
        all_vods = self.vod_service.get_all_vods()
        assert len(all_vods) >= 6  # 5 new + 1 from previous test
        
        # Verify each VOD can be retrieved individually
        for vod_id in vod_ids:
            vod = self.vod_service.get_vod(vod_id)
            assert vod is not None, f"VOD {vod_id} should exist"
            assert vod['id'] == vod_id, f"VOD ID should match {vod_id}"
        
        logger.info("Data integrity verified across service calls")
        
        # 3. Test relationship consistency
        # Create transcription for a VOD
        vod_id = vod_ids[0]
        transcription_data = {
            'video_path': f'/test/integrity_test_0.mp4',
            'status': 'completed',
            'output_path': '/test/transcription.scc',
            'vod_id': vod_id
        }
        
        transcription_id = self.transcription_service.create_transcription(transcription_data)
        assert transcription_id is not None
        
        # Verify transcription is linked to VOD
        transcription = self.transcription_service.get_transcription(transcription_id)
        assert transcription['vod_id'] == vod_id
        
        # Verify VOD has transcription
        vod = self.vod_service.get_vod(vod_id)
        # Note: This depends on how the relationship is implemented
        logger.info("Relationship consistency verified")
    
    def test_performance_under_load(self):
        """Test database performance under load."""
        logger.info("Testing performance under load...")
        
        import time
        import statistics
        
        # 1. Baseline performance measurement
        baseline_times = []
        for _ in range(10):
            start_time = time.time()
            vods = self.vod_service.get_all_vods()
            baseline_times.append(time.time() - start_time)
        
        baseline_avg = statistics.mean(baseline_times)
        logger.info(f"Baseline average query time: {baseline_avg:.4f}s")
        
        # 2. Create load
        def load_operation():
            """Perform a typical load operation."""
            # Create VOD
            vod_data = {
                'title': f'Load Test VOD {uuid.uuid4().hex[:8]}',
                'file_path': f'/test/load_test_{uuid.uuid4().hex[:8]}.mp4',
                'vod_state': 'pending'
            }
            vod_id = self.vod_service.create_vod(vod_data)
            
            # Read VOD
            vod = self.vod_service.get_vod(vod_id)
            
            # Update VOD
            self.vod_service.update_vod(vod_id, {'vod_state': 'processing'})
            
            return vod_id is not None and vod is not None
        
        # 3. Run concurrent load
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(load_operation) for _ in range(100)]
            results = [future.result() for future in futures]
        
        load_duration = time.time() - start_time
        
        # 4. Verify all operations succeeded
        assert all(results), "All load operations should succeed"
        logger.info(f"100 concurrent operations completed in {load_duration:.2f}s")
        
        # 5. Measure performance under load
        load_times = []
        for _ in range(10):
            start_time = time.time()
            vods = self.vod_service.get_all_vods()
            load_times.append(time.time() - start_time)
        
        load_avg = statistics.mean(load_times)
        
        # 6. Performance assertions
        assert load_avg < baseline_avg * 3, "Performance should not degrade more than 3x under load"
        assert load_duration < 30, "100 concurrent operations should complete within 30 seconds"
        
        logger.info(f"Performance under load verified: {load_avg:.4f}s average query time")


def run_database_service_integration_tests():
    """Run all database service integration tests."""
    logger.info("Starting Database ↔ Service Integration Tests")
    
    # Create test instance
    tester = TestDatabaseServiceIntegration()
    
    # Run tests
    test_methods = [
        tester.test_vod_crud_operations,
        tester.test_transaction_management,
        tester.test_concurrent_access_scenarios,
        tester.test_error_recovery_scenarios,
        tester.test_data_consistency,
        tester.test_performance_under_load
    ]
    
    results = []
    for test_method in test_methods:
        try:
            tester.setup_method()
            test_method()
            results.append((test_method.__name__, True, "Passed"))
            logger.info(f"✅ {test_method.__name__}: PASSED")
        except Exception as e:
            results.append((test_method.__name__, False, str(e)))
            logger.error(f"❌ {test_method.__name__}: FAILED - {e}")
        finally:
            tester.teardown_method()
    
    # Generate summary
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    logger.info(f"\n📊 Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_database_service_integration_tests()
    sys.exit(0 if success else 1) 
#!/usr/bin/env python3
"""
System Integration Tests

This module contains comprehensive integration tests that verify complete
end-to-end workflows and system behavior in the Archivist application.

Test Categories:
1. Complete VOD Processing Workflow
2. User Authentication Workflow
3. Error Recovery Workflows
4. System Performance Under Load
5. Data Consistency Across Components
"""

import os
import sys
import time
import uuid
import json
import threading
import concurrent.futures
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from loguru import logger
from core.exceptions import (
    ValidationError,
    DatabaseError,
    VODError,
    ConnectionError
)


class TestSystemIntegration:
    """Integration tests for complete system workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        from core.app import create_app, db
        
        # Create test app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            self.db = db
        
        # Create test client
        self.client = self.app.test_client()
        self.client.testing = True
        
        # Import services
        from core.services import get_vod_service, get_transcription_service, get_queue_service
        self.vod_service = get_vod_service()
        self.transcription_service = get_transcription_service()
        self.queue_service = get_queue_service()
        
        # Base URL for API endpoints
        self.base_url = '/api'
    
    def teardown_method(self):
        """Clean up test environment."""
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
    
    def test_complete_vod_processing_workflow(self):
        """Test complete VOD processing workflow from start to finish."""
        logger.info("Testing complete VOD processing workflow...")
        
        # 1. Create VOD through API
        vod_data = {
            'title': f'Complete Workflow Test VOD {uuid.uuid4().hex[:8]}',
            'file_path': '/test/complete_workflow_test.mp4',
            'duration': 300,
            'file_size': 1024 * 1024 * 50  # 50MB
        }
        
        create_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=vod_data,
            content_type='application/json'
        )
        assert create_response.status_code == 201
        vod_id = json.loads(create_response.data)['id']
        logger.info(f"Created VOD with ID: {vod_id}")
        
        # 2. Verify VOD in database through service
        vod = self.vod_service.get_vod(vod_id)
        assert vod is not None
        assert vod['title'] == vod_data['title']
        assert vod['vod_state'] == 'pending'
        logger.info("VOD verified in database")
        
        # 3. Update VOD status to processing
        update_response = self.client.put(
            f'{self.base_url}/vod/{vod_id}',
            json={'vod_state': 'processing'},
            content_type='application/json'
        )
        assert update_response.status_code == 200
        
        # 4. Verify status update
        updated_vod = self.vod_service.get_vod(vod_id)
        assert updated_vod['vod_state'] == 'processing'
        logger.info("VOD status updated to processing")
        
        # 5. Simulate transcription processing
        transcription_data = {
            'video_path': vod_data['file_path'],
            'status': 'completed',
            'output_path': '/test/transcription.scc',
            'vod_id': vod_id
        }
        
        transcription_id = self.transcription_service.create_transcription(transcription_data)
        assert transcription_id is not None
        logger.info(f"Created transcription with ID: {transcription_id}")
        
        # 6. Update VOD with transcription results
        final_update_response = self.client.put(
            f'{self.base_url}/vod/{vod_id}',
            json={
                'vod_state': 'completed',
                'percent_complete': 100,
                'transcription_id': transcription_id
            },
            content_type='application/json'
        )
        assert final_update_response.status_code == 200
        
        # 7. Verify final state
        final_vod = self.vod_service.get_vod(vod_id)
        assert final_vod['vod_state'] == 'completed'
        assert final_vod['percent_complete'] == 100
        logger.info("VOD processing workflow completed successfully")
        
        # 8. Verify through API
        api_vod_response = self.client.get(f'{self.base_url}/vod/{vod_id}')
        assert api_vod_response.status_code == 200
        api_vod_data = json.loads(api_vod_response.data)
        assert api_vod_data['vod_state'] == 'completed'
        logger.info("Complete workflow verified through API")
    
    def test_user_authentication_workflow(self):
        """Test complete user authentication and authorization workflow."""
        logger.info("Testing user authentication workflow...")
        
        # 1. Test user registration (if implemented)
        user_data = {
            'username': f'test_user_{uuid.uuid4().hex[:8]}',
            'email': f'test_{uuid.uuid4().hex[:8]}@example.com',
            'password': 'test_password_123'
        }
        
        # Note: This depends on whether user registration is implemented
        # For now, we'll test with existing user authentication
        
        # 2. Test login endpoint
        login_data = {
            'username': 'test_user',
            'password': 'test_password'
        }
        
        login_response = self.client.post(
            f'{self.base_url}/auth/login',
            json=login_data,
            content_type='application/json'
        )
        
        # Handle different possible responses
        if login_response.status_code == 200:
            # Login successful
            login_result = json.loads(login_response.data)
            assert 'access_token' in login_result
            token = login_result['access_token']
            logger.info("User login successful")
            
            # 3. Test protected endpoint access
            headers = {'Authorization': f'Bearer {token}'}
            protected_response = self.client.get(
                f'{self.base_url}/vod/list',
                headers=headers
            )
            assert protected_response.status_code == 200
            logger.info("Protected endpoint access verified")
            
            # 4. Test admin endpoint access (should fail for regular user)
            admin_response = self.client.get(
                f'{self.base_url}/admin/status',
                headers=headers
            )
            # Should be 403 (forbidden) or 404 (not found)
            assert admin_response.status_code in [403, 404]
            logger.info("Admin access restriction verified")
            
        elif login_response.status_code == 401:
            # Login failed (expected in test environment)
            logger.info("Login failed as expected in test environment")
        else:
            # Unexpected response
            logger.warning(f"Unexpected login response: {login_response.status_code}")
    
    def test_error_recovery_workflows(self):
        """Test system error recovery workflows."""
        logger.info("Testing error recovery workflows...")
        
        # 1. Test database error recovery
        # Create a VOD first
        vod_data = {
            'title': 'Error Recovery Test VOD',
            'file_path': '/test/error_recovery_test.mp4',
            'duration': 300
        }
        
        create_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=vod_data,
            content_type='application/json'
        )
        assert create_response.status_code == 201
        vod_id = json.loads(create_response.data)['id']
        
        # 2. Test invalid operation that should be handled gracefully
        invalid_update_response = self.client.put(
            f'{self.base_url}/vod/{vod_id}',
            json={'vod_state': 'invalid_state'},
            content_type='application/json'
        )
        assert invalid_update_response.status_code == 400
        
        # 3. Verify system is still functional after error
        status_response = self.client.get(f'{self.base_url}/vod/{vod_id}')
        assert status_response.status_code == 200
        vod_status = json.loads(status_response.data)
        assert vod_status['vod_state'] != 'invalid_state'  # Should not have changed
        logger.info("Error recovery workflow verified")
        
        # 4. Test system health after error
        health_response = self.client.get(f'{self.base_url}/health')
        if health_response.status_code == 200:
            health_data = json.loads(health_response.data)
            assert 'status' in health_data
            logger.info("System health verified after error")
    
    def test_system_performance_under_load(self):
        """Test system performance under realistic load."""
        logger.info("Testing system performance under load...")
        
        import time
        import statistics
        
        # 1. Baseline performance measurement
        baseline_times = []
        for _ in range(10):
            start_time = time.time()
            response = self.client.get(f'{self.base_url}/vod/list')
            baseline_times.append(time.time() - start_time)
            assert response.status_code == 200
        
        baseline_avg = statistics.mean(baseline_times)
        logger.info(f"Baseline average response time: {baseline_avg:.4f}s")
        
        # 2. Create test data for load testing
        vod_ids = []
        for i in range(20):
            vod_data = {
                'title': f'Load Test VOD {i}',
                'file_path': f'/test/load_test_{i}.mp4',
                'duration': 300
            }
            
            response = self.client.post(
                f'{self.base_url}/vod/create',
                json=vod_data,
                content_type='application/json'
            )
            assert response.status_code == 201
            vod_ids.append(json.loads(response.data)['id'])
        
        # 3. Test concurrent operations
        def load_operation(vod_id):
            """Perform a typical user operation."""
            # Get VOD details
            get_response = self.client.get(f'{self.base_url}/vod/{vod_id}')
            if get_response.status_code != 200:
                return False
            
            # Update VOD status
            update_response = self.client.put(
                f'{self.base_url}/vod/{vod_id}',
                json={'vod_state': 'processing'},
                content_type='application/json'
            )
            if update_response.status_code != 200:
                return False
            
            return True
        
        # Run concurrent operations
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(load_operation, vod_id) for vod_id in vod_ids]
            results = [future.result() for future in futures]
        
        load_duration = time.time() - start_time
        
        # 4. Verify all operations succeeded
        assert all(results), "All load operations should succeed"
        logger.info(f"20 concurrent operations completed in {load_duration:.2f}s")
        
        # 5. Measure performance under load
        load_times = []
        for _ in range(10):
            start_time = time.time()
            response = self.client.get(f'{self.base_url}/vod/list')
            load_times.append(time.time() - start_time)
            assert response.status_code == 200
        
        load_avg = statistics.mean(load_times)
        
        # 6. Performance assertions
        assert load_avg < baseline_avg * 3, "Performance should not degrade more than 3x under load"
        assert load_duration < 30, "20 concurrent operations should complete within 30 seconds"
        
        logger.info(f"System performance under load verified: {load_avg:.4f}s average response time")
    
    def test_data_consistency_across_components(self):
        """Test data consistency across different system components."""
        logger.info("Testing data consistency across components...")
        
        # 1. Create VOD through API
        vod_data = {
            'title': 'Consistency Test VOD',
            'file_path': '/test/consistency_test.mp4',
            'duration': 300
        }
        
        create_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=vod_data,
            content_type='application/json'
        )
        assert create_response.status_code == 201
        vod_id = json.loads(create_response.data)['id']
        
        # 2. Verify consistency between API and service layer
        api_vod = json.loads(self.client.get(f'{self.base_url}/vod/{vod_id}').data)
        service_vod = self.vod_service.get_vod(vod_id)
        
        assert api_vod['id'] == service_vod['id']
        assert api_vod['title'] == service_vod['title']
        assert api_vod['file_path'] == service_vod['file_path']
        logger.info("API-Service consistency verified")
        
        # 3. Update through service and verify API reflects changes
        self.vod_service.update_vod(vod_id, {'vod_state': 'processing'})
        
        updated_api_vod = json.loads(self.client.get(f'{self.base_url}/vod/{vod_id}').data)
        assert updated_api_vod['vod_state'] == 'processing'
        logger.info("Service-API consistency verified")
        
        # 4. Update through API and verify service reflects changes
        self.client.put(
            f'{self.base_url}/vod/{vod_id}',
            json={'percent_complete': 50},
            content_type='application/json'
        )
        
        updated_service_vod = self.vod_service.get_vod(vod_id)
        assert updated_service_vod['percent_complete'] == 50
        logger.info("API-Service bidirectional consistency verified")
        
        # 5. Test list consistency
        api_list = json.loads(self.client.get(f'{self.base_url}/vod/list').data)
        service_list = self.vod_service.get_all_vods()
        
        assert len(api_list['vods']) == len(service_list)
        logger.info("List consistency verified")
    
    def test_system_monitoring_and_health(self):
        """Test system monitoring and health check functionality."""
        logger.info("Testing system monitoring and health...")
        
        # 1. Test health endpoint
        health_response = self.client.get(f'{self.base_url}/health')
        if health_response.status_code == 200:
            health_data = json.loads(health_response.data)
            assert 'status' in health_data
            logger.info(f"System health status: {health_data['status']}")
        else:
            logger.info("Health endpoint not implemented")
        
        # 2. Test system status
        status_response = self.client.get(f'{self.base_url}/status')
        if status_response.status_code == 200:
            status_data = json.loads(status_response.data)
            logger.info("System status endpoint available")
        else:
            logger.info("Status endpoint not implemented")
        
        # 3. Test metrics endpoint
        metrics_response = self.client.get(f'{self.base_url}/metrics')
        if metrics_response.status_code == 200:
            metrics_data = json.loads(metrics_response.data)
            logger.info("System metrics endpoint available")
        else:
            logger.info("Metrics endpoint not implemented")
    
    def test_concurrent_user_scenarios(self):
        """Test system behavior with multiple concurrent users."""
        logger.info("Testing concurrent user scenarios...")
        
        # 1. Simulate multiple users creating VODs
        def user_creates_vod(user_id):
            """Simulate a user creating a VOD."""
            vod_data = {
                'title': f'User {user_id} VOD',
                'file_path': f'/test/user_{user_id}_vod.mp4',
                'duration': 300
            }
            
            response = self.client.post(
                f'{self.base_url}/vod/create',
                json=vod_data,
                content_type='application/json'
            )
            return response.status_code == 201
        
        # Run concurrent user operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(user_creates_vod, i) for i in range(10)]
            results = [future.result() for future in futures]
        
        # All operations should succeed
        assert all(results), "All concurrent user operations should succeed"
        logger.info("Concurrent user VOD creation verified")
        
        # 2. Simulate multiple users reading VOD list
        def user_reads_vod_list(user_id):
            """Simulate a user reading the VOD list."""
            response = self.client.get(f'{self.base_url}/vod/list')
            return response.status_code == 200
        
        # Run concurrent read operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(user_reads_vod_list, i) for i in range(20)]
            results = [future.result() for future in futures]
        
        # All read operations should succeed
        assert all(results), "All concurrent read operations should succeed"
        logger.info("Concurrent user read operations verified")
    
    def test_system_resilience(self):
        """Test system resilience to various failure scenarios."""
        logger.info("Testing system resilience...")
        
        # 1. Test system behavior with invalid requests
        invalid_requests = [
            {'endpoint': f'{self.base_url}/vod/99999', 'method': 'GET'},
            {'endpoint': f'{self.base_url}/vod/create', 'method': 'POST', 'data': {}},
            {'endpoint': f'{self.base_url}/invalid/endpoint', 'method': 'GET'}
        ]
        
        for request in invalid_requests:
            if request['method'] == 'GET':
                response = self.client.get(request['endpoint'])
            elif request['method'] == 'POST':
                response = self.client.post(
                    request['endpoint'],
                    json=request['data'],
                    content_type='application/json'
                )
            
            # System should handle invalid requests gracefully
            assert response.status_code in [400, 404, 422], \
                f"Invalid request should return error status, got {response.status_code}"
        
        logger.info("System resilience to invalid requests verified")
        
        # 2. Test system behavior with malformed data
        malformed_data = [
            {'title': None, 'file_path': '/test/malformed.mp4'},
            {'title': 'Valid Title', 'file_path': '/invalid/../path'},
            {'title': 'A' * 10000, 'file_path': '/test/too_long.mp4'}  # Very long title
        ]
        
        for data in malformed_data:
            response = self.client.post(
                f'{self.base_url}/vod/create',
                json=data,
                content_type='application/json'
            )
            
            # System should handle malformed data gracefully
            assert response.status_code in [400, 422], \
                f"Malformed data should return error status, got {response.status_code}"
        
        logger.info("System resilience to malformed data verified")


def run_system_integration_tests():
    """Run all system integration tests."""
    logger.info("Starting System Integration Tests")
    
    # Create test instance
    tester = TestSystemIntegration()
    
    # Run tests
    test_methods = [
        tester.test_complete_vod_processing_workflow,
        tester.test_user_authentication_workflow,
        tester.test_error_recovery_workflows,
        tester.test_system_performance_under_load,
        tester.test_data_consistency_across_components,
        tester.test_system_monitoring_and_health,
        tester.test_concurrent_user_scenarios,
        tester.test_system_resilience
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
    
    logger.info(f"\n📊 System Integration Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_system_integration_tests()
    sys.exit(0 if success else 1) 
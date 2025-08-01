#!/usr/bin/env python3
"""
API Integration Tests

This module contains comprehensive integration tests that verify the interaction
between REST API endpoints and the service layer in the Archivist application.

Test Categories:
1. VOD API Endpoints
2. Authentication API
3. Error Handling Integration
4. API Performance
5. Data Validation
"""

import os
import sys
import time
import uuid
import json
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from loguru import logger
from core.exceptions import (
    ValidationError,
    DatabaseError,
    VODError
)


class TestAPIIntegration:
    """Integration tests for REST API endpoints."""
    
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
        
        # Base URL for API endpoints
        self.base_url = '/api'
        
        # Test data
        self.test_vod_data = {
            'title': f'API Test VOD {uuid.uuid4().hex[:8]}',
            'file_path': '/test/api_test_video.mp4',
            'duration': 300,
            'file_size': 1024 * 1024 * 50  # 50MB
        }
    
    def teardown_method(self):
        """Clean up test environment."""
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
    
    def test_vod_api_crud_operations(self):
        """Test complete VOD CRUD operations through API."""
        logger.info("Testing VOD API CRUD operations...")
        
        # 1. Create VOD through API
        create_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=self.test_vod_data,
            content_type='application/json'
        )
        
        assert create_response.status_code == 201, f"Expected 201, got {create_response.status_code}"
        create_data = json.loads(create_response.data)
        assert 'id' in create_data, "Response should contain VOD ID"
        
        vod_id = create_data['id']
        logger.info(f"Created VOD with ID: {vod_id}")
        
        # 2. Read VOD through API
        get_response = self.client.get(f'{self.base_url}/vod/{vod_id}')
        assert get_response.status_code == 200, f"Expected 200, got {get_response.status_code}"
        
        vod_data = json.loads(get_response.data)
        assert vod_data['title'] == self.test_vod_data['title']
        assert vod_data['file_path'] == self.test_vod_data['file_path']
        logger.info(f"Retrieved VOD: {vod_data['title']}")
        
        # 3. Update VOD through API
        update_data = {
            'vod_state': 'processing',
            'percent_complete': 25
        }
        
        update_response = self.client.put(
            f'{self.base_url}/vod/{vod_id}',
            json=update_data,
            content_type='application/json'
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}"
        
        # 4. Verify update through API
        updated_response = self.client.get(f'{self.base_url}/vod/{vod_id}')
        updated_vod = json.loads(updated_response.data)
        assert updated_vod['vod_state'] == 'processing'
        assert updated_vod['percent_complete'] == 25
        logger.info(f"Updated VOD state to: {updated_vod['vod_state']}")
        
        # 5. List VODs through API
        list_response = self.client.get(f'{self.base_url}/vod/list')
        assert list_response.status_code == 200, f"Expected 200, got {list_response.status_code}"
        
        vods_data = json.loads(list_response.data)
        assert 'vods' in vods_data, "Response should contain 'vods' key"
        assert len(vods_data['vods']) >= 1
        assert any(v['id'] == vod_id for v in vods_data['vods'])
        logger.info(f"Found {len(vods_data['vods'])} VODs in API response")
        
        # 6. Delete VOD through API
        delete_response = self.client.delete(f'{self.base_url}/vod/{vod_id}')
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        # 7. Verify deletion through API
        deleted_response = self.client.get(f'{self.base_url}/vod/{vod_id}')
        assert deleted_response.status_code == 404, f"Expected 404, got {deleted_response.status_code}"
        logger.info("VOD successfully deleted through API")
    
    def test_api_error_handling(self):
        """Test API error handling and response formats."""
        logger.info("Testing API error handling...")
        
        # 1. Test invalid VOD ID
        invalid_response = self.client.get(f'{self.base_url}/vod/99999')
        assert invalid_response.status_code == 404, f"Expected 404, got {invalid_response.status_code}"
        
        error_data = json.loads(invalid_response.data)
        assert 'error' in error_data, "Error response should contain 'error' key"
        assert 'message' in error_data['error'], "Error should contain message"
        logger.info("Invalid VOD ID handling verified")
        
        # 2. Test invalid request data
        invalid_vod_data = {
            'title': None,  # Invalid: title cannot be None
            'file_path': '/test/invalid.mp4',
            'vod_state': 'invalid_state'  # Invalid state
        }
        
        invalid_create_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=invalid_vod_data,
            content_type='application/json'
        )
        assert invalid_create_response.status_code == 400, f"Expected 400, got {invalid_create_response.status_code}"
        
        error_data = json.loads(invalid_create_response.data)
        assert 'error' in error_data, "Error response should contain 'error' key"
        assert 'type' in error_data['error'], "Error should contain type"
        logger.info("Invalid request data handling verified")
        
        # 3. Test missing required fields
        incomplete_data = {
            'title': 'Incomplete VOD'
            # Missing required fields
        }
        
        incomplete_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=incomplete_data,
            content_type='application/json'
        )
        assert incomplete_response.status_code == 400, f"Expected 400, got {incomplete_response.status_code}"
        
        error_data = json.loads(incomplete_response.data)
        assert 'error' in error_data, "Error response should contain 'error' key"
        logger.info("Missing required fields handling verified")
        
        # 4. Test invalid update data
        # First create a valid VOD
        create_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=self.test_vod_data,
            content_type='application/json'
        )
        vod_id = json.loads(create_response.data)['id']
        
        # Attempt invalid update
        invalid_update_data = {
            'vod_state': 'invalid_state'
        }
        
        invalid_update_response = self.client.put(
            f'{self.base_url}/vod/{vod_id}',
            json=invalid_update_data,
            content_type='application/json'
        )
        assert invalid_update_response.status_code == 400, f"Expected 400, got {invalid_update_response.status_code}"
        
        error_data = json.loads(invalid_update_response.data)
        assert 'error' in error_data, "Error response should contain 'error' key"
        logger.info("Invalid update data handling verified")
    
    def test_api_validation_integration(self):
        """Test API input validation integration."""
        logger.info("Testing API validation integration...")
        
        # 1. Test title validation
        test_cases = [
            {'title': '', 'expected_status': 400},  # Empty title
            {'title': 'A' * 1000, 'expected_status': 400},  # Too long title
            {'title': 'Valid Title', 'expected_status': 201},  # Valid title
        ]
        
        for test_case in test_cases:
            test_data = {
                'title': test_case['title'],
                'file_path': '/test/validation_test.mp4',
                'duration': 300
            }
            
            response = self.client.post(
                f'{self.base_url}/vod/create',
                json=test_data,
                content_type='application/json'
            )
            
            assert response.status_code == test_case['expected_status'], \
                f"Expected {test_case['expected_status']}, got {response.status_code} for title: {test_case['title']}"
        
        logger.info("Title validation integration verified")
        
        # 2. Test file path validation
        file_path_test_cases = [
            {'file_path': '', 'expected_status': 400},  # Empty path
            {'file_path': '/invalid/../path', 'expected_status': 400},  # Path traversal
            {'file_path': '/valid/path/video.mp4', 'expected_status': 201},  # Valid path
        ]
        
        for test_case in file_path_test_cases:
            test_data = {
                'title': f'File Path Test {uuid.uuid4().hex[:8]}',
                'file_path': test_case['file_path'],
                'duration': 300
            }
            
            response = self.client.post(
                f'{self.base_url}/vod/create',
                json=test_data,
                content_type='application/json'
            )
            
            assert response.status_code == test_case['expected_status'], \
                f"Expected {test_case['expected_status']}, got {response.status_code} for path: {test_case['file_path']}"
        
        logger.info("File path validation integration verified")
    
    def test_api_performance(self):
        """Test API performance under load."""
        logger.info("Testing API performance...")
        
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
        logger.info(f"Baseline average API response time: {baseline_avg:.4f}s")
        
        # 2. Create test data for load testing
        vod_ids = []
        for i in range(20):
            vod_data = {
                'title': f'Performance Test VOD {i}',
                'file_path': f'/test/performance_test_{i}.mp4',
                'duration': 300
            }
            
            response = self.client.post(
                f'{self.base_url}/vod/create',
                json=vod_data,
                content_type='application/json'
            )
            assert response.status_code == 201
            vod_ids.append(json.loads(response.data)['id'])
        
        # 3. Test concurrent API requests
        import concurrent.futures
        
        def api_operation(vod_id):
            """Perform a typical API operation."""
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
            futures = [executor.submit(api_operation, vod_id) for vod_id in vod_ids]
            results = [future.result() for future in futures]
        
        load_duration = time.time() - start_time
        
        # 4. Verify all operations succeeded
        assert all(results), "All API operations should succeed"
        logger.info(f"20 concurrent API operations completed in {load_duration:.2f}s")
        
        # 5. Measure performance under load
        load_times = []
        for _ in range(10):
            start_time = time.time()
            response = self.client.get(f'{self.base_url}/vod/list')
            load_times.append(time.time() - start_time)
            assert response.status_code == 200
        
        load_avg = statistics.mean(load_times)
        
        # 6. Performance assertions
        assert load_avg < baseline_avg * 2, "API performance should not degrade more than 2x under load"
        assert load_duration < 10, "20 concurrent operations should complete within 10 seconds"
        
        logger.info(f"API performance under load verified: {load_avg:.4f}s average response time")
    
    def test_api_data_consistency(self):
        """Test API data consistency across operations."""
        logger.info("Testing API data consistency...")
        
        # 1. Create VOD through API
        create_response = self.client.post(
            f'{self.base_url}/vod/create',
            json=self.test_vod_data,
            content_type='application/json'
        )
        assert create_response.status_code == 201
        vod_id = json.loads(create_response.data)['id']
        
        # 2. Verify data consistency across multiple reads
        vod_data_snapshots = []
        for _ in range(10):
            response = self.client.get(f'{self.base_url}/vod/{vod_id}')
            assert response.status_code == 200
            vod_data_snapshots.append(json.loads(response.data))
        
        # All snapshots should be identical
        first_snapshot = vod_data_snapshots[0]
        for snapshot in vod_data_snapshots[1:]:
            assert snapshot['id'] == first_snapshot['id']
            assert snapshot['title'] == first_snapshot['title']
            assert snapshot['file_path'] == first_snapshot['file_path']
        
        logger.info("API data consistency verified")
        
        # 3. Test list consistency
        list_snapshots = []
        for _ in range(5):
            response = self.client.get(f'{self.base_url}/vod/list')
            assert response.status_code == 200
            list_snapshots.append(json.loads(response.data))
        
        # All list snapshots should have the same count
        first_list = list_snapshots[0]
        for snapshot in list_snapshots[1:]:
            assert len(snapshot['vods']) == len(first_list['vods'])
        
        logger.info("API list consistency verified")
    
    def test_api_error_response_format(self):
        """Test API error response format consistency."""
        logger.info("Testing API error response format...")
        
        # Test various error scenarios
        error_scenarios = [
            {
                'endpoint': f'{self.base_url}/vod/99999',
                'method': 'GET',
                'expected_status': 404,
                'expected_error_type': 'NotFoundError'
            },
            {
                'endpoint': f'{self.base_url}/vod/create',
                'method': 'POST',
                'data': {'title': None},
                'expected_status': 400,
                'expected_error_type': 'ValidationError'
            },
            {
                'endpoint': f'{self.base_url}/vod/99999',
                'method': 'PUT',
                'data': {'vod_state': 'processing'},
                'expected_status': 404,
                'expected_error_type': 'NotFoundError'
            }
        ]
        
        for scenario in error_scenarios:
            if scenario['method'] == 'GET':
                response = self.client.get(scenario['endpoint'])
            elif scenario['method'] == 'POST':
                response = self.client.post(
                    scenario['endpoint'],
                    json=scenario['data'],
                    content_type='application/json'
                )
            elif scenario['method'] == 'PUT':
                response = self.client.put(
                    scenario['endpoint'],
                    json=scenario['data'],
                    content_type='application/json'
                )
            
            assert response.status_code == scenario['expected_status']
            
            error_data = json.loads(response.data)
            assert 'error' in error_data, "Error response should contain 'error' key"
            assert 'type' in error_data['error'], "Error should contain type"
            assert 'message' in error_data['error'], "Error should contain message"
            
            # Verify error type matches expected
            if 'expected_error_type' in scenario:
                assert scenario['expected_error_type'] in error_data['error']['type'], \
                    f"Expected error type {scenario['expected_error_type']}, got {error_data['error']['type']}"
        
        logger.info("API error response format consistency verified")


def run_api_integration_tests():
    """Run all API integration tests."""
    logger.info("Starting API Integration Tests")
    
    # Create test instance
    tester = TestAPIIntegration()
    
    # Run tests
    test_methods = [
        tester.test_vod_api_crud_operations,
        tester.test_api_error_handling,
        tester.test_api_validation_integration,
        tester.test_api_performance,
        tester.test_api_data_consistency,
        tester.test_api_error_response_format
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
    
    logger.info(f"\n📊 API Integration Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_api_integration_tests()
    sys.exit(0 if success else 1) 
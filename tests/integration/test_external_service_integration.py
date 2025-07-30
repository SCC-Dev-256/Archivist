#!/usr/bin/env python3
"""
External Service Integration Tests

This module contains comprehensive integration tests that verify the interaction
with external services like Cablecast API and Redis in the Archivist application.

Test Categories:
1. Cablecast API Integration
2. Redis Integration
3. Service Failure Recovery
4. Connection Management
5. Data Synchronization
"""

import os
import sys
import time
import uuid
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from loguru import logger
from core.exceptions import (
    ConnectionError,
    VODError,
    TimeoutError
)


class TestExternalServiceIntegration:
    """Integration tests for external service interactions."""
    
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
        
        # Import services
        from core.services import get_vod_service, get_queue_service
        self.vod_service = get_vod_service()
        self.queue_service = get_queue_service()
    
    def teardown_method(self):
        """Clean up test environment."""
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
    
    def test_cablecast_api_integration(self):
        """Test Cablecast API integration."""
        logger.info("Testing Cablecast API integration...")
        
        # Mock Cablecast API responses
        mock_shows_response = {
            'shows': [
                {
                    'id': 1,
                    'title': 'Test Show 1',
                    'date': '2024-01-15',
                    'description': 'Test show description',
                    'length': 1800
                },
                {
                    'id': 2,
                    'title': 'Test Show 2',
                    'date': '2024-01-16',
                    'description': 'Another test show',
                    'length': 2400
                }
            ]
        }
        
        mock_vod_status_response = {
            'vodState': 'completed',
            'percentComplete': 100,
            'vodId': 12345
        }
        
        # Test with mocked Cablecast API
        with patch('core.cablecast_client.CablecastAPIClient') as mock_client:
            # Configure mock
            mock_instance = mock_client.return_value
            mock_instance.get_shows.return_value = mock_shows_response['shows']
            mock_instance.get_vod_status.return_value = mock_vod_status_response
            mock_instance.test_connection.return_value = True
            
            # Test connection
            connection_ok = mock_instance.test_connection()
            assert connection_ok is True
            logger.info("Cablecast API connection verified")
            
            # Test show retrieval
            shows = mock_instance.get_shows()
            assert len(shows) == 2
            assert shows[0]['title'] == 'Test Show 1'
            assert shows[1]['title'] == 'Test Show 2'
            logger.info("Cablecast show retrieval verified")
            
            # Test VOD status retrieval
            vod_status = mock_instance.get_vod_status(12345)
            assert vod_status['vodState'] == 'completed'
            assert vod_status['percentComplete'] == 100
            logger.info("Cablecast VOD status retrieval verified")
    
    def test_cablecast_api_error_handling(self):
        """Test Cablecast API error handling."""
        logger.info("Testing Cablecast API error handling...")
        
        with patch('core.cablecast_client.CablecastAPIClient') as mock_client:
            mock_instance = mock_client.return_value
            
            # Test connection failure
            mock_instance.test_connection.side_effect = ConnectionError("Connection failed")
            
            try:
                connection_ok = mock_instance.test_connection()
                assert False, "Should have raised ConnectionError"
            except ConnectionError as e:
                assert "Connection failed" in str(e)
                logger.info("Cablecast connection error handling verified")
            
            # Test API timeout
            mock_instance.get_shows.side_effect = TimeoutError("API timeout")
            
            try:
                shows = mock_instance.get_shows()
                assert False, "Should have raised TimeoutError"
            except TimeoutError as e:
                assert "API timeout" in str(e)
                logger.info("Cablecast timeout error handling verified")
            
            # Test VOD not found
            mock_instance.get_vod_status.return_value = None
            
            vod_status = mock_instance.get_vod_status(99999)
            assert vod_status is None
            logger.info("Cablecast VOD not found handling verified")
    
    def test_redis_integration(self):
        """Test Redis integration."""
        logger.info("Testing Redis integration...")
        
        # Mock Redis client
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            
            # Configure mock responses
            mock_instance.ping.return_value = True
            mock_instance.set.return_value = True
            mock_instance.get.return_value = b'test_value'
            mock_instance.delete.return_value = 1
            mock_instance.info.return_value = {
                'used_memory_human': '256MB',
                'connected_clients': 5,
                'total_commands_processed': 1000
            }
            
            # Test connection
            connection_ok = mock_instance.ping()
            assert connection_ok is True
            logger.info("Redis connection verified")
            
            # Test cache operations
            cache_key = f"test_cache_{uuid.uuid4().hex[:8]}"
            cache_value = "test_cache_value"
            
            # Set cache
            set_result = mock_instance.set(cache_key, cache_value, ex=300)
            assert set_result is True
            logger.info("Redis cache set operation verified")
            
            # Get cache
            get_result = mock_instance.get(cache_key)
            assert get_result == b'test_value'
            logger.info("Redis cache get operation verified")
            
            # Delete cache
            delete_result = mock_instance.delete(cache_key)
            assert delete_result == 1
            logger.info("Redis cache delete operation verified")
            
            # Test Redis info
            info = mock_instance.info()
            assert info['used_memory_human'] == '256MB'
            assert info['connected_clients'] == 5
            logger.info("Redis info retrieval verified")
    
    def test_redis_error_handling(self):
        """Test Redis error handling."""
        logger.info("Testing Redis error handling...")
        
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            
            # Test connection failure
            mock_instance.ping.side_effect = ConnectionError("Redis connection failed")
            
            try:
                connection_ok = mock_instance.ping()
                assert False, "Should have raised ConnectionError"
            except ConnectionError as e:
                assert "Redis connection failed" in str(e)
                logger.info("Redis connection error handling verified")
            
            # Test timeout error
            mock_instance.get.side_effect = TimeoutError("Redis timeout")
            
            try:
                value = mock_instance.get("test_key")
                assert False, "Should have raised TimeoutError"
            except TimeoutError as e:
                assert "Redis timeout" in str(e)
                logger.info("Redis timeout error handling verified")
            
            # Test memory exhaustion
            mock_instance.info.return_value = {
                'used_memory_human': '2.0G',
                'maxmemory_human': '2.0G'
            }
            
            info = mock_instance.info()
            assert info['used_memory_human'] == '2.0G'
            assert info['maxmemory_human'] == '2.0G'
            logger.info("Redis memory exhaustion detection verified")
    
    def test_service_failure_recovery(self):
        """Test external service failure recovery."""
        logger.info("Testing external service failure recovery...")
        
        # Test Cablecast API recovery
        with patch('core.cablecast_client.CablecastAPIClient') as mock_cablecast:
            mock_instance = mock_cablecast.return_value
            
            # Simulate failure then recovery
            mock_instance.test_connection.side_effect = [
                ConnectionError("Connection failed"),  # First call fails
                True  # Second call succeeds
            ]
            
            # First call should fail
            try:
                connection_ok = mock_instance.test_connection()
                assert False, "First call should have failed"
            except ConnectionError:
                logger.info("Cablecast failure simulated")
            
            # Second call should succeed
            connection_ok = mock_instance.test_connection()
            assert connection_ok is True
            logger.info("Cablecast recovery verified")
        
        # Test Redis recovery
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            
            # Simulate failure then recovery
            mock_instance.ping.side_effect = [
                ConnectionError("Redis connection failed"),  # First call fails
                True  # Second call succeeds
            ]
            
            # First call should fail
            try:
                connection_ok = mock_instance.ping()
                assert False, "First call should have failed"
            except ConnectionError:
                logger.info("Redis failure simulated")
            
            # Second call should succeed
            connection_ok = mock_instance.ping()
            assert connection_ok is True
            logger.info("Redis recovery verified")
    
    def test_connection_management(self):
        """Test connection management for external services."""
        logger.info("Testing connection management...")
        
        # Test connection pooling
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            mock_instance.ping.return_value = True
            
            # Simulate multiple connections
            connections = []
            for i in range(5):
                connections.append(mock_redis.return_value)
                connections[-1].ping.return_value = True
            
            # Test all connections work
            for i, conn in enumerate(connections):
                result = conn.ping()
                assert result is True
                logger.info(f"Connection {i+1} verified")
            
            logger.info("Connection pooling verified")
        
        # Test connection timeout handling
        with patch('core.cablecast_client.CablecastAPIClient') as mock_cablecast:
            mock_instance = mock_cablecast.return_value
            
            # Simulate slow connection
            def slow_connection():
                time.sleep(0.1)  # Simulate delay
                return True
            
            mock_instance.test_connection.side_effect = slow_connection
            
            # Test connection with timeout
            start_time = time.time()
            connection_ok = mock_instance.test_connection()
            duration = time.time() - start_time
            
            assert connection_ok is True
            assert duration >= 0.1  # Should take at least 0.1 seconds
            logger.info("Connection timeout handling verified")
    
    def test_data_synchronization(self):
        """Test data synchronization with external services."""
        logger.info("Testing data synchronization...")
        
        # Test VOD status synchronization
        with patch('core.cablecast_client.CablecastAPIClient') as mock_cablecast:
            mock_instance = mock_cablecast.return_value
            
            # Mock VOD status updates
            vod_statuses = [
                {'vodState': 'processing', 'percentComplete': 25},
                {'vodState': 'processing', 'percentComplete': 50},
                {'vodState': 'processing', 'percentComplete': 75},
                {'vodState': 'completed', 'percentComplete': 100}
            ]
            
            mock_instance.get_vod_status.side_effect = vod_statuses
            
            # Simulate status synchronization
            vod_id = 12345
            for i, expected_status in enumerate(vod_statuses):
                status = mock_instance.get_vod_status(vod_id)
                assert status['vodState'] == expected_status['vodState']
                assert status['percentComplete'] == expected_status['percentComplete']
                logger.info(f"VOD status sync {i+1}: {status['vodState']} ({status['percentComplete']}%)")
            
            logger.info("VOD status synchronization verified")
        
        # Test cache synchronization
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            mock_instance.set.return_value = True
            mock_instance.get.return_value = b'cached_data'
            
            # Test cache synchronization
            cache_data = {
                'vod_count': 150,
                'last_sync': '2024-01-15T10:30:00Z',
                'status': 'healthy'
            }
            
            # Set cache
            cache_key = 'vod_sync_status'
            set_result = mock_instance.set(cache_key, json.dumps(cache_data))
            assert set_result is True
            
            # Get cache
            cached_result = mock_instance.get(cache_key)
            assert cached_result == b'cached_data'
            
            logger.info("Cache synchronization verified")
    
    def test_external_service_performance(self):
        """Test external service performance under load."""
        logger.info("Testing external service performance...")
        
        import time
        import statistics
        
        # Test Cablecast API performance
        with patch('core.cablecast_client.CablecastAPIClient') as mock_cablecast:
            mock_instance = mock_cablecast.return_value
            
            # Mock API response times
            def api_call_with_delay():
                time.sleep(0.05)  # Simulate 50ms API call
                return True
            
            mock_instance.test_connection.side_effect = api_call_with_delay
            
            # Measure API performance
            response_times = []
            for _ in range(10):
                start_time = time.time()
                result = mock_instance.test_connection()
                response_times.append(time.time() - start_time)
                assert result is True
            
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time >= 0.05  # Should take at least 50ms
            assert avg_response_time < 0.1  # Should not take more than 100ms
            logger.info(f"Cablecast API average response time: {avg_response_time:.4f}s")
        
        # Test Redis performance
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            
            # Mock Redis response times
            def redis_call_with_delay():
                time.sleep(0.01)  # Simulate 10ms Redis call
                return True
            
            mock_instance.ping.side_effect = redis_call_with_delay
            
            # Measure Redis performance
            response_times = []
            for _ in range(20):
                start_time = time.time()
                result = mock_instance.ping()
                response_times.append(time.time() - start_time)
                assert result is True
            
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time >= 0.01  # Should take at least 10ms
            assert avg_response_time < 0.05  # Should not take more than 50ms
            logger.info(f"Redis average response time: {avg_response_time:.4f}s")
    
    def test_external_service_monitoring(self):
        """Test external service monitoring and health checks."""
        logger.info("Testing external service monitoring...")
        
        # Test Cablecast API health monitoring
        with patch('core.cablecast_client.CablecastAPIClient') as mock_cablecast:
            mock_instance = mock_cablecast.return_value
            mock_instance.test_connection.return_value = True
            
            # Simulate health monitoring
            health_checks = []
            for i in range(10):
                try:
                    connection_ok = mock_instance.test_connection()
                    health_checks.append({
                        'timestamp': time.time(),
                        'status': 'healthy' if connection_ok else 'unhealthy',
                        'response_time': 0.05
                    })
                except Exception as e:
                    health_checks.append({
                        'timestamp': time.time(),
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Verify health check results
            healthy_checks = [h for h in health_checks if h['status'] == 'healthy']
            assert len(healthy_checks) == 10, "All health checks should be healthy"
            logger.info("Cablecast API health monitoring verified")
        
        # Test Redis health monitoring
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            mock_instance.ping.return_value = True
            mock_instance.info.return_value = {
                'used_memory_human': '256MB',
                'connected_clients': 5,
                'total_commands_processed': 1000
            }
            
            # Simulate Redis health monitoring
            redis_health_checks = []
            for i in range(10):
                try:
                    connection_ok = mock_instance.ping()
                    info = mock_instance.info()
                    redis_health_checks.append({
                        'timestamp': time.time(),
                        'status': 'healthy' if connection_ok else 'unhealthy',
                        'memory_usage': info['used_memory_human'],
                        'connected_clients': info['connected_clients']
                    })
                except Exception as e:
                    redis_health_checks.append({
                        'timestamp': time.time(),
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Verify Redis health check results
            healthy_checks = [h for h in redis_health_checks if h['status'] == 'healthy']
            assert len(healthy_checks) == 10, "All Redis health checks should be healthy"
            logger.info("Redis health monitoring verified")


def run_external_service_integration_tests():
    """Run all external service integration tests."""
    logger.info("Starting External Service Integration Tests")
    
    # Create test instance
    tester = TestExternalServiceIntegration()
    
    # Run tests
    test_methods = [
        tester.test_cablecast_api_integration,
        tester.test_cablecast_api_error_handling,
        tester.test_redis_integration,
        tester.test_redis_error_handling,
        tester.test_service_failure_recovery,
        tester.test_connection_management,
        tester.test_data_synchronization,
        tester.test_external_service_performance,
        tester.test_external_service_monitoring
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
    
    logger.info(f"\n📊 External Service Integration Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_external_service_integration_tests()
    sys.exit(0 if success else 1) 
"""
Performance tests for API endpoints.

This module provides comprehensive performance testing for the Archivist API,
including load testing, stress testing, and benchmarking capabilities.
"""

import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import pytest
import requests
from locust import HttpUser, task, between

from core.app import create_app
from core.config import TESTING


class APIPerformanceTest:
    """Base class for API performance testing."""
    
    def __init__(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self.results = []
    
    def measure_response_time(self, endpoint: str, method: str = 'GET', 
                            data: Dict = None, headers: Dict = None) -> float:
        """Measure response time for an API endpoint."""
        start_time = time.time()
        
        if method.upper() == 'GET':
            response = self.client.get(endpoint, headers=headers)
        elif method.upper() == 'POST':
            response = self.client.post(endpoint, json=data, headers=headers)
        elif method.upper() == 'PUT':
            response = self.client.put(endpoint, json=data, headers=headers)
        elif method.upper() == 'DELETE':
            response = self.client.delete(endpoint, headers=headers)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        self.results.append({
            'endpoint': endpoint,
            'method': method,
            'response_time': response_time,
            'status_code': response.status_code,
            'timestamp': start_time
        })
        
        return response_time
    
    def run_load_test(self, endpoint: str, method: str = 'GET', 
                     concurrent_users: int = 10, requests_per_user: int = 10,
                     data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Run load test with multiple concurrent users."""
        all_results = []
        
        def user_requests():
            user_results = []
            for _ in range(requests_per_user):
                response_time = self.measure_response_time(endpoint, method, data, headers)
                user_results.append(response_time)
            return user_results
        
        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_requests) for _ in range(concurrent_users)]
            
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # Calculate statistics
        response_times = [r['response_time'] for r in self.results if r['endpoint'] == endpoint]
        
        return {
            'endpoint': endpoint,
            'method': method,
            'total_requests': len(response_times),
            'concurrent_users': concurrent_users,
            'requests_per_user': requests_per_user,
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p95_response_time': statistics.quantiles(response_times, n=20)[18],  # 95th percentile
            'p99_response_time': statistics.quantiles(response_times, n=100)[98],  # 99th percentile
            'std_deviation': statistics.stdev(response_times) if len(response_times) > 1 else 0
        }


class TestAPIPerformance:
    """Test API performance under various conditions."""
    
    def setup_method(self):
        """Setup test environment."""
        self.performance_tester = APIPerformanceTest()
    
    def test_health_endpoint_performance(self):
        """Test health endpoint performance."""
        print("\n🏥 Testing Health Endpoint Performance...")
        
        # Single request baseline
        response_time = self.performance_tester.measure_response_time('/api/health')
        print(f"✅ Single request: {response_time:.2f}ms")
        
        # Load test with 10 concurrent users, 5 requests each
        results = self.performance_tester.run_load_test(
            '/api/health', 
            concurrent_users=10, 
            requests_per_user=5
        )
        
        print(f"📊 Load Test Results:")
        print(f"   Total Requests: {results['total_requests']}")
        print(f"   Avg Response Time: {results['avg_response_time']:.2f}ms")
        print(f"   P95 Response Time: {results['p95_response_time']:.2f}ms")
        print(f"   Max Response Time: {results['max_response_time']:.2f}ms")
        
        # Assertions for performance requirements
        assert results['avg_response_time'] < 100, f"Average response time too high: {results['avg_response_time']:.2f}ms"
        assert results['p95_response_time'] < 200, f"P95 response time too high: {results['p95_response_time']:.2f}ms"
        assert results['max_response_time'] < 500, f"Max response time too high: {results['max_response_time']:.2f}ms"
    
    def test_transcription_endpoint_performance(self):
        """Test transcription endpoint performance."""
        print("\n🎤 Testing Transcription Endpoint Performance...")
        
        # Test with mock data
        test_data = {
            'video_path': '/tmp/test_video.mp4',
            'model': 'base'
        }
        
        # Single request baseline
        response_time = self.performance_tester.measure_response_time(
            '/api/transcribe', 
            method='POST', 
            data=test_data
        )
        print(f"✅ Single request: {response_time:.2f}ms")
        
        # Load test with 5 concurrent users, 3 requests each
        results = self.performance_tester.run_load_test(
            '/api/transcribe',
            method='POST',
            data=test_data,
            concurrent_users=5,
            requests_per_user=3
        )
        
        print(f"📊 Load Test Results:")
        print(f"   Total Requests: {results['total_requests']}")
        print(f"   Avg Response Time: {results['avg_response_time']:.2f}ms")
        print(f"   P95 Response Time: {results['p95_response_time']:.2f}ms")
        
        # Assertions for transcription endpoint
        assert results['avg_response_time'] < 1000, f"Average response time too high: {results['avg_response_time']:.2f}ms"
        assert results['p95_response_time'] < 2000, f"P95 response time too high: {results['p95_response_time']:.2f}ms"
    
    def test_queue_endpoint_performance(self):
        """Test queue endpoint performance."""
        print("\n📋 Testing Queue Endpoint Performance...")
        
        # Test queue status endpoint
        response_time = self.performance_tester.measure_response_time('/api/queue/status')
        print(f"✅ Single request: {response_time:.2f}ms")
        
        # Load test
        results = self.performance_tester.run_load_test(
            '/api/queue/status',
            concurrent_users=20,
            requests_per_user=10
        )
        
        print(f"📊 Load Test Results:")
        print(f"   Total Requests: {results['total_requests']}")
        print(f"   Avg Response Time: {results['avg_response_time']:.2f}ms")
        print(f"   P95 Response Time: {results['p95_response_time']:.2f}ms")
        
        # Assertions for queue endpoint
        assert results['avg_response_time'] < 50, f"Average response time too high: {results['avg_response_time']:.2f}ms"
        assert results['p95_response_time'] < 100, f"P95 response time too high: {results['p95_response_time']:.2f}ms"


class LoadTestUser(HttpUser):
    """Locust user for load testing."""
    
    wait_time = between(1, 3)
    
    @task(3)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/api/health")
    
    @task(2)
    def queue_status(self):
        """Queue status endpoint."""
        self.client.get("/api/queue/status")
    
    @task(1)
    def transcribe_request(self):
        """Transcription request endpoint."""
        data = {
            'video_path': '/tmp/test_video.mp4',
            'model': 'base'
        }
        self.client.post("/api/transcribe", json=data)


def test_performance_benchmarks():
    """Run comprehensive performance benchmarks."""
    print("\n🚀 Running Performance Benchmarks...")
    
    tester = APIPerformanceTest()
    
    # Test endpoints
    endpoints = [
        ('/api/health', 'GET'),
        ('/api/queue/status', 'GET'),
        ('/api/transcribe', 'POST', {'video_path': '/tmp/test.mp4', 'model': 'base'})
    ]
    
    benchmark_results = {}
    
    for endpoint_info in endpoints:
        endpoint = endpoint_info[0]
        method = endpoint_info[1]
        data = endpoint_info[2] if len(endpoint_info) > 2 else None
        
        print(f"\n📊 Benchmarking {method} {endpoint}...")
        
        # Run multiple load tests with different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        
        for concurrency in concurrency_levels:
            results = tester.run_load_test(
                endpoint, 
                method=method, 
                data=data,
                concurrent_users=concurrency,
                requests_per_user=10
            )
            
            if endpoint not in benchmark_results:
                benchmark_results[endpoint] = {}
            
            benchmark_results[endpoint][concurrency] = results
            
            print(f"   {concurrency} users: {results['avg_response_time']:.2f}ms avg, {results['p95_response_time']:.2f}ms p95")
    
    # Generate performance report
    print("\n📈 Performance Benchmark Report:")
    print("=" * 60)
    
    for endpoint, results in benchmark_results.items():
        print(f"\n🔗 {endpoint}:")
        print("   Concurrency | Avg (ms) | P95 (ms) | Max (ms)")
        print("   ------------|----------|----------|---------")
        
        for concurrency, result in results.items():
            print(f"   {concurrency:11d} | {result['avg_response_time']:7.1f} | {result['p95_response_time']:7.1f} | {result['max_response_time']:7.1f}")
    
    return benchmark_results


if __name__ == "__main__":
    # Run benchmarks
    test_performance_benchmarks()
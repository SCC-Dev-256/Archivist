#!/usr/bin/env python3
"""
Load Testing Script for Archivist API

This script provides comprehensive load testing capabilities for the Archivist API,
including stress testing, performance benchmarking, and automated reporting.

Usage:
    python scripts/load_testing/run_load_tests.py [options]

Options:
    --endpoint ENDPOINT    Specific endpoint to test (default: all)
    --users USERS          Number of concurrent users (default: 10)
    --duration DURATION    Test duration in seconds (default: 60)
    --report               Generate detailed report
    --continuous           Run continuous monitoring
"""

import argparse
import json
import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Any
import requests
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.app import create_app
from core.config import TESTING


class LoadTester:
    """Comprehensive load testing for Archivist API."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
        
        # Test endpoints configuration
        self.endpoints = {
            'health': {
                'url': '/api/health',
                'method': 'GET',
                'data': None,
                'expected_status': 200,
                'weight': 3
            },
            'queue_status': {
                'url': '/api/queue/status',
                'method': 'GET',
                'data': None,
                'expected_status': 200,
                'weight': 2
            },
            'transcribe': {
                'url': '/api/transcribe',
                'method': 'POST',
                'data': {
                    'video_path': '/tmp/test_video.mp4',
                    'model': 'base'
                },
                'expected_status': 202,
                'weight': 1
            },
            'jobs': {
                'url': '/api/jobs',
                'method': 'GET',
                'data': None,
                'expected_status': 200,
                'weight': 2
            }
        }
    
    def make_request(self, endpoint_name: str) -> Dict[str, Any]:
        """Make a single request to an endpoint."""
        endpoint = self.endpoints[endpoint_name]
        url = f"{self.base_url}{endpoint['url']}"
        
        start_time = time.time()
        
        try:
            if endpoint['method'] == 'GET':
                response = requests.get(url, timeout=30)
            elif endpoint['method'] == 'POST':
                response = requests.post(url, json=endpoint['data'], timeout=30)
            elif endpoint['method'] == 'PUT':
                response = requests.put(url, json=endpoint['data'], timeout=30)
            elif endpoint['method'] == 'DELETE':
                response = requests.delete(url, timeout=30)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            result = {
                'endpoint': endpoint_name,
                'url': endpoint['url'],
                'method': endpoint['method'],
                'response_time': response_time,
                'status_code': response.status_code,
                'success': response.status_code == endpoint['expected_status'],
                'timestamp': start_time,
                'error': None
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            result = {
                'endpoint': endpoint_name,
                'url': endpoint['url'],
                'method': endpoint['method'],
                'response_time': response_time,
                'status_code': None,
                'success': False,
                'timestamp': start_time,
                'error': str(e)
            }
        
        # Thread-safe result storage
        with self.lock:
            self.results.append(result)
        
        return result
    
    def user_worker(self, user_id: int, duration: int, requests_per_second: float = 1.0):
        """Worker function for a single user."""
        end_time = time.time() + duration
        request_interval = 1.0 / requests_per_second
        
        while time.time() < end_time:
            # Select endpoint based on weights
            endpoints = list(self.endpoints.keys())
            weights = [self.endpoints[ep]['weight'] for ep in endpoints]
            
            # Simple weighted random selection
            total_weight = sum(weights)
            rand_val = time.time() % total_weight
            cumulative_weight = 0
            
            selected_endpoint = endpoints[0]
            for endpoint, weight in zip(endpoints, weights):
                cumulative_weight += weight
                if rand_val <= cumulative_weight:
                    selected_endpoint = endpoint
                    break
            
            # Make request
            self.make_request(selected_endpoint)
            
            # Wait for next request
            time.sleep(request_interval)
    
    def run_load_test(self, num_users: int, duration: int, 
                     requests_per_second: float = 1.0) -> Dict[str, Any]:
        """Run a comprehensive load test."""
        print(f"🚀 Starting load test with {num_users} users for {duration} seconds...")
        print(f"   Target: {requests_per_second} requests/second per user")
        print(f"   Total target: {num_users * requests_per_second:.1f} requests/second")
        
        # Clear previous results
        self.results = []
        
        # Start time
        test_start = time.time()
        
        # Start user workers
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [
                executor.submit(self.user_worker, i, duration, requests_per_second)
                for i in range(num_users)
            ]
            
            # Wait for all workers to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"⚠️ Worker error: {e}")
        
        test_end = time.time()
        actual_duration = test_end - test_start
        
        # Calculate statistics
        stats = self.calculate_statistics()
        
        # Add test metadata
        stats.update({
            'test_duration': actual_duration,
            'target_duration': duration,
            'num_users': num_users,
            'requests_per_second_per_user': requests_per_second,
            'total_requests': len(self.results),
            'actual_requests_per_second': len(self.results) / actual_duration,
            'test_timestamp': datetime.now().isoformat()
        })
        
        return stats
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive statistics from test results."""
        if not self.results:
            return {}
        
        # Overall statistics
        response_times = [r['response_time'] for r in self.results]
        success_count = sum(1 for r in self.results if r['success'])
        error_count = len(self.results) - success_count
        
        overall_stats = {
            'total_requests': len(self.results),
            'successful_requests': success_count,
            'failed_requests': error_count,
            'success_rate': success_count / len(self.results) * 100,
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p50_response_time': statistics.quantiles(response_times, n=2)[0],
            'p90_response_time': statistics.quantiles(response_times, n=10)[8],
            'p95_response_time': statistics.quantiles(response_times, n=20)[18],
            'p99_response_time': statistics.quantiles(response_times, n=100)[98],
            'std_deviation': statistics.stdev(response_times) if len(response_times) > 1 else 0
        }
        
        # Per-endpoint statistics
        endpoint_stats = {}
        for endpoint_name in self.endpoints.keys():
            endpoint_results = [r for r in self.results if r['endpoint'] == endpoint_name]
            
            if endpoint_results:
                endpoint_response_times = [r['response_time'] for r in endpoint_results]
                endpoint_success_count = sum(1 for r in endpoint_results if r['success'])
                
                endpoint_stats[endpoint_name] = {
                    'total_requests': len(endpoint_results),
                    'successful_requests': endpoint_success_count,
                    'success_rate': endpoint_success_count / len(endpoint_results) * 100,
                    'avg_response_time': statistics.mean(endpoint_response_times),
                    'median_response_time': statistics.median(endpoint_response_times),
                    'min_response_time': min(endpoint_response_times),
                    'max_response_time': max(endpoint_response_times),
                    'p95_response_time': statistics.quantiles(endpoint_response_times, n=20)[18] if len(endpoint_response_times) > 20 else max(endpoint_response_times)
                }
        
        return {
            'overall': overall_stats,
            'endpoints': endpoint_stats
        }
    
    def generate_report(self, stats: Dict[str, Any], output_file: str = None) -> str:
        """Generate a detailed test report."""
        report = []
        report.append("=" * 80)
        report.append("📊 ARCHIVIST API LOAD TEST REPORT")
        report.append("=" * 80)
        report.append(f"Test Date: {stats.get('test_timestamp', 'Unknown')}")
        report.append(f"Duration: {stats.get('test_duration', 0):.1f} seconds")
        report.append(f"Users: {stats.get('num_users', 0)}")
        report.append(f"Total Requests: {stats.get('total_requests', 0)}")
        report.append(f"Requests/Second: {stats.get('actual_requests_per_second', 0):.1f}")
        report.append("")
        
        # Overall statistics
        overall = stats.get('overall', {})
        report.append("📈 OVERALL PERFORMANCE")
        report.append("-" * 40)
        report.append(f"Success Rate: {overall.get('success_rate', 0):.1f}%")
        report.append(f"Average Response Time: {overall.get('avg_response_time', 0):.1f}ms")
        report.append(f"Median Response Time: {overall.get('median_response_time', 0):.1f}ms")
        report.append(f"P95 Response Time: {overall.get('p95_response_time', 0):.1f}ms")
        report.append(f"P99 Response Time: {overall.get('p99_response_time', 0):.1f}ms")
        report.append(f"Min Response Time: {overall.get('min_response_time', 0):.1f}ms")
        report.append(f"Max Response Time: {overall.get('max_response_time', 0):.1f}ms")
        report.append("")
        
        # Per-endpoint statistics
        endpoints = stats.get('endpoints', {})
        if endpoints:
            report.append("🔗 PER-ENDPOINT PERFORMANCE")
            report.append("-" * 40)
            
            for endpoint_name, endpoint_stats in endpoints.items():
                report.append(f"\n{endpoint_name.upper()}:")
                report.append(f"  Requests: {endpoint_stats.get('total_requests', 0)}")
                report.append(f"  Success Rate: {endpoint_stats.get('success_rate', 0):.1f}%")
                report.append(f"  Avg Response Time: {endpoint_stats.get('avg_response_time', 0):.1f}ms")
                report.append(f"  P95 Response Time: {endpoint_stats.get('p95_response_time', 0):.1f}ms")
        
        report.append("")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"📄 Report saved to: {output_file}")
        
        return report_text
    
    def create_visualizations(self, stats: Dict[str, Any], output_dir: str = "load_test_results"):
        """Create performance visualizations."""
        try:
            import matplotlib.pyplot as plt
            import pandas as pd
            
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Convert results to DataFrame
            df = pd.DataFrame(self.results)
            
            # Response time distribution
            plt.figure(figsize=(12, 8))
            
            # Overall response time histogram
            plt.subplot(2, 2, 1)
            plt.hist(df['response_time'], bins=50, alpha=0.7, edgecolor='black')
            plt.title('Response Time Distribution')
            plt.xlabel('Response Time (ms)')
            plt.ylabel('Frequency')
            
            # Response time by endpoint
            plt.subplot(2, 2, 2)
            df.boxplot(column='response_time', by='endpoint', ax=plt.gca())
            plt.title('Response Time by Endpoint')
            plt.suptitle('')  # Remove default title
            
            # Success rate by endpoint
            plt.subplot(2, 2, 3)
            endpoints = stats.get('endpoints', {})
            endpoint_names = list(endpoints.keys())
            success_rates = [endpoints[ep]['success_rate'] for ep in endpoint_names]
            
            plt.bar(endpoint_names, success_rates)
            plt.title('Success Rate by Endpoint')
            plt.ylabel('Success Rate (%)')
            plt.xticks(rotation=45)
            
            # Requests per second over time
            plt.subplot(2, 2, 4)
            df['timestamp_rounded'] = pd.to_datetime(df['timestamp'], unit='s').dt.round('1S')
            requests_per_second = df.groupby('timestamp_rounded').size()
            
            plt.plot(requests_per_second.index, requests_per_second.values)
            plt.title('Requests per Second Over Time')
            plt.xlabel('Time')
            plt.ylabel('Requests/Second')
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/performance_analysis.png", dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"📊 Visualizations saved to: {output_dir}/performance_analysis.png")
            
        except ImportError:
            print("⚠️ matplotlib/pandas not available, skipping visualizations")
        except Exception as e:
            print(f"⚠️ Error creating visualizations: {e}")


def main():
    """Main function for running load tests."""
    parser = argparse.ArgumentParser(description='Load Testing for Archivist API')
    parser.add_argument('--endpoint', help='Specific endpoint to test')
    parser.add_argument('--users', type=int, default=10, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--rps', type=float, default=1.0, help='Requests per second per user')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL for API')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--visualize', action='store_true', help='Create performance visualizations')
    
    args = parser.parse_args()
    
    # Initialize load tester
    tester = LoadTester(args.url)
    
    if args.continuous:
        print("🔄 Running continuous monitoring...")
        while True:
            stats = tester.run_load_test(5, 30, 0.5)  # Light continuous load
            print(f"📊 Continuous test: {stats['overall']['success_rate']:.1f}% success, "
                  f"{stats['overall']['avg_response_time']:.1f}ms avg")
            time.sleep(60)  # Wait 1 minute between tests
    else:
        # Run single load test
        stats = tester.run_load_test(args.users, args.duration, args.rps)
        
        # Generate report
        if args.report or args.output:
            report = tester.generate_report(stats, args.output)
            print(report)
        
        # Create visualizations
        if args.visualize:
            tester.create_visualizations(stats)
        
        # Print summary
        overall = stats.get('overall', {})
        print(f"\n🎯 Test Summary:")
        print(f"   Success Rate: {overall.get('success_rate', 0):.1f}%")
        print(f"   Avg Response Time: {overall.get('avg_response_time', 0):.1f}ms")
        print(f"   P95 Response Time: {overall.get('p95_response_time', 0):.1f}ms")
        print(f"   Requests/Second: {stats.get('actual_requests_per_second', 0):.1f}")


if __name__ == "__main__":
    main()
"""
Performance monitoring middleware for Flask application.
Tracks response times, request rates, and other metrics.
"""

import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from flask import request, g, current_app
from loguru import logger
import redis

class PerformanceMiddleware:
    """Middleware for tracking API performance metrics."""
    
    def __init__(self, app=None, redis_client=None):
        self.app = app
        self.redis_client = redis_client
        self.request_times = deque(maxlen=1000)  # Store last 1000 request times
        self.request_counts = defaultdict(int)   # Count requests per endpoint
        self.error_counts = defaultdict(int)     # Count errors per endpoint
        self.active_requests = 0
        self.lock = threading.Lock()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with the Flask app."""
        self.app = app
        
        # Register before_request and after_request handlers
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_request(self.teardown_request)
        
        # Initialize Redis client if not provided
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis client not available for performance tracking: {e}")
                self.redis_client = None
    
    def before_request(self):
        """Called before each request."""
        g.start_time = time.time()
        g.request_id = f"{int(time.time() * 1000)}_{threading.get_ident()}"
        
        with self.lock:
            self.active_requests += 1
        
        # Track request count per endpoint
        endpoint = request.endpoint or 'unknown'
        with self.lock:
            self.request_counts[endpoint] += 1
    
    def after_request(self, response):
        """Called after each request."""
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            
            # Store response time
            with self.lock:
                self.request_times.append({
                    'endpoint': request.endpoint or 'unknown',
                    'method': request.method,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'timestamp': datetime.now()
                })
            
            # Track errors
            if response.status_code >= 400:
                endpoint = request.endpoint or 'unknown'
                with self.lock:
                    self.error_counts[endpoint] += 1
            
            # Add response time header for debugging
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
        
        return response
    
    def teardown_request(self, exception=None):
        """Called after request is complete."""
        with self.lock:
            if self.active_requests > 0:
                self.active_requests -= 1
    
    def get_performance_metrics(self):
        """Get current performance metrics."""
        with self.lock:
            # Calculate average response time
            if self.request_times:
                recent_times = [rt['response_time'] for rt in list(self.request_times)[-100:]]  # Last 100 requests
                avg_response_time = sum(recent_times) / len(recent_times)
                max_response_time = max(recent_times)
                min_response_time = min(recent_times)
            else:
                avg_response_time = max_response_time = min_response_time = 0
            
            # Calculate requests per minute
            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)
            recent_requests = [rt for rt in self.request_times if rt['timestamp'] > one_minute_ago]
            requests_per_minute = len(recent_requests)
            
            # Calculate error rate
            total_requests = sum(self.request_counts.values())
            total_errors = sum(self.error_counts.values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'avg_response_time': round(avg_response_time, 3),
                'max_response_time': round(max_response_time, 3),
                'min_response_time': round(min_response_time, 3),
                'requests_per_minute': requests_per_minute,
                'active_requests': self.active_requests,
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': round(error_rate, 2),
                'endpoint_stats': dict(self.request_counts),
                'error_stats': dict(self.error_counts)
            }
    
    def get_endpoint_metrics(self, endpoint=None):
        """Get metrics for specific endpoint or all endpoints."""
        with self.lock:
            if endpoint:
                return {
                    'requests': self.request_counts.get(endpoint, 0),
                    'errors': self.error_counts.get(endpoint, 0)
                }
            else:
                return {
                    'endpoints': dict(self.request_counts),
                    'errors': dict(self.error_counts)
                }

# Global instance
performance_middleware = PerformanceMiddleware() 
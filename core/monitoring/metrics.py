"""
VOD Processing Metrics and Monitoring System

This module provides comprehensive metrics tracking for the VOD processing system,
including retry success rates, failure patterns, performance metrics, and health checks.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import json
import os

from loguru import logger
import redis

class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class MetricPoint:
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class Metric:
    name: str
    type: MetricType
    description: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    labels: Dict[str, str] = field(default_factory=dict)

class CircuitBreaker:
    """Circuit breaker pattern for API calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }

class VODMetricsCollector:
    """Comprehensive metrics collector for VOD processing."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.metrics: Dict[str, Metric] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.redis_client = redis_client
        self.lock = threading.Lock()
        
        # Initialize core metrics
        self._init_core_metrics()
        
    def _init_core_metrics(self):
        """Initialize core VOD processing metrics."""
        core_metrics = [
            ("vod_processing_total", MetricType.COUNTER, "Total VOD processing attempts"),
            ("vod_processing_success", MetricType.COUNTER, "Successful VOD processing"),
            ("vod_processing_failed", MetricType.COUNTER, "Failed VOD processing"),
            ("vod_download_total", MetricType.COUNTER, "Total VOD download attempts"),
            ("vod_download_success", MetricType.COUNTER, "Successful VOD downloads"),
            ("vod_download_failed", MetricType.COUNTER, "Failed VOD downloads"),
            ("vod_download_retries", MetricType.COUNTER, "VOD download retry attempts"),
            ("caption_generation_total", MetricType.COUNTER, "Total caption generation attempts"),
            ("caption_generation_success", MetricType.COUNTER, "Successful caption generation"),
            ("caption_generation_failed", MetricType.COUNTER, "Failed caption generation"),
            ("video_retranscode_total", MetricType.COUNTER, "Total video retranscoding attempts"),
            ("video_retranscode_success", MetricType.COUNTER, "Successful video retranscoding"),
            ("video_retranscode_failed", MetricType.COUNTER, "Failed video retranscoding"),
            ("api_calls_total", MetricType.COUNTER, "Total API calls"),
            ("api_calls_success", MetricType.COUNTER, "Successful API calls"),
            ("api_calls_failed", MetricType.COUNTER, "Failed API calls"),
            ("storage_checks_total", MetricType.COUNTER, "Total storage availability checks"),
            ("storage_checks_failed", MetricType.COUNTER, "Failed storage availability checks"),
            ("processing_duration", MetricType.HISTOGRAM, "VOD processing duration in seconds"),
            ("download_duration", MetricType.HISTOGRAM, "VOD download duration in seconds"),
            ("caption_duration", MetricType.HISTOGRAM, "Caption generation duration in seconds"),
            ("retranscode_duration", MetricType.HISTOGRAM, "Video retranscoding duration in seconds"),
            ("active_tasks", MetricType.GAUGE, "Currently active VOD processing tasks"),
            ("queue_size", MetricType.GAUGE, "Current task queue size"),
            ("error_rate", MetricType.GAUGE, "Current error rate percentage"),
            ("retry_success_rate", MetricType.GAUGE, "Retry success rate percentage"),
        ]
        
        for name, metric_type, description in core_metrics:
            self.metrics[name] = Metric(name, metric_type, description)
    
    def increment(self, metric_name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = Metric(metric_name, MetricType.COUNTER, "")
            
            metric = self.metrics[metric_name]
            point = MetricPoint(datetime.now(), value, labels or {})
            metric.points.append(point)
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    key = f"metrics:{metric_name}"
                    self.redis_client.incrby(key, int(value))
                    self.redis_client.expire(key, 3600)  # 1 hour TTL
                except Exception as e:
                    logger.warning(f"Failed to store metric in Redis: {e}")
    
    def gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = Metric(metric_name, MetricType.GAUGE, "")
            
            metric = self.metrics[metric_name]
            point = MetricPoint(datetime.now(), value, labels or {})
            metric.points.append(point)
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    key = f"metrics:{metric_name}"
                    self.redis_client.set(key, value)
                    self.redis_client.expire(key, 3600)  # 1 hour TTL
                except Exception as e:
                    logger.warning(f"Failed to store metric in Redis: {e}")
    
    def histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric."""
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = Metric(metric_name, MetricType.HISTOGRAM, "")
            
            metric = self.metrics[metric_name]
            point = MetricPoint(datetime.now(), value, labels or {})
            metric.points.append(point)
    
    def timer(self, metric_name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a timer metric."""
        self.histogram(metric_name, duration, labels)
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for the given name."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker()
        return self.circuit_breakers[name]
    
    def get_metrics_summary(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get metrics summary for the specified time window."""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)
        
        summary = {}
        with self.lock:
            for name, metric in self.metrics.items():
                recent_points = [p for p in metric.points if p.timestamp >= cutoff_time]
                
                if not recent_points:
                    continue
                
                if metric.type == MetricType.COUNTER:
                    summary[name] = sum(p.value for p in recent_points)
                elif metric.type == MetricType.GAUGE:
                    summary[name] = recent_points[-1].value if recent_points else 0
                elif metric.type == MetricType.HISTOGRAM:
                    values = [p.value for p in recent_points]
                    summary[name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
                        "p99": sorted(values)[int(len(values) * 0.99)] if values else 0
                    }
        
        # Calculate derived metrics
        if "vod_processing_total" in summary and summary["vod_processing_total"] > 0:
            summary["error_rate"] = (summary.get("vod_processing_failed", 0) / summary["vod_processing_total"]) * 100
        
        if "vod_download_retries" in summary and "vod_download_total" in summary:
            total_downloads = summary["vod_download_total"]
            if total_downloads > 0:
                summary["retry_success_rate"] = ((total_downloads - summary.get("vod_download_failed", 0)) / total_downloads) * 100
        
        return summary
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external monitoring systems."""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.get_metrics_summary(),
            "circuit_breakers": self.get_circuit_breaker_status(),
            "total_metrics": len(self.metrics),
            "total_circuit_breakers": len(self.circuit_breakers)
        }
    
    def collect_system_metrics(self):
        """Collect system-level metrics for monitoring."""
        try:
            import psutil
            
            # System resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Update system metrics
            self.gauge("system_cpu_percent", cpu_percent)
            self.gauge("system_memory_percent", memory.percent)
            self.gauge("system_memory_used_gb", memory.used / (1024**3))
            self.gauge("system_memory_total_gb", memory.total / (1024**3))
            self.gauge("system_disk_percent", disk.percent)
            self.gauge("system_disk_used_gb", disk.used / (1024**3))
            self.gauge("system_disk_total_gb", disk.total / (1024**3))
            
            # Network metrics
            net_io = psutil.net_io_counters()
            self.gauge("system_network_bytes_sent", net_io.bytes_sent)
            self.gauge("system_network_bytes_recv", net_io.bytes_recv)
            
            # Process metrics
            process = psutil.Process()
            self.gauge("system_process_memory_mb", process.memory_info().rss / (1024**2))
            self.gauge("system_process_cpu_percent", process.cpu_percent())
            
            logger.debug(f"System metrics collected - CPU: {cpu_percent}%, Memory: {memory.percent}%")
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

# Global metrics collector instance
_metrics_collector: Optional[VODMetricsCollector] = None

def get_metrics_collector() -> VODMetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()  # Test connection
            _metrics_collector = VODMetricsCollector(redis_client)
            logger.info("Metrics collector initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis not available for metrics, using in-memory only: {e}")
            _metrics_collector = VODMetricsCollector()
    return _metrics_collector

def track_vod_processing(func):
    """Decorator to track VOD processing metrics."""
    def wrapper(*args, **kwargs):
        collector = get_metrics_collector()
        start_time = time.time()
        
        try:
            collector.increment("vod_processing_total")
            collector.increment("active_tasks")
            
            result = func(*args, **kwargs)
            
            collector.increment("vod_processing_success")
            duration = time.time() - start_time
            collector.timer("processing_duration", duration)
            
            return result
        except Exception as e:
            collector.increment("vod_processing_failed")
            duration = time.time() - start_time
            collector.timer("processing_duration", duration)
            raise
        finally:
            collector.increment("active_tasks", -1)
    
    return wrapper

def track_api_call(func):
    """Decorator to track API call metrics."""
    def wrapper(*args, **kwargs):
        collector = get_metrics_collector()
        start_time = time.time()
        
        try:
            collector.increment("api_calls_total")
            
            result = func(*args, **kwargs)
            
            collector.increment("api_calls_success")
            return result
        except Exception as e:
            collector.increment("api_calls_failed")
            raise
    
    return wrapper 
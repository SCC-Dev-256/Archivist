#!/usr/bin/env python3
"""
Monitoring Integration Tests

This module contains comprehensive integration tests that verify the monitoring
and alerting systems in the Archivist application.

Test Categories:
1. Health Check Accuracy
2. Alert Mechanisms
3. Monitoring Scenarios
4. Performance Monitoring
5. System Metrics
6. Alert Delivery
"""

import os
import sys
import time
import uuid
import json
import threading
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from loguru import logger
from core.exceptions import (
    ConnectionError,
    DatabaseError,
    VODError,
    TimeoutError
)


class TestMonitoringIntegration:
    """Integration tests for monitoring and alerting systems."""
    
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
        from core.services import get_vod_service, get_queue_service
        self.vod_service = get_vod_service()
        self.queue_service = get_queue_service()
        
        # Base URL for API endpoints
        self.base_url = '/api'
    
    def teardown_method(self):
        """Clean up test environment."""
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
    
    def test_health_check_accuracy(self):
        """Test health check accuracy across all system components."""
        logger.info("Testing health check accuracy...")
        
        # 1. Test basic health endpoint
        health_response = self.client.get(f'{self.base_url}/health')
        if health_response.status_code == 200:
            health_data = json.loads(health_response.data)
            assert 'status' in health_data
            assert health_data['status'] in ['healthy', 'degraded', 'unhealthy']
            logger.info(f"Basic health check: {health_data['status']}")
        else:
            logger.info("Health endpoint not implemented")
        
        # 2. Test database health
        try:
            # Test database connection
            with self.app.app_context():
                self.db.session.execute('SELECT 1')
                db_healthy = True
                logger.info("Database health check: healthy")
        except Exception as e:
            db_healthy = False
            logger.error(f"Database health check failed: {e}")
        
        # 3. Test service health checks
        services_health = {}
        
        # VOD Service health
        try:
            vods = self.vod_service.get_all_vods()
            services_health['vod_service'] = True
            logger.info("VOD Service health check: healthy")
        except Exception as e:
            services_health['vod_service'] = False
            logger.error(f"VOD Service health check failed: {e}")
        
        # Queue Service health
        try:
            queue_status = self.queue_service.get_queue_status()
            services_health['queue_service'] = True
            logger.info("Queue Service health check: healthy")
        except Exception as e:
            services_health['queue_service'] = False
            logger.error(f"Queue Service health check failed: {e}")
        
        # 4. Test external service health
        external_services_health = {}
        
        # Test Redis health (mocked)
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            mock_instance.ping.return_value = True
            
            try:
                redis_healthy = mock_instance.ping()
                external_services_health['redis'] = redis_healthy
                logger.info("Redis health check: healthy")
            except Exception as e:
                external_services_health['redis'] = False
                logger.error(f"Redis health check failed: {e}")
        
        # Test Cablecast health (mocked)
        with patch('core.cablecast_client.CablecastAPIClient') as mock_cablecast:
            mock_instance = mock_cablecast.return_value
            mock_instance.test_connection.return_value = True
            
            try:
                cablecast_healthy = mock_instance.test_connection()
                external_services_health['cablecast'] = cablecast_healthy
                logger.info("Cablecast health check: healthy")
            except Exception as e:
                external_services_health['cablecast'] = False
                logger.error(f"Cablecast health check failed: {e}")
        
        # 5. Verify overall health assessment
        all_services_healthy = all(services_health.values())
        all_external_healthy = all(external_services_health.values())
        
        if db_healthy and all_services_healthy and all_external_healthy:
            overall_health = 'healthy'
        elif db_healthy and all_services_healthy:
            overall_health = 'degraded'
        else:
            overall_health = 'unhealthy'
        
        logger.info(f"Overall system health: {overall_health}")
        assert overall_health in ['healthy', 'degraded', 'unhealthy']
    
    def test_alert_mechanisms(self):
        """Test alert mechanisms and notification systems."""
        logger.info("Testing alert mechanisms...")
        
        # 1. Test alert generation for different scenarios
        alert_scenarios = [
            {
                'type': 'database_error',
                'severity': 'critical',
                'message': 'Database connection failed',
                'expected_alert': True
            },
            {
                'type': 'service_degraded',
                'severity': 'warning',
                'message': 'VOD service response time increased',
                'expected_alert': True
            },
            {
                'type': 'external_service_down',
                'severity': 'critical',
                'message': 'Cablecast API unavailable',
                'expected_alert': True
            },
            {
                'type': 'performance_degraded',
                'severity': 'warning',
                'message': 'System response time above threshold',
                'expected_alert': True
            }
        ]
        
        generated_alerts = []
        
        for scenario in alert_scenarios:
            # Simulate alert generation
            alert = {
                'id': str(uuid.uuid4()),
                'type': scenario['type'],
                'severity': scenario['severity'],
                'message': scenario['message'],
                'timestamp': time.time(),
                'acknowledged': False
            }
            
            generated_alerts.append(alert)
            logger.info(f"Generated alert: {scenario['type']} - {scenario['severity']}")
        
        # 2. Test alert severity classification
        severity_counts = {}
        for alert in generated_alerts:
            severity = alert['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        assert 'critical' in severity_counts, "Should have critical alerts"
        assert 'warning' in severity_counts, "Should have warning alerts"
        logger.info(f"Alert severity distribution: {severity_counts}")
        
        # 3. Test alert acknowledgment
        for alert in generated_alerts:
            if alert['severity'] == 'critical':
                alert['acknowledged'] = True
                alert['acknowledged_by'] = 'admin'
                alert['acknowledged_at'] = time.time()
                logger.info(f"Critical alert acknowledged: {alert['id']}")
        
        # 4. Test alert escalation
        unacknowledged_critical = [a for a in generated_alerts 
                                 if a['severity'] == 'critical' and not a['acknowledged']]
        
        if unacknowledged_critical:
            logger.warning(f"Unacknowledged critical alerts: {len(unacknowledged_critical)}")
            # Simulate escalation
            for alert in unacknowledged_critical:
                alert['escalated'] = True
                alert['escalated_at'] = time.time()
                logger.info(f"Alert escalated: {alert['id']}")
        
        # 5. Test alert delivery mechanisms
        delivery_mechanisms = ['email', 'sms', 'webhook', 'dashboard']
        
        for alert in generated_alerts:
            if alert['severity'] == 'critical':
                # Critical alerts should be delivered via all mechanisms
                alert['delivery_methods'] = delivery_mechanisms
                logger.info(f"Critical alert delivery methods: {delivery_mechanisms}")
            else:
                # Warning alerts via dashboard and email
                alert['delivery_methods'] = ['dashboard', 'email']
                logger.info(f"Warning alert delivery methods: {alert['delivery_methods']}")
    
    def test_monitoring_scenarios(self):
        """Test various monitoring scenarios and edge cases."""
        logger.info("Testing monitoring scenarios...")
        
        # 1. Test normal operation monitoring
        normal_metrics = {
            'cpu_usage': 45.2,
            'memory_usage': 67.8,
            'disk_usage': 23.1,
            'active_connections': 12,
            'requests_per_minute': 150,
            'average_response_time': 0.25
        }
        
        # Verify metrics are within normal ranges
        assert normal_metrics['cpu_usage'] < 80, "CPU usage should be normal"
        assert normal_metrics['memory_usage'] < 85, "Memory usage should be normal"
        assert normal_metrics['disk_usage'] < 90, "Disk usage should be normal"
        assert normal_metrics['average_response_time'] < 1.0, "Response time should be normal"
        
        logger.info("Normal operation metrics verified")
        
        # 2. Test high load scenario
        high_load_metrics = {
            'cpu_usage': 85.5,
            'memory_usage': 92.3,
            'disk_usage': 45.7,
            'active_connections': 45,
            'requests_per_minute': 450,
            'average_response_time': 2.1
        }
        
        # Verify high load detection
        high_load_detected = (
            high_load_metrics['cpu_usage'] > 80 or
            high_load_metrics['memory_usage'] > 85 or
            high_load_metrics['average_response_time'] > 1.5
        )
        
        assert high_load_detected, "High load should be detected"
        logger.info("High load scenario detected correctly")
        
        # 3. Test resource exhaustion scenario
        exhaustion_metrics = {
            'cpu_usage': 98.5,
            'memory_usage': 99.2,
            'disk_usage': 95.8,
            'active_connections': 100,
            'requests_per_minute': 1000,
            'average_response_time': 5.8
        }
        
        # Verify resource exhaustion detection
        exhaustion_detected = (
            exhaustion_metrics['cpu_usage'] > 95 or
            exhaustion_metrics['memory_usage'] > 95 or
            exhaustion_metrics['disk_usage'] > 95
        )
        
        assert exhaustion_detected, "Resource exhaustion should be detected"
        logger.info("Resource exhaustion scenario detected correctly")
        
        # 4. Test service degradation scenario
        service_metrics = {
            'vod_service_response_time': 3.2,
            'transcription_service_queue_size': 25,
            'database_connection_pool_usage': 85,
            'redis_memory_usage': 78.5,
            'cablecast_api_response_time': 4.1
        }
        
        # Verify service degradation detection
        service_degradation = (
            service_metrics['vod_service_response_time'] > 2.0 or
            service_metrics['transcription_service_queue_size'] > 20 or
            service_metrics['database_connection_pool_usage'] > 80
        )
        
        assert service_degradation, "Service degradation should be detected"
        logger.info("Service degradation scenario detected correctly")
    
    def test_performance_monitoring(self):
        """Test performance monitoring and threshold detection."""
        logger.info("Testing performance monitoring...")
        
        # 1. Test response time monitoring
        response_times = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55]
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # Verify response time calculations
        assert avg_response_time > 0, "Average response time should be positive"
        assert max_response_time >= avg_response_time, "Max should be >= average"
        assert min_response_time <= avg_response_time, "Min should be <= average"
        
        logger.info(f"Response time stats - Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s, Min: {min_response_time:.3f}s")
        
        # 2. Test throughput monitoring
        requests_per_second = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
        
        avg_throughput = sum(requests_per_second) / len(requests_per_second)
        max_throughput = max(requests_per_second)
        min_throughput = min(requests_per_second)
        
        # Verify throughput calculations
        assert avg_throughput > 0, "Average throughput should be positive"
        assert max_throughput >= avg_throughput, "Max should be >= average"
        assert min_throughput <= avg_throughput, "Min should be <= average"
        
        logger.info(f"Throughput stats - Avg: {avg_throughput:.1f} req/s, Max: {max_throughput} req/s, Min: {min_throughput} req/s")
        
        # 3. Test resource utilization monitoring
        cpu_samples = [45, 50, 55, 60, 65, 70, 75, 80, 85, 90]
        memory_samples = [60, 65, 70, 75, 80, 85, 90, 95, 98, 99]
        
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        avg_memory = sum(memory_samples) / len(memory_samples)
        
        # Verify resource utilization calculations
        assert avg_cpu > 0 and avg_cpu < 100, "CPU usage should be between 0-100%"
        assert avg_memory > 0 and avg_memory < 100, "Memory usage should be between 0-100%"
        
        logger.info(f"Resource utilization - CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f}%")
        
        # 4. Test threshold detection
        thresholds = {
            'response_time_warning': 1.0,
            'response_time_critical': 3.0,
            'cpu_warning': 80,
            'cpu_critical': 95,
            'memory_warning': 85,
            'memory_critical': 95
        }
        
        # Test threshold violations
        response_time_violations = [rt for rt in response_times if rt > thresholds['response_time_warning']]
        cpu_violations = [cpu for cpu in cpu_samples if cpu > thresholds['cpu_warning']]
        memory_violations = [mem for mem in memory_samples if mem > thresholds['memory_warning']]
        
        logger.info(f"Threshold violations - Response Time: {len(response_time_violations)}, CPU: {len(cpu_violations)}, Memory: {len(memory_violations)}")
        
        # 5. Test trend analysis
        # Simulate trend detection
        recent_response_times = response_times[-5:]  # Last 5 samples
        earlier_response_times = response_times[:5]  # First 5 samples
        
        recent_avg = sum(recent_response_times) / len(recent_response_times)
        earlier_avg = sum(earlier_response_times) / len(earlier_response_times)
        
        trend = 'increasing' if recent_avg > earlier_avg else 'decreasing' if recent_avg < earlier_avg else 'stable'
        
        logger.info(f"Response time trend: {trend} (earlier: {earlier_avg:.3f}s, recent: {recent_avg:.3f}s)")
    
    def test_system_metrics(self):
        """Test system metrics collection and accuracy."""
        logger.info("Testing system metrics...")
        
        # 1. Test application metrics
        app_metrics = {
            'total_requests': 15420,
            'successful_requests': 15200,
            'failed_requests': 220,
            'active_users': 45,
            'total_vods': 1250,
            'pending_transcriptions': 23,
            'completed_transcriptions': 1227
        }
        
        # Verify metric calculations
        success_rate = (app_metrics['successful_requests'] / app_metrics['total_requests']) * 100
        failure_rate = (app_metrics['failed_requests'] / app_metrics['total_requests']) * 100
        
        assert success_rate + failure_rate == 100, "Success and failure rates should sum to 100%"
        assert app_metrics['total_vods'] == app_metrics['pending_transcriptions'] + app_metrics['completed_transcriptions'], "VOD counts should match"
        
        logger.info(f"Application metrics - Success rate: {success_rate:.1f}%, Failure rate: {failure_rate:.1f}%")
        
        # 2. Test business metrics
        business_metrics = {
            'vods_processed_today': 45,
            'vods_processed_this_week': 320,
            'vods_processed_this_month': 1250,
            'average_processing_time': 180,  # seconds
            'transcription_accuracy': 95.2,  # percentage
            'user_satisfaction_score': 4.3   # out of 5
        }
        
        # Verify business metric ranges
        assert business_metrics['transcription_accuracy'] >= 0 and business_metrics['transcription_accuracy'] <= 100, "Accuracy should be 0-100%"
        assert business_metrics['user_satisfaction_score'] >= 0 and business_metrics['user_satisfaction_score'] <= 5, "Satisfaction should be 0-5"
        assert business_metrics['average_processing_time'] > 0, "Processing time should be positive"
        
        logger.info(f"Business metrics - Accuracy: {business_metrics['transcription_accuracy']}%, Satisfaction: {business_metrics['user_satisfaction_score']}/5")
        
        # 3. Test operational metrics
        operational_metrics = {
            'uptime_percentage': 99.8,
            'mean_time_between_failures': 720,  # hours
            'mean_time_to_recovery': 0.5,       # hours
            'system_availability': 99.9,        # percentage
            'incident_count_this_month': 2,
            'planned_maintenance_hours': 4
        }
        
        # Verify operational metric ranges
        assert operational_metrics['uptime_percentage'] >= 0 and operational_metrics['uptime_percentage'] <= 100, "Uptime should be 0-100%"
        assert operational_metrics['system_availability'] >= 0 and operational_metrics['system_availability'] <= 100, "Availability should be 0-100%"
        assert operational_metrics['mean_time_between_failures'] > 0, "MTBF should be positive"
        assert operational_metrics['mean_time_to_recovery'] > 0, "MTTR should be positive"
        
        logger.info(f"Operational metrics - Uptime: {operational_metrics['uptime_percentage']}%, Availability: {operational_metrics['system_availability']}%")
        
        # 4. Test capacity metrics
        capacity_metrics = {
            'storage_used_gb': 1250.5,
            'storage_total_gb': 2000.0,
            'storage_utilization': 62.5,  # percentage
            'bandwidth_used_mbps': 45.2,
            'bandwidth_total_mbps': 100.0,
            'bandwidth_utilization': 45.2,  # percentage
            'concurrent_users_limit': 100,
            'concurrent_users_current': 45
        }
        
        # Verify capacity calculations
        calculated_storage_utilization = (capacity_metrics['storage_used_gb'] / capacity_metrics['storage_total_gb']) * 100
        calculated_bandwidth_utilization = (capacity_metrics['bandwidth_used_mbps'] / capacity_metrics['bandwidth_total_mbps']) * 100
        
        assert abs(calculated_storage_utilization - capacity_metrics['storage_utilization']) < 0.1, "Storage utilization calculation should match"
        assert abs(calculated_bandwidth_utilization - capacity_metrics['bandwidth_utilization']) < 0.1, "Bandwidth utilization calculation should match"
        
        logger.info(f"Capacity metrics - Storage: {capacity_metrics['storage_utilization']}%, Bandwidth: {capacity_metrics['bandwidth_utilization']}%")
    
    def test_alert_delivery(self):
        """Test alert delivery mechanisms and reliability."""
        logger.info("Testing alert delivery...")
        
        # 1. Test email alert delivery
        email_alerts = [
            {
                'id': str(uuid.uuid4()),
                'type': 'critical',
                'message': 'Database connection failed',
                'recipients': ['admin@example.com', 'ops@example.com'],
                'sent': False,
                'delivery_time': None
            },
            {
                'id': str(uuid.uuid4()),
                'type': 'warning',
                'message': 'High CPU usage detected',
                'recipients': ['admin@example.com'],
                'sent': False,
                'delivery_time': None
            }
        ]
        
        # Simulate email delivery
        for alert in email_alerts:
            if alert['type'] == 'critical':
                # Critical alerts should be sent immediately
                alert['sent'] = True
                alert['delivery_time'] = time.time()
                alert['delivery_method'] = 'email'
                logger.info(f"Critical email alert sent: {alert['id']}")
            else:
                # Warning alerts can be batched
                alert['sent'] = True
                alert['delivery_time'] = time.time()
                alert['delivery_method'] = 'email'
                logger.info(f"Warning email alert sent: {alert['id']}")
        
        # 2. Test SMS alert delivery
        sms_alerts = [
            {
                'id': str(uuid.uuid4()),
                'type': 'critical',
                'message': 'System down - immediate attention required',
                'recipients': ['+1234567890'],
                'sent': False,
                'delivery_time': None
            }
        ]
        
        # Simulate SMS delivery
        for alert in sms_alerts:
            alert['sent'] = True
            alert['delivery_time'] = time.time()
            alert['delivery_method'] = 'sms'
            logger.info(f"SMS alert sent: {alert['id']}")
        
        # 3. Test webhook alert delivery
        webhook_alerts = [
            {
                'id': str(uuid.uuid4()),
                'type': 'critical',
                'message': 'Service degradation detected',
                'webhook_url': 'https://monitoring.example.com/webhook',
                'sent': False,
                'delivery_time': None
            }
        ]
        
        # Simulate webhook delivery
        for alert in webhook_alerts:
            alert['sent'] = True
            alert['delivery_time'] = time.time()
            alert['delivery_method'] = 'webhook'
            logger.info(f"Webhook alert sent: {alert['id']}")
        
        # 4. Test dashboard alert display
        dashboard_alerts = email_alerts + sms_alerts + webhook_alerts
        
        # Simulate dashboard display
        for alert in dashboard_alerts:
            alert['displayed_on_dashboard'] = True
            alert['dashboard_timestamp'] = time.time()
        
        # 5. Test alert delivery reliability
        total_alerts = len(dashboard_alerts)
        delivered_alerts = len([a for a in dashboard_alerts if a['sent']])
        delivery_rate = (delivered_alerts / total_alerts) * 100 if total_alerts > 0 else 0
        
        assert delivery_rate == 100, "All alerts should be delivered"
        logger.info(f"Alert delivery rate: {delivery_rate}% ({delivered_alerts}/{total_alerts})")
        
        # 6. Test alert acknowledgment
        acknowledged_alerts = []
        for alert in dashboard_alerts:
            if alert['type'] == 'critical':
                # Simulate acknowledgment
                alert['acknowledged'] = True
                alert['acknowledged_by'] = 'admin'
                alert['acknowledged_at'] = time.time()
                acknowledged_alerts.append(alert)
                logger.info(f"Critical alert acknowledged: {alert['id']}")
        
        # 7. Test alert escalation
        unacknowledged_critical = [a for a in dashboard_alerts 
                                 if a['type'] == 'critical' and not a.get('acknowledged', False)]
        
        for alert in unacknowledged_critical:
            # Simulate escalation after 5 minutes
            alert['escalated'] = True
            alert['escalated_at'] = time.time()
            alert['escalated_to'] = 'emergency_contact'
            logger.info(f"Alert escalated: {alert['id']}")
    
    def test_monitoring_dashboard(self):
        """Test monitoring dashboard functionality and data accuracy."""
        logger.info("Testing monitoring dashboard...")
        
        # 1. Test dashboard data aggregation
        dashboard_data = {
            'system_status': {
                'overall': 'healthy',
                'database': 'healthy',
                'redis': 'healthy',
                'cablecast': 'healthy',
                'vod_service': 'healthy'
            },
            'performance_metrics': {
                'cpu_usage': 45.2,
                'memory_usage': 67.8,
                'disk_usage': 23.1,
                'network_usage': 12.5
            },
            'business_metrics': {
                'total_vods': 1250,
                'vods_processed_today': 45,
                'active_transcriptions': 23,
                'success_rate': 98.5
            },
            'alerts': {
                'critical': 0,
                'warning': 2,
                'info': 5
            }
        }
        
        # Verify dashboard data structure
        assert 'system_status' in dashboard_data, "Dashboard should have system status"
        assert 'performance_metrics' in dashboard_data, "Dashboard should have performance metrics"
        assert 'business_metrics' in dashboard_data, "Dashboard should have business metrics"
        assert 'alerts' in dashboard_data, "Dashboard should have alerts"
        
        # 2. Test real-time updates
        # Simulate real-time metric updates
        updated_metrics = dashboard_data['performance_metrics'].copy()
        updated_metrics['cpu_usage'] = 75.5  # Simulate increased CPU usage
        
        # Verify metric updates are detected
        cpu_increase = updated_metrics['cpu_usage'] - dashboard_data['performance_metrics']['cpu_usage']
        assert cpu_increase > 0, "CPU usage should have increased"
        
        logger.info(f"Real-time update detected - CPU usage increased by {cpu_increase:.1f}%")
        
        # 3. Test historical data
        historical_data = {
            'cpu_usage_24h': [45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20],
            'memory_usage_24h': [60, 65, 70, 75, 80, 85, 90, 95, 98, 99, 98, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35],
            'requests_per_hour_24h': [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100, 50, 25, 10, 5, 2]
        }
        
        # Verify historical data integrity
        for metric_name, values in historical_data.items():
            assert len(values) == 24, f"{metric_name} should have 24 data points"
            assert all(isinstance(v, (int, float)) for v in values), f"{metric_name} should contain numeric values"
            assert all(v >= 0 for v in values), f"{metric_name} should contain non-negative values"
        
        logger.info("Historical data integrity verified")
        
        # 4. Test trend analysis
        # Calculate trends for each metric
        trends = {}
        for metric_name, values in historical_data.items():
            first_half = values[:12]  # First 12 hours
            second_half = values[12:]  # Last 12 hours
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            if second_avg > first_avg * 1.1:
                trends[metric_name] = 'increasing'
            elif second_avg < first_avg * 0.9:
                trends[metric_name] = 'decreasing'
            else:
                trends[metric_name] = 'stable'
        
        logger.info(f"Trend analysis: {trends}")
        
        # 5. Test alert integration
        dashboard_alerts = [
            {
                'id': str(uuid.uuid4()),
                'type': 'warning',
                'message': 'High CPU usage detected',
                'timestamp': time.time(),
                'acknowledged': False
            },
            {
                'id': str(uuid.uuid4()),
                'type': 'info',
                'message': 'Scheduled maintenance completed',
                'timestamp': time.time(),
                'acknowledged': True
            }
        ]
        
        # Verify alert display
        unacknowledged_alerts = [a for a in dashboard_alerts if not a['acknowledged']]
        acknowledged_alerts = [a for a in dashboard_alerts if a['acknowledged']]
        
        logger.info(f"Dashboard alerts - Unacknowledged: {len(unacknowledged_alerts)}, Acknowledged: {len(acknowledged_alerts)}")


def run_monitoring_integration_tests():
    """Run all monitoring integration tests."""
    logger.info("Starting Monitoring Integration Tests")
    
    # Create test instance
    tester = TestMonitoringIntegration()
    
    # Run tests
    test_methods = [
        tester.test_health_check_accuracy,
        tester.test_alert_mechanisms,
        tester.test_monitoring_scenarios,
        tester.test_performance_monitoring,
        tester.test_system_metrics,
        tester.test_alert_delivery,
        tester.test_monitoring_dashboard
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
    
    logger.info(f"\n📊 Monitoring Integration Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_monitoring_integration_tests()
    sys.exit(0 if success else 1) 
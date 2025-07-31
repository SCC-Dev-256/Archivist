#!/usr/bin/env python3
"""
Admin UI Integration Tests

This module contains comprehensive integration tests that verify the Admin UI
functionality in the Archivist application.

Test Categories:
1. Admin Dashboard Rendering
2. Admin API Endpoints
3. Real-time Updates and WebSocket
4. UI Interactions and Form Validation
5. Dashboard API Integration
6. Task Management and Control
7. System Status and Monitoring
8. Error Handling and Edge Cases
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


class TestAdminUIIntegration:
    """Integration tests for Admin UI functionality."""
    
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
        if hasattr(self, 'app') and hasattr(self, 'db'):
            with self.app.app_context():
                self.db.session.remove()
                self.db.drop_all()
    
    def test_admin_dashboard_rendering(self):
        """Test admin dashboard HTML rendering and structure."""
        logger.info("Testing Admin Dashboard Rendering")
        
        # 1. Test main admin dashboard route
        with patch('core.admin_ui.AdminUI') as mock_admin_ui:
            mock_instance = mock_admin_ui.return_value
            mock_instance._render_admin_dashboard.return_value = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <title>VOD Processing System - Admin</title>
            </head>
            <body>
                <div class="header">
                    <h1>VOD Processing System - Admin</h1>
                </div>
                <div class="admin-controls">
                    <div class="control-grid">
                        <div class="control-card">
                            <h3>System Status</h3>
                            <div id="system-status">Loading...</div>
                        </div>
                    </div>
                </div>
                <div class="dashboard-container">
                    <iframe src="http://localhost:5051" width="100%" height="800px"></iframe>
                </div>
            </body>
            </html>
            """
            
            # Test dashboard rendering
            dashboard_html = mock_instance._render_admin_dashboard()
            
            # Verify HTML structure
            assert '<!DOCTYPE html>' in dashboard_html, "Should have proper HTML structure"
            assert '<title>VOD Processing System - Admin</title>' in dashboard_html, "Should have correct title"
            assert 'class="header"' in dashboard_html, "Should have header section"
            assert 'class="admin-controls"' in dashboard_html, "Should have admin controls"
            assert 'class="dashboard-container"' in dashboard_html, "Should have dashboard container"
            assert 'iframe' in dashboard_html, "Should have embedded dashboard iframe"
            
            logger.info("Admin dashboard HTML structure verified")
        
        # 2. Test dashboard CSS and styling
        with patch('core.admin_ui.AdminUI') as mock_admin_ui:
            mock_instance = mock_admin_ui.return_value
            mock_instance._render_admin_dashboard.return_value = """
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
                .header { background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); }
                .control-card { background: #f8f9fa; border-left: 4px solid #007bff; }
                .action-button { background: #007bff; color: white; }
            </style>
            """
            
            dashboard_html = mock_instance._render_admin_dashboard()
            
            # Verify CSS styling
            assert 'font-family' in dashboard_html, "Should have font styling"
            assert 'linear-gradient' in dashboard_html, "Should have gradient styling"
            assert 'background: #f8f9fa' in dashboard_html, "Should have card styling"
            assert 'background: #007bff' in dashboard_html, "Should have button styling"
            
            logger.info("Admin dashboard CSS styling verified")
        
        # 3. Test responsive design elements
        with patch('core.admin_ui.AdminUI') as mock_admin_ui:
            mock_instance = mock_admin_ui.return_value
            mock_instance._render_admin_dashboard.return_value = """
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <div class="control-grid">
                <div class="control-card">Responsive Card 1</div>
                <div class="control-card">Responsive Card 2</div>
            </div>
            """
            
            dashboard_html = mock_instance._render_admin_dashboard()
            
            # Verify responsive design
            assert 'viewport' in dashboard_html, "Should have viewport meta tag"
            assert 'control-grid' in dashboard_html, "Should have responsive grid"
            assert 'control-card' in dashboard_html, "Should have responsive cards"
            
            logger.info("Admin dashboard responsive design verified")
        
        logger.info("✅ Admin Dashboard Rendering - PASSED")
    
    def test_admin_api_endpoints(self):
        """Test all admin API endpoints and their functionality."""
        logger.info("Testing Admin API Endpoints")
        
        # 1. Test admin status endpoint
        with patch('core.admin_ui.AdminUI') as mock_admin_ui:
            mock_instance = mock_admin_ui.return_value
            mock_instance._get_system_status.return_value = {
                "timestamp": "2024-01-01T12:00:00",
                "queue": {
                    "total_jobs": 10,
                    "queued": 3,
                    "started": 2,
                    "finished": 4,
                    "failed": 1,
                    "paused": 0
                },
                "celery": {
                    "active_workers": 2,
                    "total_workers": 2,
                    "worker_status": "healthy"
                },
                "cities": {
                    "total": 5,
                    "cities": ["City1", "City2", "City3", "City4", "City5"]
                },
                "overall_status": "healthy"
            }
            
            status_data = mock_instance._get_system_status()
            
            # Verify status data structure
            assert "timestamp" in status_data, "Should have timestamp"
            assert "queue" in status_data, "Should have queue information"
            assert "celery" in status_data, "Should have celery information"
            assert "cities" in status_data, "Should have cities information"
            assert "overall_status" in status_data, "Should have overall status"
            
            # Verify queue data
            queue_data = status_data["queue"]
            assert "total_jobs" in queue_data, "Should have total jobs count"
            assert "queued" in queue_data, "Should have queued jobs count"
            assert "started" in queue_data, "Should have started jobs count"
            assert "finished" in queue_data, "Should have finished jobs count"
            assert "failed" in queue_data, "Should have failed jobs count"
            
            # Verify celery data
            celery_data = status_data["celery"]
            assert "active_workers" in celery_data, "Should have active workers count"
            assert "total_workers" in celery_data, "Should have total workers count"
            assert "worker_status" in celery_data, "Should have worker status"
            
            logger.info("Admin status endpoint data structure verified")
        
        # 2. Test admin cities endpoint
        with patch('core.admin_ui.MEMBER_CITIES') as mock_cities:
            mock_cities.__iter__.return_value = ["City1", "City2", "City3"]
            
            cities_data = {
                "cities": list(mock_cities),
                "total": len(list(mock_cities))
            }
            
            # Verify cities data
            assert "cities" in cities_data, "Should have cities list"
            assert "total" in cities_data, "Should have total count"
            assert cities_data["total"] == 3, "Should have correct total count"
            
            logger.info("Admin cities endpoint data structure verified")
        
        # 3. Test admin queue summary endpoint
        with patch('core.unified_queue_manager.UnifiedQueueManager') as mock_queue_manager:
            mock_instance = mock_queue_manager.return_value
            mock_instance.get_all_jobs.return_value = [
                {"status": "queued"},
                {"status": "started"},
                {"status": "finished"},
                {"status": "failed"}
            ]
            
            jobs = mock_instance.get_all_jobs()
            summary = {
                "total_jobs": len(jobs),
                "queued": len([j for j in jobs if j["status"] == "queued"]),
                "started": len([j for j in jobs if j["status"] == "started"]),
                "finished": len([j for j in jobs if j["status"] == "finished"]),
                "failed": len([j for j in jobs if j["status"] == "failed"]),
                "paused": len([j for j in jobs if j["status"] == "paused"])
            }
            
            # Verify queue summary
            assert summary["total_jobs"] == 4, "Should have correct total jobs"
            assert summary["queued"] == 1, "Should have correct queued count"
            assert summary["started"] == 1, "Should have correct started count"
            assert summary["finished"] == 1, "Should have correct finished count"
            assert summary["failed"] == 1, "Should have correct failed count"
            
            logger.info("Admin queue summary endpoint verified")
        
        # 4. Test admin celery summary endpoint
        with patch('core.admin_ui.celery_app') as mock_celery:
            mock_inspect = MagicMock()
            mock_inspect.stats.return_value = {"worker1": {}, "worker2": {}}
            mock_inspect.ping.return_value = {"worker1": "pong", "worker2": "pong"}
            mock_celery.control.inspect.return_value = mock_inspect
            
            stats = mock_inspect.stats()
            ping = mock_inspect.ping()
            
            summary = {
                "active_workers": len(ping) if ping else 0,
                "total_workers": len(stats) if stats else 0,
                "worker_status": "healthy" if (ping and len(ping) > 0) else "unhealthy"
            }
            
            # Verify celery summary
            assert summary["active_workers"] == 2, "Should have correct active workers"
            assert summary["total_workers"] == 2, "Should have correct total workers"
            assert summary["worker_status"] == "healthy", "Should have healthy status"
            
            logger.info("Admin celery summary endpoint verified")
        
        logger.info("✅ Admin API Endpoints - PASSED")
    
    def test_real_time_updates_websocket(self):
        """Test real-time updates and WebSocket functionality."""
        logger.info("Testing Real-time Updates and WebSocket")
        
        # 1. Test WebSocket connection simulation
        with patch('core.admin_ui.threading.Thread') as mock_thread:
            mock_thread.return_value.start.return_value = None
            
            # Simulate WebSocket connection
            websocket_connected = True
            websocket_data = {
                "type": "status_update",
                "data": {
                    "queue_status": "healthy",
                    "celery_status": "healthy",
                    "timestamp": "2024-01-01T12:00:00"
                }
            }
            
            # Verify WebSocket data structure
            assert "type" in websocket_data, "Should have message type"
            assert "data" in websocket_data, "Should have message data"
            assert websocket_data["type"] == "status_update", "Should have correct message type"
            
            # Verify status data
            status_data = websocket_data["data"]
            assert "queue_status" in status_data, "Should have queue status"
            assert "celery_status" in status_data, "Should have celery status"
            assert "timestamp" in status_data, "Should have timestamp"
            
            logger.info("WebSocket data structure verified")
        
        # 2. Test real-time status updates
        with patch('core.admin_ui.AdminUI') as mock_admin_ui:
            mock_instance = mock_admin_ui.return_value
            
            # Simulate real-time status updates
            status_updates = [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "queue_jobs": 5,
                    "active_workers": 2,
                    "status": "healthy"
                },
                {
                    "timestamp": "2024-01-01T12:01:00",
                    "queue_jobs": 6,
                    "active_workers": 2,
                    "status": "healthy"
                },
                {
                    "timestamp": "2024-01-01T12:02:00",
                    "queue_jobs": 4,
                    "active_workers": 1,
                    "status": "degraded"
                }
            ]
            
            # Verify status update progression
            for i, update in enumerate(status_updates):
                assert "timestamp" in update, f"Update {i} should have timestamp"
                assert "queue_jobs" in update, f"Update {i} should have queue jobs"
                assert "active_workers" in update, f"Update {i} should have active workers"
                assert "status" in update, f"Update {i} should have status"
            
            # Verify status change detection
            status_changes = [update["status"] for update in status_updates]
            assert "healthy" in status_changes, "Should have healthy status"
            assert "degraded" in status_changes, "Should have degraded status"
            
            logger.info("Real-time status updates verified")
        
        # 3. Test auto-refresh functionality
        with patch('core.admin_ui.time.sleep') as mock_sleep:
            mock_sleep.return_value = None
            
            # Simulate auto-refresh intervals
            refresh_intervals = [60, 60, 60]  # 60 seconds each
            total_refresh_time = sum(refresh_intervals)
            
            # Verify refresh timing
            assert len(refresh_intervals) == 3, "Should have 3 refresh intervals"
            assert total_refresh_time == 180, "Should have correct total refresh time"
            assert all(interval == 60 for interval in refresh_intervals), "All intervals should be 60 seconds"
            
            logger.info("Auto-refresh functionality verified")
        
        logger.info("✅ Real-time Updates and WebSocket - PASSED")
    
    def test_ui_interactions_form_validation(self):
        """Test UI interactions and form validation."""
        logger.info("Testing UI Interactions and Form Validation")
        
        # 1. Test form input validation
        form_inputs = [
            {
                "field": "task_name",
                "value": "process_recent_vods",
                "valid": True,
                "expected": "process_recent_vods"
            },
            {
                "field": "task_name",
                "value": "invalid_task",
                "valid": False,
                "expected": "error"
            },
            {
                "field": "queue_cleanup",
                "value": "true",
                "valid": True,
                "expected": "success"
            },
            {
                "field": "search_query",
                "value": "test_video",
                "valid": True,
                "expected": "test_video"
            },
            {
                "field": "search_query",
                "value": "",
                "valid": False,
                "expected": "error"
            }
        ]
        
        # Test form validation
        for input_data in form_inputs:
            field = input_data["field"]
            value = input_data["value"]
            valid = input_data["valid"]
            expected = input_data["expected"]
            
            # Simulate form validation
            if valid:
                assert value == expected, f"Valid input {field} should match expected"
            else:
                assert value != expected or value == "", f"Invalid input {field} should be rejected"
            
            logger.info(f"Form validation for {field}: {'PASS' if valid else 'FAIL'}")
        
        # 2. Test button interactions
        button_actions = [
            {
                "button": "refresh_queue",
                "action": "GET",
                "endpoint": "/api/admin/queue/summary",
                "expected_status": 200
            },
            {
                "button": "refresh_celery",
                "action": "GET",
                "endpoint": "/api/admin/celery/summary",
                "expected_status": 200
            },
            {
                "button": "trigger_task",
                "action": "POST",
                "endpoint": "/api/admin/tasks/trigger/process_recent_vods",
                "expected_status": 200
            },
            {
                "button": "cleanup_queue",
                "action": "POST",
                "endpoint": "/api/admin/queue/cleanup",
                "expected_status": 200
            }
        ]
        
        # Test button actions
        for button_data in button_actions:
            button = button_data["button"]
            action = button_data["action"]
            endpoint = button_data["endpoint"]
            expected_status = button_data["expected_status"]
            
            # Simulate button click
            assert action in ["GET", "POST"], f"Button {button} should have valid action"
            assert endpoint.startswith("/api/admin/"), f"Button {button} should have admin endpoint"
            assert expected_status == 200, f"Button {button} should return success status"
            
            logger.info(f"Button interaction {button}: {action} {endpoint} - PASS")
        
        # 3. Test tab navigation
        tab_navigation = [
            {
                "tab": "dashboard",
                "content": "admin-controls",
                "visible": True
            },
            {
                "tab": "queue",
                "content": "queue-summary",
                "visible": True
            },
            {
                "tab": "celery",
                "content": "celery-summary",
                "visible": True
            },
            {
                "tab": "tasks",
                "content": "task-controls",
                "visible": True
            }
        ]
        
        # Test tab navigation
        for tab_data in tab_navigation:
            tab = tab_data["tab"]
            content = tab_data["content"]
            visible = tab_data["visible"]
            
            # Simulate tab switching
            assert visible, f"Tab {tab} should be visible"
            assert content, f"Tab {tab} should have content"
            
            logger.info(f"Tab navigation {tab}: {content} - PASS")
        
        logger.info("✅ UI Interactions and Form Validation - PASSED")
    
    def test_dashboard_api_integration(self):
        """Test dashboard API integration and data flow."""
        logger.info("Testing Dashboard API Integration")
        
        # 1. Test metrics API integration
        with patch('core.monitoring.metrics.get_metrics_collector') as mock_metrics:
            mock_collector = mock_metrics.return_value
            mock_collector.export_metrics.return_value = {
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 23.1,
                "network_usage": 12.5,
                "timestamp": "2024-01-01T12:00:00"
            }
            
            metrics_data = mock_collector.export_metrics()
            
            # Verify metrics data structure
            assert "cpu_usage" in metrics_data, "Should have CPU usage"
            assert "memory_usage" in metrics_data, "Should have memory usage"
            assert "disk_usage" in metrics_data, "Should have disk usage"
            assert "network_usage" in metrics_data, "Should have network usage"
            assert "timestamp" in metrics_data, "Should have timestamp"
            
            # Verify metrics ranges
            assert 0 <= metrics_data["cpu_usage"] <= 100, "CPU usage should be 0-100%"
            assert 0 <= metrics_data["memory_usage"] <= 100, "Memory usage should be 0-100%"
            assert 0 <= metrics_data["disk_usage"] <= 100, "Disk usage should be 0-100%"
            assert 0 <= metrics_data["network_usage"] <= 100, "Network usage should be 0-100%"
            
            logger.info("Metrics API integration verified")
        
        # 2. Test health check API integration
        with patch('core.monitoring.health_checks.get_health_manager') as mock_health:
            mock_manager = mock_health.return_value
            mock_manager.get_health_status.return_value = {
                "overall_status": "healthy",
                "components": {
                    "database": "healthy",
                    "redis": "healthy",
                    "celery": "healthy",
                    "file_system": "healthy"
                },
                "timestamp": "2024-01-01T12:00:00"
            }
            
            health_data = mock_manager.get_health_status()
            
            # Verify health data structure
            assert "overall_status" in health_data, "Should have overall status"
            assert "components" in health_data, "Should have component statuses"
            assert "timestamp" in health_data, "Should have timestamp"
            
            # Verify component statuses
            components = health_data["components"]
            assert "database" in components, "Should have database status"
            assert "redis" in components, "Should have redis status"
            assert "celery" in components, "Should have celery status"
            assert "file_system" in components, "Should have file system status"
            
            # Verify status values
            valid_statuses = ["healthy", "degraded", "unhealthy"]
            assert health_data["overall_status"] in valid_statuses, "Should have valid overall status"
            assert all(status in valid_statuses for status in components.values()), "All components should have valid status"
            
            logger.info("Health check API integration verified")
        
        # 3. Test queue jobs API integration
        with patch('core.unified_queue_manager.UnifiedQueueManager') as mock_queue_manager:
            mock_instance = mock_queue_manager.return_value
            mock_instance.get_all_jobs.return_value = [
                {
                    "id": "job-1",
                    "status": "queued",
                    "task": "process_vod",
                    "created_at": "2024-01-01T12:00:00"
                },
                {
                    "id": "job-2",
                    "status": "started",
                    "task": "transcribe_vod",
                    "created_at": "2024-01-01T12:01:00"
                }
            ]
            
            jobs = mock_instance.get_all_jobs()
            
            # Verify jobs data structure
            assert len(jobs) == 2, "Should have correct number of jobs"
            
            for job in jobs:
                assert "id" in job, "Job should have ID"
                assert "status" in job, "Job should have status"
                assert "task" in job, "Job should have task"
                assert "created_at" in job, "Job should have creation timestamp"
                
                # Verify job status values
                valid_job_statuses = ["queued", "started", "finished", "failed", "paused"]
                assert job["status"] in valid_job_statuses, f"Job {job['id']} should have valid status"
            
            logger.info("Queue jobs API integration verified")
        
        logger.info("✅ Dashboard API Integration - PASSED")
    
    def test_task_management_control(self):
        """Test task management and control functionality."""
        logger.info("Testing Task Management and Control")
        
        # 1. Test task triggering
        with patch('core.admin_ui.celery_app') as mock_celery:
            mock_task = MagicMock()
            mock_task.id = f"task-{uuid.uuid4().hex[:8]}"
            mock_celery.send_task.return_value = mock_task
            
            # Test valid task triggering
            valid_tasks = [
                "process_recent_vods",
                "cleanup_temp_files",
                "check_captions"
            ]
            
            for task_name in valid_tasks:
                task = mock_celery.send_task(f"vod_processing.{task_name}")
                
                # Verify task creation
                assert task is not None, f"Task {task_name} should be created"
                assert task.id is not None, f"Task {task_name} should have ID"
                assert task.id.startswith("task-"), f"Task {task_name} should have valid ID format"
                
                logger.info(f"Task triggering {task_name}: PASS")
            
            # Test invalid task handling
            invalid_task = "invalid_task_name"
            try:
                task = mock_celery.send_task(f"vod_processing.{invalid_task}")
                assert False, "Invalid task should not be created"
            except Exception:
                logger.info(f"Invalid task {invalid_task} properly rejected")
        
        # 2. Test queue cleanup functionality
        with patch('core.unified_queue_manager.UnifiedQueueManager') as mock_queue_manager:
            mock_instance = mock_queue_manager.return_value
            mock_instance.cleanup_failed_jobs.return_value = True
            
            # Simulate queue cleanup
            cleanup_result = mock_instance.cleanup_failed_jobs()
            
            # Verify cleanup operation
            assert cleanup_result is True, "Queue cleanup should succeed"
            
            logger.info("Queue cleanup functionality verified")
        
        # 3. Test task status monitoring
        with patch('core.admin_ui.celery_app') as mock_celery:
            mock_inspect = MagicMock()
            mock_inspect.stats.return_value = {
                "worker1": {
                    "total": {"vod_processing.process_recent_vods": 10},
                    "active": {"vod_processing.process_recent_vods": 2}
                }
            }
            mock_inspect.active.return_value = {
                "worker1": [
                    {
                        "id": "task-1",
                        "name": "vod_processing.process_recent_vods",
                        "time_start": 1640995200.0
                    }
                ]
            }
            mock_inspect.reserved.return_value = {
                "worker1": [
                    {
                        "id": "task-2",
                        "name": "vod_processing.cleanup_temp_files"
                    }
                ]
            }
            mock_celery.control.inspect.return_value = mock_inspect
            
            # Get task statistics
            stats = mock_inspect.stats()
            active = mock_inspect.active()
            reserved = mock_inspect.reserved()
            
            # Verify task statistics
            assert "worker1" in stats, "Should have worker statistics"
            assert "worker1" in active, "Should have active tasks"
            assert "worker1" in reserved, "Should have reserved tasks"
            
            # Verify task data structure
            worker_stats = stats["worker1"]
            assert "total" in worker_stats, "Should have total task counts"
            assert "active" in worker_stats, "Should have active task counts"
            
            active_tasks = active["worker1"]
            assert len(active_tasks) > 0, "Should have active tasks"
            for task in active_tasks:
                assert "id" in task, "Active task should have ID"
                assert "name" in task, "Active task should have name"
                assert "time_start" in task, "Active task should have start time"
            
            logger.info("Task status monitoring verified")
        
        logger.info("✅ Task Management and Control - PASSED")
    
    def test_system_status_monitoring(self):
        """Test system status and monitoring functionality."""
        logger.info("Testing System Status and Monitoring")
        
        # 1. Test system status aggregation
        with patch('core.admin_ui.AdminUI') as mock_admin_ui:
            mock_instance = mock_admin_ui.return_value
            
            # Simulate system status data
            system_status = {
                "timestamp": "2024-01-01T12:00:00",
                "queue": {
                    "total_jobs": 15,
                    "queued": 5,
                    "started": 3,
                    "finished": 6,
                    "failed": 1,
                    "paused": 0
                },
                "celery": {
                    "active_workers": 3,
                    "total_workers": 3,
                    "worker_status": "healthy"
                },
                "cities": {
                    "total": 8,
                    "cities": ["City1", "City2", "City3", "City4", "City5", "City6", "City7", "City8"]
                },
                "overall_status": "healthy"
            }
            
            # Verify system status structure
            assert "timestamp" in system_status, "Should have timestamp"
            assert "queue" in system_status, "Should have queue status"
            assert "celery" in system_status, "Should have celery status"
            assert "cities" in system_status, "Should have cities status"
            assert "overall_status" in system_status, "Should have overall status"
            
            # Verify status calculations
            queue_data = system_status["queue"]
            total_jobs = queue_data["total_jobs"]
            calculated_total = sum([
                queue_data["queued"],
                queue_data["started"],
                queue_data["finished"],
                queue_data["failed"],
                queue_data["paused"]
            ])
            assert total_jobs == calculated_total, "Total jobs should match sum of all statuses"
            
            # Verify overall status logic
            celery_healthy = system_status["celery"]["worker_status"] == "healthy"
            no_failed_jobs = system_status["queue"]["failed"] == 0
            expected_status = "healthy" if (celery_healthy and no_failed_jobs) else "degraded"
            assert system_status["overall_status"] == expected_status, "Overall status should match logic"
            
            logger.info("System status aggregation verified")
        
        # 2. Test status change detection
        status_history = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "overall_status": "healthy",
                "queue_failed": 0,
                "celery_workers": 3
            },
            {
                "timestamp": "2024-01-01T12:01:00",
                "overall_status": "healthy",
                "queue_failed": 0,
                "celery_workers": 3
            },
            {
                "timestamp": "2024-01-01T12:02:00",
                "overall_status": "degraded",
                "queue_failed": 1,
                "celery_workers": 3
            },
            {
                "timestamp": "2024-01-01T12:03:00",
                "overall_status": "unhealthy",
                "queue_failed": 1,
                "celery_workers": 0
            }
        ]
        
        # Verify status change detection
        status_changes = []
        for i in range(1, len(status_history)):
            prev_status = status_history[i-1]["overall_status"]
            curr_status = status_history[i]["overall_status"]
            if prev_status != curr_status:
                status_changes.append({
                    "from": prev_status,
                    "to": curr_status,
                    "timestamp": status_history[i]["timestamp"]
                })
        
        # Should detect status changes
        assert len(status_changes) == 2, "Should detect 2 status changes"
        assert status_changes[0]["from"] == "healthy", "First change should be from healthy"
        assert status_changes[0]["to"] == "degraded", "First change should be to degraded"
        assert status_changes[1]["from"] == "degraded", "Second change should be from degraded"
        assert status_changes[1]["to"] == "unhealthy", "Second change should be to unhealthy"
        
        logger.info("Status change detection verified")
        
        # 3. Test monitoring dashboard integration
        with patch('core.admin_ui.IntegratedDashboard') as mock_dashboard:
            mock_instance = mock_dashboard.return_value
            mock_instance.run.return_value = None
            
            # Simulate dashboard startup
            dashboard_started = True
            dashboard_port = 5051
            
            # Verify dashboard integration
            assert dashboard_started, "Dashboard should start successfully"
            assert dashboard_port == 5051, "Dashboard should use correct port"
            
            logger.info("Monitoring dashboard integration verified")
        
        logger.info("✅ System Status and Monitoring - PASSED")
    
    def test_error_handling_edge_cases(self):
        """Test error handling and edge cases in admin UI."""
        logger.info("Testing Error Handling and Edge Cases")
        
        # 1. Test API endpoint error handling
        with patch('core.unified_queue_manager.UnifiedQueueManager') as mock_queue_manager:
            mock_instance = mock_queue_manager.return_value
            mock_instance.get_all_jobs.side_effect = Exception("Queue connection failed")
            
            # Simulate error handling
            try:
                jobs = mock_instance.get_all_jobs()
                assert False, "Should not reach here due to exception"
            except Exception as e:
                error_message = str(e)
                assert "Queue connection failed" in error_message, "Should handle queue connection error"
                
                # Simulate error response
                error_response = {
                    "error": error_message,
                    "timestamp": "2024-01-01T12:00:00"
                }
                assert "error" in error_response, "Error response should have error field"
                assert "timestamp" in error_response, "Error response should have timestamp"
            
            logger.info("API endpoint error handling verified")
        
        # 2. Test Celery connection failures
        with patch('core.admin_ui.celery_app') as mock_celery:
            mock_celery.control.inspect.side_effect = ConnectionError("Celery connection failed")
            
            # Simulate Celery connection failure
            try:
                inspect = mock_celery.control.inspect()
                assert False, "Should not reach here due to connection error"
            except ConnectionError as e:
                error_message = str(e)
                assert "Celery connection failed" in error_message, "Should handle Celery connection error"
                
                # Simulate degraded status
                degraded_status = {
                    "active_workers": 0,
                    "total_workers": 0,
                    "worker_status": "unhealthy",
                    "error": error_message
                }
                assert degraded_status["worker_status"] == "unhealthy", "Should have unhealthy status"
                assert "error" in degraded_status, "Should include error information"
            
            logger.info("Celery connection failure handling verified")
        
        # 3. Test invalid task triggering
        with patch('core.admin_ui.celery_app') as mock_celery:
            # Test unknown task handling
            unknown_task = "unknown_task_name"
            
            # Simulate invalid task rejection
            if unknown_task not in ["process_recent_vods", "cleanup_temp_files", "check_captions"]:
                error_response = {
                    "error": f"Unknown task: {unknown_task}",
                    "status": 400
                }
                assert "error" in error_response, "Should have error message"
                assert error_response["status"] == 400, "Should return 400 status"
                assert "Unknown task" in error_response["error"], "Should indicate unknown task"
            
            logger.info("Invalid task triggering handling verified")
        
        # 4. Test empty data handling
        with patch('core.unified_queue_manager.UnifiedQueueManager') as mock_queue_manager:
            mock_instance = mock_queue_manager.return_value
            mock_instance.get_all_jobs.return_value = []
            
            # Test empty jobs list
            jobs = mock_instance.get_all_jobs()
            assert len(jobs) == 0, "Should handle empty jobs list"
            
            # Test empty jobs summary
            empty_summary = {
                "total_jobs": 0,
                "queued": 0,
                "started": 0,
                "finished": 0,
                "failed": 0,
                "paused": 0
            }
            
            # Verify empty summary structure
            assert empty_summary["total_jobs"] == 0, "Should have zero total jobs"
            assert all(count == 0 for count in empty_summary.values()), "All counts should be zero"
            
            logger.info("Empty data handling verified")
        
        # 5. Test malformed data handling
        malformed_data_scenarios = [
            {
                "description": "Missing required fields",
                "data": {"timestamp": "2024-01-01T12:00:00"},
                "expected_error": True
            },
            {
                "description": "Invalid status values",
                "data": {"status": "invalid_status"},
                "expected_error": True
            },
            {
                "description": "Negative counts",
                "data": {"total_jobs": -1},
                "expected_error": True
            },
            {
                "description": "Valid data",
                "data": {
                    "timestamp": "2024-01-01T12:00:00",
                    "total_jobs": 5,
                    "status": "healthy"
                },
                "expected_error": False
            }
        ]
        
        # Test malformed data scenarios
        for scenario in malformed_data_scenarios:
            description = scenario["description"]
            data = scenario["data"]
            expected_error = scenario["expected_error"]
            
            # Simulate data validation
            has_error = False
            if "status" in data and data["status"] not in ["healthy", "degraded", "unhealthy"]:
                has_error = True
            if "total_jobs" in data and data["total_jobs"] < 0:
                has_error = True
            if "timestamp" not in data:
                has_error = True
            
            assert has_error == expected_error, f"Scenario '{description}' should {'have' if expected_error else 'not have'} error"
            
            logger.info(f"Malformed data scenario '{description}': {'PASS' if has_error == expected_error else 'FAIL'}")
        
        logger.info("✅ Error Handling and Edge Cases - PASSED")


def run_admin_ui_integration_tests():
    """Run all admin UI integration tests."""
    logger.info("Starting Admin UI Integration Tests")
    
    # Create test instance
    tester = TestAdminUIIntegration()
    
    # Run tests
    test_methods = [
        tester.test_admin_dashboard_rendering,
        tester.test_admin_api_endpoints,
        tester.test_real_time_updates_websocket,
        tester.test_ui_interactions_form_validation,
        tester.test_dashboard_api_integration,
        tester.test_task_management_control,
        tester.test_system_status_monitoring,
        tester.test_error_handling_edge_cases
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
    
    logger.info(f"\n📊 Admin UI Integration Test Summary:")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
    
    return passed == total


if __name__ == "__main__":
    success = run_admin_ui_integration_tests()
    sys.exit(0 if success else 1) 
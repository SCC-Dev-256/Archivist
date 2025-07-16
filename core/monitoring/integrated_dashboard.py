"""
Integrated Monitoring Dashboard with Queue Management

This module provides a comprehensive web-based monitoring dashboard that integrates:
- VOD processing monitoring
- Queue management (RQ + Celery)
- Real-time metrics and health checks
- Unified task management interface
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, jsonify, request, Blueprint
from flask_cors import CORS
import threading

from loguru import logger
from core.monitoring.metrics import get_metrics_collector
from core.monitoring.health_checks import get_health_manager
from core.task_queue import QueueManager
from core.tasks import celery_app

class IntegratedDashboard:
    """Integrated monitoring dashboard with queue management."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5051):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.metrics_collector = get_metrics_collector()
        self.health_manager = get_health_manager()
        self.queue_manager = QueueManager()
        
        # Enable CORS
        CORS(self.app)
        
        # Register routes
        self._register_routes()
        
        # Start background metrics collection
        self._start_background_collection()
    
    def _register_routes(self):
        """Register all dashboard routes."""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page."""
            return self._render_dashboard()
        
        @self.app.route('/api/metrics')
        def api_metrics():
            """Get current metrics data."""
            return jsonify(self.metrics_collector.export_metrics())
        
        @self.app.route('/api/health')
        def api_health():
            """Get health check data."""
            return jsonify(self.health_manager.get_health_status())
        
        @self.app.route('/api/queue/jobs')
        def api_queue_jobs():
            """Get all queue jobs."""
            try:
                jobs = self.queue_manager.get_all_jobs()
                return jsonify({
                    'jobs': jobs,
                    'total': len(jobs),
                    'status_counts': self._count_job_statuses(jobs)
                })
            except Exception as e:
                logger.error(f"Error getting queue jobs: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>')
        def api_queue_job_detail(job_id):
            """Get specific job details."""
            try:
                job_status = self.queue_manager.get_job_status(job_id)
                return jsonify(job_status)
            except Exception as e:
                logger.error(f"Error getting job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/reorder', methods=['POST'])
        def api_queue_reorder_job(job_id):
            """Reorder a job in the queue."""
            try:
                data = request.get_json()
                position = data.get('position', 0)
                success = self.queue_manager.reorder_job(job_id, position)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error reordering job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/stop', methods=['POST'])
        def api_queue_stop_job(job_id):
            """Stop a running job."""
            try:
                success = self.queue_manager.stop_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error stopping job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/pause', methods=['POST'])
        def api_queue_pause_job(job_id):
            """Pause a job."""
            try:
                success = self.queue_manager.pause_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error pausing job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/resume', methods=['POST'])
        def api_queue_resume_job(job_id):
            """Resume a paused job."""
            try:
                success = self.queue_manager.resume_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error resuming job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/remove', methods=['DELETE'])
        def api_queue_remove_job(job_id):
            """Remove a job from the queue."""
            try:
                success = self.queue_manager.remove_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error removing job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/celery/tasks')
        def api_celery_tasks():
            """Get Celery task statistics."""
            try:
                # Get Celery task stats
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                active = inspect.active()
                reserved = inspect.reserved()
                
                return jsonify({
                    'stats': stats,
                    'active': active,
                    'reserved': reserved,
                    'summary': self._summarize_celery_tasks(stats, active, reserved)
                })
            except Exception as e:
                logger.error(f"Error getting Celery tasks: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/celery/workers')
        def api_celery_workers():
            """Get Celery worker status."""
            try:
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                ping = inspect.ping()
                
                return jsonify({
                    'workers': stats,
                    'ping': ping,
                    'summary': self._summarize_celery_workers(stats, ping)
                })
            except Exception as e:
                logger.error(f"Error getting Celery workers: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/unified/tasks')
        def api_unified_tasks():
            """Get unified task view (RQ + Celery)."""
            try:
                # Get RQ jobs
                rq_jobs = self.queue_manager.get_all_jobs()
                
                # Get Celery tasks
                inspect = celery_app.control.inspect()
                celery_active = inspect.active() or {}
                celery_reserved = inspect.reserved() or {}
                
                # Combine into unified view
                unified_tasks = []
                
                # Add RQ jobs
                for job in rq_jobs:
                    unified_tasks.append({
                        'id': job['id'],
                        'type': 'rq',
                        'name': 'Transcription Job',
                        'status': job['status'],
                        'progress': job.get('progress', 0),
                        'created_at': job.get('created_at'),
                        'started_at': job.get('started_at'),
                        'ended_at': job.get('ended_at'),
                        'video_path': job.get('video_path', ''),
                        'worker': 'RQ Worker'
                    })
                
                # Add Celery tasks
                for worker, tasks in celery_active.items():
                    for task in tasks:
                        unified_tasks.append({
                            'id': task['id'],
                            'type': 'celery',
                            'name': task['name'],
                            'status': 'active',
                            'progress': 0,  # Celery doesn't provide progress
                            'created_at': task.get('time_start'),
                            'started_at': task.get('time_start'),
                            'ended_at': None,
                            'video_path': '',
                            'worker': worker
                        })
                
                for worker, tasks in celery_reserved.items():
                    for task in tasks:
                        unified_tasks.append({
                            'id': task['id'],
                            'type': 'celery',
                            'name': task['name'],
                            'status': 'reserved',
                            'progress': 0,
                            'created_at': task.get('time_start'),
                            'started_at': None,
                            'ended_at': None,
                            'video_path': '',
                            'worker': worker
                        })
                
                return jsonify({
                    'tasks': unified_tasks,
                    'summary': {
                        'total': len(unified_tasks),
                        'rq_count': len(rq_jobs),
                        'celery_active': sum(len(tasks) for tasks in celery_active.values()),
                        'celery_reserved': sum(len(tasks) for tasks in celery_reserved.values())
                    }
                })
            except Exception as e:
                logger.error(f"Error getting unified tasks: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _count_job_statuses(self, jobs: List[Dict]) -> Dict[str, int]:
        """Count jobs by status."""
        counts = {}
        for job in jobs:
            status = job.get('status', 'unknown')
            counts[status] = counts.get(status, 0) + 1
        return counts
    
    def _summarize_celery_tasks(self, stats: Dict, active: Dict, reserved: Dict) -> Dict[str, Any]:
        """Summarize Celery task statistics."""
        total_tasks = 0
        active_tasks = 0
        reserved_tasks = 0
        
        if stats:
            for worker_stats in stats.values():
                total_tasks += worker_stats.get('total', {})
        
        if active:
            for worker_tasks in active.values():
                active_tasks += len(worker_tasks)
        
        if reserved:
            for worker_tasks in reserved.values():
                reserved_tasks += len(worker_tasks)
        
        return {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'reserved_tasks': reserved_tasks,
            'worker_count': len(stats) if stats else 0
        }
    
    def _summarize_celery_workers(self, stats: Dict, ping: Dict) -> Dict[str, Any]:
        """Summarize Celery worker statistics."""
        if not stats:
            return {'active_workers': 0, 'total_workers': 0}
        
        active_workers = len(ping) if ping else 0
        total_workers = len(stats)
        
        return {
            'active_workers': active_workers,
            'total_workers': total_workers,
            'worker_status': 'healthy' if active_workers > 0 else 'unhealthy'
        }
    
    def _render_dashboard(self) -> str:
        """Render the integrated dashboard HTML."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integrated VOD Processing Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .nav-tabs {{
            display: flex;
            background: white;
            border-radius: 10px 10px 0 0;
            overflow: hidden;
            margin-bottom: 0;
        }}
        .nav-tab {{
            flex: 1;
            padding: 15px;
            text-align: center;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .nav-tab.active {{
            background: white;
            font-weight: bold;
        }}
        .nav-tab:hover {{
            background: #e9ecef;
        }}
        .tab-content {{
            background: white;
            padding: 20px;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-height: 600px;
        }}
        .tab-pane {{
            display: none;
        }}
        .tab-pane.active {{
            display: block;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .status-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .status-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-healthy {{ background-color: #28a745; }}
        .status-degraded {{ background-color: #ffc107; }}
        .status-unhealthy {{ background-color: #dc3545; }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .refresh-button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }}
        .refresh-button:hover {{
            background: #5a6fd8;
        }}
        .task-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .task-table th, .task-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .task-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .task-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .action-button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            margin: 2px;
            font-size: 12px;
        }}
        .action-button:hover {{
            background: #0056b3;
        }}
        .action-button.danger {{
            background: #dc3545;
        }}
        .action-button.danger:hover {{
            background: #c82333;
        }}
        .action-button.warning {{
            background: #ffc107;
            color: #333;
        }}
        .action-button.warning:hover {{
            background: #e0a800;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Integrated VOD Processing Monitor</h1>
            <p>Unified monitoring for VOD processing, queue management, and system health</p>
            <button class="refresh-button" onclick="refreshAllData()">🔄 Refresh All</button>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('overview')">📊 Overview</button>
            <button class="nav-tab" onclick="showTab('queue')">📋 Queue Management</button>
            <button class="nav-tab" onclick="showTab('celery')">⚡ Celery Tasks</button>
            <button class="nav-tab" onclick="showTab('health')">🏥 Health Checks</button>
            <button class="nav-tab" onclick="showTab('metrics')">📈 Metrics</button>
        </div>
        
        <div class="tab-content">
            <!-- Overview Tab -->
            <div id="overview" class="tab-pane active">
                <div class="status-grid">
                    <div class="status-card">
                        <h3>💻 System Health</h3>
                        <div id="system-health">Loading...</div>
                    </div>
                    <div class="status-card">
                        <h3>📋 Queue Status</h3>
                        <div id="queue-overview">Loading...</div>
                    </div>
                    <div class="status-card">
                        <h3>⚡ Celery Workers</h3>
                        <div id="celery-overview">Loading...</div>
                    </div>
                    <div class="status-card">
                        <h3>📈 Recent Activity</h3>
                        <div id="recent-activity">Loading...</div>
                    </div>
                </div>
            </div>
            
            <!-- Queue Management Tab -->
            <div id="queue" class="tab-pane">
                <h2>Queue Management</h2>
                <div id="queue-jobs">Loading...</div>
            </div>
            
            <!-- Celery Tasks Tab -->
            <div id="celery" class="tab-pane">
                <h2>Celery Task Management</h2>
                <div id="celery-tasks">Loading...</div>
            </div>
            
            <!-- Health Checks Tab -->
            <div id="health" class="tab-pane">
                <h2>System Health Checks</h2>
                <div id="health-checks">Loading...</div>
            </div>
            
            <!-- Metrics Tab -->
            <div id="metrics" class="tab-pane">
                <h2>Performance Metrics</h2>
                <div id="performance-metrics">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        let currentTab = 'overview';
        
        function showTab(tabName) {{
            // Hide all tab panes
            document.querySelectorAll('.tab-pane').forEach(pane => {{
                pane.classList.remove('active');
            }});
            
            // Remove active class from all tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Show selected tab pane
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to selected tab
            event.target.classList.add('active');
            
            currentTab = tabName;
            
            // Refresh data for the selected tab
            refreshTabData(tabName);
        }}
        
        function refreshAllData() {{
            refreshTabData(currentTab);
        }}
        
        function refreshTabData(tabName) {{
            switch(tabName) {{
                case 'overview':
                    refreshOverviewData();
                    break;
                case 'queue':
                    refreshQueueData();
                    break;
                case 'celery':
                    refreshCeleryData();
                    break;
                case 'health':
                    refreshHealthData();
                    break;
                case 'metrics':
                    refreshMetricsData();
                    break;
            }}
        }}
        
        function refreshOverviewData() {{
            // Load system health
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {{
                    updateSystemHealth(data);
                }});
            
            // Load queue overview
            fetch('/api/queue/jobs')
                .then(response => response.json())
                .then(data => {{
                    updateQueueOverview(data);
                }});
            
            // Load Celery overview
            fetch('/api/celery/workers')
                .then(response => response.json())
                .then(data => {{
                    updateCeleryOverview(data);
                }});
            
            // Load recent activity
            fetch('/api/unified/tasks')
                .then(response => response.json())
                .then(data => {{
                    updateRecentActivity(data);
                }});
        }}
        
        function refreshQueueData() {{
            fetch('/api/queue/jobs')
                .then(response => response.json())
                .then(data => {{
                    updateQueueJobs(data);
                }});
        }}
        
        function refreshCeleryData() {{
            fetch('/api/celery/tasks')
                .then(response => response.json())
                .then(data => {{
                    updateCeleryTasks(data);
                }});
        }}
        
        function refreshHealthData() {{
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {{
                    updateHealthChecks(data);
                }});
        }}
        
        function refreshMetricsData() {{
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {{
                    updatePerformanceMetrics(data);
                }});
        }}
        
        function updateSystemHealth(data) {{
            const div = document.getElementById('system-health');
            const overallStatus = data.overall_status || 'unknown';
            const statusClass = overallStatus === 'healthy' ? 'healthy' : 
                              overallStatus === 'degraded' ? 'degraded' : 'unhealthy';
            
            div.innerHTML = `
                <div><span class="status-indicator status-${{statusClass}}"></span>Overall: ${{overallStatus.toUpperCase()}}</div>
                <div>Checks: ${{data.total_checks || 0}}</div>
                <div>Healthy: ${{data.healthy_checks || 0}}</div>
                <div>Failed: ${{data.failed_checks || 0}}</div>
            `;
        }}
        
        function updateQueueOverview(data) {{
            const div = document.getElementById('queue-overview');
            const summary = data.summary || {{}};
            
            div.innerHTML = `
                <div class="metric-value">${{data.total || 0}}</div>
                <div class="metric-label">Total Jobs</div>
                <div>Queued: ${{summary.queued || 0}}</div>
                <div>Started: ${{summary.started || 0}}</div>
                <div>Finished: ${{summary.finished || 0}}</div>
                <div>Failed: ${{summary.failed || 0}}</div>
            `;
        }}
        
        function updateCeleryOverview(data) {{
            const div = document.getElementById('celery-overview');
            const summary = data.summary || {{}};
            
            div.innerHTML = `
                <div class="metric-value">${{summary.active_workers || 0}}</div>
                <div class="metric-label">Active Workers</div>
                <div>Total Workers: ${{summary.total_workers || 0}}</div>
                <div>Status: ${{summary.worker_status || 'unknown'}}</div>
            `;
        }}
        
        function updateRecentActivity(data) {{
            const div = document.getElementById('recent-activity');
            const tasks = data.tasks || [];
            const summary = data.summary || {{}};
            
            let html = `
                <div class="metric-value">${{summary.total || 0}}</div>
                <div class="metric-label">Total Tasks</div>
                <div>RQ Jobs: ${{summary.rq_count || 0}}</div>
                <div>Celery Active: ${{summary.celery_active || 0}}</div>
                <div>Celery Reserved: ${{summary.celery_reserved || 0}}</div>
            `;
            
            if (tasks.length > 0) {{
                html += '<div style="margin-top: 15px;"><strong>Recent Tasks:</strong></div>';
                tasks.slice(0, 5).forEach(task => {{
                    const statusClass = task.status === 'finished' ? 'healthy' : 
                                      task.status === 'failed' ? 'unhealthy' : 'degraded';
                    html += `
                        <div style="margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee;">
                            <div><strong>${{task.name}}</strong> (${{task.type}})</div>
                            <div>Status: <span class="status-indicator status-${{statusClass}}"></span>${{task.status}}</div>
                        </div>
                    `;
                }});
            }}
            
            div.innerHTML = html;
        }}
        
        function updateQueueJobs(data) {{
            const div = document.getElementById('queue-jobs');
            const jobs = data.jobs || [];
            
            if (jobs.length === 0) {{
                div.innerHTML = '<p>No jobs in queue</p>';
                return;
            }}
            
            let html = `
                <table class="task-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Status</th>
                            <th>Progress</th>
                            <th>Video Path</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            jobs.forEach(job => {{
                const statusClass = job.status === 'finished' ? 'healthy' : 
                                  job.status === 'failed' ? 'unhealthy' : 'degraded';
                const progress = job.progress || 0;
                
                html += `
                    <tr>
                        <td>${{job.id}}</td>
                        <td><span class="status-indicator status-${{statusClass}}"></span>${{job.status}}</td>
                        <td>${{progress}}%</td>
                        <td>${{job.video_path || 'N/A'}}</td>
                        <td>${{new Date(job.created_at).toLocaleString()}}</td>
                        <td>
                            ${{job.status === 'queued' ? '<button class="action-button" onclick="stopJob(\'' + job.id + '\')">Stop</button>' : ''}}
                            ${{job.status === 'started' ? '<button class="action-button warning" onclick="pauseJob(\'' + job.id + '\')">Pause</button>' : ''}}
                            ${{job.status === 'paused' ? '<button class="action-button" onclick="resumeJob(\'' + job.id + '\')">Resume</button>' : ''}}
                            <button class="action-button danger" onclick="removeJob(\'' + job.id + '\')">Remove</button>
                        </td>
                    </tr>
                `;
            }});
            
            html += '</tbody></table>';
            div.innerHTML = html;
        }}
        
        function updateCeleryTasks(data) {{
            const div = document.getElementById('celery-tasks');
            const summary = data.summary || {{}};
            
            let html = `
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">${{summary.total_tasks || 0}}</div>
                        <div class="metric-label">Total Tasks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${{summary.active_tasks || 0}}</div>
                        <div class="metric-label">Active Tasks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${{summary.reserved_tasks || 0}}</div>
                        <div class="metric-label">Reserved Tasks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${{summary.worker_count || 0}}</div>
                        <div class="metric-label">Workers</div>
                    </div>
                </div>
            `;
            
            if (data.active) {{
                html += '<h3>Active Tasks</h3>';
                Object.entries(data.active).forEach(([worker, tasks]) => {{
                    html += `<h4>Worker: ${{worker}}</h4>`;
                    if (tasks.length > 0) {{
                        html += '<table class="task-table"><thead><tr><th>Task ID</th><th>Name</th><th>Started</th></tr></thead><tbody>';
                        tasks.forEach(task => {{
                            html += `
                                <tr>
                                    <td>${{task.id}}</td>
                                    <td>${{task.name}}</td>
                                    <td>${{new Date(task.time_start * 1000).toLocaleString()}}</td>
                                </tr>
                            `;
                        }});
                        html += '</tbody></table>';
                    }} else {{
                        html += '<p>No active tasks</p>';
                    }}
                }});
            }}
            
            div.innerHTML = html;
        }}
        
        function updateHealthChecks(data) {{
            const div = document.getElementById('health-checks');
            const checks = data.checks || {{}};
            
            let html = '';
            Object.entries(checks).forEach(([category, categoryChecks]) => {{
                html += `<h3>${{category.charAt(0).toUpperCase() + category.slice(1)}} Health</h3>`;
                if (Array.isArray(categoryChecks)) {{
                    categoryChecks.forEach(check => {{
                        const statusClass = check.status === 'healthy' ? 'healthy' : 
                                          check.status === 'degraded' ? 'degraded' : 'unhealthy';
                        html += `
                            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                <div><strong>${{check.name}}</strong> <span class="status-indicator status-${{statusClass}}"></span>${{check.status}}</div>
                                <div>${{check.message || ''}}</div>
                                ${{check.details ? '<div><small>Details: ' + JSON.stringify(check.details) + '</small></div>' : ''}}
                            </div>
                        `;
                    }});
                }}
            }});
            
            div.innerHTML = html;
        }}
        
        function updatePerformanceMetrics(data) {{
            const div = document.getElementById('performance-metrics');
            
            let html = '<div class="metrics-grid">';
            Object.entries(data.counters || {{}}).forEach(([name, value]) => {{
                html += `
                    <div class="metric-card">
                        <div class="metric-value">${{value}}</div>
                        <div class="metric-label">${{name}}</div>
                    </div>
                `;
            }});
            html += '</div>';
            
            if (data.timers && Object.keys(data.timers).length > 0) {{
                html += '<h3>Performance Timers</h3><div class="metrics-grid">';
                Object.entries(data.timers).forEach(([name, stats]) => {{
                    html += `
                        <div class="metric-card">
                            <div class="metric-value">${{stats.avg ? stats.avg.toFixed(2) : 0}}ms</div>
                            <div class="metric-label">${{name}} (avg)</div>
                            <div>Min: ${{stats.min || 0}}ms</div>
                            <div>Max: ${{stats.max || 0}}ms</div>
                        </div>
                    `;
                }});
                html += '</div>';
            }}
            
            div.innerHTML = html;
        }}
        
        // Queue management functions
        function stopJob(jobId) {{
            fetch(`/api/queue/jobs/${{jobId}}/stop`, {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        refreshQueueData();
                    }} else {{
                        alert('Failed to stop job');
                    }}
                }});
        }}
        
        function pauseJob(jobId) {{
            fetch(`/api/queue/jobs/${{jobId}}/pause`, {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        refreshQueueData();
                    }} else {{
                        alert('Failed to pause job');
                    }}
                }});
        }}
        
        function resumeJob(jobId) {{
            fetch(`/api/queue/jobs/${{jobId}}/resume`, {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        refreshQueueData();
                    }} else {{
                        alert('Failed to resume job');
                    }}
                }});
        }}
        
        function removeJob(jobId) {{
            if (confirm('Are you sure you want to remove this job?')) {{
                fetch(`/api/queue/jobs/${{jobId}}/remove`, {{method: 'DELETE'}})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            refreshQueueData();
                        }} else {{
                            alert('Failed to remove job');
                        }}
                    }});
            }}
        }}
        
        // Initial load
        refreshOverviewData();
        
        // Auto-refresh every 30 seconds
        setInterval(() => refreshTabData(currentTab), 30000);
    </script>
</body>
</html>
        """
    
    def _start_background_collection(self):
        """Start background metrics collection."""
        def background_collector():
            while True:
                try:
                    # Collect metrics every 30 seconds
                    self.metrics_collector.collect_system_metrics()
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"Background metrics collection error: {e}")
                    time.sleep(60)
    
    def run(self):
        """Run the dashboard server."""
        logger.info(f"Starting integrated monitoring dashboard on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

def start_integrated_dashboard(host: str = "0.0.0.0", port: int = 5051):
    """Start the integrated monitoring dashboard."""
    dashboard = IntegratedDashboard(host, port)
    dashboard.run()

if __name__ == "__main__":
    start_integrated_dashboard() 
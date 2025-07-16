"""
Main Admin UI for VOD Processing System

This module provides the main administrative interface that embeds the monitoring
dashboard via iframe and provides additional administrative functions.
"""

from flask import Flask, render_template, jsonify, request, Blueprint
from flask_cors import CORS
import threading
import time
from datetime import datetime
from typing import Dict

from loguru import logger
from core.monitoring.integrated_dashboard import IntegratedDashboard
from core.task_queue import QueueManager
from core.tasks import celery_app
from core.config import MEMBER_CITIES

class AdminUI:
    """Main administrative interface for the VOD processing system."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080, dashboard_port: int = 5051):
        self.host = host
        self.port = port
        self.dashboard_port = dashboard_port
        self.app = Flask(__name__)
        self.queue_manager = QueueManager()
        
        # Enable CORS
        CORS(self.app)
        
        # Register routes
        self._register_routes()
        
        # Start embedded dashboard
        self._start_embedded_dashboard()
    
    def _register_routes(self):
        """Register all admin UI routes."""
        
        @self.app.route('/')
        def admin_dashboard():
            """Main admin dashboard with embedded monitoring."""
            return self._render_admin_dashboard()
        
        @self.app.route('/api/admin/status')
        def api_admin_status():
            """Get overall system status."""
            return jsonify(self._get_system_status())
        
        @self.app.route('/api/admin/cities')
        def api_admin_cities():
            """Get member cities information."""
            return jsonify({
                'cities': MEMBER_CITIES,
                'total': len(MEMBER_CITIES)
            })
        
        @self.app.route('/api/admin/queue/summary')
        def api_admin_queue_summary():
            """Get queue summary for admin view."""
            try:
                jobs = self.queue_manager.get_all_jobs()
                summary = {
                    'total_jobs': len(jobs),
                    'queued': len([j for j in jobs if j['status'] == 'queued']),
                    'started': len([j for j in jobs if j['status'] == 'started']),
                    'finished': len([j for j in jobs if j['status'] == 'finished']),
                    'failed': len([j for j in jobs if j['status'] == 'failed']),
                    'paused': len([j for j in jobs if j['status'] == 'paused'])
                }
                return jsonify(summary)
            except Exception as e:
                logger.error(f"Error getting queue summary: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/admin/celery/summary')
        def api_admin_celery_summary():
            """Get Celery summary for admin view."""
            try:
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                ping = inspect.ping()
                
                summary = {
                    'active_workers': len(ping) if ping else 0,
                    'total_workers': len(stats) if stats else 0,
                    'worker_status': 'healthy' if (ping and len(ping) > 0) else 'unhealthy'
                }
                return jsonify(summary)
            except Exception as e:
                logger.error(f"Error getting Celery summary: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/admin/tasks/trigger/<task_name>', methods=['POST'])
        def api_admin_trigger_task(task_name):
            """Trigger a specific Celery task."""
            try:
                data = request.get_json() or {}
                
                if task_name == 'process_recent_vods':
                    task = celery_app.send_task('vod_processing.process_recent_vods')
                elif task_name == 'cleanup_temp_files':
                    task = celery_app.send_task('vod_processing.cleanup_temp_files')
                elif task_name == 'check_captions':
                    task = celery_app.send_task('caption_checks.check_latest_vod_captions')
                else:
                    return jsonify({'error': f'Unknown task: {task_name}'}), 400
                
                return jsonify({
                    'success': True,
                    'task_id': task.id,
                    'task_name': task_name,
                    'message': f'Task {task_name} triggered successfully'
                })
            except Exception as e:
                logger.error(f"Error triggering task {task_name}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/admin/queue/cleanup', methods=['POST'])
        def api_admin_queue_cleanup():
            """Clean up failed jobs in the queue."""
            try:
                self.queue_manager.cleanup_failed_jobs()
                return jsonify({
                    'success': True,
                    'message': 'Failed jobs cleaned up successfully'
                })
            except Exception as e:
                logger.error(f"Error cleaning up queue: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Register unified queue routes
        try:
            from core.api.unified_queue_routes import register_unified_queue_routes
            register_unified_queue_routes(self.app)
            logger.info("Successfully registered unified queue routes in admin UI")
        except Exception as e:
            logger.error(f"Failed to register unified queue routes: {e}")
    
    def _render_admin_dashboard(self) -> str:
        """Render the main admin dashboard HTML with embedded monitoring."""
        dashboard_url = f"http://localhost:{self.dashboard_port}"
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VOD Processing System - Admin</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .admin-controls {{
            background: white;
            padding: 20px;
            margin: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .control-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .control-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .control-card h3 {{
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
        .action-button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            font-size: 14px;
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
        .action-button.success {{
            background: #28a745;
        }}
        .action-button.success:hover {{
            background: #218838;
        }}
        .dashboard-container {{
            margin: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .dashboard-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
        }}
        .dashboard-header h2 {{
            margin: 0;
            color: #333;
        }}
        .dashboard-iframe {{
            width: 100%;
            height: 800px;
            border: none;
            display: block;
        }}
        .refresh-button {{
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }}
        .refresh-button:hover {{
            background: #5a6268;
        }}
        .metric {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
            margin: 10px 0;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 VOD Processing System</h1>
        <p>Administrative Control Panel & Monitoring Dashboard</p>
    </div>
    
    <div class="admin-controls">
        <h2>🛠️ Administrative Controls</h2>
        <div class="control-grid">
            <div class="control-card">
                <h3>📋 Queue Management</h3>
                <div id="queue-status">Loading...</div>
                <div style="margin-top: 15px;">
                    <button class="action-button" onclick="refreshQueueStatus()">🔄 Refresh</button>
                    <button class="action-button danger" onclick="cleanupFailedJobs()">🧹 Cleanup Failed</button>
                </div>
            </div>
            
            <div class="control-card">
                <h3>⚡ Celery Workers</h3>
                <div id="celery-status">Loading...</div>
                <div style="margin-top: 15px;">
                    <button class="action-button" onclick="refreshCeleryStatus()">🔄 Refresh</button>
                </div>
            </div>
            
            <div class="control-card">
                <h3>🎯 Task Triggers</h3>
                <div style="margin-top: 15px;">
                    <button class="action-button success" onclick="triggerTask('process_recent_vods')">🚀 Process VODs</button>
                    <button class="action-button" onclick="triggerTask('check_captions')">📝 Check Captions</button>
                    <button class="action-button" onclick="triggerTask('cleanup_temp_files')">🧹 Cleanup Files</button>
                </div>
            </div>
            
            <div class="control-card">
                <h3>🏙️ Member Cities</h3>
                <div id="cities-info">Loading...</div>
                <div style="margin-top: 15px;">
                    <button class="action-button" onclick="refreshCitiesInfo()">🔄 Refresh</button>
                </div>
            </div>
        </div>
    </div>
    
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h2>📊 Real-Time Monitoring Dashboard</h2>
            <button class="refresh-button" onclick="refreshDashboard()">🔄 Refresh Dashboard</button>
        </div>
        <iframe 
            src="{dashboard_url}" 
            class="dashboard-iframe" 
            id="monitoring-dashboard"
            title="VOD Processing Monitoring Dashboard">
        </iframe>
    </div>

    <script>
        function refreshQueueStatus() {{
            fetch('/api/admin/queue/summary')
                .then(response => response.json())
                .then(data => {{
                    const div = document.getElementById('queue-status');
                    if (data.error) {{
                        div.innerHTML = `<span class="status-indicator status-unhealthy"></span>Error: ${{data.error}}`;
                        return;
                    }}
                    
                    const totalJobs = data.total_jobs || 0;
                    const failedJobs = data.failed || 0;
                    const statusClass = failedJobs === 0 ? 'healthy' : failedJobs < 3 ? 'degraded' : 'unhealthy';
                    
                    div.innerHTML = `
                        <div class="metric">${{totalJobs}}</div>
                        <div class="metric-label">Total Jobs</div>
                        <div><span class="status-indicator status-${{statusClass}}"></span>Status: ${{statusClass}}</div>
                        <div>Queued: ${{data.queued || 0}}</div>
                        <div>Started: ${{data.started || 0}}</div>
                        <div>Finished: ${{data.finished || 0}}</div>
                        <div>Failed: ${{data.failed || 0}}</div>
                        <div>Paused: ${{data.paused || 0}}</div>
                    `;
                }})
                .catch(error => {{
                    console.error('Error fetching queue status:', error);
                    document.getElementById('queue-status').innerHTML = 
                        '<span class="status-indicator status-unhealthy"></span>Connection Error';
                }});
        }}
        
        function refreshCeleryStatus() {{
            fetch('/api/admin/celery/summary')
                .then(response => response.json())
                .then(data => {{
                    const div = document.getElementById('celery-status');
                    if (data.error) {{
                        div.innerHTML = `<span class="status-indicator status-unhealthy"></span>Error: ${{data.error}}`;
                        return;
                    }}
                    
                    const activeWorkers = data.active_workers || 0;
                    const totalWorkers = data.total_workers || 0;
                    const statusClass = data.worker_status === 'healthy' ? 'healthy' : 'unhealthy';
                    
                    div.innerHTML = `
                        <div class="metric">${{activeWorkers}}</div>
                        <div class="metric-label">Active Workers</div>
                        <div>Total Workers: ${{totalWorkers}}</div>
                        <div><span class="status-indicator status-${{statusClass}}"></span>Status: ${{data.worker_status}}</div>
                    `;
                }})
                .catch(error => {{
                    console.error('Error fetching Celery status:', error);
                    document.getElementById('celery-status').innerHTML = 
                        '<span class="status-indicator status-unhealthy"></span>Connection Error';
                }});
        }}
        
        function refreshCitiesInfo() {{
            fetch('/api/admin/cities')
                .then(response => response.json())
                .then(data => {{
                    const div = document.getElementById('cities-info');
                    const cities = data.cities || [];
                    
                    div.innerHTML = `
                        <div class="metric">${{cities.length}}</div>
                        <div class="metric-label">Member Cities</div>
                        <div style="margin-top: 10px;">
                            ${{cities.slice(0, 3).map(city => `<div>${{city.name}}</div>`).join('')}}
                            ${{cities.length > 3 ? `<div>... and ${{cities.length - 3}} more</div>` : ''}}
                        </div>
                    `;
                }})
                .catch(error => {{
                    console.error('Error fetching cities info:', error);
                    document.getElementById('cities-info').innerHTML = 
                        '<span class="status-indicator status-unhealthy"></span>Connection Error';
                }});
        }}
        
        function triggerTask(taskName) {{
            fetch(`/api/admin/tasks/trigger/${{taskName}}`, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{}})
            }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        alert(`Task ${{taskName}} triggered successfully!\\nTask ID: ${{data.task_id}}`);
                        // Refresh status after triggering task
                        setTimeout(() => {{
                            refreshQueueStatus();
                            refreshCeleryStatus();
                        }}, 2000);
                    }} else {{
                        alert(`Failed to trigger task: ${{data.error}}`);
                    }}
                }})
                .catch(error => {{
                    console.error('Error triggering task:', error);
                    alert('Error triggering task. Check console for details.');
                }});
        }}
        
        function cleanupFailedJobs() {{
            if (confirm('Are you sure you want to clean up all failed jobs?')) {{
                fetch('/api/admin/queue/cleanup', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }}
                }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('Failed jobs cleaned up successfully!');
                            refreshQueueStatus();
                        }} else {{
                            alert(`Failed to cleanup jobs: ${{data.error}}`);
                        }}
                    }})
                    .catch(error => {{
                        console.error('Error cleaning up jobs:', error);
                        alert('Error cleaning up jobs. Check console for details.');
                    }});
            }}
        }}
        
        function refreshDashboard() {{
            const iframe = document.getElementById('monitoring-dashboard');
            iframe.src = iframe.src;
        }}
        
        // Initial load
        refreshQueueStatus();
        refreshCeleryStatus();
        refreshCitiesInfo();
        
        // Auto-refresh every 60 seconds
        setInterval(() => {{
            refreshQueueStatus();
            refreshCeleryStatus();
        }}, 60000);
    </script>
</body>
</html>
        """
    
    def _get_system_status(self) -> Dict:
        """Get overall system status."""
        try:
            # Get queue status
            queue_jobs = self.queue_manager.get_all_jobs()
            queue_summary = {
                'total_jobs': len(queue_jobs),
                'queued': len([j for j in queue_jobs if j['status'] == 'queued']),
                'started': len([j for j in queue_jobs if j['status'] == 'started']),
                'finished': len([j for j in queue_jobs if j['status'] == 'finished']),
                'failed': len([j for j in queue_jobs if j['status'] == 'failed']),
                'paused': len([j for j in queue_jobs if j['status'] == 'paused'])
            }
            
            # Get Celery status
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            ping = inspect.ping()
            
            celery_summary = {
                'active_workers': len(ping) if ping else 0,
                'total_workers': len(stats) if stats else 0,
                'worker_status': 'healthy' if (ping and len(ping) > 0) else 'unhealthy'
            }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'queue': queue_summary,
                'celery': celery_summary,
                'cities': {
                    'total': len(MEMBER_CITIES),
                    'cities': MEMBER_CITIES
                },
                'overall_status': 'healthy' if (celery_summary['worker_status'] == 'healthy' and queue_summary['failed'] == 0) else 'degraded'
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'overall_status': 'unhealthy'
            }
    
    def _start_embedded_dashboard(self):
        """Start the embedded monitoring dashboard in a separate thread."""
        def start_dashboard():
            try:
                dashboard = IntegratedDashboard(host="0.0.0.0", port=self.dashboard_port)
                dashboard.run()
            except Exception as e:
                logger.error(f"Failed to start embedded dashboard: {e}")
        
        # Start dashboard in background thread
        dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
        dashboard_thread.start()
        
        # Wait a moment for dashboard to start
        time.sleep(2)
        logger.info(f"Embedded monitoring dashboard started on port {self.dashboard_port}")
    
    def run(self):
        """Run the admin UI server."""
        logger.info(f"Starting admin UI on {self.host}:{self.port}")
        logger.info(f"Monitoring dashboard embedded at http://localhost:{self.dashboard_port}")
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

def start_admin_ui(host: str = "0.0.0.0", port: int = 8080, dashboard_port: int = 5051):
    """Start the main admin UI with embedded monitoring dashboard."""
    admin_ui = AdminUI(host, port, dashboard_port)
    admin_ui.run()

if __name__ == "__main__":
    start_admin_ui() 
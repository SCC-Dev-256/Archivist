#!/usr/bin/env python3
"""
VOD Processing System Monitoring Dashboard
Provides real-time monitoring of system components and tasks
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import redis
from flask import Flask, render_template, jsonify
from flask_cors import CORS

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)
CORS(app)

class SystemMonitor:
    """System monitoring and health checks"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
    def get_system_stats(self):
        """Get system resource statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_total_gb': memory.total / (1024**3),
                'disk_percent': disk.percent,
                'disk_used_gb': disk.used / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_redis_status(self):
        """Check Redis connection and stats"""
        try:
            info = self.redis_client.info()
            return {
                'status': 'connected',
                'version': info.get('redis_version', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_mb': info.get('used_memory_human', 'unknown'),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            return {'status': 'disconnected', 'error': str(e)}
    
    def get_celery_stats(self):
        """Get Celery worker and task statistics"""
        try:
            # Get active workers
            active_workers = self.redis_client.smembers('celery:workers')
            worker_count = len(active_workers)
            
            # Get task statistics
            task_stats = {}
            for key in self.redis_client.keys('celery:task-meta-*'):
                task_id = key.decode('utf-8').split(':')[-1]
                task_data = self.redis_client.get(key)
                if task_data:
                    task_info = json.loads(task_data)
                    status = task_info.get('status', 'unknown')
                    task_stats[status] = task_stats.get(status, 0) + 1
            
            return {
                'active_workers': worker_count,
                'task_stats': task_stats,
                'total_tasks': sum(task_stats.values())
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_flex_mount_status(self):
        """Check flex mount status and write access"""
        mounts = {
            'flex-1': '/mnt/flex-1',
            'flex-2': '/mnt/flex-2', 
            'flex-3': '/mnt/flex-3',
            'flex-4': '/mnt/flex-4',
            'flex-5': '/mnt/flex-5',
            'flex-6': '/mnt/flex-6',
            'flex-7': '/mnt/flex-7',
            'flex-8': '/mnt/flex-8',
            'flex-9': '/mnt/flex-9'
        }
        
        status = {}
        for name, path in mounts.items():
            try:
                # Check if mounted
                if os.path.ismount(path):
                    # Test write access
                    test_file = f"{path}/monitor_test_{int(time.time())}.txt"
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    
                    status[name] = {
                        'mounted': True,
                        'write_access': True,
                        'path': path
                    }
                else:
                    status[name] = {
                        'mounted': False,
                        'write_access': False,
                        'path': path
                    }
            except Exception as e:
                status[name] = {
                    'mounted': os.path.ismount(path),
                    'write_access': False,
                    'error': str(e),
                    'path': path
                }
        
        return status
    
    def get_cablecast_status(self):
        """Check Cablecast API connection"""
        try:
            from core.cablecast_client import CablecastAPIClient
            client = CablecastAPIClient()
            
            if client.test_connection():
                return {
                    'status': 'connected',
                    'last_check': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'failed',
                    'last_check': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def get_recent_tasks(self, limit=10):
        """Get recent Celery tasks"""
        try:
            tasks = []
            for key in self.redis_client.keys('celery:task-meta-*'):
                task_data = self.redis_client.get(key)
                if task_data:
                    task_info = json.loads(task_data)
                    tasks.append({
                        'id': task_info.get('task_id', 'unknown'),
                        'status': task_info.get('status', 'unknown'),
                        'result': task_info.get('result', ''),
                        'date_done': task_info.get('date_done', ''),
                        'name': task_info.get('name', 'unknown')
                    })
            
            # Sort by date_done and return recent ones
            tasks.sort(key=lambda x: x.get('date_done', ''), reverse=True)
            return tasks[:limit]
        except Exception as e:
            return {'error': str(e)}

# Initialize monitor
monitor = SystemMonitor()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Get comprehensive system status"""
    try:
        status = {
            'system': monitor.get_system_stats(),
            'redis': monitor.get_redis_status(),
            'celery': monitor.get_celery_stats(),
            'flex_mounts': monitor.get_flex_mount_status(),
            'cablecast': monitor.get_cablecast_status(),
            'recent_tasks': monitor.get_recent_tasks(),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system')
def get_system():
    """Get system statistics"""
    return jsonify(monitor.get_system_stats())

@app.route('/api/celery')
def get_celery():
    """Get Celery statistics"""
    return jsonify(monitor.get_celery_stats())

@app.route('/api/mounts')
def get_mounts():
    """Get flex mount status"""
    return jsonify(monitor.get_flex_mount_status())

@app.route('/api/tasks')
def get_tasks():
    """Get recent tasks"""
    return jsonify(monitor.get_recent_tasks())

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Create dashboard template
    dashboard_template = templates_dir / 'dashboard.html'
    if not dashboard_template.exists():
        with open(dashboard_template, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VOD Processing System Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #333; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status { padding: 5px 10px; border-radius: 4px; color: white; font-weight: bold; }
        .status.ok { background: #28a745; }
        .status.error { background: #dc3545; }
        .status.warning { background: #ffc107; color: #333; }
        .metric { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 VOD Processing System Monitor</h1>
            <p>Real-time system status and performance metrics</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>💻 System Resources</h3>
                <div id="system-stats">Loading...</div>
            </div>
            
            <div class="card">
                <h3>🔴 Redis Status</h3>
                <div id="redis-status">Loading...</div>
            </div>
            
            <div class="card">
                <h3>⚡ Celery Workers</h3>
                <div id="celery-status">Loading...</div>
            </div>
            
            <div class="card">
                <h3>📡 Cablecast API</h3>
                <div id="cablecast-status">Loading...</div>
            </div>
            
            <div class="card">
                <h3>💾 Flex Mounts</h3>
                <div id="mounts-status">Loading...</div>
            </div>
            
            <div class="card">
                <h3>📋 Recent Tasks</h3>
                <div id="tasks-list">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateSystemStats(data.system);
                    updateRedisStatus(data.redis);
                    updateCeleryStatus(data.celery);
                    updateCablecastStatus(data.cablecast);
                    updateMountsStatus(data.flex_mounts);
                    updateTasksList(data.recent_tasks);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                    document.body.innerHTML += '<div style="color: red; padding: 20px;">Error loading data</div>';
                });
        }

        function updateSystemStats(stats) {
            const div = document.getElementById('system-stats');
            if (stats.error) {
                div.innerHTML = `<span class="status error">Error: ${stats.error}</span>`;
                return;
            }
            
            div.innerHTML = `
                <div class="metric">${stats.cpu_percent}%</div>
                <div>CPU Usage</div>
                <div class="metric">${stats.memory_percent}%</div>
                <div>Memory Usage (${stats.memory_used_gb.toFixed(1)}GB / ${stats.memory_total_gb.toFixed(1)}GB)</div>
                <div class="metric">${stats.disk_percent}%</div>
                <div>Disk Usage (${stats.disk_used_gb.toFixed(1)}GB / ${stats.disk_total_gb.toFixed(1)}GB)</div>
            `;
        }

        function updateRedisStatus(status) {
            const div = document.getElementById('redis-status');
            if (status.status === 'connected') {
                div.innerHTML = `
                    <span class="status ok">Connected</span>
                    <div>Version: ${status.version}</div>
                    <div>Clients: ${status.connected_clients}</div>
                    <div>Memory: ${status.used_memory_mb}</div>
                    <div>Uptime: ${Math.floor(status.uptime_seconds / 3600)}h</div>
                `;
            } else {
                div.innerHTML = `<span class="status error">Disconnected</span>`;
            }
        }

        function updateCeleryStatus(status) {
            const div = document.getElementById('celery-status');
            if (status.error) {
                div.innerHTML = `<span class="status error">Error: ${status.error}</span>`;
                return;
            }
            
            const taskStats = Object.entries(status.task_stats || {})
                .map(([status, count]) => `${status}: ${count}`)
                .join('<br>');
            
            div.innerHTML = `
                <div class="metric">${status.active_workers}</div>
                <div>Active Workers</div>
                <div class="metric">${status.total_tasks}</div>
                <div>Total Tasks</div>
                <div><strong>Task Status:</strong></div>
                <div>${taskStats}</div>
            `;
        }

        function updateCablecastStatus(status) {
            const div = document.getElementById('cablecast-status');
            if (status.status === 'connected') {
                div.innerHTML = `<span class="status ok">Connected</span>`;
            } else {
                div.innerHTML = `<span class="status error">Disconnected</span>`;
            }
        }

        function updateMountsStatus(mounts) {
            const div = document.getElementById('mounts-status');
            let html = '';
            
            Object.entries(mounts).forEach(([name, mount]) => {
                const statusClass = mount.mounted && mount.write_access ? 'ok' : 
                                  mount.mounted ? 'warning' : 'error';
                const statusText = mount.mounted && mount.write_access ? 'OK' :
                                 mount.mounted ? 'Read Only' : 'Not Mounted';
                
                html += `
                    <div style="margin: 5px 0;">
                        <strong>${name}:</strong> 
                        <span class="status ${statusClass}">${statusText}</span>
                    </div>
                `;
            });
            
            div.innerHTML = html;
        }

        function updateTasksList(tasks) {
            const div = document.getElementById('tasks-list');
            if (tasks.error) {
                div.innerHTML = `<span class="status error">Error: ${tasks.error}</span>`;
                return;
            }
            
            if (tasks.length === 0) {
                div.innerHTML = '<div>No recent tasks</div>';
                return;
            }
            
            let html = '';
            tasks.slice(0, 5).forEach(task => {
                const statusClass = task.status === 'SUCCESS' ? 'ok' : 
                                  task.status === 'FAILURE' ? 'error' : 'warning';
                html += `
                    <div style="margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee;">
                        <div><strong>${task.name}</strong></div>
                        <div>ID: ${task.id}</div>
                        <div>Status: <span class="status ${statusClass}">${task.status}</span></div>
                    </div>
                `;
            });
            
            div.innerHTML = html;
        }

        // Initial load
        refreshData();
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
            ''')
    
    print("🚀 Starting VOD Processing System Monitor...")
    print("📊 Dashboard available at: http://localhost:5051")
    print("📡 API endpoints:")
    print("   - /api/status - Complete system status")
    print("   - /api/system - System resources")
    print("   - /api/celery - Celery statistics")
    print("   - /api/mounts - Flex mount status")
    print("   - /api/tasks - Recent tasks")
    
    app.run(host='0.0.0.0', port=5051, debug=False) 
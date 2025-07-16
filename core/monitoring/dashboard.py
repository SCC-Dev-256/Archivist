"""
VOD Processing Monitoring Dashboard

This module provides a comprehensive web-based monitoring dashboard for the VOD processing system,
including real-time metrics, health checks, and error rate visibility.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading

from loguru import logger
from core.monitoring.metrics import get_metrics_collector
from core.monitoring.health_checks import get_health_manager

class MonitoringDashboard:
    """Comprehensive monitoring dashboard for VOD processing."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.metrics_collector = get_metrics_collector()
        self.health_manager = get_health_manager()
        
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
        
        @self.app.route('/api/metrics/summary')
        def api_metrics_summary():
            """Get metrics summary for the last hour."""
            time_window = request.args.get('window', 3600, type=int)
            return jsonify(self.metrics_collector.get_metrics_summary(time_window))
        
        @self.app.route('/api/circuit-breakers')
        def api_circuit_breakers():
            """Get circuit breaker status."""
            return jsonify(self.metrics_collector.get_circuit_breaker_status())
        
        @self.app.route('/api/health/storage')
        def api_storage_health():
            """Get storage health status."""
            health_status = self.health_manager.get_health_status()
            storage_checks = health_status.get('checks', {}).get('storage', [])
            return jsonify({
                'storage_checks': storage_checks,
                'summary': self._summarize_storage_health(storage_checks)
            })
        
        @self.app.route('/api/health/api')
        def api_api_health():
            """Get API health status."""
            health_status = self.health_manager.get_health_status()
            api_checks = health_status.get('checks', {}).get('api', [])
            return jsonify({
                'api_checks': api_checks,
                'summary': self._summarize_api_health(api_checks)
            })
        
        @self.app.route('/api/health/system')
        def api_system_health():
            """Get system health status."""
            health_status = self.health_manager.get_health_status()
            system_checks = health_status.get('checks', {}).get('system', [])
            return jsonify({
                'system_checks': system_checks,
                'summary': self._summarize_system_health(system_checks)
            })
    
    def _render_dashboard(self) -> str:
        """Render the main dashboard HTML."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VOD Processing Monitor</title>
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
            max-width: 1400px;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 VOD Processing Monitor</h1>
            <p>Real-time monitoring and health checks for the VOD processing system</p>
        </div>
        
        <button class="refresh-button" onclick="refreshAll()">🔄 Refresh All Data</button>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>Overall System Status</h3>
                <div id="overall-status">Loading...</div>
            </div>
            <div class="status-card">
                <h3>Storage Health</h3>
                <div id="storage-status">Loading...</div>
            </div>
            <div class="status-card">
                <h3>API Health</h3>
                <div id="api-status">Loading...</div>
            </div>
            <div class="status-card">
                <h3>System Resources</h3>
                <div id="system-status">Loading...</div>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="error-rate">-</div>
                <div class="metric-label">Error Rate (%)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="retry-success-rate">-</div>
                <div class="metric-label">Retry Success Rate (%)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="active-tasks">-</div>
                <div class="metric-label">Active Tasks</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="queue-size">-</div>
                <div class="metric-label">Queue Size</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="processing-total">-</div>
                <div class="metric-label">Total Processing</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="processing-success">-</div>
                <div class="metric-label">Successful Processing</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>Processing Performance</h3>
            <canvas id="performanceChart" width="400" height="200"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>Error Rate Over Time</h3>
            <canvas id="errorChart" width="400" height="200"></canvas>
        </div>
    </div>

    <script>
        let performanceChart, errorChart;
        
        function updateStatusIndicator(status, elementId) {{
            const element = document.getElementById(elementId);
            const statusClass = status === 'healthy' ? 'status-healthy' : 
                              status === 'degraded' ? 'status-degraded' : 'status-unhealthy';
            element.innerHTML = '<span class="status-indicator ' + statusClass + '"></span>' + status.toUpperCase();
        }}
        
        function updateMetrics(metrics) {{
            document.getElementById('error-rate').textContent = 
                metrics.error_rate ? metrics.error_rate.toFixed(1) : '0.0';
            document.getElementById('retry-success-rate').textContent = 
                metrics.retry_success_rate ? metrics.retry_success_rate.toFixed(1) : '0.0';
            document.getElementById('active-tasks').textContent = 
                metrics.active_tasks || '0';
            document.getElementById('queue-size').textContent = 
                metrics.queue_size || '0';
            document.getElementById('processing-total').textContent = 
                metrics.vod_processing_total || '0';
            document.getElementById('processing-success').textContent = 
                metrics.vod_processing_success || '0';
        }}
        
        function updateHealthStatus(healthData) {{
            updateStatusIndicator(healthData.overall_status, 'overall-status');
            
            // Update storage status
            const storageChecks = healthData.checks.storage || [];
            const storageHealthy = storageChecks.filter(c => c.status === 'healthy').length;
            const storageTotal = storageChecks.length;
            updateStatusIndicator(
                storageHealthy === storageTotal ? 'healthy' : 
                storageHealthy > 0 ? 'degraded' : 'unhealthy',
                'storage-status'
            );
            
            // Update API status
            const apiChecks = healthData.checks.api || [];
            const apiStatus = apiChecks.length > 0 ? apiChecks[0].status : 'unhealthy';
            updateStatusIndicator(apiStatus, 'api-status');
            
            // Update system status
            const systemChecks = healthData.checks.system || [];
            const systemHealthy = systemChecks.filter(c => c.status === 'healthy').length;
            const systemTotal = systemChecks.length;
            updateStatusIndicator(
                systemHealthy === systemTotal ? 'healthy' : 
                systemHealthy > 0 ? 'degraded' : 'unhealthy',
                'system-status'
            );
        }}
        
        function updateCharts(metrics) {{
            const now = new Date();
            
            // Performance chart
            if (!performanceChart) {{
                const ctx = document.getElementById('performanceChart').getContext('2d');
                performanceChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: [],
                        datasets: [{{
                            label: 'Processing Duration (s)',
                            data: [],
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true
                            }}
                        }}
                    }}
                }});
            }}
            
            // Error rate chart
            if (!errorChart) {{
                const ctx = document.getElementById('errorChart').getContext('2d');
                errorChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: [],
                        datasets: [{{
                            label: 'Error Rate (%)',
                            data: [],
                            borderColor: '#dc3545',
                            backgroundColor: 'rgba(220, 53, 69, 0.1)',
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 100
                            }}
                        }}
                    }}
                }});
            }}
            
            // Update chart data
            if (metrics.processing_duration && metrics.processing_duration.avg) {{
                performanceChart.data.labels.push(now.toLocaleTimeString());
                performanceChart.data.datasets[0].data.push(metrics.processing_duration.avg);
                
                if (performanceChart.data.labels.length > 20) {{
                    performanceChart.data.labels.shift();
                    performanceChart.data.datasets[0].data.shift();
                }}
                performanceChart.update();
            }}
            
            if (metrics.error_rate !== undefined) {{
                errorChart.data.labels.push(now.toLocaleTimeString());
                errorChart.data.datasets[0].data.push(metrics.error_rate);
                
                if (errorChart.data.labels.length > 20) {{
                    errorChart.data.labels.shift();
                    errorChart.data.datasets[0].data.shift();
                }}
                errorChart.update();
            }}
        }}
        
        async function refreshMetrics() {{
            try {{
                const response = await fetch('/api/metrics/summary');
                const metrics = await response.json();
                updateMetrics(metrics);
                updateCharts(metrics);
            }} catch (error) {{
                console.error('Failed to fetch metrics:', error);
            }}
        }}
        
        async function refreshHealth() {{
            try {{
                const response = await fetch('/api/health');
                const healthData = await response.json();
                updateHealthStatus(healthData);
            }} catch (error) {{
                console.error('Failed to fetch health data:', error);
            }}
        }}
        
        function refreshAll() {{
            refreshMetrics();
            refreshHealth();
        }}
        
        // Initial load
        refreshAll();
        
        // Auto-refresh every 30 seconds
        setInterval(refreshAll, 30000);
    </script>
</body>
</html>
        """
    
    def _summarize_storage_health(self, storage_checks: List[Dict]) -> Dict[str, Any]:
        """Summarize storage health status."""
        healthy = sum(1 for check in storage_checks if check['status'] == 'healthy')
        degraded = sum(1 for check in storage_checks if check['status'] == 'degraded')
        unhealthy = sum(1 for check in storage_checks if check['status'] == 'unhealthy')
        
        return {
            'total': len(storage_checks),
            'healthy': healthy,
            'degraded': degraded,
            'unhealthy': unhealthy,
            'overall_status': 'healthy' if unhealthy == 0 else 'degraded' if degraded > 0 else 'unhealthy'
        }
    
    def _summarize_api_health(self, api_checks: List[Dict]) -> Dict[str, Any]:
        """Summarize API health status."""
        if not api_checks:
            return {'overall_status': 'unhealthy', 'message': 'No API checks available'}
        
        check = api_checks[0]
        return {
            'overall_status': check['status'],
            'response_time': check.get('response_time'),
            'message': check['message']
        }
    
    def _summarize_system_health(self, system_checks: List[Dict]) -> Dict[str, Any]:
        """Summarize system health status."""
        healthy = sum(1 for check in system_checks if check['status'] == 'healthy')
        degraded = sum(1 for check in system_checks if check['status'] == 'degraded')
        unhealthy = sum(1 for check in system_checks if check['status'] == 'unhealthy')
        
        return {
            'total': len(system_checks),
            'healthy': healthy,
            'degraded': degraded,
            'unhealthy': unhealthy,
            'overall_status': 'healthy' if unhealthy == 0 else 'degraded' if degraded > 0 else 'unhealthy'
        }
    
    def _start_background_collection(self):
        """Start background metrics collection."""
        def background_collector():
            while True:
                try:
                    # Update queue size metric
                    # This would typically come from Celery inspection
                    self.metrics_collector.gauge("queue_size", 0)  # Placeholder
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    logger.error(f"Background metrics collection error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        thread = threading.Thread(target=background_collector, daemon=True)
        thread.start()
    
    def run(self):
        """Start the monitoring dashboard."""
        logger.info(f"Starting monitoring dashboard on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=False)

def start_monitoring_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Start the monitoring dashboard."""
    dashboard = MonitoringDashboard(host, port)
    dashboard.run()

if __name__ == "__main__":
    start_monitoring_dashboard() 
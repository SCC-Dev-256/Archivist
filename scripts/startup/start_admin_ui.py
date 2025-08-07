#!/usr/bin/env python3
"""
Simplified Admin UI Starter

This script starts the admin UI with proper error handling and fallbacks.
"""

import os
import sys
import traceback
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Check if all required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    missing_deps = []
    
    try:
        from flask import Flask
        print("  ✓ Flask")
    except ImportError:
        missing_deps.append("flask")
        print("  ❌ Flask")
    
    try:
        from flask_cors import CORS
        print("  ✓ Flask-CORS")
    except ImportError:
        missing_deps.append("flask-cors")
        print("  ❌ Flask-CORS")
    
    try:
        from loguru import logger
        print("  ✓ Loguru")
    except ImportError:
        missing_deps.append("loguru")
        print("  ❌ Loguru")
    
    try:
        from core.tasks import celery_app
        print("  ✓ Celery app")
    except ImportError as e:
        print(f"  ⚠️  Celery app: {e}")
    
    try:
        from core.config import MEMBER_CITIES
        print("  ✓ Config")
    except ImportError as e:
        print(f"  ⚠️  Config: {e}")
    
    if missing_deps:
        print(f"\n❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install " + " ".join(missing_deps))
        return False
    
    return True

def create_simple_admin_ui():
    """Create a simple admin UI that works without complex dependencies."""
    from flask import Flask, jsonify, render_template_string
    from flask_cors import CORS
    from loguru import logger
    
    app = Flask(__name__)
    CORS(app)
    
    @app.route("/")
    def admin_dashboard():
        """Simple admin dashboard."""
        return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VOD Processing System - Admin</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .status-ok { background: #28a745; }
        .status-error { background: #dc3545; }
        .status-warning { background: #ffc107; }
        .button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        .button:hover { background: #0056b3; }
        .metric { font-size: 24px; font-weight: bold; color: #007bff; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 VOD Processing System - Admin Panel</h1>
        <p>Simplified Administrative Interface</p>
    </div>
    
    <div class="card">
        <h2>📊 System Status</h2>
        <div id="system-status">Loading...</div>
        <button class="button" onclick="refreshStatus()">🔄 Refresh</button>
    </div>
    
    <div class="card">
        <h2>🎯 Quick Actions</h2>
        <button class="button" onclick="testTranscription()">🧪 Test Transcription</button>
        <button class="button" onclick="checkWorkers()">👥 Check Workers</button>
        <button class="button" onclick="viewLogs()">📋 View Logs</button>
    </div>
    
    <div class="card">
        <h2>📝 Debug Information</h2>
        <div id="debug-info">Loading...</div>
    </div>

    <script>
        function refreshStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const div = document.getElementById('system-status');
                    div.innerHTML = `
                        <div class="metric">${data.workers || 0}</div>
                        <div>Active Workers</div>
                        <div><span class="status status-${data.status === 'ok' ? 'ok' : 'error'}"></span>${data.status}</div>
                        <div>Last Check: ${data.timestamp}</div>
                    `;
                })
                .catch(error => {
                    document.getElementById('system-status').innerHTML = 
                        '<span class="status status-error"></span>Connection Error';
                });
        }
        
        function testTranscription() {
            fetch('/api/test-transcription', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                })
                .catch(error => {
                    alert('Error testing transcription: ' + error);
                });
        }
        
        function checkWorkers() {
            fetch('/api/workers')
                .then(response => response.json())
                .then(data => {
                    alert(`Workers: ${data.workers}\\nStatus: ${data.status}`);
                })
                .catch(error => {
                    alert('Error checking workers: ' + error);
                });
        }
        
        function viewLogs() {
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    const logText = data.logs.join('\\n');
                    const newWindow = window.open('', '_blank');
                    newWindow.document.write('<pre>' + logText + '</pre>');
                })
                .catch(error => {
                    alert('Error viewing logs: ' + error);
                });
        }
        
        // Initial load
        refreshStatus();
        loadDebugInfo();
        
        function loadDebugInfo() {
            fetch('/api/debug')
                .then(response => response.json())
                .then(data => {
                    const div = document.getElementById('debug-info');
                    div.innerHTML = `
                        <div><strong>Python Version:</strong> ${data.python_version}</div>
                        <div><strong>Working Directory:</strong> ${data.working_dir}</div>
                        <div><strong>Environment:</strong> ${data.environment}</div>
                        <div><strong>Available Modules:</strong> ${data.available_modules.join(', ')}</div>
                    `;
                })
                .catch(error => {
                    document.getElementById('debug-info').innerHTML = 'Error loading debug info';
                });
        }
    </script>
</body>
</html>
        """)
    
    @app.route("/api/status")
    def api_status():
        """Get basic system status."""
        try:
            # Try to get Celery status
            try:
                from core.tasks import celery_app
                inspect = celery_app.control.inspect()
                ping = inspect.ping()
                workers = len(ping) if ping else 0
                status = "ok" if workers > 0 else "no_workers"
            except Exception as e:
                workers = 0
                status = f"error: {str(e)}"
            
            return jsonify({
                "workers": workers,
                "status": status,
                "timestamp": "2025-08-05T17:45:00Z"
            })
        except Exception as e:
            return jsonify({
                "workers": 0,
                "status": f"error: {str(e)}",
                "timestamp": "2025-08-05T17:45:00Z"
            })
    
    @app.route("/api/test-transcription", methods=["POST"])
    def api_test_transcription():
        """Test transcription functionality."""
        try:
            # Import and test transcription
            from core.transcription import _transcribe_with_faster_whisper
            
            test_video = "/mnt/flex-1/14204-1-Birchwood Special Council Meeting (20190325).mpeg"
            
            if not os.path.exists(test_video):
                return jsonify({
                    "success": False,
                    "message": f"Test video not found: {test_video}"
                })
            
            # Test transcription
            result = _transcribe_with_faster_whisper(test_video)
            
            return jsonify({
                "success": True,
                "message": f"Transcription test completed. Status: {result.get('status', 'unknown')}",
                "result": result
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Transcription test failed: {str(e)}"
            })
    
    @app.route("/api/workers")
    def api_workers():
        """Get worker status."""
        try:
            from core.tasks import celery_app
            inspect = celery_app.control.inspect()
            ping = inspect.ping()
            workers = len(ping) if ping else 0
            
            return jsonify({
                "workers": workers,
                "status": "ok" if workers > 0 else "no_workers"
            })
        except Exception as e:
            return jsonify({
                "workers": 0,
                "status": f"error: {str(e)}"
            })
    
    @app.route("/api/logs")
    def api_logs():
        """Get recent logs."""
        try:
            log_file = "/opt/Archivist/logs/archivist.log"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Get last 50 lines
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    return jsonify({"logs": recent_lines})
            else:
                return jsonify({"logs": ["Log file not found"]})
        except Exception as e:
            return jsonify({"logs": [f"Error reading logs: {str(e)}"]})
    
    @app.route("/api/debug")
    def api_debug():
        """Get debug information."""
        import sys
        
        available_modules = []
        for module in ['faster_whisper', 'core.transcription', 'core.tasks', 'flask', 'celery']:
            try:
                __import__(module)
                available_modules.append(module)
            except ImportError:
                pass
        
        return jsonify({
            "python_version": sys.version,
            "working_dir": os.getcwd(),
            "environment": os.environ.get('FLASK_ENV', 'production'),
            "available_modules": available_modules
        })
    
    return app

def main():
    """Start the admin UI."""
    print("🚀 Starting Admin UI...")
    
    if not check_dependencies():
        print("❌ Cannot start admin UI due to missing dependencies")
        return
    
    try:
        app = create_simple_admin_ui()
        
        host = "0.0.0.0"
        port = 8080
        
        print(f"✅ Starting admin UI on {host}:{port}")
        print(f"🌐 Access at: http://localhost:{port}")
        
        app.run(host=host, port=port, debug=False, threaded=True)
        
    except Exception as e:
        print(f"❌ Failed to start admin UI: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 
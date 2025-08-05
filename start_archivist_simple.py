#!/usr/bin/env python3
"""
Simple Archivist Startup Script

This script starts the Archivist system with minimal health checks,
focusing on getting the services running quickly and reliably.
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path

def print_status(message, color="\033[0m"):
    """Print a status message with color."""
    print(f"{color}{message}\033[0m")

def check_port(port):
    """Check if a port is in use."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return False
    except OSError:
        return True

def start_celery_worker():
    """Start Celery worker."""
    print_status("🚀 Starting Celery worker...", "\033[34m")
    
    cmd = [
        "celery", "-A", "core.tasks", "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--hostname=vod_worker@%h",
        "--queues=vod_processing,default"
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path.cwd()
    )
    
    # Wait a moment for startup
    time.sleep(3)
    
    if process.poll() is None:
        print_status("✅ Celery worker started", "\033[32m")
        return process
    else:
        print_status("❌ Celery worker failed to start", "\033[31m")
        return None

def start_celery_beat():
    """Start Celery beat scheduler."""
    print_status("⏰ Starting Celery beat scheduler...", "\033[34m")
    
    cmd = [
        "celery", "-A", "core.tasks", "beat",
        "--loglevel=info",
        "--scheduler=celery.beat.PersistentScheduler"
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path.cwd()
    )
    
    # Wait a moment for startup
    time.sleep(2)
    
    if process.poll() is None:
        print_status("✅ Celery beat scheduler started", "\033[32m")
        return process
    else:
        print_status("❌ Celery beat scheduler failed to start", "\033[31m")
        return None

def start_admin_ui():
    """Start Admin UI."""
    print_status("🌐 Starting Admin UI...", "\033[34m")
    
    def run_admin_ui():
        try:
            from core.admin_ui import start_admin_ui
            start_admin_ui(host="0.0.0.0", port=8080, dashboard_port=5051)
        except Exception as e:
            print_status(f"❌ Admin UI error: {e}", "\033[31m")
    
    thread = threading.Thread(target=run_admin_ui, daemon=True)
    thread.start()
    
    # Wait for admin UI to start
    for attempt in range(30):
        time.sleep(1)
        if check_port(8080):
            print_status("✅ Admin UI started", "\033[32m")
            return thread
    
    print_status("❌ Admin UI failed to start", "\033[31m")
    return None

def start_monitoring_dashboard():
    """Start monitoring dashboard."""
    print_status("📊 Starting monitoring dashboard...", "\033[34m")
    
    def run_dashboard():
        try:
            from core.monitoring.integrated_dashboard import start_integrated_dashboard
            start_integrated_dashboard(port=5051)
        except Exception as e:
            print_status(f"❌ Dashboard error: {e}", "\033[31m")
    
    thread = threading.Thread(target=run_dashboard, daemon=True)
    thread.start()
    
    # Wait for dashboard to start
    for attempt in range(30):
        time.sleep(1)
        if check_port(5051):
            print_status("✅ Monitoring dashboard started", "\033[32m")
            return thread
    
    print_status("❌ Monitoring dashboard failed to start", "\033[31m")
    return None

def main():
    """Main startup function."""
    print_status("🚀 Simple Archivist Startup", "\033[1;36m")
    print_status("=" * 50, "\033[1;36m")
    
    # Check if we're in the right directory
    if not Path("core/tasks/__init__.py").exists():
        print_status("❌ Not in Archivist project directory", "\033[31m")
        sys.exit(1)
    
    # Check if Redis is running
    try:
        result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True)
        if result.returncode != 0:
            print_status("❌ Redis is not running", "\033[31m")
            sys.exit(1)
        print_status("✅ Redis is running", "\033[32m")
    except Exception:
        print_status("❌ Cannot connect to Redis", "\033[31m")
        sys.exit(1)
    
    # Check if PostgreSQL is running
    try:
        result = subprocess.run(['pg_isready'], capture_output=True, text=True)
        if result.returncode != 0:
            print_status("❌ PostgreSQL is not running", "\033[31m")
            sys.exit(1)
        print_status("✅ PostgreSQL is running", "\033[32m")
    except Exception:
        print_status("❌ Cannot connect to PostgreSQL", "\033[31m")
        sys.exit(1)
    
    # Start services
    processes = []
    threads = []
    
    # Start Celery worker
    worker_process = start_celery_worker()
    if worker_process:
        processes.append(worker_process)
    
    # Start Celery beat
    beat_process = start_celery_beat()
    if beat_process:
        processes.append(beat_process)
    
    # Start Admin UI
    admin_thread = start_admin_ui()
    if admin_thread:
        threads.append(admin_thread)
    
    # Start monitoring dashboard
    dashboard_thread = start_monitoring_dashboard()
    if dashboard_thread:
        threads.append(dashboard_thread)
    
    # Print status
    print_status("\n🎉 Archivist System Started!", "\033[1;32m")
    print_status("=" * 50, "\033[1;32m")
    print_status("📊 Admin UI: http://0.0.0.0:8080", "\033[32m")
    print_status("📈 Monitoring Dashboard: http://localhost:5051", "\033[32m")
    print_status("📚 API Documentation: http://0.0.0.0:8080/api/docs", "\033[32m")
    print_status("🔄 Celery Workers: 4 concurrent workers active", "\033[32m")
    print_status("⏰ Scheduled Tasks: Daily caption check, VOD processing", "\033[32m")
    print_status("=" * 50, "\033[1;32m")
    
    # Keep the script running
    try:
        while True:
            time.sleep(10)
            # Check if any processes have died
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    print_status(f"⚠️ Process {i} has stopped", "\033[33m")
    except KeyboardInterrupt:
        print_status("\n🛑 Shutting down...", "\033[33m")
        
        # Stop processes
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        
        print_status("✅ Shutdown complete", "\033[32m")

if __name__ == "__main__":
    main() 
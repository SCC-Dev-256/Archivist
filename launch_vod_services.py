#!/usr/bin/env python3
"""
VOD Services Launcher

This script launches all required services for VOD system testing:
1. Redis (if not running)
2. Admin UI Flask server
3. Celery worker
4. Celery beat scheduler
5. Monitoring dashboard

Usage:
    python3 launch_vod_services.py [--stop] [--status] [--logs]
"""

import os
import sys
import time
import signal
import subprocess
import threading
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class VODServiceManager:
    """Manages VOD system services."""
    
    def __init__(self):
        self.services = {
            'redis': {
                'name': 'Redis Server',
                'command': ['redis-server', '--daemonize', 'yes'],
                'check_command': ['redis-cli', 'ping'],
                'port': 6379,
                'pid_file': '/tmp/redis_vod.pid'
            },
            'admin_ui': {
                'name': 'Admin UI Server',
                'command': [sys.executable, '-c', '''
import sys
sys.path.insert(0, "/opt/Archivist")
from core.admin_ui import AdminUI
admin_ui = AdminUI(host="127.0.0.1", port=8080, dashboard_port=5051)
admin_ui.run()
'''],
                'check_command': ['curl', '-f', 'http://127.0.0.1:8080/api/admin/status'],
                'port': 8080,
                'pid_file': '/tmp/admin_ui_vod.pid'
            },
            'celery_worker': {
                'name': 'Celery Worker',
                'command': [sys.executable, '-m', 'celery', '-A', 'core.tasks', 'worker', 
                           '--loglevel=info', '--concurrency=2', '--hostname=vod_worker@%h'],
                'check_command': [sys.executable, '-c', '''
import sys
sys.path.insert(0, "/opt/Archivist")
from core.tasks import celery_app
print("Celery worker check")
'''],
                'port': None,
                'pid_file': '/tmp/celery_worker_vod.pid'
            },
            'celery_beat': {
                'name': 'Celery Beat Scheduler',
                'command': [sys.executable, '-m', 'celery', '-A', 'core.tasks', 'beat',
                           '--loglevel=info', '--scheduler=celery.beat.PersistentScheduler'],
                'check_command': [sys.executable, '-c', '''
import sys
sys.path.insert(0, "/opt/Archivist")
from core.tasks import celery_app
print("Celery beat check")
'''],
                'port': None,
                'pid_file': '/tmp/celery_beat_vod.pid'
            }
        }
        
        self.processes = {}
        self.log_file = '/tmp/vod_services.log'
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamps."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        
        # Also write to log file
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def check_port(self, port: int) -> bool:
        """Check if a port is in use."""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except:
            return False
    
    def check_service(self, service_name: str) -> bool:
        """Check if a service is running."""
        service = self.services[service_name]
        
        # Check if process is running
        if service_name in self.processes:
            process = self.processes[service_name]
            if process.poll() is None:
                return True
        
        # Check port if specified
        if service['port']:
            return self.check_port(service['port'])
        
        # Check with custom command
        try:
            result = subprocess.run(service['check_command'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def start_redis(self) -> bool:
        """Start Redis server."""
        try:
            self.log("Starting Redis server...")
            
            # Check if Redis is already running
            if self.check_port(6379):
                self.log("Redis already running on port 6379")
                return True
            
            # Start Redis
            result = subprocess.run(['redis-server', '--daemonize', 'yes'], 
                                  capture_output=True, timeout=10)
            
            if result.returncode == 0:
                time.sleep(2)  # Wait for startup
                if self.check_port(6379):
                    self.log("✓ Redis started successfully")
                    return True
                else:
                    self.log("✗ Redis failed to start", "ERROR")
                    return False
            else:
                self.log(f"✗ Redis start failed: {result.stderr.decode()}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ Redis start error: {e}", "ERROR")
            return False
    
    def start_service(self, service_name: str) -> bool:
        """Start a specific service."""
        if service_name == 'redis':
            return self.start_redis()
        
        service = self.services[service_name]
        
        try:
            self.log(f"Starting {service['name']}...")
            
            # Check if already running
            if self.check_service(service_name):
                self.log(f"{service['name']} already running")
                return True
            
            # Start service
            process = subprocess.Popen(
                service['command'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            self.processes[service_name] = process
            
            # Wait for startup
            time.sleep(3)
            
            # Check if started successfully
            if self.check_service(service_name):
                self.log(f"✓ {service['name']} started successfully")
                return True
            else:
                self.log(f"✗ {service['name']} failed to start", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ {service['name']} start error: {e}", "ERROR")
            return False
    
    def stop_service(self, service_name: str):
        """Stop a specific service."""
        if service_name == 'redis':
            try:
                subprocess.run(['redis-cli', 'shutdown'], capture_output=True)
                self.log("Redis stopped")
            except:
                self.log("Failed to stop Redis", "ERROR")
            return
        
        if service_name in self.processes:
            process = self.processes[service_name]
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                
                process.wait(timeout=5)
                self.log(f"{self.services[service_name]['name']} stopped")
            except:
                try:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                    self.log(f"{self.services[service_name]['name']} force stopped")
                except:
                    self.log(f"Failed to stop {self.services[service_name]['name']}", "ERROR")
            
            del self.processes[service_name]
    
    def start_all_services(self) -> Dict[str, bool]:
        """Start all services."""
        self.log("Starting all VOD services...")
        
        results = {}
        
        # Start services in order
        service_order = ['redis', 'celery_worker', 'celery_beat', 'admin_ui']
        
        for service_name in service_order:
            results[service_name] = self.start_service(service_name)
            if not results[service_name]:
                self.log(f"Failed to start {service_name}, stopping all services", "ERROR")
                self.stop_all_services()
                break
        
        return results
    
    def stop_all_services(self):
        """Stop all services."""
        self.log("Stopping all VOD services...")
        
        # Stop in reverse order
        service_order = ['admin_ui', 'celery_beat', 'celery_worker', 'redis']
        
        for service_name in service_order:
            self.stop_service(service_name)
    
    def get_status(self) -> Dict[str, Dict]:
        """Get status of all services."""
        status = {}
        
        for service_name, service in self.services.items():
            is_running = self.check_service(service_name)
            status[service_name] = {
                'name': service['name'],
                'running': is_running,
                'port': service['port'],
                'status': 'RUNNING' if is_running else 'STOPPED'
            }
        
        return status
    
    def print_status(self):
        """Print service status."""
        status = self.get_status()
        
        print("\n" + "="*60)
        print("VOD SERVICES STATUS")
        print("="*60)
        
        for service_name, info in status.items():
            status_icon = "✓" if info['running'] else "✗"
            port_info = f" (port {info['port']})" if info['port'] else ""
            print(f"{status_icon} {info['name']}{port_info}: {info['status']}")
        
        print("="*60)
    
    def show_logs(self, lines: int = 50):
        """Show recent logs."""
        try:
            with open(self.log_file, 'r') as f:
                log_lines = f.readlines()
                recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
                print("\n".join(recent_logs))
        except FileNotFoundError:
            print("No log file found")
    
    def signal_handler(self, signum, frame):
        """Handle cleanup on interrupt."""
        self.log("Received interrupt signal, cleaning up...", "WARNING")
        self.stop_all_services()
        sys.exit(0)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='VOD Services Manager')
    parser.add_argument('--stop', action='store_true', help='Stop all services')
    parser.add_argument('--status', action='store_true', help='Show service status')
    parser.add_argument('--logs', action='store_true', help='Show recent logs')
    parser.add_argument('--lines', type=int, default=50, help='Number of log lines to show')
    
    args = parser.parse_args()
    
    # Create service manager
    manager = VODServiceManager()
    
    # Set up signal handler
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    try:
        if args.stop:
            manager.stop_all_services()
        elif args.status:
            manager.print_status()
        elif args.logs:
            manager.show_logs(args.lines)
        else:
            # Start all services
            results = manager.start_all_services()
            
            # Print results
            print("\n" + "="*60)
            print("SERVICE STARTUP RESULTS")
            print("="*60)
            
            for service_name, success in results.items():
                status = "✓ STARTED" if success else "✗ FAILED"
                print(f"{status}: {manager.services[service_name]['name']}")
            
            print("="*60)
            
            # Show final status
            manager.print_status()
            
            # Keep running
            manager.log("All services started. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            
    except Exception as e:
        manager.log(f"Error: {e}", "ERROR")
        sys.exit(1)
    finally:
        manager.stop_all_services()

if __name__ == "__main__":
    main() 
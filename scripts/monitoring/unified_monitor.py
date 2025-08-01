#!/usr/bin/env python3
"""
Unified monitoring script for Archivist system.
Consolidates system monitoring, VOD sync monitoring, and status checking.
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import psutil
import redis
import requests

from core.exceptions import (
    ConnectionError,
    DatabaseError,
    NetworkError,
    TimeoutError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/unified_monitor.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class UnifiedMonitor:
    def __init__(self, monitor_type="all"):
        self.monitor_type = monitor_type
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
        )
        self.base_url = f"http://{os.getenv('API_HOST', 'localhost')}:{os.getenv('API_PORT', '5050')}"

    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "timestamp": datetime.now().isoformat(),
        }

    def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health and metrics"""
        try:
            info = self.redis_client.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "uptime": info.get("uptime_in_seconds", 0),
                "timestamp": datetime.now().isoformat(),
            }
        except ConnectionError as e:
            return {
                "status": "unhealthy",
                "error": f"Redis connection error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Unexpected Redis error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def check_api_health(self) -> Dict[str, Any]:
        """Check API health and response time"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/queue", timeout=5)
            duration = time.time() - start_time

            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": duration,
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat(),
            }
        except requests.ConnectionError as e:
            return {
                "status": "unhealthy",
                "error": f"API connection error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except requests.Timeout as e:
            return {
                "status": "unhealthy",
                "error": f"API timeout error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Unexpected API error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def check_celery_workers(self) -> Dict[str, Any]:
        """Check Celery worker status"""
        try:
            # Try to get Celery worker info
            from core.tasks import celery_app
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            active = inspect.active()
            
            if stats:
                worker_count = len(stats)
                active_tasks = sum(len(tasks) for tasks in active.values()) if active else 0
                return {
                    "status": "healthy",
                    "worker_count": worker_count,
                    "active_tasks": active_tasks,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "No Celery workers found",
                    "timestamp": datetime.now().isoformat(),
                }
        except ImportError as e:
            return {
                "status": "unhealthy",
                "error": f"Celery import error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except ConnectionError as e:
            return {
                "status": "unhealthy",
                "error": f"Celery connection error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Unexpected Celery error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def check_database_health(self) -> Dict[str, Any]:
        """Check database connection and health"""
        try:
            # First check if we can import the database module
            try:
                from core.database import db
            except ImportError as e:
                return {
                    "status": "unhealthy",
                    "error": f"Database module import failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            
            # Check if database URL is configured
            db_url = os.getenv('DATABASE_URL', '')
            if not db_url:
                return {
                    "status": "unhealthy",
                    "error": "DATABASE_URL not configured",
                    "timestamp": datetime.now().isoformat(),
                }
            
            # Simple database connection test
            try:
                db.session.execute('SELECT 1')
                db.session.commit()
                return {
                    "status": "healthy",
                    "database_url": db_url.split('@')[1] if '@' in db_url else "configured",
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as db_error:
                return {
                    "status": "unhealthy",
                    "error": f"Database connection failed: {str(db_error)}",
                    "database_url": db_url.split('@')[1] if '@' in db_url else "configured",
                    "timestamp": datetime.now().isoformat(),
                }
                
        except DatabaseError as e:
            return {
                "status": "unhealthy",
                "error": f"Database error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Database health check failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }

    def check_vod_sync_status(self) -> Dict[str, Any]:
        """Check VOD synchronization status"""
        try:
            # Check if VOD-related files exist and are accessible
            vod_paths = [
                "/mnt/flex-1",
                "/mnt/flex-2", 
                "/mnt/flex-3",
                "/mnt/flex-4",
                "/mnt/flex-5"
            ]
            
            accessible_paths = []
            for path in vod_paths:
                if os.path.exists(path) and os.access(path, os.R_OK):
                    accessible_paths.append(path)
            
            return {
                "status": "healthy" if accessible_paths else "unhealthy",
                "accessible_paths": len(accessible_paths),
                "total_paths": len(vod_paths),
                "timestamp": datetime.now().isoformat(),
            }
        except OSError as e:
            return {
                "status": "unhealthy",
                "error": f"VOD sync file system error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Unexpected VOD sync error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def check_rate_limits(self) -> Dict[str, Any]:
        """Check rate limit usage"""
        try:
            rate_limit_keys = self.redis_client.keys("flask-limiter:*")
            rate_limits = {}

            for key in rate_limit_keys:
                value = self.redis_client.get(key)
                if value:
                    rate_limits[key.decode()] = value.decode()

            return {"rate_limits": rate_limits, "timestamp": datetime.now().isoformat()}
        except ConnectionError as e:
            return {"error": f"Rate limit connection error: {e}", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"error": f"Unexpected rate limit error: {e}", "timestamp": datetime.now().isoformat()}

    def run_health_check(self, monitor_type: str = None) -> Dict[str, Any]:
        """Run health checks based on monitor type"""
        if monitor_type is None:
            monitor_type = self.monitor_type
            
        results = {}
        
        if monitor_type in ["all", "system"]:
            results["system"] = self.check_system_resources()
            results["redis"] = self.check_redis_health()
            results["database"] = self.check_database_health()
            
        if monitor_type in ["all", "api"]:
            results["api"] = self.check_api_health()
            results["celery"] = self.check_celery_workers()
            
        if monitor_type in ["all", "vod"]:
            results["vod_sync"] = self.check_vod_sync_status()
            
        if monitor_type in ["all", "rate_limits"]:
            results["rate_limits"] = self.check_rate_limits()

        # Save results to file
        os.makedirs("logs", exist_ok=True)
        with open("logs/health_check.json", "w") as f:
            json.dump(results, f, indent=2)

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of monitoring results"""
        print("\n" + "="*50)
        print("ARCHIVIST SYSTEM MONITORING SUMMARY")
        print("="*50)
        
        if "system" in results:
            sys = results["system"]
            print(f"💻 System Resources:")
            print(f"   CPU: {sys['cpu_percent']}%")
            print(f"   Memory: {sys['memory_percent']}%")
            print(f"   Disk: {sys['disk_usage']}%")
        
        if "redis" in results:
            redis_status = results["redis"]
            status_icon = "✅" if redis_status["status"] == "healthy" else "❌"
            print(f"{status_icon} Redis: {redis_status['status']}")
            if redis_status["status"] == "healthy":
                print(f"   Clients: {redis_status['connected_clients']}")
                print(f"   Memory: {redis_status['used_memory']}")
        
        if "database" in results:
            db_status = results["database"]
            status_icon = "✅" if db_status["status"] == "healthy" else "❌"
            print(f"{status_icon} Database: {db_status['status']}")
            if db_status["status"] == "healthy":
                print(f"   URL: {db_status.get('database_url', 'configured')}")
            else:
                print(f"   Error: {db_status.get('error', 'Unknown error')}")
        
        if "api" in results:
            api_status = results["api"]
            status_icon = "✅" if api_status["status"] == "healthy" else "❌"
            print(f"{status_icon} API: {api_status['status']}")
            if api_status["status"] == "healthy":
                print(f"   Response Time: {api_status['response_time']:.3f}s")
        
        if "celery" in results:
            celery_status = results["celery"]
            status_icon = "✅" if celery_status["status"] == "healthy" else "❌"
            print(f"{status_icon} Celery Workers: {celery_status['status']}")
            if celery_status["status"] == "healthy":
                print(f"   Workers: {celery_status['worker_count']}")
                print(f"   Active Tasks: {celery_status['active_tasks']}")
        
        if "vod_sync" in results:
            vod_status = results["vod_sync"]
            status_icon = "✅" if vod_status["status"] == "healthy" else "❌"
            print(f"{status_icon} VOD Sync: {vod_status['status']}")
            if vod_status["status"] == "healthy":
                print(f"   Accessible Paths: {vod_status['accessible_paths']}/{vod_status['total_paths']}")
        
        print("="*50)
        print(f"📊 Full results saved to: logs/health_check.json")
        print(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    parser = argparse.ArgumentParser(description="Unified Archivist System Monitor")
    parser.add_argument(
        "--type", 
        choices=["all", "system", "api", "vod", "rate_limits"],
        default="all",
        help="Type of monitoring to perform"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run monitoring continuously"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Interval between checks in seconds (for continuous mode)"
    )
    
    args = parser.parse_args()
    
    monitor = UnifiedMonitor(args.type)
    
    if args.continuous:
        print(f"🔄 Starting continuous monitoring (type: {args.type}, interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                results = monitor.run_health_check(args.type)
                monitor.print_summary(results)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
    else:
        print(f"🔍 Running single monitoring check (type: {args.type})")
        results = monitor.run_health_check(args.type)
        monitor.print_summary(results)


if __name__ == "__main__":
    main()
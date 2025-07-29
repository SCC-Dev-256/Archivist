#!/usr/bin/env python3
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

import psutil

import redis
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/monitor.log"), logging.StreamHandler()],
)


class SystemMonitor:
    def __init__(self):
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
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def check_api_health(self) -> Dict[str, Any]:
        """Check API health and response time"""
        try:
            start_time = time.time()
            # Use the queue endpoint as a health check since it's always available
            response = requests.get(f"{self.base_url}/api/queue")
            duration = time.time() - start_time

            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": duration,
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def check_rate_limits(self) -> Dict[str, Any]:
        """Check rate limit usage"""
        try:
            # Get rate limit keys from Redis
            rate_limit_keys = self.redis_client.keys("flask-limiter:*")
            rate_limits = {}

            for key in rate_limit_keys:
                value = self.redis_client.get(key)
                if value:
                    rate_limits[key.decode()] = value.decode()

            return {"rate_limits": rate_limits, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def run_health_check(self):
        """Run all health checks and save results"""
        results = {
            "system": self.check_system_resources(),
            "redis": self.check_redis_health(),
            "api": self.check_api_health(),
            "rate_limits": self.check_rate_limits(),
        }

        # Save results to file
        os.makedirs("logs", exist_ok=True)
        with open("logs/health_check.json", "w") as f:
            json.dump(results, f, indent=2)

        # Log results
        logging.info("Health check completed")
        logging.info(f"System CPU: {results['system']['cpu_percent']}%")
        logging.info(f"System Memory: {results['system']['memory_percent']}%")
        logging.info(f"Redis Status: {results['redis']['status']}")
        logging.info(f"API Status: {results['api']['status']}")

        return results


def main():
    monitor = SystemMonitor()
    while True:
        try:
            monitor.run_health_check()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
            break
        except Exception as e:
            logging.error(f"Error during health check: {e}")
            time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    main()

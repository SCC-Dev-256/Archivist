#!/usr/bin/env python3
"""
Integrated VOD Processing System Startup Script

This script starts the complete integrated system including:
- Main Admin UI with embedded monitoring dashboard
- Unified queue management
- Health checks and metrics collection
"""

import os
import sys
import threading
import time
from pathlib import Path

from loguru import logger

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent  # Go up 3 levels: deployment -> scripts -> project root
sys.path.insert(0, str(project_root))

from core.admin_ui import start_admin_ui
from core.monitoring.integrated_dashboard import start_integrated_dashboard

def setup_logging():
    """Setup logging configuration."""
    logger.remove()  # Remove default handler
    
    # Add console handler with color
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Add file handler
    logger.add(
        "logs/integrated_system.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )

def check_dependencies():
    """Check if all required dependencies are available."""
    required_modules = [
        'flask',
        'celery',
        'redis',
        'rq',
        'psutil',
        'requests',
        'tenacity'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"Missing required modules: {', '.join(missing_modules)}")
        logger.error("Please install missing dependencies: pip install " + " ".join(missing_modules))
        return False
    
    logger.info("All required dependencies are available")
    return True

def check_environment():
    """Check environment configuration."""
    required_env_vars = [
        'REDIS_URL',
        'CABLECAST_USER_ID',
        'CABLECAST_PASSWORD',
        'CABLECAST_BASE_URL'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Some features may not work correctly")
    
    logger.info("Environment check completed")

def start_background_services():
    """Start background services in separate threads."""
    
    def start_health_monitor():
        """Start health monitoring in background."""
        try:
            from core.monitoring.health_checks import get_health_manager
            health_manager = get_health_manager()
            
            while True:
                try:
                    # Run health checks every 60 seconds
                    health_manager.run_all_checks()
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(120)
        except Exception as e:
            logger.error(f"Failed to start health monitor: {e}")
    
    def start_metrics_collector():
        """Start metrics collection in background."""
        try:
            from core.monitoring.metrics import get_metrics_collector
            metrics_collector = get_metrics_collector()
            
            while True:
                try:
                    # Collect metrics every 30 seconds
                    metrics_collector.collect_system_metrics()
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"Metrics collector error: {e}")
                    time.sleep(60)
        except Exception as e:
            logger.error(f"Failed to start metrics collector: {e}")
    
    # Start background threads
    health_thread = threading.Thread(target=start_health_monitor, daemon=True)
    health_thread.start()
    
    metrics_thread = threading.Thread(target=start_metrics_collector, daemon=True)
    metrics_thread.start()
    
    logger.info("Background services started")

def main():
    """Main startup function."""
    logger.info("🚀 Starting Integrated VOD Processing System")
    logger.info("=" * 50)
    
    # Setup logging
    setup_logging()
    logger.info("Starting Integrated VOD Processing System")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Check environment
    check_environment()
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Start background services
    start_background_services()
    
    # Configuration
    admin_host = os.getenv("ADMIN_HOST", "0.0.0.0")
    admin_port = int(os.getenv("ADMIN_PORT", "8080"))
    dashboard_port = int(os.getenv("DASHBOARD_PORT", "5051"))
    
    logger.info(f"Admin UI will start on {admin_host}:{admin_port}")
    logger.info(f"Monitoring dashboard will be embedded on port {dashboard_port}")
    
    logger.info("")
    logger.info(f"📊 Admin UI: http://{admin_host}:{admin_port}")
    logger.info(f"📈 Monitoring Dashboard: http://localhost:{dashboard_port}")
    logger.info(f"📚 API Documentation: http://{admin_host}:{admin_port}/api/docs")
    logger.info(f"🔗 Unified Queue API: http://{admin_host}:{admin_port}/api/unified-queue/docs")
    logger.info("")
    logger.info("=" * 50)
    
    try:
        # Start the integrated admin UI
        start_admin_ui(admin_host, admin_port, dashboard_port)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Unified Archivist System Startup Script

This script replaces all the duplicated startup scripts with a single, configurable entry point.
It supports all the different startup modes and provides a consistent interface.

Usage:
    python3 start_archivist_unified.py [mode] [options]

Modes:
    complete     - Full system with all features (default)
    simple       - Basic system with alternative ports
    integrated   - Integrated dashboard mode
    vod-only     - VOD processing only
    centralized  - Centralized service management

Options:
    --ports admin=8080,dashboard=5051  - Custom port configuration
    --concurrency 4                    - Celery worker concurrency
    --log-level INFO                   - Logging level
    --config-file config.json          - Load configuration from file
    --help                             - Show this help message

Examples:
    python3 start_archivist_unified.py complete
    python3 start_archivist_unified.py simple --ports admin=5052,dashboard=5053
    python3 start_archivist_unified.py vod-only --concurrency 2
    python3 start_archivist_unified.py --config-file production.json
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our unified startup system
from scripts.deployment.startup_config import StartupConfig, StartupMode, create_config_from_args, load_config_from_file
from scripts.deployment.startup_manager import StartupManager

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified Archivist System Startup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        default='complete',
        choices=[mode.value for mode in StartupMode],
        help='Startup mode (default: complete)'
    )
    
    parser.add_argument(
        '--ports',
        help='Custom port configuration (e.g., admin=8080,dashboard=5051)'
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        help='Celery worker concurrency'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    parser.add_argument(
        '--config-file',
        type=Path,
        help='Load configuration from JSON/YAML file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be started without actually starting'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show system status and exit'
    )
    
    return parser.parse_args()

def create_config_from_parsed_args(args) -> StartupConfig:
    """Create configuration from parsed arguments."""
    if args.config_file:
        # Load from file
        return load_config_from_file(args.config_file)
    else:
        # Create from command line arguments
        config_args = {
            'mode': args.mode,
        }
        
        if args.ports:
            config_args['ports'] = args.ports
        
        if args.concurrency:
            config_args['concurrency'] = args.concurrency
        
        if args.log_level:
            config_args['log_level'] = args.log_level
        
        return create_config_from_args(config_args)

def show_system_status(config: StartupConfig):
    """Show current system status."""
    print("🔍 Archivist System Status")
    print("=" * 50)
    
    # Show configuration
    print(f"Mode: {config.mode.value}")
    print(f"Project Root: {config.project_root}")
    print(f"Admin UI Port: {config.ports.admin_ui}")
    print(f"Dashboard Port: {config.ports.dashboard}")
    print(f"Celery Concurrency: {config.celery.concurrency}")
    print(f"Health Checks: {'Enabled' if config.health_checks.enabled else 'Disabled'}")
    
    # Show enabled features
    print("\nEnabled Features:")
    for feature, enabled in config.features.items():
        status = "✅" if enabled else "❌"
        print(f"  {status} {feature}")
    
    # Show service status
    print("\nService Configuration:")
    for service_name, service_config in config.services.items():
        status = "✅" if service_config.enabled else "❌"
        print(f"  {status} {service_name}")
    
    print("=" * 50)

def show_dry_run_info(config: StartupConfig):
    """Show what would be started in dry-run mode."""
    print("🔍 Dry Run - What Would Be Started")
    print("=" * 50)
    
    print(f"Mode: {config.mode.value}")
    print(f"Admin UI: http://0.0.0.0:{config.ports.admin_ui}")
    print(f"Dashboard: http://localhost:{config.ports.dashboard}")
    print(f"Celery Workers: {config.celery.concurrency}")
    
    print("\nServices to start:")
    service_order = [
        "redis", "postgresql", "celery_worker", "celery_beat",
        "vod_sync_monitor", "admin_ui", "monitoring_dashboard"
    ]
    
    for service_name in service_order:
        service_config = config.get_service_config(service_name)
        if service_config.enabled:
            print(f"  ✅ {service_name}")
        else:
            print(f"  ❌ {service_name} (disabled)")
    
    print("\nFeatures enabled:")
    for feature, enabled in config.features.items():
        if enabled:
            print(f"  ✅ {feature}")
    
    print("=" * 50)
    print("Run without --dry-run to actually start the system")

def main():
    """Main entry point."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Create configuration
        config = create_config_from_parsed_args(args)
        
        # Handle special modes
        if args.status:
            show_system_status(config)
            return 0
        
        if args.dry_run:
            show_dry_run_info(config)
            return 0
        
        # Create startup manager
        startup_manager = StartupManager(config)
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
            startup_manager.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the system
        print(f"🚀 Starting Archivist System in {config.mode.value} mode")
        print("=" * 60)
        
        if not startup_manager.run():
            print("❌ Failed to start Archivist system")
            return 1
        
        # Keep the system running
        try:
            while startup_manager.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
        finally:
            startup_manager.stop()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
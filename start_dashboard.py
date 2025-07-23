#!/usr/bin/env python3
"""
Simple startup script for the Integrated VOD Processing Dashboard
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set environment variables if not already set
if not os.getenv('PYTHONPATH'):
    os.environ['PYTHONPATH'] = str(current_dir)

print(f"Project root: {current_dir}")
print(f"Python path: {sys.path[0]}")

try:
    from core.monitoring.integrated_dashboard import start_integrated_dashboard
    print("✅ Successfully imported integrated dashboard")
    
    # Start the dashboard
    print("🚀 Starting Integrated VOD Processing Dashboard...")
    start_integrated_dashboard(host="0.0.0.0", port=5051)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Available modules:")
    for path in sys.path:
        if os.path.exists(path):
            print(f"  - {path}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting dashboard: {e}")
    sys.exit(1) 
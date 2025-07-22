#!/usr/bin/env python3
"""
Integrated Dashboard Startup Script
Starts the enhanced Integrated Dashboard with real-time task monitoring.
"""

import os
import sys
import signal
from pathlib import Path

def main():
    """Start the Integrated Dashboard with real-time monitoring."""
    
    # Add the project root to Python path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Set environment variables
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_SECRET_KEY'] = 'archivist-integrated-dashboard-2025'
    
    print("🚀 Starting Enhanced Integrated Dashboard...")
    print(f"📁 Project root: {project_root}")
    print(f"🐍 Python path: {sys.executable}")
    
    try:
        # Import and start the integrated dashboard
        from core.monitoring.integrated_dashboard import start_integrated_dashboard
        
        print("✅ Integrated Dashboard imported successfully")
        print("🌐 Starting server on http://0.0.0.0:5051")
        print("📊 Dashboard available at http://localhost:5051")
        print("⚡ Real-time task monitoring enabled")
        print("🔌 WebSocket support active")
        print("🛑 Press Ctrl+C to stop the server")
        
        # Start the integrated dashboard
        start_integrated_dashboard(host="0.0.0.0", port=5051)
        
    except ImportError as e:
        print(f"❌ Error importing Integrated Dashboard: {e}")
        print("💡 Make sure you're running from the project root directory")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Integrated Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting Integrated Dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
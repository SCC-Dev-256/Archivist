#!/usr/bin/env python3
"""
Simple test script to start the Archivist web UI for testing the captioning system.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'
os.environ['TESTING'] = 'false'

# Import and start the app
from core.app import app

if __name__ == "__main__":
    print("Starting Archivist Web UI for captioning system testing...")
    print("Access the web interface at: http://localhost:5050")
    print("Press Ctrl+C to stop the server")
    
    # Start the Flask app with SocketIO
    app.socketio.run(
        app, 
        host="0.0.0.0", 
        port=5050, 
        debug=True,
        use_reloader=False  # Disable reloader to avoid duplicate processes
    )
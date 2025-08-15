#!/usr/bin/env python3
# PURPOSE: Start the full Archivist API with digitalfiles endpoints
# DEPENDENCIES: core.app, flask
# MODIFICATION NOTES: v1.0 - API startup for PDF integration

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_archivist_api():
    """Start the full Archivist API with all endpoints."""
    try:
        from core.app import create_app
        from flask import Flask
        
        print("🚀 Starting Archivist API with digitalfiles endpoints...")
        
        # Create the Flask app
        app = create_app()
        
        # Verify digitalfiles routes are registered
        with app.app_context():
            routes = []
            for rule in app.url_map.iter_rules():
                if 'digitalfiles' in rule.rule:
                    routes.append(rule.rule)
            
            if routes:
                print(f"✅ Digitalfiles routes registered: {len(routes)} endpoints")
                for route in routes[:5]:  # Show first 5
                    print(f"   - {route}")
            else:
                print("⚠️  No digitalfiles routes found")
        
        # Start the API server
        print("🌐 Starting API server on port 8080...")
        app.run(
            host='0.0.0.0',
            port=8080,
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start Archivist API: {e}")
        return False

if __name__ == "__main__":
    start_archivist_api() 
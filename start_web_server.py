#!/usr/bin/env python3
"""Simple script to start the Archivist web server."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Start the web server."""
    try:
        from core.web_app import create_app
        print("🚀 Starting Archivist Web Server...")
        
        app, limiter, api = create_app()
        print("✅ Flask app created successfully")
        print("🌐 Starting server on http://0.0.0.0:5000")
        print("📊 Health check: http://localhost:5000/health")
        print("📚 API docs: http://localhost:5000/api/docs")
        print("=" * 50)
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
"""
Core package for the Archivist application.
"""
from .app import create_app, create_app_with_config

# Create the application instance
app = create_app()

__all__ = ['app', 'create_app', 'create_app_with_config'] 
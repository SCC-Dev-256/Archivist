"""
Core package for the Archivist application.
"""
from .app import app, create_app, create_app_with_config

__all__ = ['app', 'create_app', 'create_app_with_config'] 
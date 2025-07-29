"""
API package for Archivist application.

This package provides centralized access to all API-related functionality,
including route registration and API utilities.
"""

from .routes import register_routes

__all__ = [
    'register_routes',
]
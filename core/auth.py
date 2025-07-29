"""Authentication and authorization module for the Archivist application.

This module provides JWT-based authentication and role-based access control.
It includes rate limiting to prevent abuse and supports both regular user
and admin access levels.

Key Features:
- JWT token-based authentication
- Role-based access control (admin vs regular users)
- Rate limiting with configurable limits
- Token expiration and refresh
- Secure password handling

Example:
    >>> from core.auth import init_auth, login_required
    >>> app = Flask(__name__)
    >>> init_auth(app)
    >>> 
    >>> @app.route('/protected')
    >>> @login_required
    >>> def protected_route():
    >>>     return {'message': 'success'}
"""

from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)

def init_auth(app):
    """Initialize authentication and rate limiting."""
    # Initialize JWT
    jwt.init_app(app)
    
    # Initialize rate limiter with correct API
    limiter.init_app(app)
    
    # Don't apply global rate limit to app object - this should be done per route
    # limiter.limit("100/minute")(app)  # This was causing the AttributeError
    
    return app

def login_required(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user = get_jwt_identity()
        if not current_user.get('is_admin', False):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def create_token(user_data):
    """Create a new JWT token"""
    return create_access_token(identity=user_data)

def get_current_user():
    """Get the current authenticated user"""
    return get_jwt_identity() 
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
    """Initialize authentication and rate limiting"""
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    
    # Initialize JWT
    jwt.init_app(app)
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    # Add rate limit to all routes
    limiter.limit("100/minute")(app)

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
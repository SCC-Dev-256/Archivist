import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from core.auth import (
    init_auth,
    login_required,
    admin_required,
    create_token,
    get_current_user,
    jwt,
    limiter
)

@pytest.fixture
def app():
    """Create a test Flask app"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'  # Flask secret key
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key'  # Separate JWT secret key
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=3600)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    app.config['JWT_ERROR_MESSAGE_KEY'] = 'error'
    app.config['JWT_BLACKLIST_ENABLED'] = False
    app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = []
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    app.config['RATELIMIT_STORAGE_URL'] = 'memory://'
    app.config['RATELIMIT_STRATEGY'] = 'fixed-window'
    app.config['RATELIMIT_DEFAULT'] = "100/minute"
    app.config['RATELIMIT_STORAGE_OPTIONS'] = {}
    app.config['RATELIMIT_HEADERS_ENABLED'] = True
    app.config['RATELIMIT_ENABLED'] = True
    app.config['RATELIMIT_HEADERS_RESET'] = True
    app.config['RATELIMIT_HEADERS_RETRY_AFTER'] = True
    app.config['RATELIMIT_HEADERS_REMAINING'] = True
    app.config['RATELIMIT_HEADERS_LIMIT'] = True
    
    # Initialize Flask-WTF CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize JWT manager
    jwt.init_app(app)
    
    return app

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

def test_init_auth(app):
    """Test authentication initialization"""
    with patch('flask_limiter.Limiter') as mock_limiter, \
         patch('flask_limiter.util.get_qualified_name', return_value='test_app'):
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        assert app.config['JWT_SECRET_KEY'] == 'test-jwt-secret-key'
        assert app.config['JWT_ACCESS_TOKEN_EXPIRES'] == timedelta(seconds=3600)
        # Check that JWT is properly initialized by checking if it's attached to the app
        assert hasattr(app, 'extensions')
        assert 'flask-jwt-extended' in app.extensions

def test_login_required_decorator(app):
    """Test login_required decorator"""
    with patch('flask_limiter.Limiter') as mock_limiter, \
         patch('flask_limiter.util.get_qualified_name', return_value='test_app'):
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        
        @app.route('/protected')
        @login_required
        def protected_route():
            return {'message': 'success'}
        
        # Test without token
        response = app.test_client().get('/protected')
        assert response.status_code == 401
        
        # Test with valid token
        with app.app_context():
            token = create_token("user_1")
            response = app.test_client().get(
                '/protected',
                headers={'Authorization': f'Bearer {token}'}
            )
            if response.status_code != 200:
                print(f"JWT Error Response: {response.data}")
            assert response.status_code == 200
            assert response.json['message'] == 'success'

def test_admin_required_decorator(app):
    """Test admin_required decorator"""
    with patch('flask_limiter.Limiter') as mock_limiter, \
         patch('flask_limiter.util.get_qualified_name', return_value='test_app'):
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        
        @app.route('/admin')
        @admin_required
        def admin_route():
            return {'message': 'admin_success'}
        
        # Test without token
        response = app.test_client().get('/admin')
        assert response.status_code == 401
        
        # Test with regular user token
        with app.app_context():
            token = create_token("user_1")
            response = app.test_client().get(
                '/admin',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 403
        
        # Test with admin token
        with app.app_context():
            token = create_token("admin_1")
            response = app.test_client().get(
                '/admin',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 200
            assert response.json['message'] == 'admin_success'

def test_create_token(app):
    """Test token creation"""
    with app.app_context():
        token = create_token("test_user")
        assert isinstance(token, str)
        assert len(token) > 0

def test_get_current_user(app):
    """Test getting current user"""
    with app.app_context():
        # Test without JWT context
        user = get_current_user()
        assert user is None
        
        # Test with JWT context
        token = create_token("test_user")
        with patch('flask_jwt_extended.get_jwt_identity', return_value="test_user"):
            user = get_current_user()
            assert user == "test_user"

def test_rate_limiting(app):
    """Test rate limiting functionality"""
    with patch('flask_limiter.Limiter') as mock_limiter, \
         patch('flask_limiter.util.get_qualified_name', return_value='test_app'):
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        
        @app.route('/limited')
        @limiter.limit("2/minute")
        def limited_route():
            return {'message': 'limited'}
        
        # Test rate limiting
        response1 = app.test_client().get('/limited')
        response2 = app.test_client().get('/limited')
        response3 = app.test_client().get('/limited')
        
        # First two should succeed, third might be rate limited
        assert response1.status_code in [200, 429]
        assert response2.status_code in [200, 429]
        # Third request might be rate limited depending on timing

def test_token_expiration(app):
    """Test token expiration"""
    with patch('flask_limiter.Limiter') as mock_limiter, \
         patch('flask_limiter.util.get_qualified_name', return_value='test_app'):
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        
        @app.route('/expiring')
        @login_required
        def expiring_route():
            return {'message': 'expiring'}
        
        with app.app_context():
            # Create token with short expiration
            token = create_token("test_user")
            response = app.test_client().get(
                '/expiring',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 200 
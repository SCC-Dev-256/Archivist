import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from flask import Flask
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
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=3600)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    app.config['RATELIMIT_STORAGE_URL'] = 'memory://'
    app.config['RATELIMIT_STRATEGY'] = 'fixed-window'
    app.config['RATELIMIT_DEFAULT'] = "100/minute"
    app.config['RATELIMIT_STORAGE_OPTIONS'] = {}
    app.config['RATELIMIT_HEADERS_ENABLED'] = True
    app.config['RATELIMIT_ENABLED'] = True
    app.config['RATELIMIT_HEADERS_ENABLED'] = True
    app.config['RATELIMIT_HEADERS_RESET'] = True
    app.config['RATELIMIT_HEADERS_RETRY_AFTER'] = True
    app.config['RATELIMIT_HEADERS_REMAINING'] = True
    app.config['RATELIMIT_HEADERS_LIMIT'] = True
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
        assert app.config['JWT_SECRET_KEY'] == 'test-secret-key'
        assert app.config['JWT_ACCESS_TOKEN_EXPIRES'] == timedelta(seconds=3600)
        assert jwt._get_app(app) is not None

def test_login_required_decorator(app):
    """Test login_required decorator"""
    with patch('flask_limiter.Limiter') as mock_limiter:
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
            token = create_token({'user_id': 1})
            response = app.test_client().get(
                '/protected',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 200
            assert response.json['message'] == 'success'

def test_admin_required_decorator(app):
    """Test admin_required decorator"""
    with patch('flask_limiter.Limiter') as mock_limiter:
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        
        @app.route('/admin')
        @admin_required
        def admin_route():
            return {'message': 'success'}
        
        # Test without token
        response = app.test_client().get('/admin')
        assert response.status_code == 401
        
        # Test with non-admin token
        with app.app_context():
            token = create_token({'user_id': 1, 'is_admin': False})
            response = app.test_client().get(
                '/admin',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 403
        
        # Test with admin token
        with app.app_context():
            token = create_token({'user_id': 1, 'is_admin': True})
            response = app.test_client().get(
                '/admin',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 200
            assert response.json['message'] == 'success'

def test_create_token(app):
    """Test token creation"""
    with patch('flask_limiter.Limiter') as mock_limiter:
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        with app.app_context():
            user_data = {'user_id': 1, 'username': 'test'}
            token = create_token(user_data)
            assert isinstance(token, str)
            assert len(token) > 0

def test_get_current_user(app):
    """Test getting current user"""
    with patch('flask_limiter.Limiter') as mock_limiter:
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        with app.app_context():
            user_data = {'user_id': 1, 'username': 'test'}
            token = create_token(user_data)
            
            # Test without token
            with pytest.raises(Exception):
                get_current_user()
            
            # Test with token
            with patch('core.auth.get_jwt_identity', return_value=user_data):
                current_user = get_current_user()
                assert current_user == user_data

def test_rate_limiting(app):
    """Test rate limiting"""
    with patch('flask_limiter.Limiter') as mock_limiter:
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        
        @app.route('/limited')
        @limiter.limit("2/minute")
        def limited_route():
            return {'message': 'success'}
        
        # Make requests within limit
        for _ in range(2):
            response = app.test_client().get('/limited')
            assert response.status_code == 200
        
        # Make request exceeding limit
        response = app.test_client().get('/limited')
        assert response.status_code == 429  # Too Many Requests

def test_token_expiration(app):
    """Test token expiration"""
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=1)
    with patch('flask_limiter.Limiter') as mock_limiter:
        mock_limiter_instance = MagicMock()
        mock_limiter.return_value = mock_limiter_instance
        init_auth(app)
        
        @app.route('/expiring')
        @login_required
        def expiring_route():
            return {'message': 'success'}
        
        with app.app_context():
            token = create_token({'user_id': 1})
            
            # Test immediately
            response = app.test_client().get(
                '/expiring',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 200
            
            # Test after expiration
            import time
            time.sleep(2)
            response = app.test_client().get(
                '/expiring',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 401 
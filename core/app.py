from flask import Flask, render_template
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from core.logging_config import setup_logging

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()

# Get Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
REDIS_OPTIONS = {
    "socket_connect_timeout": 30,
    "socket_timeout": 30,
    "retry_on_timeout": True
}

# Initialize limiter with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    storage_options=REDIS_OPTIONS,
    strategy="fixed-window",
    default_limits=["200 per day", "50 per hour"]
)

def create_app():
    app = Flask(__name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )
    setup_logging()
    
    # Load configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///archivist.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key'),
        CACHE_TYPE='simple',
        RATELIMIT_STORAGE_URL=REDIS_URL,
        RATELIMIT_STRATEGY='fixed-window',
        RATELIMIT_DEFAULT=os.getenv('API_RATE_LIMIT', '100/minute'),
        RATELIMIT_STORAGE_OPTIONS=REDIS_OPTIONS,
        # Add server name configuration
        SERVER_NAME=os.getenv('SERVER_NAME', None),  # Set to None for development
        PREFERRED_URL_SCHEME=os.getenv('PREFERRED_URL_SCHEME', 'http'),
        # Add CORS configuration
        CORS_ORIGINS=os.getenv('CORS_ORIGINS', '*').split(','),
        CORS_METHODS=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        CORS_ALLOW_HEADERS=['Content-Type', 'Authorization']
    )
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)
    
    # Import routes after app creation to avoid circular imports
    with app.app_context():
        from .web_app import register_routes
        register_routes(app, limiter)
    
    return app

def create_app_with_config(config_object=None):
    app = create_app()
    if config_object:
        app.config.from_object(config_object)
    return app

# Create the application instance
app = create_app() 
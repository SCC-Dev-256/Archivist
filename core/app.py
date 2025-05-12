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
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window"
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
        RATELIMIT_STORAGE_URL=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        RATELIMIT_STRATEGY='fixed-window',
        RATELIMIT_DEFAULT=os.getenv('API_RATE_LIMIT', '100/minute'),
        RATELIMIT_STORAGE_OPTIONS={
            "socket_connect_timeout": 30,
            "socket_timeout": 30,
            "retry_on_timeout": True
        }
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
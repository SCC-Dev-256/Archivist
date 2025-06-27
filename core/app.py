from dotenv import load_dotenv
load_dotenv()

# Debug prints - REMOVED for security (leaked sensitive configuration)
# import os
# print("DATABASE_URL from environment:", os.getenv('DATABASE_URL'))
# print("SQLALCHEMY_DATABASE_URI from environment:", os.getenv('SQLALCHEMY_DATABASE_URI'))

import os
from flask import Flask, render_template
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from core.logging_config import setup_logging
from core.database import db
from core.web_app import register_routes
from core.security import security_manager
from loguru import logger

# Initialize extensions
migrate = Migrate()
cache = Cache()

# Initialize limiter with Redis storage for better security
# Rate limiting configuration via environment variables
RATE_LIMIT_DAILY = os.getenv('RATE_LIMIT_DAILY', '200 per day')
RATE_LIMIT_HOURLY = os.getenv('RATE_LIMIT_HOURLY', '50 per hour')

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/0",
    strategy="fixed-window",
    default_limits=[RATE_LIMIT_DAILY, RATE_LIMIT_HOURLY],
    headers_enabled=True,
    retry_after="x-ratelimit-reset"
)

def create_app(testing=False):
    """Create and configure the Flask application
    
    Args:
        testing (bool): If True, configure the app for testing
    """
    # Setup logging with appropriate mode
    setup_logging(testing=testing)
    
    # Create the Flask app
    app = Flask(__name__)
    
    # Configure the app BEFORE initializing the database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://archivist:archivist_password@localhost:5432/archivist')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Security Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(32).hex())
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
    app.config['WTF_CSRF_SSL_STRICT'] = True
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Configure cache
    app.config['CACHE_TYPE'] = 'redis'
    app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutes default timeout
    
    # Initialize the database AFTER setting the configuration
    db.init_app(app)
    
    # Initialize extensions with app
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)
    
    # Configure CORS with security restrictions
    CORS(app, 
         origins=os.getenv('CORS_ORIGINS', '*').split(','),
         methods=os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE,OPTIONS').split(','),
         allow_headers=os.getenv('CORS_ALLOW_HEADERS', 'Content-Type,Authorization').split(','),
         supports_credentials=True
    )
    
    # Initialize security manager with HTTPS enforcement based on environment
    force_https = os.getenv('FLASK_ENV') == 'production' or os.getenv('FORCE_HTTPS', 'false').lower() == 'true'
    security_manager.init_app(app, force_https=force_https)
    
    # Register routes from web_app
    register_routes(app, limiter)
    
    # Log application startup (without sensitive details)
    if testing:
        logger.info("Flask application created in testing mode")
    else:
        logger.info("Flask application created successfully")
        # Log non-sensitive configuration details
        logger.debug(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
        logger.debug(f"HTTPS enforced: {force_https}")
        logger.debug(f"Rate limiting: {RATE_LIMIT_DAILY}, {RATE_LIMIT_HOURLY}")
    
    return app

def create_app_with_config(config_object=None):
    app = create_app()
    if config_object:
        app.config.from_object(config_object)
    return app

# Create the default app instance
app = create_app(testing=os.getenv("TESTING", "false").lower() == "true")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True) 
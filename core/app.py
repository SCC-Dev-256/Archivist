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
from core.security import security_manager
from loguru import logger
from flask_socketio import SocketIO
from core.monitoring.middleware import performance_middleware
from core.monitoring.socket_tracker import socket_tracker
# from core.services.queue_analytics import queue_analytics  # Temporarily commented out
from core.database_health import init_db_health_checker

# Initialize extensions
migrate = Migrate()
cache = Cache()

# Initialize limiter with Redis storage for better security
# Rate limiting configuration will be set dynamically in create_app
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/0",
    strategy="fixed-window",
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
    db_url = os.getenv('DATABASE_URL', 'postgresql://archivist:archivist_password@localhost:5432/archivist')
    
    # Add timeout parameters to database URL
    if '?' not in db_url:
        db_url += '?'
    else:
        db_url += '&'
    
    db_url += 'connect_timeout=5&application_name=archivist'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 5,
        'max_overflow': 10,
        'pool_size': 5
    }
    
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
    
    # Configure rate limiting based on environment
    if testing or os.getenv('TESTING') == 'true':
        # Higher limits for testing environment
        rate_limit_daily = '10000 per day'
        rate_limit_hourly = '1000 per hour'
        logger.debug(f"Rate limiting (testing): {rate_limit_daily}, {rate_limit_hourly}")
    else:
        # Normal limits for production
        rate_limit_daily = '200 per day'
        rate_limit_hourly = '50 per hour'
        logger.debug(f"Rate limiting (production): {rate_limit_daily}, {rate_limit_hourly}")
    
    # Set rate limiting configuration
    app.config['RATELIMIT_DEFAULT'] = f'{rate_limit_daily}; {rate_limit_hourly}'
    app.config['RATELIMIT_STORAGE_URL'] = "redis://localhost:6379/0"
    
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
    # Only enforce HTTPS in production or if FORCE_HTTPS is explicitly true
    force_https = (os.getenv('FLASK_ENV') == 'production' or os.getenv('FORCE_HTTPS', 'false').lower() == 'true')
    security_manager.init_app(app, force_https=force_https)
    
    # Register routes from web_app
    from core.api import register_routes
    register_routes(app, limiter)
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    app.socketio = socketio
    # Register real-time event handlers
    from core.realtime import register_realtime_events
    register_realtime_events(app)
    
    # Initialize database health checker
    with app.app_context():
        try:
            init_db_health_checker(db.session)
            logger.info("Database health checker initialized successfully")
        except Exception as e:
            logger.warning(f"Database health checker initialization failed: {e}")
    
    # Initialize performance monitoring middleware
    try:
        performance_middleware.init_app(app)
        logger.info("Performance monitoring middleware initialized successfully")
    except Exception as e:
        logger.warning(f"Performance monitoring middleware initialization failed: {e}")
    
    # Log application startup (without sensitive details)
    if testing:
        logger.info("Flask application created in testing mode")
    else:
            logger.info("Flask application created successfully")
    # Log non-sensitive configuration details
    logger.debug(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    logger.debug(f"HTTPS enforced: {force_https}")
    
    return app

def create_app_with_config(config_object=None):
    app = create_app()
    if config_object:
        app.config.from_object(config_object)
    return app

# Create the default app instance
app = create_app(testing=os.getenv("TESTING", "false").lower() == "true")

# Add route to render the main GUI
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.socketio.run(app, host="0.0.0.0", port=5050, debug=True) 
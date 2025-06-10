from dotenv import load_dotenv
load_dotenv()

# Debug prints
import os
print("DATABASE_URL from environment:", os.getenv('DATABASE_URL'))
print("SQLALCHEMY_DATABASE_URI from environment:", os.getenv('SQLALCHEMY_DATABASE_URI'))

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

# Initialize extensions
migrate = Migrate()
cache = Cache()

# Initialize limiter with in-memory storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    strategy="fixed-window",
    default_limits=["200 per day", "50 per hour"]
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
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
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
    CORS(app)
    
    # Register routes from web_app
    register_routes(app, limiter)
    
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
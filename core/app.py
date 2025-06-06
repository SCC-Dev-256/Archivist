from flask import Flask, render_template
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os
from core.logging_config import setup_logging

# Initialize extensions
db = SQLAlchemy()
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
    
    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://archivist:archivist_password@db:5432/archivist')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)
    CORS(app)
    
    # Register blueprints here
    
    return app

def create_app_with_config(config_object=None):
    app = create_app()
    if config_object:
        app.config.from_object(config_object)
    return app

# Create the default app instance
app = create_app(testing=os.getenv("TESTING", "false").lower() == "true") 
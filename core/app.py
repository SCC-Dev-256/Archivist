from flask import Flask, render_template
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os
from core.logging_config import setup_logging
from fastapi import FastAPI

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
    """Create and configure the FastAPI application
    
    Args:
        testing (bool): If True, configure the app for testing
    """
    # Setup logging with appropriate mode
    setup_logging(testing=testing)
    
    # Create the FastAPI app
    app = FastAPI(
        title="Archivist API",
        description="Video transcription and management API",
        version="0.1.0"
    )
    
    # Add routes and middleware here
    
    return app

def create_app_with_config(config_object=None):
    app = create_app()
    if config_object:
        app.config.from_object(config_object)
    return app

# Create the default app instance
app = create_app(testing=os.getenv("TESTING", "false").lower() == "true") 
from flask import Flask
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv('SECRET_KEY'),
        CACHE_TYPE='simple',
        RATELIMIT_STORAGE_URL=os.getenv('REDIS_URL'),
        RATELIMIT_STRATEGY='fixed-window',
        RATELIMIT_DEFAULT=os.getenv('API_RATE_LIMIT', '100/minute')
    )
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)
    
    # Register blueprints
    from .web_app import bp as web_bp
    from .api_docs import bp as api_docs_bp
    
    app.register_blueprint(web_bp)
    app.register_blueprint(api_docs_bp, url_prefix='/api/docs')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    return app

app = create_app() 
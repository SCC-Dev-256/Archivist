#!/usr/bin/env python3
"""Create Cablecast database tables.

This script creates the necessary database tables for the Cablecast integration.
"""

import sys
import os
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_cablecast_tables():
    """Create the cablecast_shows table"""
    try:
        from core.app import create_app, db
        from core.models import CablecastShowORM
        
        # Create Flask app
        app = create_app()
        
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("✓ Database tables created successfully")
            
            # Verify the table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'cablecast_shows' in tables:
                logger.info("✓ cablecast_shows table created successfully")
                return True
            else:
                logger.error("✗ cablecast_shows table was not created")
                return False
                
    except Exception as e:
        logger.error(f"✗ Error creating database tables: {e}")
        return False

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    success = create_cablecast_tables()
    sys.exit(0 if success else 1) 
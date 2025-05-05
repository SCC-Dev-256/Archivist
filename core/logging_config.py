from loguru import logger
import sys
import os

def setup_logging():
    """Configure logging for the application"""
    # Remove default logger
    logger.remove()
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Add console handler with INFO level
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Add file handler with DEBUG level and rotation
    log_file = os.path.join(logs_dir, "archivist.log")
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="1 week",
        compression="zip"
    )
    
    # Log the setup completion
    logger.info(f"Logging configured. Log file: {log_file}") 
from loguru import logger
import sys
import os

def setup_logging(testing=False):
    """Configure logging for the application
    
    Args:
        testing (bool): If True, configure minimal logging for tests
    """
    # Remove default logger if not in testing mode
    if not testing:
        logger.remove()
    
    # Add console handler with appropriate level
    level = "DEBUG" if testing else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Only add file handler if not in testing mode
    if not testing:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
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
    else:
        logger.debug("Test logging configured") 
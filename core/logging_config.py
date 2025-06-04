from loguru import logger
import sys
import os
from typing import Optional

def setup_logging(testing: bool = False, log_level: Optional[str] = None) -> None:
    """Configure logging for the application
    
    Args:
        testing (bool): If True, configure minimal logging for tests
        log_level (str, optional): Override the default log level
    """
    # Remove default logger
    logger.remove()
    
    # Set appropriate level
    level = log_level or ("DEBUG" if testing else "INFO")
    
    # Add console handler
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        backtrace=not testing,  # Disable backtrace in tests
        diagnose=not testing    # Disable diagnose in tests
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
        
        logger.info(f"Logging configured. Log file: {log_file}")
    else:
        logger.debug("Test logging configured") 
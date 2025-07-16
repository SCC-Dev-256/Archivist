"""Configuration management module for the Archivist application.

This module centralizes all configuration settings for the application,
including environment variables, default values, and configuration validation.
It provides a single source of truth for all application settings.

Key Features:
- Environment variable management
- Configuration validation
- Default value handling
- Mount point configuration
- Location-based access settings
- Redis and database connection settings

Example:
    >>> from core.config import MOUNT_POINTS, LOCATIONS
    >>> print(MOUNT_POINTS['nas'])
    >>> print(LOCATIONS['default']['allowed_users'])
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent

# Storage configuration
DEFAULT_MOUNT_POINTS = {
    'nas': '/mnt/nas',  # Default NAS mount
}

# Add default Flex server mounts (1-9)
for i in range(1, 10):
    DEFAULT_MOUNT_POINTS[f'flex{i}'] = f'/mnt/flex{i}'

# Get mount points from environment or use defaults
MOUNT_POINTS = {}
for mount_name, default_path in DEFAULT_MOUNT_POINTS.items():
    env_var = f"{mount_name.upper()}_PATH"
    MOUNT_POINTS[mount_name] = os.getenv(env_var, default_path)

# For backward compatibility
NAS_PATH = MOUNT_POINTS['nas']

# Get all Flex server paths
FLEX_PATHS = {k: v for k, v in MOUNT_POINTS.items() if k.startswith('flex')}

# Location and User Configuration
LOCATIONS = {
    'default': {
        'name': 'Default Location',
        'flex_servers': list(FLEX_PATHS.keys()),  # All Flex servers by default
        'allowed_users': ['*']  # All users by default
    }
}

# Load custom locations from environment
LOCATIONS_CONFIG = os.getenv('LOCATIONS_CONFIG')
if LOCATIONS_CONFIG and os.path.exists(LOCATIONS_CONFIG):
    import json
    with open(LOCATIONS_CONFIG, 'r') as f:
        custom_locations = json.load(f)
        LOCATIONS.update(custom_locations)

# Output configuration
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(NAS_PATH, "transcriptions"))

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Construct Redis URL
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# WhisperX configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v2")
USE_GPU = os.getenv("USE_GPU", "false").lower() == "true"
COMPUTE_TYPE = "float16" if USE_GPU else "int8"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))  # Increased for better CPU utilization
NUM_WORKERS = int(os.getenv("NUM_WORKERS", "4"))  # Number of CPU workers
LANGUAGE = os.getenv("LANGUAGE", "en")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "4"))

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# PostgreSQL configuration
POSTGRES_CONFIG = {
    "shared_buffers": "4GB",           # Reduced for CPU-only system
    "effective_cache_size": "12GB",    # Reduced for CPU-only system
    "maintenance_work_mem": "1GB",
    "work_mem": "64MB",
    "max_worker_processes": 4,         # Reduced for CPU-only system
    "max_parallel_workers": 4,
    "max_parallel_workers_per_gather": 2
} 

# Cablecast configuration
CABLECAST_BASE_URL = os.getenv("CABLECAST_BASE_URL", "https://rays-house.cablecast.net")
CABLECAST_SERVER_URL = os.getenv("CABLECAST_SERVER_URL", CABLECAST_BASE_URL)  # Backward compatibility
CABLECAST_API_KEY = os.getenv("CABLECAST_API_KEY", "your_api_key_here")
CABLECAST_USER_ID = os.getenv("CABLECAST_USER_ID", "")
CABLECAST_PASSWORD = os.getenv("CABLECAST_PASSWORD", "")
CABLECAST_LOCATION_ID = os.getenv("CABLECAST_LOCATION_ID", "123456")

# Request configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# VOD Integration Configuration
CABLECAST_API_URL = os.getenv("CABLECAST_API_URL", "https://vod.scctv.org/ui/api-docs/explorer")
VOD_DEFAULT_QUALITY = int(os.getenv("VOD_DEFAULT_QUALITY", "1"))
VOD_UPLOAD_TIMEOUT = int(os.getenv("VOD_UPLOAD_TIMEOUT", "300"))
VOD_MAX_RETRIES = int(os.getenv("VOD_MAX_RETRIES", "3"))
VOD_RETRY_DELAY = int(os.getenv("VOD_RETRY_DELAY", "60"))
VOD_BATCH_SIZE = int(os.getenv("VOD_BATCH_SIZE", "10"))
VOD_STATUS_CHECK_INTERVAL = int(os.getenv("VOD_STATUS_CHECK_INTERVAL", "30"))
VOD_PROCESSING_TIMEOUT = int(os.getenv("VOD_PROCESSING_TIMEOUT", "1800"))

# VOD Advanced Settings
VOD_ENABLE_CHAPTERS = os.getenv("VOD_ENABLE_CHAPTERS", "true").lower() == "true"
VOD_ENABLE_METADATA_ENHANCEMENT = os.getenv("VOD_ENABLE_METADATA_ENHANCEMENT", "true").lower() == "true"
VOD_ENABLE_AUTO_TAGGING = os.getenv("VOD_ENABLE_AUTO_TAGGING", "false").lower() == "true"

# VOD Quality Settings
VOD_QUALITY_LOW = int(os.getenv("VOD_QUALITY_LOW", "1"))
VOD_QUALITY_MEDIUM = int(os.getenv("VOD_QUALITY_MEDIUM", "2"))
VOD_QUALITY_HIGH = int(os.getenv("VOD_QUALITY_HIGH", "3"))
VOD_QUALITY_ORIGINAL = int(os.getenv("VOD_QUALITY_ORIGINAL", "4"))

# VOD Error Handling
VOD_ENABLE_RETRY_ON_FAILURE = os.getenv("VOD_ENABLE_RETRY_ON_FAILURE", "true").lower() == "true"
VOD_MAX_RETRY_ATTEMPTS = int(os.getenv("VOD_MAX_RETRY_ATTEMPTS", "5"))
VOD_RETRY_BACKOFF_MULTIPLIER = float(os.getenv("VOD_RETRY_BACKOFF_MULTIPLIER", "2"))

# VOD Logging
VOD_LOG_LEVEL = os.getenv("VOD_LOG_LEVEL", "INFO")
VOD_ENABLE_DEBUG_LOGGING = os.getenv("VOD_ENABLE_DEBUG_LOGGING", "false").lower() == "true"

# Local Summarization Configuration
SUMMARIZATION_MODEL = os.getenv("SUMMARIZATION_MODEL", "facebook/bart-large-cnn")
SUMMARIZATION_MAX_LENGTH = int(os.getenv("SUMMARIZATION_MAX_LENGTH", "100"))
SUMMARIZATION_MIN_LENGTH = int(os.getenv("SUMMARIZATION_MIN_LENGTH", "30"))
SUMMARIZATION_CHUNK_SIZE = int(os.getenv("SUMMARIZATION_CHUNK_SIZE", "5"))
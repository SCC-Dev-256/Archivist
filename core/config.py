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
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent

# Storage configuration
DEFAULT_MOUNT_POINTS = {
    'nas': '/mnt/nas',  # Default NAS mount
}

# Member City Flex Server Configuration
MEMBER_CITIES = {
    'flex1': {
        'name': 'Birchwood',
        'mount_path': '/mnt/flex-1',
        'description': 'Birchwood City Council and community content'
    },
    'flex2': {
        'name': 'Dellwood Grant Willernie',
        'mount_path': '/mnt/flex-2', 
        'description': 'Dellwood, Grant, and Willernie combined storage'
    },
    'flex3': {
        'name': 'Lake Elmo',
        'mount_path': '/mnt/flex-3',
        'description': 'Lake Elmo City Council and community content'
    },
    'flex4': {
        'name': 'Mahtomedi',
        'mount_path': '/mnt/flex-4',
        'description': 'Mahtomedi City Council and community content'
    },
    'flex5': {
        'name': 'Spare Record Storage 1',
        'mount_path': '/mnt/flex-5',
        'description': 'Spare storage for overflow and additional cities'
    },
    'flex6': {
        'name': 'Spare Record Storage 2', 
        'mount_path': '/mnt/flex-6',
        'description': 'Spare storage for overflow and additional cities'
    },
    'flex7': {
        'name': 'Oakdale',
        'mount_path': '/mnt/flex-7',
        'description': 'Oakdale City Council and community content'
    },
    'flex8': {
        'name': 'White Bear Lake',
        'mount_path': '/mnt/flex-8',
        'description': 'White Bear Lake City Council and community content'
    },
    'flex9': {
        'name': 'White Bear Township',
        'mount_path': '/mnt/flex-9',
        'description': 'White Bear Township Council and community content'
    }
}

# Add flex server mounts to default mount points
for city_id, city_config in MEMBER_CITIES.items():
    DEFAULT_MOUNT_POINTS[city_id] = city_config['mount_path']

# Get mount points from environment or use defaults
MOUNT_POINTS = {}
for mount_name, default_path in DEFAULT_MOUNT_POINTS.items():
    env_var = f"{mount_name.upper()}_PATH"
    MOUNT_POINTS[mount_name] = os.getenv(env_var, default_path)

# For backward compatibility
NAS_PATH = MOUNT_POINTS['nas']

# Get all Flex server paths (member cities)
FLEX_PATHS = {k: v for k, v in MOUNT_POINTS.items() if k.startswith('flex')}

# Location and User Configuration - Updated for member cities
LOCATIONS = {
    'default': {
        'name': 'Default Location',
        'member_cities': list(FLEX_PATHS.keys()),  # All member cities by default
        'allowed_users': ['*']  # All users by default
    },
    'birchwood': {
        'name': 'Birchwood',
        'member_cities': ['flex1'],
        'allowed_users': ['*']
    },
    'dellwood_grant_willernie': {
        'name': 'Dellwood Grant Willernie',
        'member_cities': ['flex2'],
        'allowed_users': ['*']
    },
    'lake_elmo': {
        'name': 'Lake Elmo',
        'member_cities': ['flex3'],
        'allowed_users': ['*']
    },
    'mahtomedi': {
        'name': 'Mahtomedi',
        'member_cities': ['flex4'],
        'allowed_users': ['*']
    },
    'oakdale': {
        'name': 'Oakdale',
        'member_cities': ['flex7'],
        'allowed_users': ['*']
    },
    'white_bear_lake': {
        'name': 'White Bear Lake',
        'member_cities': ['flex8'],
        'allowed_users': ['*']
    },
    'white_bear_township': {
        'name': 'White Bear Township',
        'member_cities': ['flex9'],
        'allowed_users': ['*']
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
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
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

# Database URL configuration
# Prefer explicit DATABASE_URL; otherwise, build from POSTGRES_* with proper URL-encoding
_env_database_url = os.getenv("DATABASE_URL", "").strip()
if _env_database_url:
    DATABASE_URL = _env_database_url
else:
    _pg_user = os.getenv("POSTGRES_USER", "archivist")
    _pg_pass_raw = os.getenv("POSTGRES_PASSWORD", "archivist_password")
    _pg_pass = quote_plus(_pg_pass_raw)
    _pg_host = os.getenv("POSTGRES_HOST", "localhost")
    _pg_port = os.getenv("POSTGRES_PORT", "5432")
    _pg_db = os.getenv("POSTGRES_DB", "archivist")
    DATABASE_URL = f"postgresql://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"

# Cablecast configuration
CABLECAST_BASE_URL = os.getenv("CABLECAST_BASE_URL", "https://rays-house.cablecast.net")
CABLECAST_SERVER_URL = os.getenv("CABLECAST_SERVER_URL", CABLECAST_BASE_URL)  # Backward compatibility
"""
PURPOSE: CABLECAST_API_URL should point to the full REST base, e.g. https://<host>/CablecastAPI/v1
DEPENDENCIES: core.cablecast_client.CablecastAPIClient
MODIFICATION NOTES: v2025-08-08 ensure single source of truth and remove duplicate override
"""
CABLECAST_API_URL = os.getenv("CABLECAST_API_URL", "https://192.168.181.55/CablecastAPI/v1")
CABLECAST_USER_ID = os.getenv("CABLECAST_USER_ID", "admin")
CABLECAST_PASSWORD = os.getenv("CABLECAST_PASSWORD", "rwscctrms")
CABLECAST_LOCATION_ID = os.getenv("CABLECAST_LOCATION_ID", "3")
CABLECAST_API_KEY = os.getenv("CABLECAST_API_KEY", "")
CABLECAST_VERIFY_SSL = os.getenv("CABLECAST_VERIFY_SSL", "false").lower() == "true"
CABLECAST_CHANNEL_ID = os.getenv("CABLECAST_CHANNEL_ID", "")
CABLECAST_DEFAULT_RUN_SECONDS = int(os.getenv("CABLECAST_DEFAULT_RUN_SECONDS", "7200"))

# Optional: Channel ID -> city key mapping for precise device targeting by channel
#I personally don't understand this, but it's here for reference
CABLECAST_CHANNEL_TO_CITY_JSON = os.getenv("CABLECAST_CHANNEL_TO_CITY_JSON", "")
CABLECAST_CHANNEL_TO_CITY: dict[str, str] = {}
if CABLECAST_CHANNEL_TO_CITY_JSON and os.path.exists(CABLECAST_CHANNEL_TO_CITY_JSON):
    try:
        import json
        with open(CABLECAST_CHANNEL_TO_CITY_JSON, "r") as f:
            CABLECAST_CHANNEL_TO_CITY = json.load(f)
    except Exception:
        CABLECAST_CHANNEL_TO_CITY = {}

_CHANNEL_TO_CITY_INLINE = os.getenv("CABLECAST_CHANNEL_TO_CITY", "")
if _CHANNEL_TO_CITY_INLINE:
    try:
        import json
        CABLECAST_CHANNEL_TO_CITY = json.loads(_CHANNEL_TO_CITY_INLINE)
    except Exception:
        pass

# Channel ID mapping for reference
CABLECAST_CHANNEL_IDS = {
    3: "SCC Community",
    4: "SCC Community2",
    5: "Birchwood",
    6: "Dellwood Grant Willernie",
    7: "Lake Elmo",
    8: "Mahtomedi",
    #9: "SCC Community (?)",
    #10: "SCC Community (?)",
    11: "Oakdale",
    12: "White Bear Lake",
    13: "White Bear Township",
    #14: "SCC Community (?)",
    #15: "SCC Community (?)",
    #16: "SCC Community (?)",
    18: "SCC Government",
    #23: "SCC Community (?)",
    24: "Commission Meetings",
    #27: "SCC Community (?)",
    #1034: "Unknown"
}


# Request configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# VOD Integration Configuration
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

# AJA HELO integration configuration
# Map member cities to HELO device connection info. Preferred via JSON file path for flexibility.
HELO_DEVICES_JSON = os.getenv("HELO_DEVICES_JSON", "")
HELO_DEVICES: dict = {}
if HELO_DEVICES_JSON and os.path.exists(HELO_DEVICES_JSON):
    import json
    try:
        with open(HELO_DEVICES_JSON, "r") as f:
            HELO_DEVICES = json.load(f)
    except Exception:
        HELO_DEVICES = {}

# Fallback simple env-based mapping for a single device per city
# Example: export HELO_FLEX1_IP=10.0.0.10 HELO_FLEX1_USER=admin HELO_FLEX1_PASS=admin
for city_key in FLEX_PATHS.keys():
    env_key = city_key.upper()
    ip = os.getenv(f"HELO_{env_key}_IP")
    if ip:
        HELO_DEVICES[city_key] = {
            "ip": ip,
            "username": os.getenv(f"HELO_{env_key}_USER", ""),
            "password": os.getenv(f"HELO_{env_key}_PASS", ""),
            # Optional RTMP defaults for streaming
            "rtmp_url": os.getenv(f"HELO_{env_key}_RTMP_URL", ""),
            "stream_key": os.getenv(f"HELO_{env_key}_STREAM_KEY", ""),
        }

HELO_REQUEST_TIMEOUT = int(os.getenv("HELO_REQUEST_TIMEOUT", "10"))
HELO_MAX_RETRIES = int(os.getenv("HELO_MAX_RETRIES", "3"))
HELO_SCHEDULE_LOOKAHEAD_MIN = int(os.getenv("HELO_SCHEDULE_LOOKAHEAD_MIN", "360"))  # 6 hours
HELO_ENABLE_RUNTIME_TRIGGERS = os.getenv("HELO_ENABLE_RUNTIME_TRIGGERS", "true").lower() == "true"

# Optional: Cablecast location -> city key mapping for precise targeting
CABLECAST_LOCATION_TO_CITY_JSON = os.getenv("CABLECAST_LOCATION_TO_CITY_JSON", "")
CABLECAST_LOCATION_TO_CITY: dict = {}
if CABLECAST_LOCATION_TO_CITY_JSON and os.path.exists(CABLECAST_LOCATION_TO_CITY_JSON):
    import json  # safe: may already be imported above
    try:
        with open(CABLECAST_LOCATION_TO_CITY_JSON, "r") as f:
            CABLECAST_LOCATION_TO_CITY = json.load(f)
    except Exception:
        CABLECAST_LOCATION_TO_CITY = {}

# Also allow inline JSON in env var for convenience
_LOC_TO_CITY_INLINE = os.getenv("CABLECAST_LOCATION_TO_CITY", "")
if _LOC_TO_CITY_INLINE:
    try:
        import json
        CABLECAST_LOCATION_TO_CITY = json.loads(_LOC_TO_CITY_INLINE)
    except Exception:
        pass

# Optional: Title alias -> HELO city key mapping to map show titles to a specific device
CITY_ALIASES_TO_HELO_JSON = os.getenv("CITY_ALIASES_TO_HELO_JSON", "")
CITY_ALIASES_TO_HELO: dict[str, str] = {}
if CITY_ALIASES_TO_HELO_JSON and os.path.exists(CITY_ALIASES_TO_HELO_JSON):
    try:
        import json
        with open(CITY_ALIASES_TO_HELO_JSON, "r") as f:
            CITY_ALIASES_TO_HELO = json.load(f)
    except Exception:
        CITY_ALIASES_TO_HELO = {}

_CITY_ALIASES_INLINE = os.getenv("CITY_ALIASES_TO_HELO", "")
if _CITY_ALIASES_INLINE:
    try:
        import json
        CITY_ALIASES_TO_HELO = json.loads(_CITY_ALIASES_INLINE)
    except Exception:
        pass
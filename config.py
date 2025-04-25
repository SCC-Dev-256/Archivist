import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
NAS_PATH = os.getenv("NAS_PATH", "/mnt/nas/media")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(BASE_DIR / "output"))

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# WhisperX configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v2")
COMPUTE_TYPE = "float16" if os.getenv("USE_GPU", "true").lower() == "true" else "int8"

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "1"))

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# PostgreSQL configuration
POSTGRES_CONFIG = {
    "shared_buffers": "17GB",          # 25% of RAM
    "effective_cache_size": "53GB",    # 75% of RAM
    "maintenance_work_mem": "2GB",
    "work_mem": "128MB",
    "max_worker_processes": 16,        # Match CPU cores
    "max_parallel_workers": 16,
    "max_parallel_workers_per_gather": 8
} 
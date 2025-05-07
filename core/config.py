import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
NAS_PATH = os.getenv("NAS_PATH", "/mnt")  # Updated to allow browsing all flex mounts
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(NAS_PATH, "transcriptions"))

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

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
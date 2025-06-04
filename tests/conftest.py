import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set test environment variables
os.environ["TESTING"] = "true"
os.environ["NAS_PATH"] = "/tmp/test_nas"
os.environ["OUTPUT_DIR"] = "/tmp/test_output"

# Create test directories
os.makedirs(os.environ["NAS_PATH"], exist_ok=True)
os.makedirs(os.environ["OUTPUT_DIR"], exist_ok=True) 
#!/bin/bash

# Set the project root directory
export PROJECT_ROOT="/opt/Archivist"

# Set Python path to include the project root
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Change to the project directory
cd "${PROJECT_ROOT}"

# Activate virtual environment if it exists
if [ -d "venv_py311" ]; then
    source venv_py311/bin/activate
fi

# Start the integrated system
echo "Starting Integrated VOD Processing System..."
echo "PYTHONPATH: ${PYTHONPATH}"
echo "Project Root: ${PROJECT_ROOT}"

python3 scripts/deployment/start_integrated_system.py 
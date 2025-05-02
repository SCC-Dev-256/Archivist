#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create templates directory if it doesn't exist
mkdir -p core/templates

# Add the current directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run the Flask application
export FLASK_APP=core.web_app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000 
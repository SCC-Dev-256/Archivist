# Deployment Scripts

This directory contains scripts for deploying and running the Archivist system.

## Scripts

- **deploy.sh** - Main deployment script
- **start_archivist.sh** - Start the Archivist system
- **stop_archivist.sh** - Stop the Archivist system
- **run_web.sh** - Run the web interface
- **run_worker.sh** - Run the Celery worker
- **run_worker_debug.sh** - Run the Celery worker in debug mode
- **start_archivist_centralized.py** - Centralized system startup
- **start_archivist_centralized.sh** - Centralized system startup script
- **start_complete_system.py** - Start complete system
- **start_integrated_system.py** - Start integrated system
- **start_vod_system_simple.py** - Start VOD system
- **init-letsencrypt.sh** - Initialize Let's Encrypt certificates
- **setup-grafana.sh** - Setup Grafana monitoring

## Usage

Most scripts can be run directly from this directory. For example:
```bash
./start_archivist.sh
./run_web.sh
```

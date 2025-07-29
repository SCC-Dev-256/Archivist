# Deployment Scripts

This directory contains scripts for deploying and running the Archivist system.

## Quick Start

### For Development/Testing:
```bash
# Start the web UI for testing
python3 test_web_ui.py

# Or use the web script (requires gunicorn)
bash scripts/deployment/run_web.sh
```

### For Production:
```bash
# Start the complete system
bash scripts/deployment/start_archivist.sh

# Or use the centralized startup
bash scripts/deployment/start_archivist_centralized.sh
```

## Script Overview

### Core System Scripts
- **start_archivist.sh** - Start the complete Archivist system (web + workers)
- **run_web.sh** - Start only the web server (requires gunicorn)
- **run_worker.sh** - Start Celery worker for transcription tasks
- **run_worker_debug.sh** - Start Celery worker in debug mode
- **stop_archivist.sh** - Stop all Archivist processes

### Advanced Deployment
- **start_archivist_centralized.py** - Python-based centralized system startup
- **start_archivist_centralized.sh** - Shell-based centralized system startup
- **start_integrated_system.py** - Integrated system with monitoring
- **start_complete_system.py** - Complete system with all components
- **start_vod_system_simple.py** - VOD processing system only

### Infrastructure Setup
- **setup-grafana.sh** - Setup Grafana monitoring dashboard
- **init-letsencrypt.sh** - Initialize Let's Encrypt SSL certificates
- **deploy.sh** - Full deployment automation script

## System Architecture

### Current Stack:
- **Web Server**: Flask with Socket.IO (development) / Gunicorn (production)
- **Task Queue**: Celery with Redis broker
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for caching and rate limiting
- **Monitoring**: Grafana + Prometheus (optional)

### Key Changes:
- ✅ **Migrated from RQ to Celery** for task management
- ✅ **Centralized imports** in `core/__init__.py`
- ✅ **Fixed signal handling** issues in background threads
- ✅ **Updated virtual environment** references to `venv_py311`

## Environment Requirements

### Required Services:
- **Redis**: `redis-server` (for Celery broker and caching)
- **PostgreSQL**: `postgresql` (for data persistence)
- **Python**: `venv_py311` virtual environment

### Optional Services:
- **Gunicorn**: For production web server
- **Grafana**: For monitoring dashboard
- **Certbot**: For SSL certificates

## Usage Examples

### Development Testing:
```bash
# Start web UI for captioning system testing
python3 test_web_ui.py

# Access at: http://localhost:5050
```

### Production Deployment:
```bash
# Start complete system
bash scripts/deployment/start_archivist.sh

# Monitor system health
python3 scripts/monitoring/monitor.py

# Run system tests
bash scripts/development/run_tests.sh
```

### Worker Management:
```bash
# Start transcription worker
bash scripts/deployment/run_worker.sh

# Start debug worker
bash scripts/deployment/run_worker_debug.sh

# Monitor worker status
celery -A core.tasks inspect active
```

## Troubleshooting

### Common Issues:
1. **Redis Connection**: Ensure Redis is running (`redis-cli ping`)
2. **Database Connection**: Check PostgreSQL status (`pg_isready`)
3. **Virtual Environment**: Activate `venv_py311` before running scripts
4. **Port Conflicts**: Ensure port 5050 is available

### Debug Mode:
```bash
# Start system in debug mode
bash scripts/deployment/run_worker_debug.sh

# Check logs
tail -f logs/archivist.log
tail -f logs/celery-worker.log
```

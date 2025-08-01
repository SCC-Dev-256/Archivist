# Scripts Directory

This directory contains all scripts for the Archivist system, organized by category.

## Directory Structure

```
scripts/
├── deployment/          # Deployment and system startup scripts
├── development/         # Development and testing scripts
├── maintenance/         # System maintenance and code organization
├── monitoring/          # Monitoring and health check scripts
├── security/           # Security scanning and configuration
├── setup/              # Initial setup and configuration scripts
├── utils/              # Utility scripts
└── logs/               # Script logs and reports
```

## Quick Start

### For Development/Testing:
```bash
# Start the web UI for captioning system testing
python3 test_web_ui.py

# Access at: http://localhost:5050
```

### For Production:
```bash
# Start the complete system
bash scripts/deployment/start_archivist.sh

# Monitor system health
python3 scripts/monitoring/monitor.py
```

## Categories

### Deployment Scripts (`deployment/`)
Scripts for deploying and running the Archivist system:
- **Core System**: `start_archivist.sh`, `run_web.sh`, `run_worker.sh`
- **Advanced**: `start_archivist_centralized.py`, `start_integrated_system.py`
- **Infrastructure**: `setup-grafana.sh`, `init-letsencrypt.sh`, `deploy.sh`

### Development Scripts (`development/`)
Scripts for development and testing:
- **Testing**: `run_tests.sh` - Test API endpoints and system health
- **Utilities**: `vod_cli.py`, `test_cablecast_auth.py`, `backfill_transcriptions.py`
- **Documentation**: `update_docs.py` - Update documentation files

### Maintenance Scripts (`maintenance/`)
Scripts for system maintenance:
- **Code Organization**: `reorganize_codebase.py`, `reorganize_directory_structure.py`
- **Dependencies**: `manage_deps.py` - Manage Python dependencies

### Monitoring Scripts (`monitoring/`)
Scripts for monitoring and health checks:
- **System Monitoring**: `monitor.py` - Real-time system health monitoring
- **VOD Monitoring**: `vod_sync_monitor.py` - VOD synchronization monitoring
- **Debug Tools**: `show_debug_logs.sh` - View and analyze debug logs
- **Status Check**: `system_status.py` - Comprehensive system status

### Security Scripts (`security/`)
Scripts for security:
- **Security Scanning**: Various security audit scripts
- **GitHub Actions**: CI/CD pipeline management

### Setup Scripts (`setup/`)
Scripts for initial setup:
- **Cablecast Integration**: Setup Cablecast API integration
- **Credential Management**: Create and manage system credentials
- **Mount Configuration**: Configure NAS mounts and file systems
- **System Initialization**: Initial system setup and configuration

### Utility Scripts (`utils/`)
General utility scripts:
- **File Processing**: `transdirectmake.py` - Transcription directory management
- **System Tools**: `download_pyan_seg.sh`, `sitecustomize.py`

## System Architecture

### Current Stack (Updated):
- **Web Server**: Flask with Socket.IO (development) / Gunicorn (production)
- **Task Queue**: Celery with Redis broker (migrated from RQ)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for caching and rate limiting
- **Monitoring**: Grafana + Prometheus (optional)

### Key Updates:
- ✅ **Celery Migration**: All worker scripts now use Celery instead of RQ
- ✅ **Import Centralization**: Fixed circular imports via `core/__init__.py`
- ✅ **Signal Handling**: Removed signal-based timeouts that caused thread issues
- ✅ **Virtual Environment**: Standardized on `venv_py311`

## Usage Examples

### Development Testing:
```bash
# Start web UI for testing
python3 test_web_ui.py

# Run system tests
bash scripts/development/run_tests.sh

# Monitor system health
python3 scripts/monitoring/monitor.py
```

### Production Deployment:
```bash
# Start complete system
bash scripts/deployment/start_archivist.sh

# Start individual components
bash scripts/deployment/run_web.sh
bash scripts/deployment/run_worker.sh

# Monitor and debug
bash scripts/monitoring/show_debug_logs.sh
```

### Maintenance:
```bash
# Reorganize codebase
python3 scripts/maintenance/reorganize_codebase.py

# Manage dependencies
python3 scripts/maintenance/manage_deps.py

# Update documentation
python3 scripts/development/update_docs.py
```

## Running Scripts

Most scripts can be run directly from their respective directories. For example:
```bash
# Run deployment script
bash scripts/deployment/start_archivist.sh

# Run development test
bash scripts/development/run_tests.sh

# Run monitoring script
python3 scripts/monitoring/monitor.py
```

## Troubleshooting

### Common Issues:
1. **Virtual Environment**: Always activate `venv_py311` before running scripts
2. **Redis Connection**: Ensure Redis is running (`redis-cli ping`)
3. **Database Connection**: Check PostgreSQL status (`pg_isready`)
4. **Port Conflicts**: Ensure port 5050 is available

### Debug Mode:
```bash
# Start worker in debug mode
bash scripts/deployment/run_worker_debug.sh

# View debug logs
bash scripts/monitoring/show_debug_logs.sh
``` 
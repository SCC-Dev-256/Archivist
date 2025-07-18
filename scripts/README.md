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

## Categories

### Deployment Scripts (`deployment/`)
Scripts for deploying and running the Archivist system:
- System startup/shutdown scripts
- Web and worker process management
- Deployment automation
- Certificate and monitoring setup

### Development Scripts (`development/`)
Scripts for development and testing:
- Test runners
- Development utilities
- Documentation updates
- Database setup

### Maintenance Scripts (`maintenance/`)
Scripts for system maintenance:
- Dependency management
- Code reorganization
- System cleanup

### Monitoring Scripts (`monitoring/`)
Scripts for monitoring and health checks:
- System monitoring
- VOD synchronization monitoring
- Debug log viewing
- System status checking

### Security Scripts (`security/`)
Scripts for security:
- Security scanning
- GitHub Actions management

### Setup Scripts (`setup/`)
Scripts for initial setup:
- Cablecast integration setup
- Credential creation
- Mount configuration
- System initialization

### Utility Scripts (`utils/`)
General utility scripts:
- File processing
- System customization
- Various utilities

## Usage

Each subdirectory contains a README with specific usage instructions for the scripts in that category.

## Running Scripts

Most scripts can be run directly from their respective directories. For example:
```bash
# Run deployment script
./scripts/deployment/start_archivist.sh

# Run development test
python3 scripts/development/run_tests.sh

# Run monitoring script
python3 scripts/monitoring/monitor.py
``` 
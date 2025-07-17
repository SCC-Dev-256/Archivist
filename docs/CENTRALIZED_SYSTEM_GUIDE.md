# Centralized Archivist System Guide

## Overview

The Centralized Archivist System provides a unified startup and management solution for all Archivist services with full GUI integration, automatic restart capabilities, and comprehensive monitoring.

## 🚀 Quick Start

### Python Version
```bash
# Start all services
python3 start_archivist_centralized.py

# Stop all services (Ctrl+C)
```

### Shell Script Version
```bash
# Start all services
./start_archivist_centralized.sh

# Stop all services (Ctrl+C)
```

## 📋 System Components

### Core Services (Startup Order)
1. **Redis** - Message broker and caching
2. **PostgreSQL** - Database
3. **Celery Worker** - Task processing
4. **Celery Beat** - Scheduled tasks
5. **VOD Sync Monitor** - VOD synchronization
6. **Admin UI** - Main administration interface
7. **Monitoring Dashboard** - Real-time monitoring

### GUI Integration
- **Admin UI** (Port 8080): Main administration interface
- **Monitoring Dashboard** (Port 5051): Real-time monitoring and task management
- **Cross-linking**: Both GUIs can communicate and link to each other
- **Unified Task Management**: Single interface for RQ and Celery tasks

## 🔗 GUI Connectivity Features

### Admin UI ↔ Monitoring Dashboard Integration
- **Cross-linking**: Click links in Admin UI to open monitoring dashboard
- **Shared APIs**: Both GUIs access the same backend APIs
- **Unified Task Queue**: Manage both RQ transcription jobs and Celery VOD tasks
- **Real-time Updates**: Live status updates across both interfaces

### Unified Task Management
- **RQ Jobs**: Transcription queue management
- **Celery Tasks**: VOD processing tasks
- **Combined View**: Single interface showing all task types
- **Task Control**: Start, stop, pause, resume, and reorder tasks

## 🔄 Service Management

### Automatic Startup Order
The system ensures services start in the correct dependency order:
```
Redis → PostgreSQL → Celery Worker → Celery Beat → VOD Sync Monitor → Admin UI → Monitoring Dashboard
```

### Health Monitoring
- **Real-time Health Checks**: Continuous monitoring of all services
- **Automatic Restart**: Failed services restart automatically (max 3 attempts)
- **Graceful Shutdown**: Proper cleanup on system shutdown
- **Status Reporting**: Live status updates in both GUIs

### Service Health Checks
- **Redis**: `redis-cli ping`
- **PostgreSQL**: `pg_isready`
- **Admin UI**: HTTP health endpoint
- **Dashboard**: HTTP health endpoint
- **Celery**: Worker inspection
- **VOD Sync**: Monitor process status

## 📊 Monitoring Dashboard Features

### Real-time Monitoring
- **System Metrics**: CPU, memory, disk usage
- **Service Status**: All service health indicators
- **Task Queues**: RQ and Celery task status
- **Performance Metrics**: Response times and throughput

### VOD Integration
- **VOD Sync Status**: Real-time VOD synchronization monitoring
- **VOD Automation**: Transcription-to-show linking interface
- **Queue Management**: Process transcription linking queue
- **Manual Linking**: Link transcriptions to specific shows

### Task Management
- **Unified Queue View**: Combined RQ and Celery tasks
- **Task Control**: Start, stop, pause, resume tasks
- **Queue Reordering**: Change task execution order
- **Progress Tracking**: Real-time task progress updates

## 🎬 VOD Processing Integration

### VOD Sync Monitor
- **Automatic Monitoring**: Continuous VOD synchronization checks
- **Health Reporting**: Integration with main monitoring dashboard
- **Failure Detection**: Automatic detection of sync issues
- **Status API**: REST API for VOD sync status

### VOD Automation
- **Auto-linking**: Automatic transcription-to-show linking
- **Manual Linking**: Manual transcription-to-show assignment
- **Show Suggestions**: AI-powered show matching suggestions
- **Queue Processing**: Batch processing of unlinked transcriptions

## 🔧 Configuration

### Environment Variables
```bash
# Service Ports
ADMIN_UI_PORT=8080
DASHBOARD_PORT=5051
REDIS_PORT=6379
POSTGRESQL_PORT=5432

# VOD Processing
VOD_PROCESSING_TIME=19:00

# Celery Configuration
CELERY_WORKER_CONCURRENCY=2
CELERY_TASK_TIMEOUT=7200

# Restart Configuration
MAX_RESTART_ATTEMPTS=3
RESTART_DELAY=10
```

### Directory Structure
```
/opt/Archivist/
├── start_archivist_centralized.py      # Python startup script
├── start_archivist_centralized.sh      # Shell startup script
├── logs/                               # System logs
│   ├── centralized_system.log
│   ├── admin_ui.log
│   ├── monitoring_dashboard.log
│   ├── celery_worker.log
│   ├── celery_beat.log
│   └── vod_sync_monitor.log
├── pids/                               # Process ID files
│   ├── admin_ui.pid
│   ├── monitoring_dashboard.pid
│   ├── celery_worker.pid
│   └── celery_beat.pid
└── core/                               # Application code
    ├── admin_ui.py
    ├── monitoring/
    │   └── integrated_dashboard.py
    ├── vod_automation.py
    └── task_queue.py
```

## 📡 API Endpoints

### Monitoring Dashboard APIs
- `GET /api/metrics` - System metrics
- `GET /api/health` - Health check data
- `GET /api/queue/jobs` - RQ queue jobs
- `GET /api/celery/tasks` - Celery task statistics
- `GET /api/celery/workers` - Celery worker status
- `GET /api/unified/tasks` - Combined RQ + Celery tasks

### VOD Integration APIs
- `GET /api/vod/sync-status` - VOD sync monitor status
- `GET /api/vod/automation/status` - VOD automation status
- `POST /api/vod/automation/link/<id>` - Auto-link transcription
- `POST /api/vod/automation/manual-link/<id>/<show_id>` - Manual link
- `GET /api/vod/automation/suggestions/<id>` - Show suggestions
- `POST /api/vod/automation/process-queue` - Process linking queue

### Task Management APIs
- `POST /api/queue/jobs/<id>/stop` - Stop RQ job
- `POST /api/queue/jobs/<id>/pause` - Pause RQ job
- `POST /api/queue/jobs/<id>/resume` - Resume RQ job
- `POST /api/queue/jobs/<id>/reorder` - Reorder RQ job
- `DELETE /api/queue/jobs/<id>/remove` - Remove RQ job

## 🛠️ Troubleshooting

### Common Issues

#### Service Won't Start
1. Check dependencies: `./start_archivist_centralized.sh` (will show dependency status)
2. Check logs: `tail -f logs/centralized_system.log`
3. Check service-specific logs: `tail -f logs/[service_name].log`

#### GUI Not Accessible
1. Check if services are running: `ps aux | grep python`
2. Check ports: `netstat -tlnp | grep :8080` and `netstat -tlnp | grep :5051`
3. Check firewall: Ensure ports 8080 and 5051 are open

#### Task Queue Issues
1. Check Redis: `redis-cli ping`
2. Check Celery workers: `celery -A core.tasks inspect active`
3. Check RQ queue: Access via Admin UI or monitoring dashboard

#### VOD Processing Issues
1. Check VOD sync monitor: `tail -f logs/vod_sync_monitor.log`
2. Check flex mounts: `mount | grep flex`
3. Check Cablecast API: Verify API credentials and connectivity

### Log Locations
- **System Log**: `logs/centralized_system.log`
- **Admin UI**: `logs/admin_ui.log`
- **Dashboard**: `logs/monitoring_dashboard.log`
- **Celery Worker**: `logs/celery_worker.log`
- **Celery Beat**: `logs/celery_beat.log`
- **VOD Sync**: `logs/vod_sync_monitor.log`

### Health Check Commands
```bash
# Check all services
curl http://localhost:5051/api/health

# Check Admin UI
curl http://localhost:8080/api/admin/status

# Check Redis
redis-cli ping

# Check PostgreSQL
pg_isready

# Check Celery workers
celery -A core.tasks inspect active
```

## 🔄 Service Lifecycle

### Startup Process
1. **Dependency Check**: Verify Python, Redis, PostgreSQL, flex mounts
2. **Service Startup**: Start services in dependency order
3. **Health Verification**: Verify each service is healthy
4. **GUI Launch**: Start Admin UI and monitoring dashboard
5. **Monitoring**: Begin continuous health monitoring

### Shutdown Process
1. **Signal Handling**: Catch SIGINT/SIGTERM
2. **Service Stop**: Stop services in reverse order
3. **Cleanup**: Remove PID files and cleanup resources
4. **Graceful Exit**: Exit with proper status codes

### Restart Process
1. **Failure Detection**: Monitor service health
2. **Restart Attempt**: Attempt service restart
3. **Backoff Delay**: Wait before retry
4. **Max Attempts**: Limit restart attempts to prevent loops

## 📈 Performance Monitoring

### Metrics Collection
- **System Metrics**: CPU, memory, disk, network
- **Application Metrics**: Request rates, response times
- **Task Metrics**: Queue lengths, processing times
- **VOD Metrics**: Sync status, processing rates

### Dashboard Features
- **Real-time Charts**: Live performance graphs
- **Alert System**: Automatic alerts for issues
- **Historical Data**: Performance trends over time
- **Export Capabilities**: Data export for analysis

## 🔐 Security Features

### HTTPS Enforcement
- **SSL/TLS**: All web interfaces use HTTPS
- **Certificate Management**: Automatic Let's Encrypt integration
- **Secure Headers**: Security headers for web applications

### Access Control
- **Rate Limiting**: API rate limiting to prevent abuse
- **Authentication**: Secure authentication for admin interfaces
- **Authorization**: Role-based access control

## 🚀 Production Deployment

### System Requirements
- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM recommended
- **Storage**: 100GB+ available space
- **Network**: Stable internet connection for API access

### Deployment Steps
1. **Install Dependencies**: Python 3.11+, Redis, PostgreSQL
2. **Configure Environment**: Set up environment variables
3. **Start System**: Run centralized startup script
4. **Verify Health**: Check all services are running
5. **Monitor**: Use monitoring dashboard for ongoing management

### Backup Strategy
- **Database**: Regular PostgreSQL backups
- **Configuration**: Backup configuration files
- **Logs**: Archive logs for troubleshooting
- **VOD Data**: Backup VOD processing results

## 📞 Support

### Getting Help
1. **Check Logs**: Review system and service logs
2. **Health Dashboard**: Use monitoring dashboard for diagnostics
3. **Documentation**: Refer to this guide and other documentation
4. **Community**: Check project documentation and forums

### Emergency Procedures
1. **Service Failure**: Check logs and restart individual services
2. **System Crash**: Restart with centralized script
3. **Data Loss**: Restore from backups
4. **Security Breach**: Review logs and update credentials

---

*This guide covers the complete centralized Archivist system. For specific component details, refer to individual component documentation.* 
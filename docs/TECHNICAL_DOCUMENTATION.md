# Technical Documentation

Technical reference for Archivist system architecture, configuration, deployment, and maintenance.

## 🏗️ System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHIVIST SYSTEM                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Web Server    │  │  Transcription  │  │   VOD Service   │ │
│  │   (Flask)       │  │    Service      │  │   (Cablecast)   │ │
│  │                 │  │   (WhisperX)    │  │                 │ │
│  │ • API Routes    │  │ • Audio Extract │  │ • Publishing    │ │
│  │ • Auth System   │  │ • SCC Format    │  │ • Metadata      │ │
│  │ • File Browse   │  │ • Summarization │  │ • Integration   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                      │                      │       │
│           └──────────────────────┼──────────────────────┘       │
│                                  │                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Database      │  │  Queue System   │  │  Storage Layer  │ │
│  │  (PostgreSQL)   │  │    (Redis)      │  │  (Flex Servers) │ │
│  │                 │  │                 │  │                 │ │
│  │ • Transcripts   │  │ • Job Queue     │  │ • NFS Mounts    │ │
│  │ • Users/Auth    │  │ • Progress      │  │ • File System   │ │
│  │ • VOD Metadata  │  │ • Scheduling    │  │ • Backup        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend Framework:**
- **Flask**: Web framework and API server
- **SQLAlchemy**: Database ORM
- **Celery**: Distributed task queue
- **Redis**: Message broker and caching
- **PostgreSQL**: Primary database

**Transcription Engine:**
- **WhisperX**: Advanced speech recognition
- **Local Models**: Self-hosted AI models
- **SCC Format**: Scenarist Closed Caption output
- **SMPTE Timestamps**: Industry-standard timing

**Storage Infrastructure:**
- **NFS**: Network file system
- **Flex Servers**: Distributed storage
- **Backup Systems**: Automated data protection
- **Mount Management**: Dynamic storage allocation

**Integration Layer:**
- **Cablecast API**: VOD platform integration
- **Webhook System**: Event notifications
- **REST API**: External system integration
- **Authentication**: Multi-tier security

## 🔧 Configuration Management

### Environment Configuration

```bash
# /opt/Archivist/.env

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/archivist_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Transcription Configuration
WHISPER_MODEL_PATH=/opt/models/whisper-large-v2
WHISPER_DEVICE=cpu
WHISPER_BATCH_SIZE=16
WHISPER_COMPUTE_TYPE=int8
DEFAULT_LANGUAGE=en
OUTPUT_FORMAT=scc
INCLUDE_SUMMARY=true

# Storage Configuration
FLEX_SERVERS=/mnt/flex-1,/mnt/flex-2,/mnt/flex-3,/mnt/flex-4,/mnt/flex-5
DEFAULT_OUTPUT_PATH=/mnt/flex-1/transcriptions
TEMP_DIRECTORY=/tmp/archivist
MAX_FILE_SIZE=10737418240  # 10GB

# Queue Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_WORKER_CONCURRENCY=4
CELERY_TASK_TIMEOUT=7200  # 2 hours
MAX_QUEUE_SIZE=100

# VOD Configuration
CABLECAST_API_URL=https://your-cablecast-server.com/api
CABLECAST_API_KEY=your-api-key
CABLECAST_LOCATION_ID=1
AUTO_PUBLISH_TO_VOD=true
VOD_DEFAULT_QUALITY=1080
VOD_TIMEOUT=300

# Security Configuration
JWT_SECRET_KEY=your-jwt-secret
SESSION_TIMEOUT=3600
API_RATE_LIMIT=100
WEBHOOK_TIMEOUT=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/archivist/archivist.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5
```

### Application Configuration

```python
# /opt/Archivist/config.py

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = int(os.environ.get('DATABASE_POOL_SIZE', 20))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get('DATABASE_MAX_OVERFLOW', 30))
    
    # Redis settings
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Transcription settings
    WHISPER_MODEL_PATH = os.environ.get('WHISPER_MODEL_PATH', '/opt/models/whisper-large-v2')
    WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE', 'cpu')
    WHISPER_BATCH_SIZE = int(os.environ.get('WHISPER_BATCH_SIZE', 16))
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'en')
    OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'scc')
    INCLUDE_SUMMARY = os.environ.get('INCLUDE_SUMMARY', 'true').lower() == 'true'
    
    # Storage settings
    FLEX_SERVERS = os.environ.get('FLEX_SERVERS', '').split(',')
    DEFAULT_OUTPUT_PATH = os.environ.get('DEFAULT_OUTPUT_PATH', '/mnt/flex-1/transcriptions')
    TEMP_DIRECTORY = os.environ.get('TEMP_DIRECTORY', '/tmp/archivist')
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 10737418240))
    
    # Queue settings
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', 4))
    
    # VOD settings
    CABLECAST_API_URL = os.environ.get('CABLECAST_API_URL')
    CABLECAST_API_KEY = os.environ.get('CABLECAST_API_KEY')
    AUTO_PUBLISH_TO_VOD = os.environ.get('AUTO_PUBLISH_TO_VOD', 'true').lower() == 'true'
    
    # Security settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 100))

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'INFO'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

## 📊 Database Schema

### Core Tables

```sql
-- Users and Authentication
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Transcription Jobs
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    duration INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    language VARCHAR(10) DEFAULT 'en',
    model VARCHAR(50) DEFAULT 'large-v2',
    output_format VARCHAR(10) DEFAULT 'scc',
    include_summary BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_date TIMESTAMP,
    completed_date TIMESTAMP,
    scc_file_path VARCHAR(500),
    summary_file_path VARCHAR(500),
    metadata_file_path VARCHAR(500),
    error_message TEXT,
    processing_time INTEGER,
    vod_id VARCHAR(100),
    vod_url VARCHAR(500),
    vod_status VARCHAR(20)
);

-- Cablecast Shows
CREATE TABLE cablecast_shows (
    id SERIAL PRIMARY KEY,
    cablecast_id INTEGER UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    producer VARCHAR(100),
    runtime INTEGER,
    created_date TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- VOD Content
CREATE TABLE vod_content (
    id SERIAL PRIMARY KEY,
    transcription_id UUID REFERENCES transcriptions(id),
    cablecast_show_id INTEGER REFERENCES cablecast_shows(id),
    vod_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    duration INTEGER,
    quality INTEGER,
    status VARCHAR(20) DEFAULT 'processing',
    published_date TIMESTAMP,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API Keys
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions TEXT[],
    active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System Logs
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    component VARCHAR(50),
    user_id INTEGER REFERENCES users(id),
    transcription_id UUID REFERENCES transcriptions(id),
    metadata JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes and Constraints

```sql
-- Performance indexes
CREATE INDEX idx_transcriptions_status ON transcriptions(status);
CREATE INDEX idx_transcriptions_user_id ON transcriptions(user_id);
CREATE INDEX idx_transcriptions_created_date ON transcriptions(created_date);
CREATE INDEX idx_transcriptions_vod_status ON transcriptions(vod_status);

CREATE INDEX idx_cablecast_shows_cablecast_id ON cablecast_shows(cablecast_id);
CREATE INDEX idx_cablecast_shows_title ON cablecast_shows(title);

CREATE INDEX idx_vod_content_transcription_id ON vod_content(transcription_id);
CREATE INDEX idx_vod_content_status ON vod_content(status);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(active);

CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_component ON system_logs(component);
CREATE INDEX idx_system_logs_created_date ON system_logs(created_date);

-- Check constraints
ALTER TABLE transcriptions ADD CONSTRAINT check_status 
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'));

ALTER TABLE transcriptions ADD CONSTRAINT check_priority 
    CHECK (priority >= 1 AND priority <= 5);

ALTER TABLE users ADD CONSTRAINT check_role 
    CHECK (role IN ('admin', 'operator', 'user'));

ALTER TABLE vod_content ADD CONSTRAINT check_vod_status 
    CHECK (status IN ('processing', 'published', 'failed', 'removed'));
```

## 🚀 Deployment Guide

### System Requirements

**Hardware Requirements:**
- CPU: 8+ cores (Intel/AMD x86_64)
- RAM: 16GB minimum, 32GB recommended
- Storage: 100GB system disk + network storage
- Network: 1Gbps connection for NFS

**Software Requirements:**
- Ubuntu 20.04 LTS or CentOS 8
- Python 3.8+
- PostgreSQL 12+
- Redis 6.0+
- Node.js 16+ (for frontend)
- FFmpeg 4.2+

### Installation Steps

#### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3.8 \
    python3.8-venv \
    python3.8-dev \
    postgresql-12 \
    postgresql-contrib \
    redis-server \
    nginx \
    ffmpeg \
    nfs-common \
    git \
    curl \
    build-essential

# Create application user
sudo useradd -r -s /bin/false -m -d /opt/Archivist archivist
sudo mkdir -p /opt/Archivist
sudo chown archivist:archivist /opt/Archivist
```

#### 2. Database Setup

```bash
# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE archivist_db;
CREATE USER archivist_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE archivist_db TO archivist_user;
ALTER USER archivist_user CREATEDB;
EOF

# Configure PostgreSQL
sudo cp /etc/postgresql/12/main/postgresql.conf /etc/postgresql/12/main/postgresql.conf.bak

# Edit postgresql.conf
sudo tee -a /etc/postgresql/12/main/postgresql.conf <<EOF
# Archivist optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 64MB
checkpoint_segments = 16
wal_buffers = 16MB
EOF

# Configure connections
sudo tee /etc/postgresql/12/main/pg_hba.conf <<EOF
# Database administrative login by Unix domain socket
local   all             postgres                                peer

# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   archivist_db    archivist_user                         md5
host    archivist_db    archivist_user  127.0.0.1/32           md5
host    archivist_db    archivist_user  ::1/128                md5
EOF

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 3. Redis Configuration

```bash
# Configure Redis
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.bak

# Edit redis.conf
sudo tee /etc/redis/redis.conf <<EOF
# Basic configuration
port 6379
bind 127.0.0.1
timeout 0
tcp-keepalive 60

# Memory configuration
maxmemory 1gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
rdbcompression yes
dbfilename dump.rdb
dir /var/lib/redis

# Security
requirepass your-redis-password
EOF

# Restart Redis
sudo systemctl restart redis
sudo systemctl enable redis
```

#### 4. Application Deployment

```bash
# Switch to application user
sudo -u archivist bash

# Clone repository
cd /opt/Archivist
git clone https://github.com/your-org/archivist.git .

# Create virtual environment
python3.8 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create configuration file
cp .env.example .env
# Edit .env with your specific configuration

# Initialize database
flask db upgrade

# Create initial admin user
flask create-admin --username admin --email admin@example.com --password admin123

# Exit application user
exit
```

#### 5. Storage Configuration

```bash
# Create mount points
sudo mkdir -p /mnt/flex-{1..5}

# Configure NFS mounts
sudo tee -a /etc/fstab <<EOF
# Archivist flex servers
server1:/volume1/flex-1 /mnt/flex-1 nfs defaults,_netdev,rsize=32768,wsize=32768 0 0
server1:/volume1/flex-2 /mnt/flex-2 nfs defaults,_netdev,rsize=32768,wsize=32768 0 0
server2:/volume1/flex-3 /mnt/flex-3 nfs defaults,_netdev,rsize=32768,wsize=32768 0 0
server2:/volume1/flex-4 /mnt/flex-4 nfs defaults,_netdev,rsize=32768,wsize=32768 0 0
server3:/volume1/flex-5 /mnt/flex-5 nfs defaults,_netdev,rsize=32768,wsize=32768 0 0
EOF

# Mount all filesystems
sudo mount -a

# Set permissions
sudo chown -R archivist:archivist /mnt/flex-*
sudo chmod 755 /mnt/flex-*
```

#### 6. Service Configuration

```bash
# Create systemd service for main application
sudo tee /etc/systemd/system/archivist.service <<EOF
[Unit]
Description=Archivist Transcription Service
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=archivist
WorkingDirectory=/opt/Archivist
Environment=PATH=/opt/Archivist/venv/bin
ExecStart=/opt/Archivist/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for Celery workers
sudo tee /etc/systemd/system/archivist-worker.service <<EOF
[Unit]
Description=Archivist Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=archivist
WorkingDirectory=/opt/Archivist
Environment=PATH=/opt/Archivist/venv/bin
ExecStart=/opt/Archivist/venv/bin/celery -A app.celery worker --loglevel=info --concurrency=4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable archivist archivist-worker
sudo systemctl start archivist archivist-worker
```

#### 7. Web Server Configuration

```bash
# Configure Nginx
sudo tee /etc/nginx/sites-available/archivist <<EOF
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 10G;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    location /static/ {
        alias /opt/Archivist/static/;
        expires 30d;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/archivist /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🔍 Monitoring and Logging

### Log Configuration

```python
# /opt/Archivist/logging_config.py

import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    """Configure application logging"""
    
    # Create logs directory
    log_dir = '/var/log/archivist'
    os.makedirs(log_dir, exist_ok=True)
    
    # Main application log
    app_handler = RotatingFileHandler(
        os.path.join(log_dir, 'archivist.log'),
        maxBytes=100*1024*1024,  # 100MB
        backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    
    # Transcription log
    transcription_handler = RotatingFileHandler(
        os.path.join(log_dir, 'transcription.log'),
        maxBytes=100*1024*1024,
        backupCount=5
    )
    transcription_handler.setLevel(logging.INFO)
    transcription_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(funcName)s: %(message)s'
    ))
    
    # VOD log
    vod_handler = RotatingFileHandler(
        os.path.join(log_dir, 'vod.log'),
        maxBytes=50*1024*1024,
        backupCount=3
    )
    vod_handler.setLevel(logging.INFO)
    vod_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] VOD: %(message)s'
    ))
    
    # Error log
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=50*1024*1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
    ))
    
    # Configure loggers
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)
    
    # Transcription logger
    transcription_logger = logging.getLogger('transcription')
    transcription_logger.addHandler(transcription_handler)
    transcription_logger.addHandler(error_handler)
    transcription_logger.setLevel(logging.INFO)
    
    # VOD logger
    vod_logger = logging.getLogger('vod')
    vod_logger.addHandler(vod_handler)
    vod_logger.addHandler(error_handler)
    vod_logger.setLevel(logging.INFO)
```

### Health Monitoring

```python
# /opt/Archivist/monitoring.py

import psutil
import redis
import psycopg2
from datetime import datetime
import logging

class SystemMonitor:
    def __init__(self, app):
        self.app = app
        self.redis_client = redis.from_url(app.config['REDIS_URL'])
        self.logger = logging.getLogger('monitoring')
    
    def check_system_health(self):
        """Comprehensive system health check"""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'services': {}
        }
        
        # Check database
        health_status['services']['database'] = self.check_database()
        
        # Check Redis
        health_status['services']['redis'] = self.check_redis()
        
        # Check storage
        health_status['services']['storage'] = self.check_storage()
        
        # Check system resources
        health_status['services']['system'] = self.check_system_resources()
        
        # Check transcription service
        health_status['services']['transcription'] = self.check_transcription_service()
        
        # Determine overall status
        if any(service['status'] == 'unhealthy' for service in health_status['services'].values()):
            health_status['overall_status'] = 'unhealthy'
        elif any(service['status'] == 'degraded' for service in health_status['services'].values()):
            health_status['overall_status'] = 'degraded'
        
        return health_status
    
    def check_database(self):
        """Check database connectivity and performance"""
        try:
            from app import db
            
            # Test connection
            db.engine.execute('SELECT 1')
            
            # Check active connections
            result = db.engine.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            active_connections = result.fetchone()[0]
            
            status = 'healthy'
            if active_connections > 50:
                status = 'degraded'
            
            return {
                'status': status,
                'active_connections': active_connections,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def check_redis(self):
        """Check Redis connectivity and performance"""
        try:
            # Test connection
            self.redis_client.ping()
            
            # Get memory usage
            info = self.redis_client.info('memory')
            used_memory = info['used_memory']
            max_memory = info.get('maxmemory', 0)
            
            status = 'healthy'
            if max_memory > 0 and used_memory / max_memory > 0.8:
                status = 'degraded'
            
            return {
                'status': status,
                'used_memory': used_memory,
                'max_memory': max_memory,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def check_storage(self):
        """Check storage mount points and usage"""
        try:
            mount_status = {}
            overall_status = 'healthy'
            
            flex_servers = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', '/mnt/flex-5']
            
            for mount_point in flex_servers:
                try:
                    # Check if mounted
                    if not os.path.ismount(mount_point):
                        mount_status[mount_point] = {
                            'status': 'unhealthy',
                            'error': 'Not mounted'
                        }
                        overall_status = 'unhealthy'
                        continue
                    
                    # Check disk usage
                    usage = psutil.disk_usage(mount_point)
                    percent_used = (usage.used / usage.total) * 100
                    
                    status = 'healthy'
                    if percent_used > 90:
                        status = 'unhealthy'
                        overall_status = 'unhealthy'
                    elif percent_used > 80:
                        status = 'degraded'
                        if overall_status == 'healthy':
                            overall_status = 'degraded'
                    
                    mount_status[mount_point] = {
                        'status': status,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent_used': percent_used
                    }
                    
                except Exception as e:
                    mount_status[mount_point] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
                    overall_status = 'unhealthy'
            
            return {
                'status': overall_status,
                'mount_points': mount_status,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Storage health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def check_system_resources(self):
        """Check system resource utilization"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            status = 'healthy'
            if cpu_percent > 90 or memory.percent > 90:
                status = 'unhealthy'
            elif cpu_percent > 80 or memory.percent > 80:
                status = 'degraded'
            
            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_total': memory.total,
                'memory_used': memory.used,
                'disk_read_bytes': disk_io.read_bytes,
                'disk_write_bytes': disk_io.write_bytes,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"System resources check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def check_transcription_service(self):
        """Check transcription service health"""
        try:
            from app import celery
            
            # Check active workers
            inspect = celery.control.inspect()
            active_workers = inspect.active()
            
            if not active_workers:
                return {
                    'status': 'unhealthy',
                    'error': 'No active workers',
                    'last_check': datetime.utcnow().isoformat()
                }
            
            # Check queue length
            queue_length = len(self.redis_client.lrange('celery', 0, -1))
            
            status = 'healthy'
            if queue_length > 50:
                status = 'degraded'
            
            return {
                'status': status,
                'active_workers': len(active_workers),
                'queue_length': queue_length,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Transcription service check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
```

## 🛠️ Maintenance and Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check database status
sudo systemctl status postgresql

# Check connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Restart database
sudo systemctl restart postgresql

# Check logs
sudo tail -f /var/log/postgresql/postgresql-12-main.log
```

#### Redis Issues

```bash
# Check Redis status
sudo systemctl status redis

# Check Redis logs
sudo tail -f /var/log/redis/redis-server.log

# Test Redis connection
redis-cli ping

# Monitor Redis
redis-cli monitor
```

#### Storage Issues

```bash
# Check mount status
mount | grep flex

# Test NFS connectivity
showmount -e nfs-server

# Remount filesystem
sudo umount /mnt/flex-1
sudo mount /mnt/flex-1

# Check disk usage
df -h /mnt/flex-*
```

#### Application Issues

```bash
# Check application logs
sudo tail -f /var/log/archivist/archivist.log

# Check service status
sudo systemctl status archivist archivist-worker

# Restart services
sudo systemctl restart archivist archivist-worker

# Check process status
ps aux | grep -E "(gunicorn|celery)"
```

### Performance Optimization

#### Database Optimization

```sql
-- Analyze table statistics
ANALYZE transcriptions;
ANALYZE cablecast_shows;
ANALYZE vod_content;

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- Vacuum and reindex
VACUUM ANALYZE transcriptions;
REINDEX TABLE transcriptions;
```

#### Application Optimization

```python
# /opt/Archivist/optimization.py

def optimize_transcription_pipeline():
    """Optimize transcription processing pipeline"""
    
    # Adjust batch sizes based on available memory
    import psutil
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    if memory_gb >= 32:
        batch_size = 32
        worker_concurrency = 6
    elif memory_gb >= 16:
        batch_size = 16
        worker_concurrency = 4
    else:
        batch_size = 8
        worker_concurrency = 2
    
    # Update configuration
    os.environ['WHISPER_BATCH_SIZE'] = str(batch_size)
    os.environ['CELERY_WORKER_CONCURRENCY'] = str(worker_concurrency)
```

---

**This technical documentation provides comprehensive guidance for deploying, configuring, and maintaining the Archivist system. For operational procedures, refer to the User Manual and API Reference.** 
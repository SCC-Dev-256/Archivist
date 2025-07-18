#!/bin/bash

# Exit on error
set -e

# Configuration
DB_NAME="archivist"
DB_USER="archivist"
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
POSTGRES_VERSION="15"
REDIS_VERSION="7"
GRAFANA_VERSION="10.2.0"
PROMETHEUS_VERSION="2.47.0"
NODE_EXPORTER_VERSION="1.6.3"

# Create necessary directories
echo "Creating directory structure..."
sudo mkdir -p /opt/archivist/{docker,src,scripts,data/{postgres,redis,prometheus,grafana}}
sudo chown -R $USER:$USER /opt/archivist

# Install required packages
echo "Installing required packages..."
sudo apt-get update
sudo apt-get install -y \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    htop \
    iotop \
    sysstat

# Start and enable Docker
echo "Configuring Docker..."
sudo systemctl enable docker
sudo systemctl start docker

# Create Docker Compose file
echo "Creating Docker Compose configuration..."
cat > /opt/archivist/docker/docker-compose.yml << EOL
version: '3.8'

services:
  postgres:
    image: postgres:${POSTGRES_VERSION}
    container_name: archivist-postgres
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - /opt/archivist/data/postgres:/var/lib/postgresql/data
      - ./postgres/postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c 'config_file=/etc/postgresql/postgresql.conf'
    restart: unless-stopped
    networks:
      - archivist-network

  redis:
    image: redis:${REDIS_VERSION}
    container_name: archivist-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - /opt/archivist/data/redis:/data
    restart: unless-stopped
    networks:
      - archivist-network

  prometheus:
    image: prom/prometheus:${PROMETHEUS_VERSION}
    container_name: archivist-prometheus
    volumes:
      - /opt/archivist/data/prometheus:/prometheus
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    restart: unless-stopped
    networks:
      - archivist-network

  grafana:
    image: grafana/grafana:${GRAFANA_VERSION}
    container_name: archivist-grafana
    volumes:
      - /opt/archivist/data/grafana:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped
    networks:
      - archivist-network

  node-exporter:
    image: prom/node-exporter:${NODE_EXPORTER_VERSION}
    container_name: archivist-node-exporter
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped
    networks:
      - archivist-network

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: archivist-postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}?sslmode=disable"
    restart: unless-stopped
    networks:
      - archivist-network

  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: archivist-redis-exporter
    environment:
      REDIS_ADDR: "redis://redis:6379"
      REDIS_PASSWORD: "${REDIS_PASSWORD}"
    restart: unless-stopped
    networks:
      - archivist-network

networks:
  archivist-network:
    driver: bridge
EOL

# Create optimized PostgreSQL configuration
echo "Creating optimized PostgreSQL configuration..."
cat > /opt/archivist/docker/postgres/postgresql.conf << EOL
# Memory Configuration
shared_buffers = 17GB
effective_cache_size = 53GB
maintenance_work_mem = 2GB
work_mem = 256MB

# Checkpoint Configuration
checkpoint_completion_target = 0.9
max_wal_size = 16GB
min_wal_size = 4GB

# Query Planning
random_page_cost = 1.1
effective_io_concurrency = 200

# Write Ahead Log
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10

# Monitoring
track_io_timing = on
track_functions = all
track_activity_query_size = 2048

# Performance
max_connections = 100
max_worker_processes = 16
max_parallel_workers_per_gather = 4
max_parallel_workers = 16

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
log_autovacuum_min_duration = 0
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_timezone = 'UTC'
EOL

# Create Prometheus configuration
echo "Creating Prometheus configuration..."
cat > /opt/archivist/docker/prometheus/prometheus.yml << EOL
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['192.168.181.154:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']
EOL

# Create environment file
echo "Creating environment file..."
cat > /opt/archivist/.env << EOL
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=postgres
DB_PORT=5432
REDIS_HOST=redis
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_PORT=6379
EOL

# Set up Nginx configuration
echo "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/archivist << EOL
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://192.168.181.154:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /grafana/ {
        proxy_pass http://192.168.181.154:3000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /prometheus/ {
        proxy_pass http://192.168.181.154:9090/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOL

sudo ln -sf /etc/nginx/sites-available/archivist /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Start the services
echo "Starting services..."
cd /opt/archivist/docker
docker-compose up -d

# Set up SSL with Let's Encrypt
echo "Setting up SSL..."
sudo certbot --nginx -d your-domain.com --non-interactive --agree-tos --email your-email@example.com

# Create backup script
echo "Creating backup script..."
cat > /opt/archivist/scripts/backup.sh << EOL
#!/bin/bash

BACKUP_DIR="/opt/archivist/backups"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

# Backup PostgreSQL
docker exec archivist-postgres pg_dump -U ${DB_USER} ${DB_NAME} > \$BACKUP_DIR/postgres_\$TIMESTAMP.sql

# Backup Redis
docker exec archivist-redis redis-cli -a ${REDIS_PASSWORD} SAVE
docker cp archivist-redis:/data/dump.rdb \$BACKUP_DIR/redis_\$TIMESTAMP.rdb

# Backup configuration files
tar -czf \$BACKUP_DIR/config_\$TIMESTAMP.tar.gz /opt/archivist/docker/*.yml /opt/archivist/.env

# Clean up old backups (keep last 7 days)
find \$BACKUP_DIR -type f -mtime +7 -delete
EOL

chmod +x /opt/archivist/scripts/backup.sh

# Create monitoring script
echo "Creating monitoring script..."
cat > /opt/archivist/scripts/monitor.sh << EOL
#!/bin/bash

# Check system resources
echo "System Resources:"
free -h
echo -e "\nDisk Usage:"
df -h
echo -e "\nCPU Usage:"
mpstat 1 1

# Check container status
echo -e "\nContainer Status:"
docker ps

# Check service health
echo -e "\nService Health:"
curl -s http://192.168.181.154:9090/-/healthy
curl -s http://192.168.181.154:3000/api/health
EOL

chmod +x /opt/archivist/scripts/monitor.sh

echo "Deployment completed successfully!"
echo "Please update the domain name in the Nginx configuration and run certbot again."
echo "Access Grafana at http://your-domain.com/grafana (default credentials: admin/${DB_PASSWORD})"
echo "Access Prometheus at http://your-domain.com/prometheus"

# Set up Grafana dashboards
echo "Setting up Grafana dashboards..."
chmod +x /opt/archivist/scripts/setup-grafana.sh
/opt/archivist/scripts/setup-grafana.sh 
# Archivist Deployment Guide

This guide provides instructions for deploying the Archivist application on a Proxmox server.

## Prerequisites

- Proxmox server with Debian
- Root access or sudo privileges
- Domain name (for SSL)
- Git installed

## Deployment Steps

1. Clone the repository:
```bash
git clone https://github.com/your-username/archivist.git /opt/archivist
```

2. Make the deployment script executable:
```bash
chmod +x /opt/archivist/scripts/deploy.sh
```

3. Run the deployment script:
```bash
cd /opt/archivist/scripts
./deploy.sh
```

4. Update the domain name and email in the Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/archivist
```

5. Run certbot again with your domain:
```bash
sudo certbot --nginx -d your-domain.com --non-interactive --agree-tos --email your-email@example.com
```

## Configuration Details

### PostgreSQL Optimization
The PostgreSQL configuration is optimized for video processing with:
- 17GB shared buffers (25% of RAM)
- 53GB effective cache size (75% of RAM)
- 2GB maintenance work memory
- Parallel query processing enabled
- Comprehensive logging and monitoring

### Monitoring Setup
The deployment includes:
- Prometheus for metrics collection
- Grafana for visualization
- Node Exporter for system metrics
- Redis and PostgreSQL exporters

### Backup Strategy
Daily backups are configured for:
- PostgreSQL database
- Redis data
- Configuration files
- 7-day retention policy

## Accessing Services

- Grafana: http://your-domain.com/grafana
  - Default credentials: admin/[generated-password]
- Prometheus: http://your-domain.com/prometheus
- API: http://your-domain.com/api

## Maintenance

### Backup
Run the backup script manually:
```bash
/opt/archivist/scripts/backup.sh
```

### Monitoring
Check system health:
```bash
/opt/archivist/scripts/monitor.sh
```

### Updates
To update the application:
```bash
cd /opt/archivist
git pull
docker-compose -f docker/docker-compose.yml up -d --build
```

## Security Considerations

1. All services are containerized and isolated
2. SSL is enforced using Let's Encrypt
3. Strong random passwords are generated for all services
4. Network access is restricted to necessary ports
5. Regular security updates are applied

## Troubleshooting

1. Check service logs:
```bash
docker-compose -f docker/docker-compose.yml logs
```

2. Verify Nginx configuration:
```bash
sudo nginx -t
```

3. Check system resources:
```bash
htop
```

4. Monitor disk usage:
```bash
df -h
```

## Support

For issues or questions, please open an issue on the GitHub repository. 
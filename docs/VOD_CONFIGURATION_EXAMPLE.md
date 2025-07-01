# VOD Integration Configuration Example

This document provides example configurations for setting up the Cablecast VOD integration with Archivist.

## Environment Configuration

### Basic VOD Integration Setup

Add these variables to your `.env` file:

```bash
# =============================================================================
# CABLECAST VOD INTEGRATION CONFIGURATION
# =============================================================================

# Cablecast API Configuration
CABLECAST_API_URL=https://vod.scctv.org/ui/api-docs/explorer
CABLECAST_API_KEY=your_cablecast_api_key_here
CABLECAST_LOCATION_ID=1

# VOD Integration Settings
AUTO_PUBLISH_TO_VOD=true
VOD_DEFAULT_QUALITY=1
VOD_UPLOAD_TIMEOUT=300

# VOD Processing Settings
VOD_MAX_RETRIES=3
VOD_RETRY_DELAY=60
VOD_BATCH_SIZE=10

# VOD Monitoring
VOD_STATUS_CHECK_INTERVAL=30
VOD_PROCESSING_TIMEOUT=1800
```

### Advanced Configuration

For more complex setups, you can add these optional settings:

```bash
# Advanced VOD Settings
VOD_ENABLE_CHAPTERS=true
VOD_ENABLE_METADATA_ENHANCEMENT=true
VOD_ENABLE_AUTO_TAGGING=true

# Quality Settings
VOD_QUALITY_LOW=1
VOD_QUALITY_MEDIUM=2
VOD_QUALITY_HIGH=3
VOD_QUALITY_ORIGINAL=4

# Error Handling
VOD_ENABLE_RETRY_ON_FAILURE=true
VOD_MAX_RETRY_ATTEMPTS=5
VOD_RETRY_BACKOFF_MULTIPLIER=2

# Logging
VOD_LOG_LEVEL=INFO
VOD_ENABLE_DEBUG_LOGGING=false
```

## Docker Configuration

### Docker Compose Example

Add these services to your `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # ... existing services ...
  
  # VOD Integration Service (optional)
  vod-integration:
    build: .
    image: archivist:latest
    container_name: archivist-vod-integration
    environment:
      - CABLECAST_API_URL=${CABLECAST_API_URL}
      - CABLECAST_API_KEY=${CABLECAST_API_KEY}
      - CABLECAST_LOCATION_ID=${CABLECAST_LOCATION_ID}
      - AUTO_PUBLISH_TO_VOD=${AUTO_PUBLISH_TO_VOD}
      - VOD_DEFAULT_QUALITY=${VOD_DEFAULT_QUALITY}
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    depends_on:
      - db
      - redis
    restart: unless-stopped
    profiles:
      - vod-integration

  # VOD Monitoring Service (optional)
  vod-monitor:
    build: .
    image: archivist:latest
    container_name: archivist-vod-monitor
    command: python -m core.vod_monitor
    environment:
      - CABLECAST_API_URL=${CABLECAST_API_URL}
      - CABLECAST_API_KEY=${CABLECAST_API_KEY}
      - VOD_STATUS_CHECK_INTERVAL=${VOD_STATUS_CHECK_INTERVAL}
    volumes:
      - ./logs:/app/logs
    depends_on:
      - db
      - redis
    restart: unless-stopped
    profiles:
      - vod-monitoring
```

## Database Configuration

### PostgreSQL Settings

For optimal VOD integration performance, consider these PostgreSQL settings:

```sql
-- Increase connection pool for VOD operations
ALTER SYSTEM SET max_connections = 200;

-- Optimize for VOD data
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Enable parallel processing for VOD queries
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;

-- Reload configuration
SELECT pg_reload_conf();
```

### Redis Configuration

For VOD queue management, optimize Redis settings:

```bash
# Redis configuration for VOD integration
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## API Configuration

### Rate Limiting for VOD Endpoints

Configure rate limiting in your application:

```python
# VOD-specific rate limits
VOD_PUBLISH_RATE_LIMIT = '10 per hour'
VOD_SYNC_RATE_LIMIT = '5 per hour'
VOD_STATUS_RATE_LIMIT = '60 per minute'
```

### CORS Configuration

If accessing VOD endpoints from web applications:

```python
# CORS settings for VOD integration
CORS_ORIGINS = [
    "https://your-cablecast-instance.com",
    "https://vod.scctv.org",
    "http://localhost:3000"
]

CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-CSRF-Token"]
```

## Monitoring Configuration

### Prometheus Metrics

Add VOD-specific metrics to your monitoring:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'archivist-vod'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Grafana Dashboard

Create a VOD monitoring dashboard:

```json
{
  "dashboard": {
    "title": "Archivist VOD Integration",
    "panels": [
      {
        "title": "VOD Publishing Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(vod_publish_success_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "VOD Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(vod_processing_duration_seconds_bucket[5m]))",
            "legendFormat": "95th Percentile"
          }
        ]
      }
    ]
  }
}
```

## Security Configuration

### API Key Management

Store API keys securely:

```bash
# Use environment variables (recommended)
export CABLECAST_API_KEY="your-secure-api-key"

# Or use a secrets manager
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id cablecast-api-key

# HashiCorp Vault
vault kv get secret/cablecast-api-key
```

### Network Security

Configure firewall rules for VOD integration:

```bash
# Allow outbound connections to Cablecast API
iptables -A OUTPUT -p tcp --dport 443 -d vod.scctv.org -j ACCEPT

# Allow inbound connections for VOD webhooks (if applicable)
iptables -A INPUT -p tcp --dport 8080 -s your-cablecast-ip -j ACCEPT
```

## Testing Configuration

### Test Environment Setup

Create a test configuration:

```bash
# test.env
CABLECAST_API_URL=https://test-vod.scctv.org/api
CABLECAST_API_KEY=test_api_key
CABLECAST_LOCATION_ID=999
AUTO_PUBLISH_TO_VOD=false
VOD_LOG_LEVEL=DEBUG
```

### Test Scripts

Create test scripts for VOD integration:

```python
# test_vod_integration.py
import os
import requests

def test_vod_connection():
    """Test VOD API connection"""
    api_url = os.getenv('CABLECAST_API_URL')
    api_key = os.getenv('CABLECAST_API_KEY')
    
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(f"{api_url}/shows", headers=headers)
    
    assert response.status_code == 200
    print("VOD API connection successful")

def test_vod_publishing():
    """Test VOD publishing functionality"""
    # Test implementation
    pass

if __name__ == "__main__":
    test_vod_connection()
    test_vod_publishing()
```

## Troubleshooting Configuration

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export VOD_ENABLE_DEBUG_LOGGING=true

# Enable verbose API logging
export CABLECAST_DEBUG=true
export VOD_API_VERBOSE=true
```

### Error Reporting

Configure error reporting for VOD integration:

```python
# Error reporting configuration
VOD_ERROR_REPORTING = {
    'enabled': True,
    'service': 'sentry',  # or 'loggly', 'datadog'
    'dsn': 'your-sentry-dsn',
    'environment': 'production'
}
```

## Performance Tuning

### Optimize for High Volume

For high-volume VOD processing:

```bash
# Increase worker processes
VOD_WORKER_PROCESSES=4
VOD_WORKER_THREADS=8

# Optimize database connections
VOD_DB_POOL_SIZE=20
VOD_DB_MAX_OVERFLOW=30

# Cache settings
VOD_CACHE_TTL=3600
VOD_CACHE_MAX_SIZE=1000
```

### Memory Optimization

Optimize memory usage for VOD operations:

```python
# Memory optimization settings
VOD_MEMORY_LIMIT = '2GB'
VOD_PROCESS_TIMEOUT = 1800
VOD_BATCH_SIZE = 5  # Reduce for memory-constrained environments
```

This configuration example provides a comprehensive setup for the VOD integration. Adjust the values based on your specific requirements and infrastructure constraints. 
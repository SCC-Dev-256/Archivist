#!/bin/bash

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
until curl -s http://localhost:3000/api/health; do
    sleep 2
done

# Get Grafana admin password from environment
GRAFANA_PASSWORD=$(grep DB_PASSWORD /opt/archivist/.env | cut -d '=' -f2)

# Create API key
API_KEY=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"name":"setup-key", "role": "Admin"}' \
    http://admin:${GRAFANA_PASSWORD}@localhost:3000/api/auth/keys | \
    jq -r '.key')

# Add Prometheus data source
curl -s -X POST -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_KEY}" \
    -d '{
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",
        "access": "proxy",
        "basicAuth": false
    }' \
    http://192.168.181.154:3000/api/datasources

# Create Video Processing Dashboard
curl -s -X POST -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_KEY}" \
    -d '{
        "dashboard": {
            "id": null,
            "title": "Video Processing Overview",
            "tags": ["video", "processing"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "System Resources",
                    "type": "row",
                    "panels": [
                        {
                            "title": "CPU Usage",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                                    "legendFormat": "CPU Usage"
                                }
                            ],
                            "yaxes": [
                                {"format": "percent", "min": 0, "max": 100},
                                {"format": "short"}
                            ]
                        },
                        {
                            "title": "Memory Usage",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes",
                                    "legendFormat": "Used Memory"
                                }
                            ],
                            "yaxes": [
                                {"format": "bytes"},
                                {"format": "short"}
                            ]
                        }
                    ]
                },
                {
                    "title": "Video Processing Metrics",
                    "type": "row",
                    "panels": [
                        {
                            "title": "Active Processing Jobs",
                            "type": "stat",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "sum(redis_connected_clients{instance=\"redis-exporter:9121\"})",
                                    "legendFormat": "Active Jobs"
                                }
                            ]
                        },
                        {
                            "title": "Processing Queue Length",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "redis_db_keys{instance=\"redis-exporter:9121\"}",
                                    "legendFormat": "Queue Length"
                                }
                            ]
                        }
                    ]
                },
                {
                    "title": "Database Performance",
                    "type": "row",
                    "panels": [
                        {
                            "title": "Active Connections",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "pg_stat_activity_count{datname=\"archivist\"}",
                                    "legendFormat": "Connections"
                                }
                            ]
                        },
                        {
                            "title": "Query Performance",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "rate(pg_stat_database_tup_returned{datname=\"archivist\"}[5m])",
                                    "legendFormat": "Tuples Returned"
                                },
                                {
                                    "expr": "rate(pg_stat_database_tup_fetched{datname=\"archivist\"}[5m])",
                                    "legendFormat": "Tuples Fetched"
                                }
                            ]
                        }
                    ]
                },
                {
                    "title": "Storage Metrics",
                    "type": "row",
                    "panels": [
                        {
                            "title": "Disk Usage",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "node_filesystem_size_bytes{mountpoint=\"/\"} - node_filesystem_free_bytes{mountpoint=\"/\"}",
                                    "legendFormat": "Used Space"
                                }
                            ],
                            "yaxes": [
                                {"format": "bytes"},
                                {"format": "short"}
                            ]
                        },
                        {
                            "title": "IO Operations",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "rate(node_disk_read_bytes_total[5m])",
                                    "legendFormat": "Read"
                                },
                                {
                                    "expr": "rate(node_disk_written_bytes_total[5m])",
                                    "legendFormat": "Write"
                                }
                            ],
                            "yaxes": [
                                {"format": "bytes"},
                                {"format": "short"}
                            ]
                        }
                    ]
                }
            ],
            "schemaVersion": 26,
            "version": 0
        },
        "overwrite": true
    }' \
    http://192.168.181.154:3000/api/dashboards/db

# Create Video Processing Alerts
curl -s -X POST -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_KEY}" \
    -d '{
        "name": "Video Processing Alerts",
        "interval": "1m",
        "rules": [
            {
                "grafana_alert": {
                    "title": "High CPU Usage",
                    "condition": "B",
                    "data": [
                        {
                            "refId": "A",
                            "queryType": "prometheus",
                            "relativeTimeRange": {
                                "from": 600,
                                "to": 0
                            },
                            "datasourceUid": "prometheus",
                            "model": {
                                "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 80",
                                "intervalMs": 15000,
                                "maxDataPoints": 43200
                            }
                        }
                    ]
                }
            },
            {
                "grafana_alert": {
                    "title": "High Memory Usage",
                    "condition": "B",
                    "data": [
                        {
                            "refId": "A",
                            "queryType": "prometheus",
                            "relativeTimeRange": {
                                "from": 600,
                                "to": 0
                            },
                            "datasourceUid": "prometheus",
                            "model": {
                                "expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 90",
                                "intervalMs": 15000,
                                "maxDataPoints": 43200
                            }
                        }
                    ]
                }
            },
            {
                "grafana_alert": {
                    "title": "Processing Queue Backlog",
                    "condition": "B",
                    "data": [
                        {
                            "refId": "A",
                            "queryType": "prometheus",
                            "relativeTimeRange": {
                                "from": 600,
                                "to": 0
                            },
                            "datasourceUid": "prometheus",
                            "model": {
                                "expr": "redis_db_keys{instance=\"redis-exporter:9121\"} > 100",
                                "intervalMs": 15000,
                                "maxDataPoints": 43200
                            }
                        }
                    ]
                }
            }
        ]
    }' \
    http://192.168.181.154:3000/api/v1/provisioning/alert-rules

echo "Grafana dashboards and alerts have been set up successfully!" 
# Deployment Notes (Monitoring)

## Network Ports (VLAN)
- Grafana: TCP 3000
- Prometheus: TCP 9090
- Alertmanager: TCP 9093
- Blackbox Exporter: TCP 9115 (internal)
- Node Exporter: TCP 9100 (internal)
- Process Exporter: TCP 9256 (internal)
- Postgres Exporter: TCP 9187 (internal)
- Celery Exporter: TCP 9808 (internal)

Open 3000/9090/9093 on the VLAN or front them with a reverse proxy.

## Reverse Proxy (Nginx) with TLS (example)
```
server {
  listen 443 ssl;
  server_name grafana.archivist.local;
  ssl_certificate /etc/letsencrypt/live/grafana/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/grafana/privkey.pem;
  location / { proxy_pass http://127.0.0.1:3000; }
}
```

## Blackbox ICMP
The container must run with `--cap-add=NET_RAW` for ICMP probes.

## CIFS mounts
Ensure SMB TCP/445 is reachable to Flex servers; see runbooks if down.

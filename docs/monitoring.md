# Monitoring and Alerting (Archivist)

## Stack overview
- Prometheus (host: 9090)
- Grafana (host: 3000)
- Alertmanager (host: 9093)
- Exporters (host network):
  - blackbox_exporter (9115) with ICMP/TCP and HTTP modules
  - node_exporter (9100)
  - process-exporter (9256)
  - postgres-exporter (9187)
  - celery-exporter (9808)
  - pve-exporter (9221)

## File layout
- docker/prometheus/prometheus.yml
- docker/prometheus/alerting/*.yml
- docker/prometheus/alertmanager.yml
- docker/prometheus/file_sd/*.yml  # flex server targets with labels
- docker/grafana/provisioning/{datasources,dashboards}
- docker/grafana/dashboards/{noc.json,app-health.json}
- docker/process-exporter/process-exporter.yml
- docker/pve-exporter/pve.yml (token config) – keep secrets out of VCS
- docker-compose.yml (optional)
- .env (not committed) – secrets and connection strings

## Environment (.env)
```
GF_ADMIN_PASSWORD=
# Postgres
DATA_SOURCE_NAME=postgresql://USER:PASS@127.0.0.1:5432/DB?sslmode=disable
# SMTP
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=
ALERT_TO=utility@scctv.org
# Celery (Redis)
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
```

## Bring-up (individual containers)
- Prometheus and exporters already run with host networking. To (re)load config:
```
curl -X POST http://127.0.0.1:9090/-/reload
```
- Start/Restart services (examples):
```
docker restart archivist-grafana archivist-prometheus alertmanager || true
```

## Compose option
From `/opt/Archivist`:
```
sudo docker compose up -d prometheus grafana blackbox-exporter node-exporter process-exporter pve-exporter redis-exporter postgres-exporter
```

## Proxmox exporter
`docker/pve-exporter/pve.yml` token auth example:
```
default:
  verify_ssl: false
  user: root@pam
  token_name: archivist-monitor
  token_value: <token secret>
```
Prometheus job passes the target URL; exporter listens on 9221.

## Flex servers file_sd
- `flex_icmp.yml` – ICMP to 192.168.181.56–65 with `city` and `flex_id` labels
- `flex_smb.yml` – TCP 445 checks to same list

## Dashboards
- NOC: high-level tiles for API, Celery, ICMP
- App Health: Postgres connections/commits/rollbacks, Celery queue length/failure rate

## Alerts (rules)
- Core: API health, node/process exporter up
- Flex ICMP/TCP: critical/warning
- Celery: backlog warning/critical; failure rate > 5% (10m)
- PVE exporter down

## SMTP / Email
- Alertmanager config: `docker/prometheus/alertmanager.yml`
- For Gmail/Workspace: use App Password (not regular password); set SMTP_* and SMTP_FROM to the same account.
- Test alert:
```
curl -XPOST -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"TestEmail","severity":"critical"},"annotations":{"summary":"Test alert"}}]' \
  http://127.0.0.1:9093/api/v2/alerts
```

## Health endpoints
- API health probe: http://127.0.0.1:8585/healthz (via http-echo until app /healthz returns 200)

## Troubleshooting
- Grafana 500 when querying Prometheus: set datasource URL to host IP (e.g., `http://192.168.181.154:9090`) not 127.0.0.1
- ICMP probes fail: ensure blackbox_exporter has `--cap-add=NET_RAW`
- `file_sd` missing in logs: copy `docker/prometheus/file_sd/*` into container `/etc/prometheus/file_sd` and reload
- Celery exporter 000: confirm Redis URLs and credentials; restart container
- Postgres exporter auth: create read-only role
```
CREATE ROLE prom_exporter WITH LOGIN PASSWORD '<strong-pass>';
GRANT pg_monitor TO prom_exporter;
```
Update DSN accordingly.

## Runbooks
- See `/opt/Archivist/runbooks/*.md` for Flex down and API health procedures.


## Secrets management
- Keep secrets in `.env` with `chmod 600`; do not commit to VCS. Use `.env.example` as a template.
- Consider sops or Vault for production secret storage.

## Postgres monitoring role
See `docs/security.md` for SQL and DSN format.

## Celery exporter with Redis auth
If Redis is password-protected, set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to include `:password@` and restart `celery-exporter`.

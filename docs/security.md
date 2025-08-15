# Security & Secrets

## .env storage
- File: `/opt/Archivist/.env`
- Permissions: `chmod 600`, owner `root` (or service user)
- Never commit `.env` to version control; only `.env.example` lives in the repo.

## Rotation
- SMTP credentials: rotate every 90 days or per policy
- Postgres exporter role password: rotate every 180 days
- Proxmox API token: rotate quarterly

## Postgres monitoring role
Run as superuser:
```sql
CREATE ROLE prom_exporter WITH LOGIN PASSWORD '<strong-pass>'; 
GRANT pg_monitor TO prom_exporter;
```
Then set DSN in `.env`:
```
DATA_SOURCE_NAME=postgresql://prom_exporter:<strong-pass>@127.0.0.1:5432/postgres?sslmode=disable
```

## Celery exporter with Redis auth
If Redis requires auth:
```
CELERY_BROKER_URL=redis://:<redis-pass>@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:<redis-pass>@127.0.0.1:6379/1
```
Restart exporter:
```
docker restart celery-exporter
```

## Proxmox token file
- File: `docker/pve-exporter/pve.yml` (not committed)
- Permissions: `chmod 600`
- Restart exporter after change.

# Redis/Postgres Outage Steps

## Redis
1) Liveness: `redis-cli -h 127.0.0.1 -p 6379 ping`
2) Logs: system or container logs
3) Restart: `systemctl restart redis` or `docker restart redis`
4) Confirm celery-exporter metrics

## Postgres
1) Liveness: `psql -h 127.0.0.1 -U postgres -c 'select 1'`
2) Logs: `journalctl -u postgresql` or container logs
3) Restart service if required
4) Verify exporter at 9187 returns 200
5) If auth failures: rotate exporter password and update DSN in `.env`

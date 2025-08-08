# Systemd

Managed units for Archivist background processing and scheduling.

## Celery Worker & Beat

Units:
- `/etc/systemd/system/archivist-celery.service`
- `/etc/systemd/system/archivist-celery-beat.service`

Environment file:
- `/etc/default/archivist-celery`

Example `/etc/default/archivist-celery`:
```
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_TIMEZONE=America/Chicago
CAPTION_CHECK_TIME=03:00
VOD_PROCESSING_TIME=04:00
VOD_PROCESSING_TIME_2=19:00
CELERY_CONCURRENCY=6
PYTHONPATH=/opt/Archivist
```

Commands:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now archivist-celery.service archivist-celery-beat.service
sudo systemctl --no-pager status archivist-celery.service archivist-celery-beat.service

# Logs
sudo journalctl -u archivist-celery.service -f
sudo journalctl -u archivist-celery-beat.service -f
```

Notes:
- Schedules are defined in `core/tasks/scheduler.py` and feed off the env above.
- Ensure `venv_py311` exists at `/opt/Archivist/venv_py311` or update ExecStart.

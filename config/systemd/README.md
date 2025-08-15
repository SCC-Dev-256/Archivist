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

## Direct Autoprioritizer (no Celery)

Install these units to run newest-to-oldest transcription directly at 06:00 and 18:00 UTC.

1) `/etc/systemd/system/archivist-autoprioritize.service`

```
[Unit]
Description=Archivist direct autoprioritize transcription
After=network.target

[Service]
Type=oneshot
User=schum
Group=schum
WorkingDirectory=/opt/Archivist
Environment=PYTHONPATH=/opt/Archivist
ExecStart=/opt/Archivist/venv_py311/bin/python3 /opt/Archivist/scripts/scheduling/autoprioritize_direct.py --max-per-city 1 --scan-limit 50
StandardOutput=journal
StandardError=journal
```

2) `/etc/systemd/system/archivist-autoprioritize.timer`

```
[Unit]
Description=Run autoprioritize at 06:00 and 18:00 UTC daily

[Timer]
OnCalendar=*-*-* 06:00:00 UTC
OnCalendar=*-*-* 18:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

3) Enable & verify

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now archivist-autoprioritize.timer
systemctl list-timers archivist-autoprioritize.timer
```

To log to a file, add e.g. `StandardOutput=append:/var/log/archivist/autoprioritize.log` to the service and create the directory with correct perms.

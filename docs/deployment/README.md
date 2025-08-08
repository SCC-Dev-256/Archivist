# Deployment

Deployment guides

## Model Cache & Offline Mode (faster-whisper)

faster-whisper downloads models once and then can run fully offline. For production, use a shared cache path and bake it into the Celery worker environment.

### Recommended shared cache paths

```bash
export HF_HOME=/opt/Archivist/.cache/huggingface
export CTRANSLATE2_ROOT=/opt/Archivist/.cache/ctranslate2
sudo mkdir -p "$HF_HOME" "$CTRANSLATE2_ROOT"
sudo chown -R $(whoami) "$HF_HOME" "$CTRANSLATE2_ROOT"
```

### One-time model bootstrap (temporarily allow HTTPS outbound)

```bash
sudo ufw allow out 443/tcp
cd /opt/Archivist && source venv_py311/bin/activate
python -c "from faster_whisper import WhisperModel; WhisperModel('base'); print('Model cached')"
sudo ufw delete allow out 443/tcp
```

Notes:
- Choose model size: tiny | base | small | medium | large-v2. Start with `base` for CPU-only.
- If Celery runs under systemd, ensure these env vars are set for the service.

### Systemd integration (Celery Worker/Beat)

Add these to `/etc/default/archivist-celery` so both worker and beat inherit them:

```bash
HF_HOME=/opt/Archivist/.cache/huggingface
CTRANSLATE2_ROOT=/opt/Archivist/.cache/ctranslate2
```

Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart archivist-celery.service archivist-celery-beat.service
```

Verification:

```bash
sudo journalctl -u archivist-celery.service -f | grep -E "(faster-whisper|WhisperModel|transcribe)"
```

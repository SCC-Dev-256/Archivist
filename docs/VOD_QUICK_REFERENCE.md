# VOD Integration Quick Reference

## Quick Start

### 1. Enable VOD Integration
```bash
# Add to .env file
CABLECAST_API_URL=https://your-cablecast-instance.com/api
CABLECAST_API_KEY=your_api_key_here
AUTO_PUBLISH_TO_VOD=true
```

### 2. Run Database Migration
```bash
flask db migrate -m "Add Cablecast VOD integration"
flask db upgrade
```

### 3. Test Connection
```bash
curl -X GET "http://localhost:5000/api/vod/sync-status"
```

## API Endpoints Quick Reference

### Content Publishing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/vod/publish/<id>` | Publish single transcription |
| POST | `/api/vod/batch-publish` | Publish multiple transcriptions |
| GET | `/api/vod/sync-status` | Get sync status |

### Cablecast Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cablecast/shows` | List synced shows |
| POST | `/api/cablecast/sync/shows` | Sync shows from Cablecast |
| POST | `/api/cablecast/sync/vods` | Sync VODs from Cablecast |
| POST | `/api/cablecast/shows/<id>/transcribe` | Transcribe Cablecast show |

## Common Commands

### Publish Content to VOD
```bash
# Single transcription
curl -X POST "http://localhost:5000/api/vod/publish/transcription-uuid" \
  -H "Content-Type: application/json" \
  -d '{"quality": 1}'

# Batch publish
curl -X POST "http://localhost:5000/api/vod/batch-publish" \
  -H "Content-Type: application/json" \
  -d '{"transcription_ids": ["uuid1", "uuid2"]}'
```

### Check Sync Status
```bash
curl -X GET "http://localhost:5000/api/vod/sync-status"
```

### Sync from Cablecast
```bash
# Sync shows
curl -X POST "http://localhost:5000/api/cablecast/sync/shows"

# Sync VODs
curl -X POST "http://localhost:5000/api/cablecast/sync/vods"
```

## Python Code Examples

### Basic VOD Publishing
```python
from core.vod_content_manager import VODContentManager

manager = VODContentManager()
result = manager.process_archivist_content_for_vod("transcription_id")
print(f"Published: {result}")
```

### Cablecast API Client
```python
from core.cablecast_client import CablecastAPIClient

client = CablecastAPIClient()
shows = client.get_shows()
vods = client.get_vods(show_id=123)
```

### Check VOD Status
```python
from core.cablecast_client import CablecastAPIClient

client = CablecastAPIClient()
status = client.get_vod_status(vod_id=456)
print(f"VOD Status: {status}")
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CABLECAST_API_URL` | Cablecast API base URL | - |
| `CABLECAST_API_KEY` | API authentication key | - |
| `CABLECAST_LOCATION_ID` | Location ID for content | - |
| `AUTO_PUBLISH_TO_VOD` | Auto-publish on completion | false |
| `VOD_DEFAULT_QUALITY` | Default VOD quality | 1 |
| `VOD_UPLOAD_TIMEOUT` | Upload timeout (seconds) | 300 |

## Troubleshooting

### Common Issues

1. **API Authentication Error**
   ```bash
   # Check API key
   echo $CABLECAST_API_KEY
   ```

2. **Database Connection**
   ```bash
   # Check database
   flask db current
   ```

3. **File Access**
   ```bash
   # Check file permissions
   ls -la /path/to/video/files
   ```

### Debug Logging
```bash
export LOG_LEVEL=DEBUG
flask run
```

### Test API Connection
```python
from core.cablecast_client import CablecastAPIClient

client = CablecastAPIClient()
try:
    shows = client.get_shows()
    print(f"Connection successful: {len(shows)} shows found")
except Exception as e:
    print(f"Connection failed: {e}")
```

## Monitoring

### Key Metrics
- VOD publishing success rate
- Content sync status
- API response times
- Error rates

### Log Files
- Application logs: `logs/app.log`
- VOD integration logs: `logs/vod.log`
- Error logs: `logs/error.log`

## Support

- **Documentation**: `docs/CABLECAST_VOD_INTEGRATION.md`
- **API Docs**: `http://localhost:5000/api/docs`
- **Logs**: Check application logs for errors
- **Status**: `http://localhost:5000/api/vod/sync-status` 
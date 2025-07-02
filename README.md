# Archivist - Audio Transcription and Analysis Service

A Flask-based REST API service for audio transcription and analysis, built with modern best practices and optimized for production deployment. Now with integrated VOD (Video on Demand) system support for Cablecast platforms.

## Features

- Audio transcription using WhisperX
- Speaker diarization with Pyannote
- **NEW: Cablecast VOD Integration** - Automated content publishing to VOD systems
- **NEW: Content Management** - Sync and manage content between Archivist and Cablecast
- RESTful API with OpenAPI documentation
- PostgreSQL database with SQLAlchemy ORM
- Redis caching and rate limiting
- Prometheus metrics and Grafana dashboards
- Docker support with HTTPS via Let's Encrypt

## VOD Integration Features

- **Automated Publishing**: Automatically publish transcriptions to VOD systems
- **Content Synchronization**: Sync shows and VODs between Archivist and Cablecast
- **Batch Processing**: Process multiple files simultaneously
- **Status Monitoring**: Real-time tracking of VOD processing status
- **Metadata Enhancement**: Enrich VOD content with transcription data
- **API Integration**: Full REST API for VOD content management

## Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- CUDA-compatible GPU (recommended)
- **NEW: Cablecast API access** (for VOD integration)

## Setup

1. Create and activate a virtual environment:
```bash
python3.11 -m venv venv_py311
source venv_py311/bin/activate
```

2. Install dependencies:
```bash
# For development
pip install -r requirements/dev.txt

# For production
pip install -r requirements/prod.txt
```

3. Set up environment variables:
```bash
cp .env.example /opt/Archivist/.env
# Edit /opt/Archivist/.env with your configuration
```

4. **NEW: Configure VOD Integration** (optional):
```bash
# Add to .env file
CABLECAST_API_URL=https://your-cablecast-instance.com/api
CABLECAST_API_KEY=your_api_key_here
AUTO_PUBLISH_TO_VOD=true
# Transcriptions will automatically publish to VOD after completion
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the development server:
```bash
flask run
```

## VOD Integration Quick Start

### Enable VOD Features
```bash
# Add to your .env file
CABLECAST_API_URL=https://your-cablecast-instance.com/api
CABLECAST_API_KEY=your_api_key_here
AUTO_PUBLISH_TO_VOD=true
```

### Publish Content to VOD
```bash
# Publish a single transcription
curl -X POST "http://localhost:5000/api/vod/publish/transcription-uuid"

# Batch publish multiple transcriptions
curl -X POST "http://localhost:5000/api/vod/batch-publish" \
  -H "Content-Type: application/json" \
  -d '{"transcription_ids": ["uuid1", "uuid2"]}'
```

### Check VOD Status
```bash
curl -X GET "http://localhost:5000/api/vod/sync-status"
```

## Development

- Run tests: `pytest`
- Format code: `black .`
- Sort imports: `isort .`
- Type checking: `mypy .`

## Production Deployment

1. Build and run with Docker:
```bash
docker-compose up -d
```

2. Set up HTTPS with Let's Encrypt:
```bash
certbot --nginx -d your-domain.com
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://192.168.181.154:5050/api/`
- ReDoc: `http://192.168.181.154:5050/api/redoc`

### New VOD API Endpoints

- `POST /api/vod/publish/<id>` - Publish transcription to VOD
- `POST /api/vod/batch-publish` - Batch publish transcriptions
- `GET /api/vod/sync-status` - Get VOD sync status
- `GET /api/cablecast/shows` - List synced Cablecast shows
- `POST /api/cablecast/sync/shows` - Sync shows from Cablecast
- `POST /api/cablecast/sync/vods` - Sync VODs from Cablecast

## Monitoring

- Prometheus metrics: `http://192.168.181.154:5050/metrics`
- Grafana dashboards: `http://192.168.181.154:3000`
- **NEW: VOD Integration metrics** - Publishing success rates, sync status
- Run `scripts/vod_sync_monitor.py` to log `/api/vod/sync-status` regularly

## Documentation

- [Main Documentation](README.md)
- **[VOD Integration Guide](docs/CABLECAST_VOD_INTEGRATION.md)** - Comprehensive VOD integration documentation
- **[VOD Quick Reference](docs/VOD_QUICK_REFERENCE.md)** - Quick commands and examples
- [API Documentation](core/api_docs.py)
- [Database Schema](core/models.py)

## License

MIT License 
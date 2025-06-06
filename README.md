# Archivist - Audio Transcription and Analysis Service

A Flask-based REST API service for audio transcription and analysis, built with modern best practices and optimized for production deployment.

## Features

- Audio transcription using WhisperX
- Speaker diarization with Pyannote
- RESTful API with OpenAPI documentation
- PostgreSQL database with SQLAlchemy ORM
- Redis caching and rate limiting
- Prometheus metrics and Grafana dashboards
- Docker support with HTTPS via Let's Encrypt

## Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- CUDA-compatible GPU (recommended)

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

4. Initialize the database:
```bash
flask db upgrade
```

5. Run the development server:
```bash
flask run
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

## Monitoring

- Prometheus metrics: `http://192.168.181.154:5050/metrics`
- Grafana dashboards: `http://192.168.181.154:3000`

## License

MIT License 
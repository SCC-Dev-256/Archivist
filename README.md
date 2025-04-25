# Video Transcription API

A FastAPI-based backend service for video transcription and summarization using WhisperX and local LLaMA models.

## Features

- List MP4 files from a configured NAS directory
- Transcribe videos using WhisperX
- Generate meeting minutes summaries
- Asynchronous job processing with Redis queue
- RESTful API endpoints
- Comprehensive error handling and logging

## Prerequisites

- Python 3.10+
- Redis server
- NAS mount with video files
- CUDA (optional, for GPU acceleration)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd video-transcription-api
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```bash
cp .env.example .env
```

5. Configure the environment variables in `.env`:
```env
NAS_PATH=/mnt/nas/media
OUTPUT_DIR=./output
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
WHISPER_MODEL=large-v2
USE_GPU=true
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
```

## Running the Service

1. Start Redis:
```bash
redis-server
```

2. Start the RQ worker:
```bash
rq worker transcription
```

3. Start the FastAPI server:
```bash
uvicorn main_fastapi_server:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

- `GET /files` - List available video files
- `POST /transcribe` - Start transcription of a video
- `GET /status/{job_id}` - Check job status
- `GET /summary/{video_id}` - Get meeting minutes summary

## Testing

Run the test suite:
```bash
pytest tests/
```

## Development

/opt/archivist/
├── docker/
│   ├── docker-compose.yml
│   ├── nginx/
│   │   └── nginx.conf
│   ├── postgres/
│   │   └── postgresql.conf
│   └── prometheus/
│       └── prometheus.yml
├── src/
│   └── (your existing code)
├── scripts/
│   ├── deploy.sh
│   ├── backup.sh
│   └── monitor.sh
└── .env

## License

MIT License 
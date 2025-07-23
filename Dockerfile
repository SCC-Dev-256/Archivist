# Use Python 3.11 slim image for production
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/Archivist \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    git \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /opt/Archivist

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install additional production dependencies
RUN pip install --no-cache-dir \
    gunicorn[gevent] \
    prometheus-client \
    psutil \
    redis \
    flask-limiter

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /mnt/vod /var/log/archivist /tmp/transcriptions

# Create non-root user for security
RUN groupadd -r archivist && useradd -r -g archivist archivist && \
    chown -R archivist:archivist /opt/Archivist /mnt/vod /var/log/archivist /tmp/transcriptions

# Switch to non-root user
USER archivist

# Expose ports
EXPOSE 8080 5051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Default command
CMD ["python", "scripts/deployment/start_integrated_system.py"] 
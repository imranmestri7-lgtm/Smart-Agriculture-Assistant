# =============================================================================
# AgriSmart Production Docker Image
# Multi-stage lightweight build for Flask + TensorFlow CPU + Gunicorn
# =============================================================================

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    FLASK_ENV=production \
    FLASK_DEBUG=false \
    KERAS_HOME=/app/backend/keras_config \
    TF_ENABLE_ONEDNN_OPTS=0

# Install system dependencies (curl for healthcheck, libgl for image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application source code
COPY . .

# Ensure writable directories exist
RUN mkdir -p /app/backend/uploads /app/backend/keras_config && \
    chmod -R 755 /app/backend/uploads /app/backend/keras_config

# Expose backend port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/test || exit 1

# Start production WSGI server with preloaded TensorFlow model
CMD ["gunicorn", "-c", "gunicorn.conf.py", "backend.app:app"]

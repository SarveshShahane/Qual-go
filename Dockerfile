# ==============================================================================
# QUALGO Backend - Production Dockerfile
# Python 3.12 / FastAPI / SQLAlchemy / Alembic / Quantum Simulators
# ==============================================================================

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install runtime and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -r -g 10001 qualgo && \
    useradd -r -u 10001 -g qualgo -d /home/qualgo -m -s /bin/bash qualgo

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and migrations
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY seed_modules.py .
COPY docker-entrypoint.sh .

# Set execution permissions and transfer file ownership to non-root user
RUN chmod +x docker-entrypoint.sh && \
    chown -R qualgo:qualgo /app

USER qualgo

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]

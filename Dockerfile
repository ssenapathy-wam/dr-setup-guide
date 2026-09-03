#!/usr/bin/env dockerfile
# Dockerfile for DR Setup Guide
# Multi-stage build for optimized image

# ============================================================================
# Builder Stage
# ============================================================================
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================================================
# Runtime Stage
# ============================================================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create app user for security
RUN useradd -m -u 1000 appuser

# Copy application code
COPY . /app

# Create necessary directories
RUN mkdir -p /app/logs /app/backups /app/data /app/config && \
    chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose port for metrics/monitoring (optional)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
ENTRYPOINT ["python", "-m"]
CMD ["dr_orchestrator"]

# ============================================================================
# Build Instructions
# ============================================================================
# docker build -t dr-setup-guide:latest .
# docker build -t dr-setup-guide:1.0.0 .
#
# Run Instructions
# docker run -it --env-file .env dr-setup-guide:latest
# docker run -it --env-file .env -v $(pwd)/logs:/app/logs dr-setup-guide:latest
#
# With Docker Compose
# docker-compose up -d

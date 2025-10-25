# Backend Dockerfile with multi-stage build using uv

# Development stage
FROM python:3.12-slim AS development

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy backend application code
COPY . .

# Install dependencies with uv (including dev dependencies)
RUN uv sync

# Expose port
EXPOSE 8000

# Run with uvicorn (hot-reload enabled in docker-compose)
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM python:3.11-slim

# Prevent Python from buffering logs and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for Postgres and general build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker and shared logic
COPY worker/ .
COPY backend/database.py .
COPY backend/models.py .
COPY backend/security.py .

# Create a non-root user
RUN adduser --disabled-password --gecos "" workeruser
USER workeruser

# The entrypoint for this container is the Celery worker command
CMD ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

# Prevent Python from writing .pyc files and force stdout/stderr to be unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway injects $PORT at runtime; default to 8000 for local runs
ENV PORT=8000
EXPOSE 8000

# Use shell form so $PORT expands at runtime
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
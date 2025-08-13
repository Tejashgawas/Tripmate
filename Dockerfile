# Use Python 3.10 slim as base image for smaller size
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the project files
COPY . .

# Expose port 8000
EXPOSE 8000


CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

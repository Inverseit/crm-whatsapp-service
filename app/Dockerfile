FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
  apt-get install -y --no-install-recommends gcc postgresql-client && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make sure the application directory is in the Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000
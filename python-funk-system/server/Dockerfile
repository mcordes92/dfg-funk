FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY . .

# Create data and updates directories
RUN mkdir -p /app/data /app/updates

# Create volume mount points for database and updates
VOLUME ["/app/data", "/app/updates"]

# Expose ports
EXPOSE 5000/udp
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/funkserver.db

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python healthcheck.py || exit 1

# Run both UDP server and API server
CMD ["python", "run_server.py"]

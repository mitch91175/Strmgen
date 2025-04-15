# Base image with Python 3.11
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create working directory
WORKDIR /app

# Copy Python scripts into the container
COPY . /app

# Install system dependencies if needed (e.g., for certifi + TLS)
RUN apt-get update && \
    apt-get install -y gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        requests \
        aiohttp \
        certifi \
        opensubtitlescom \
        python-dotenv

# Set default command to run your main script
CMD ["python", "main.py"]
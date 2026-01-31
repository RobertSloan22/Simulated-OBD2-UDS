FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    iproute2 \
    kmod \
    can-utils \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY mock_ecu.py .
COPY test_client.py .
COPY setup_vcan.sh .

# Make scripts executable
RUN chmod +x mock_ecu.py test_client.py setup_vcan.sh

# Default command
CMD ["python", "mock_ecu.py"]

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
COPY mock_ecu_v2.py .
COPY test_client.py .
COPY test_client_v2.py .
COPY elm327_emulator.py .
COPY control_api.py .
COPY setup_vcan.sh .

# Copy lib modules
COPY lib/ ./lib/

# Copy vehicle profiles
COPY vehicle_profiles/ ./vehicle_profiles/

# Copy static files (dashboard UI)
COPY static/ ./static/

# Make scripts executable
RUN chmod +x mock_ecu.py mock_ecu_v2.py test_client.py test_client_v2.py elm327_emulator.py control_api.py setup_vcan.sh

# Default command
CMD ["python", "mock_ecu.py"]

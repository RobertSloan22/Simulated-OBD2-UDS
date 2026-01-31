#!/bin/bash
# Setup and start the Mock OBD system in Docker

set -e

echo "=========================================="
echo "Mock OBD System - Docker Setup"
echo "=========================================="
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not available"
    echo "Please install Docker Compose plugin"
    exit 1
fi

# Setup vcan0 interface on host
echo "Setting up virtual CAN interface (vcan0)..."
if ! ip link show vcan0 &> /dev/null; then
    echo "Creating vcan0 interface (requires sudo)..."
    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
    sudo ip link set up vcan0
    echo "✓ vcan0 interface created"
else
    echo "✓ vcan0 interface already exists"
fi

# Build and start the containers
echo
echo "Building Docker image..."
docker compose build

echo
echo "Starting Mock ECU..."
docker compose up -d mock-ecu

echo
echo "=========================================="
echo "Mock OBD System is running!"
echo "=========================================="
echo
echo "Useful commands:"
echo "  - View ECU logs:      docker compose logs -f mock-ecu"
echo "  - Run test client:    docker compose run --rm test-client"
echo "  - Monitor CAN:        candump vcan0"
echo "  - Stop ECU:           docker compose down"
echo "  - Interactive shell:  docker compose run --rm mock-ecu bash"
echo

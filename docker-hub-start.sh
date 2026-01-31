#!/bin/bash
# Start Mock OBD system using pre-built image from Docker Hub

set -e

echo "=========================================="
echo "Mock OBD System - Docker Hub Image"
echo "=========================================="
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/engine/install/"
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

# Pull latest image
echo
echo "Pulling latest image from Docker Hub..."
docker pull robertsloan2023mit/mock-obd:latest

# Start the container
echo
echo "Starting Mock ECU..."
docker compose -f docker-compose.hub.yml up -d mock-ecu

echo
echo "=========================================="
echo "Mock OBD System is running!"
echo "=========================================="
echo
echo "Useful commands:"
echo "  - View ECU logs:      docker compose -f docker-compose.hub.yml logs -f mock-ecu"
echo "  - Run test client:    docker compose -f docker-compose.hub.yml run --rm test-client"
echo "  - Monitor CAN:        candump vcan0"
echo "  - Stop ECU:           docker compose -f docker-compose.hub.yml down"
echo

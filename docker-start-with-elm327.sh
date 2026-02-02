#!/bin/bash
# Start Mock OBD-II system with ELM327 emulator for app testing

set -e

echo "Starting Mock OBD-II System with ELM327 Emulator..."

# Setup vcan0 if not already present
if ! ip link show vcan0 &> /dev/null; then
    echo "Setting up vcan0..."
    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
    sudo ip link set up vcan0
    echo "✓ vcan0 created"
else
    echo "✓ vcan0 already exists"
fi

# Start Docker services
echo "Starting Docker containers..."
docker compose up -d mock-ecu elm327-emulator

echo ""
echo "✓ Mock OBD-II system is running!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Connect your OBD-II app to:"
echo "  Host: $(hostname -I | awk '{print $1}'):35000"
echo "  (Use TCP/IP connection, not Bluetooth)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To view logs:"
echo "  docker compose logs -f elm327-emulator"
echo ""
echo "To stop:"
echo "  docker compose down"
echo ""

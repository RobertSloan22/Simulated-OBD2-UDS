#!/bin/bash
# Stop the Mock OBD Docker containers

echo "Stopping Mock OBD containers..."
docker compose down

echo "✓ Containers stopped"
echo
echo "Note: vcan0 interface is still active on the host"
echo "To remove it: sudo ip link delete vcan0"

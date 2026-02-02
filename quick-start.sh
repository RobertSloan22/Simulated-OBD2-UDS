#!/bin/bash
# Quick Start Script for Mock OBD-II System v2.0

set -e

echo "=================================="
echo "Mock OBD-II System v2.0 Quick Start"
echo "=================================="
echo ""

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

echo ""
echo "Choose a mode:"
echo "  1) Docker (recommended)"
echo "  2) Native Python"
echo ""
read -p "Enter choice [1-2]: " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "Starting Docker containers..."
    docker compose build
    docker compose up -d mock-ecu elm327-emulator

    echo ""
    echo "✓ System started in Docker!"
    echo ""
    echo "Services running:"
    echo "  - Mock ECU with 3 ECUs (Engine, Transmission, ABS)"
    echo "  - ELM327 Emulator on port 35000"
    echo "  - Control API on port 5000"
    echo ""
    echo "View logs:"
    echo "  docker compose logs -f mock-ecu"
    echo ""
    echo "Stop system:"
    echo "  docker compose down"

elif [ "$choice" = "2" ]; then
    echo ""
    echo "Activating virtual environment..."
    source venv/bin/activate

    echo "Installing dependencies..."
    pip install -q -r requirements.txt

    echo ""
    echo "Starting Mock ECU System in background..."
    nohup python mock_ecu_v2.py > mock_ecu.log 2>&1 &
    ECU_PID=$!
    echo "  ECU PID: $ECU_PID"

    sleep 2

    echo "Starting ELM327 Emulator in background..."
    nohup python elm327_emulator.py > elm327.log 2>&1 &
    ELM_PID=$!
    echo "  ELM327 PID: $ELM_PID"

    echo ""
    echo "✓ System started!"
    echo ""
    echo "Processes:"
    echo "  - Mock ECU (PID: $ECU_PID) - log: mock_ecu.log"
    echo "  - ELM327 (PID: $ELM_PID) - log: elm327.log"
    echo ""
    echo "Stop system:"
    echo "  kill $ECU_PID $ELM_PID"
    echo ""
    echo "View logs:"
    echo "  tail -f mock_ecu.log"
    echo "  tail -f elm327.log"
fi

echo ""
echo "=================================="
echo "Connection Details"
echo "=================================="
echo "ELM327 Emulator: $(hostname -I | awk '{print $1}'):35000"
echo "Control API: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Test the system:"
echo "  python test_client_v2.py --test all"
echo ""
echo "Inject a DTC via API:"
echo "  curl -X POST http://localhost:5000/api/dtc/inject \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"ecu\": \"Engine Control Unit\", \"code\": \"P0420\"}'"
echo ""
echo "Get vehicle state:"
echo "  curl http://localhost:5000/api/vehicle/state"
echo ""

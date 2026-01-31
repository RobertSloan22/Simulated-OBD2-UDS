#!/bin/bash
# Setup virtual CAN interface

# Load vcan kernel module
sudo modprobe vcan

# Create virtual CAN interface
sudo ip link add dev vcan0 type vcan

# Bring the interface up
sudo ip link set up vcan0

echo "Virtual CAN interface vcan0 created and brought up"
echo "Check with: ip link show vcan0"

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mock OBD-II/UDS system for testing automotive applications using virtual CAN interfaces. Simulates an ECU (Engine Control Unit) that responds to OBD-II and UDS diagnostic requests over a virtual CAN bus.

## Core Architecture

### Two-Component System

1. **mock_ecu.py** - ECU server that:
   - Listens for CAN messages on request_id (default: 0x7E0)
   - Processes OBD-II and UDS service requests
   - Responds on response_id (default: 0x7E8)
   - Simulates vehicle data (RPM, speed, temperature, etc.)
   - Runs in a background thread with continuous message polling

2. **test_client.py** - Diagnostic client that:
   - Sends OBD-II/UDS requests
   - Waits for ECU responses with timeout
   - Parses and displays results
   - Can be used as a library (OBDClient class) or standalone test suite

### Protocol Stack

- **Transport**: python-can library with socketcan interface
- **Network**: Virtual CAN interface (vcan0) via Linux kernel module
- **Protocol**: ISO-TP (ISO 15765-2) for frame formatting
  - Only single-frame mode implemented (payload ≤7 bytes)
  - PCI byte format: `0x0N` where N = payload length
  - Multi-frame support incomplete
- **Application**: OBD-II (Mode 01, Mode 09) and UDS services

### Frame Format

All CAN messages use ISO-TP single-frame format:
```
[PCI byte] [payload bytes (1-7)] [padding 0x00]
```

Example: `02 01 0C 00 00 00 00 00`
- `0x02`: PCI (single frame, 2 bytes)
- `0x01 0x0C`: Service 01 (OBD Mode 01), PID 0x0C (RPM)

## Development Commands

### Native Python Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup vcan0 (requires sudo)
./setup_vcan.sh

# Run ECU server (terminal 1)
python mock_ecu.py

# Run test client (terminal 2)
python test_client.py

# Monitor CAN traffic
candump vcan0
```

### Docker (Recommended)

```bash
# Build and start ECU
./docker-start.sh
# OR
docker compose up -d mock-ecu

# View logs
docker compose logs -f mock-ecu

# Run test client
docker compose run --rm test-client

# Stop
./docker-stop.sh
# OR
docker compose down
```

### Docker Hub (Pre-built Image)

```bash
# Start ECU
./docker-hub-start.sh
# OR
docker compose -f docker-compose.hub.yml up -d

# Run test client
docker compose -f docker-compose.hub.yml run --rm test-client
```

## Key Implementation Details

### Service Request Handling (mock_ecu.py)

- `_handle_request()`: Parses ISO-TP PCI byte, extracts payload
- `_process_service()`: Routes to service handlers based on first byte
- Service handlers return raw response bytes (no PCI byte)
- `_send_response()`: Wraps response in ISO-TP single frame format

### Supported Services

**OBD-II Mode 01 (Current Data)**:
- 0x00: Supported PIDs bitmask
- 0x04: Engine load (%)
- 0x05: Coolant temperature (°C + 40 offset)
- 0x0C: Engine RPM (value * 4, big-endian 16-bit)
- 0x0D: Vehicle speed (km/h)
- 0x11: Throttle position (0-255 scale)
- 0x2F: Fuel level (0-255 scale)

**UDS Services**:
- 0x10: Diagnostic Session Control
- 0x3E: Tester Present
- 0x22: Read Data By Identifier (DIDs: 0xF190=VIN, 0xF187=Part#)

**OBD-II Mode 09** (partial):
- 0x02: VIN (only first frame, multi-frame incomplete)

### Response Format

Positive response: Service ID + 0x40 (e.g., request 0x01 → response 0x41)
Negative response: `0x7F [service] [NRC]` where NRC is error code

### Virtual CAN Interface

- Interface name: vcan0 (hardcoded)
- Requires Linux kernel vcan module
- Must be created before running ECU/client
- Uses socketcan backend (Linux-specific)
- Requires privileged/host network mode in Docker

## Docker Considerations

- **network_mode: host** - Required for vcan0 access
- **privileged: true** - Required for network interface access
- vcan0 must exist on host before starting containers
- WSL2 requires kernel 5.10+ for vcan support

## Extension Points

### Adding OBD-II PIDs

Edit `_handle_mode_01()` in mock_ecu.py:
```python
elif pid == 0x0F:  # Intake air temp
    temp = int(self.vehicle_data['intake_temp'] + 40)
    return bytes([0x41, 0x0F, temp])
```

### Adding UDS Services

Edit `_process_service()` in mock_ecu.py:
```python
elif service == 0x27:  # Security Access
    return self._handle_security_access(payload)
```

### Using as Library

```python
from test_client import OBDClient

client = OBDClient(can_interface='vcan0')
rpm = client.read_engine_rpm()
client.close()
```

## Limitations

- Only ISO-TP single frames (≤7 bytes payload)
- Multi-frame responses incomplete (VIN truncated)
- No flow control handling
- No functional addressing (0x7DF broadcast)
- vcan0 name hardcoded throughout
- No error injection or fault simulation
- Vehicle data updates in mock loop, not persistent

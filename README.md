# Mock OBD System

A complete mock OBD-II/UDS system for testing automotive applications using virtual CAN interfaces.

[![Docker Hub](https://img.shields.io/badge/docker-robertsloan2023mit%2Fmock--obd-blue?logo=docker)](https://hub.docker.com/r/robertsloan2023mit/mock-obd)
[![Docker Pulls](https://img.shields.io/docker/pulls/robertsloan2023mit/mock-obd)](https://hub.docker.com/r/robertsloan2023mit/mock-obd)

**Quick Start**: See [QUICKSTART.md](QUICKSTART.md) for a 2-minute setup guide.

## Architecture

This setup uses:
- **python-can**: CAN bus interface
- **socketcan**: Virtual CAN interface (vcan0)
- **ISO-TP**: Transport protocol implementation
- **OBD-II**: Standard diagnostic protocol
- **UDS**: Unified Diagnostic Services

## Components

1. **mock_ecu.py**: Simulates an ECU that responds to OBD-II and UDS requests
2. **test_client.py**: Test client that queries the mock ECU
3. **setup_vcan.sh**: Script to setup virtual CAN interface

## Setup

### Option 1: Docker Hub Image (Easiest - No Build Required)

The fastest way to get started using the pre-built image from Docker Hub:

```bash
# Start the mock ECU (pulls image automatically)
./docker-hub-start.sh

# View ECU logs
docker compose -f docker-compose.hub.yml logs -f mock-ecu

# Run test client
docker compose -f docker-compose.hub.yml run --rm test-client

# Stop everything
docker compose -f docker-compose.hub.yml down
```

Or use directly with docker run:
```bash
# Setup vcan0 first
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Run the mock ECU
docker run -d --name mock-obd --network host --privileged \
  robertsloan2023mit/mock-obd:latest

# Run test client
docker run --rm --network host --privileged \
  robertsloan2023mit/mock-obd:latest python test_client.py
```

Docker Hub: https://hub.docker.com/r/robertsloan2023mit/mock-obd

### Option 2: Docker Build from Source

Build the image locally:

```bash
# Start the mock ECU
./docker-start.sh

# View ECU logs
docker compose logs -f mock-ecu

# Run test client
docker compose run --rm test-client

# Stop everything
./docker-stop.sh
```

Requirements:
- Docker and Docker Compose installed
- WSL2 (if on Windows) with kernel support for vcan
- Sudo access to create vcan interface

### Option 3: Native Python

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Setup Virtual CAN Interface

```bash
chmod +x setup_vcan.sh
./setup_vcan.sh
```

Verify the interface is up:
```bash
ip link show vcan0
```

#### 3. Run the Mock ECU

In one terminal:
```bash
python mock_ecu.py
```

#### 4. Run the Test Client

In another terminal:
```bash
python test_client.py
```

## Supported Services

### OBD-II (Mode 01 - Current Data)

| PID  | Description          | Response Format |
|------|---------------------|-----------------|
| 0x00 | Supported PIDs      | 4 bytes bitmask |
| 0x04 | Engine Load         | 0-100%          |
| 0x05 | Coolant Temperature | -40 to 215°C    |
| 0x0C | Engine RPM          | 0-16383 RPM     |
| 0x0D | Vehicle Speed       | 0-255 km/h      |
| 0x11 | Throttle Position   | 0-100%          |
| 0x2F | Fuel Level          | 0-100%          |

### UDS Services

| Service | Description               | Response |
|---------|--------------------------|----------|
| 0x10    | Diagnostic Session Control | 0x50   |
| 0x3E    | Tester Present            | 0x7E   |
| 0x22    | Read Data By Identifier   | 0x62   |

## CAN IDs

- Request ID: `0x7E0` (Client → ECU)
- Response ID: `0x7E8` (ECU → Client)

Standard OBD-II uses:
- Physical addressing: 0x7E0-0x7E7 (requests), 0x7E8-0x7EF (responses)
- Functional addressing: 0x7DF (broadcast)

## Example Usage

### Reading Engine RPM

```python
from test_client import OBDClient

client = OBDClient(can_interface='vcan0')
rpm = client.read_engine_rpm()
print(f"Engine RPM: {rpm}")
client.close()
```

### Custom Request

```python
import can

bus = can.interface.Bus(channel='vcan0', bustype='socketcan')

# Request engine RPM (Mode 01, PID 0x0C)
msg = can.Message(
    arbitration_id=0x7E0,
    data=[0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00],
    is_extended_id=False
)
bus.send(msg)

# Receive response
response = bus.recv(timeout=1.0)
print(f"Response: {response.data.hex()}")

bus.shutdown()
```

## ISO-TP Frame Format

### Single Frame (SF)
```
Byte 0: PCI (0x0N where N = length)
Byte 1-7: Data payload
```

Example: `02 01 0C 00 00 00 00 00`
- `02`: Single frame, 2 bytes of data
- `01 0C`: Service 01, PID 0C

### Multi-Frame (not fully implemented)
- First Frame (FF): `1X LL ...` where X+LL = total length
- Consecutive Frame (CF): `2N ...` where N = sequence number
- Flow Control (FC): `30 BS ST` where BS = block size, ST = separation time

## Monitoring CAN Traffic

Use `candump` to monitor all CAN traffic:

```bash
candump vcan0
```

Filter by specific ID:
```bash
candump vcan0,7E0:7FF
```

## Troubleshooting

### Docker Issues

#### WSL: vcan module not available
If you get "operation not supported" when creating vcan0:
```bash
# Check kernel version (need 5.10+)
uname -r

# Update WSL kernel
wsl --update
```

#### Container can't access vcan0
Ensure you're using `network_mode: host` and `privileged: true` in docker-compose.yml

### Virtual CAN interface not found

```bash
# Reload vcan module
sudo modprobe -r vcan
sudo modprobe vcan

# Recreate interface
./setup_vcan.sh
```

### Permission denied

```bash
# Add user to can group (if exists)
sudo usermod -a -G can $USER

# Or run with sudo
sudo python mock_ecu.py
```

### No response from ECU

1. Check if ECU is running: `ps aux | grep mock_ecu` or `docker compose ps`
2. Verify vcan0 is up: `ip link show vcan0`
3. Monitor traffic: `candump vcan0`
4. Check CAN IDs match between client and server

## Extending the Mock ECU

### Adding New PIDs

Edit `mock_ecu.py` and add to `_handle_mode_01()`:

```python
# PID 0x0F: Intake air temperature
elif pid == 0x0F:
    temp = int(self.vehicle_data['intake_temp'] + 40)
    return bytes([0x41, 0x0F, temp])
```

### Adding UDS Services

Edit `_process_service()` to handle new service IDs:

```python
elif service == 0x27:  # Security Access
    return self._handle_security_access(payload)
```

## References

- [ISO 15765-2 (ISO-TP)](https://en.wikipedia.org/wiki/ISO_15765-2)
- [OBD-II PIDs](https://en.wikipedia.org/wiki/OBD-II_PIDs)
- [Unified Diagnostic Services](https://en.wikipedia.org/wiki/Unified_Diagnostic_Services)
- [python-can Documentation](https://python-can.readthedocs.io/)

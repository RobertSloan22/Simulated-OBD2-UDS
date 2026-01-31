# Mock OBD System

A complete mock OBD-II/UDS ECU simulator for testing automotive diagnostic applications without a real vehicle.

## Quick Start

### 1. Setup Virtual CAN
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

### 2. Run Mock ECU
```bash
docker run -d --name mock-obd --network host --privileged \
  robertsloan2023mit/mock-obd:latest
```

### 3. Test It
```bash
docker run --rm --network host --privileged \
  robertsloan2023mit/mock-obd:latest python test_client.py
```

## Features

### OBD-II Mode 01 (Current Data)
- **PID 0x00**: Supported PIDs
- **PID 0x04**: Engine Load (0-100%)
- **PID 0x05**: Coolant Temperature (-40 to 215°C)
- **PID 0x0C**: Engine RPM (0-16383 RPM)
- **PID 0x0D**: Vehicle Speed (0-255 km/h)
- **PID 0x11**: Throttle Position (0-100%)
- **PID 0x2F**: Fuel Level (0-100%)

### UDS Services
- **0x10**: Diagnostic Session Control
- **0x3E**: Tester Present
- **0x22**: Read Data By Identifier

### Protocol Support
- **ISO-TP**: Single-frame transport
- **CAN IDs**: 0x7E0 (request), 0x7E8 (response)
- **Standard OBD-II addressing**

## Requirements

- Docker
- Linux or WSL2 with kernel 5.10+
- vcan kernel module support
- Privileged container access (for CAN interface)

## Usage Examples

### Monitor CAN Traffic
```bash
candump vcan0
```

### View ECU Logs
```bash
docker logs -f mock-obd
```

### Custom Python Client
```python
import can

bus = can.interface.Bus(channel='vcan0', interface='socketcan')

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

## Docker Compose

Create `docker-compose.yml`:
```yaml
services:
  mock-ecu:
    image: robertsloan2023mit/mock-obd:latest
    network_mode: host
    privileged: true
    restart: unless-stopped
```

Run with:
```bash
docker compose up -d
```

## Use Cases

- **Testing OBD-II Scanners**: Validate diagnostic tools without a vehicle
- **Automotive Software Development**: Test applications against a known ECU
- **Education**: Learn CAN bus, OBD-II, and UDS protocols
- **CI/CD**: Automated testing of automotive applications
- **Prototyping**: Develop and test before hardware integration

## Architecture

```
┌──────────────┐         CAN (vcan0)         ┌──────────────┐
│   Client     │◄────────────────────────────►│   Mock ECU   │
│ Application  │    Request: 0x7E0            │  (Container) │
│              │    Response: 0x7E8           │              │
└──────────────┘                              └──────────────┘
```

## Troubleshooting

### WSL: vcan module not available
```bash
# Update WSL kernel
wsl --update

# Check kernel version (need 5.10+)
uname -r
```

### Container can't access vcan0
Ensure you're using:
- `--network host` flag
- `--privileged` flag

### vcan0 doesn't exist
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

## Available Tags

- `latest` - Latest stable version
- `1.0.0` - Version 1.0.0

## Source Code

Full source code, examples, and documentation:
- GitHub: (Add your repo URL here)

## Support

For issues, questions, or contributions, please visit the GitHub repository.

## License

(Add your license information here)

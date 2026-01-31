# Mock OBD System - Quick Start

Get up and running in under 2 minutes!

## Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Linux or WSL2 with kernel 5.10+ (for vcan support)
- Sudo access

## 3 Easy Steps

### 1. Setup Virtual CAN Interface

```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

Verify it's working:
```bash
ip link show vcan0
```

### 2. Run the Mock ECU

```bash
docker run -d --name mock-obd --network host --privileged \
  robertsloan2023mit/mock-obd:latest
```

### 3. Test It

```bash
docker run --rm --network host --privileged \
  robertsloan2023mit/mock-obd:latest python test_client.py
```

You should see output like:
```
============================================================
OBD/UDS Test Client
============================================================

[Reading Engine RPM]
→ Sent: 02010c0000000000
← Received: 04410c1388000000
✓ Engine RPM: 1250 RPM
...
```

## That's It!

You now have a working mock OBD-II/UDS ECU running.

## Next Steps

### Monitor CAN Traffic
```bash
candump vcan0
```

### View ECU Logs
```bash
docker logs -f mock-obd
```

### Stop the ECU
```bash
docker stop mock-obd
docker rm mock-obd
```

### Use the Helper Scripts

For easier management, clone the repo and use the scripts:

```bash
git clone <your-repo-url>
cd mockobd
./docker-hub-start.sh
```

## Troubleshooting

### WSL: Module not found
```bash
# Update WSL
wsl --update

# Check kernel version (need 5.10+)
uname -r
```

### vcan0 already exists
```bash
# Delete and recreate
sudo ip link delete vcan0
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

### Permission denied
Make sure to include `--privileged` flag when running Docker commands.

## What's This For?

This mock OBD system simulates an automotive ECU (Engine Control Unit) for:
- Testing OBD-II diagnostic tools
- Developing automotive applications
- Learning CAN bus protocols
- Testing without a real vehicle

## Supported Features

- **OBD-II Mode 01**: Engine RPM, speed, coolant temp, throttle, fuel level
- **UDS Services**: Diagnostic sessions, tester present, read data by ID
- **ISO-TP**: Single-frame requests/responses
- **Standard CAN IDs**: 0x7E0 (request), 0x7E8 (response)

## More Information

- Full documentation: See [README.md](README.md)
- Docker guide: See [DOCKER.md](DOCKER.md)
- Docker Hub: https://hub.docker.com/r/robertsloan2023mit/mock-obd

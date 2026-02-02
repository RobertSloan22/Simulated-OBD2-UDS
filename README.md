# Mock OBD-II/UDS System

**Production-grade automotive diagnostic system simulator** for testing OBD-II applications without a real vehicle.

[![Docker Hub](https://img.shields.io/badge/docker-robertsloan2023mit%2Fmock--obd-blue?logo=docker)](https://hub.docker.com/r/robertsloan2023mit/mock-obd)
[![Docker Pulls](https://img.shields.io/docker/pulls/robertsloan2023mit/mock-obd)](https://hub.docker.com/r/robertsloan2023mit/mock-obd)

---

## 🎉 Version 2.0 Available!

**A complete rewrite with enterprise features:**

- ✅ **Complete ISO-TP**: Multi-frame messages (up to 4095 bytes)
- ✅ **All OBD-II Modes**: Full compliance with 30+ PIDs
- ✅ **Advanced UDS**: 15+ professional diagnostic services
- ✅ **Multi-ECU**: Engine, Transmission, ABS on same bus
- ✅ **Realistic Simulation**: Physics-based vehicle behavior
- ✅ **Control API**: HTTP REST API for runtime control
- ✅ **30+ DTCs**: Fault codes with freeze frames
- ✅ **JSON Config**: Easy vehicle customization

**📖 See [README_V2.md](README_V2.md) for v2.0 documentation**

---

## Quick Start

### Version 2.0 (Recommended)

```bash
# Easy automated setup
./quick-start.sh

# Or manually with Docker
docker compose build
docker compose up -d mock-ecu elm327-emulator

# Connect your app to: server-ip:35000
# Control API available at: http://server-ip:5000
```

**Full v2.0 Guide:** [README_V2.md](README_V2.md)

### Version 1.0 (Legacy)

```bash
# Docker Hub (pre-built image)
./docker-hub-start.sh

# Or build from source
./docker-start.sh
docker compose run --rm test-client
```

---

## Documentation

### Version 2.0
- **[README_V2.md](README_V2.md)** - Complete user guide
- **[CLAUDE_V2.md](CLAUDE_V2.md)** - Technical documentation
- **[APP_TESTING.md](APP_TESTING.md)** - App testing guide

### Version 1.0 (Legacy)
- **[QUICKSTART.md](QUICKSTART.md)** - Quick setup
- **[DOCKER.md](DOCKER.md)** - Docker usage
- **[DOCKERHUB.md](DOCKERHUB.md)** - Docker Hub images

---

## Features Comparison

| Feature | v1.0 | v2.0 |
|---------|------|------|
| OBD-II PIDs | 6 | 30+ |
| OBD-II Modes | 2 | 10 (complete) |
| UDS Services | 3 | 15+ |
| DTCs | None | 30+ with freeze frames |
| Multi-frame ISO-TP | ❌ | ✅ |
| Multi-ECU | ❌ | ✅ (3 ECUs) |
| Control API | ❌ | ✅ (HTTP REST) |
| Readiness Monitors | ❌ | ✅ |
| Vehicle Simulation | Basic | Realistic physics |
| Configuration | Hard-coded | JSON profiles |

---

## Use Cases

### Mobile App Development
Test your iOS/Android OBD-II app without a physical vehicle.

### Fault Injection Testing
Dynamically inject DTCs via API to test error handling.

### CI/CD Integration
Automated testing in your deployment pipeline.

### Education & Training
Learn OBD-II and UDS protocols hands-on.

---

## Architecture

```
┌─────────────────┐
│   Your App      │
└────────┬────────┘
         │ TCP:35000
┌────────▼────────┐
│ ELM327 Emulator │ (AT commands → OBD)
└────────┬────────┘
         │ vcan0
┌────────▼────────┐
│  Mock ECU v2    │ (ISO-TP, Multi-frame)
├─────────────────┤
│ • OBD Services  │ (Modes 01-0A)
│ • UDS Services  │ (0x10-0x85)
│ • Vehicle Sim   │ (Physics-based)
│ • DTC Manager   │ (30+ codes)
└────────┬────────┘
         │
    HTTP REST API (port 5000)
```

---

## V1.0 Quick Reference

### Supported Services (v1.0)

**OBD-II Mode 01 (Current Data):**

| PID  | Description          | Response Format |
|------|---------------------|-----------------|
| 0x00 | Supported PIDs      | 4 bytes bitmask |
| 0x04 | Engine Load         | 0-100%          |
| 0x05 | Coolant Temperature | -40 to 215°C    |
| 0x0C | Engine RPM          | 0-16383 RPM     |
| 0x0D | Vehicle Speed       | 0-255 km/h      |
| 0x11 | Throttle Position   | 0-100%          |
| 0x2F | Fuel Level          | 0-100%          |

**UDS Services:**

| Service | Description               | Response |
|---------|--------------------------|----------|
| 0x10    | Diagnostic Session Control | 0x50   |
| 0x3E    | Tester Present            | 0x7E   |
| 0x22    | Read Data By Identifier   | 0x62   |

### CAN IDs

- Request ID: `0x7E0` (Client → ECU)
- Response ID: `0x7E8` (ECU → Client)
- Functional (broadcast): `0x7DF`

### Setup (v1.0)

**Docker Hub (Easiest):**
```bash
./docker-hub-start.sh
docker compose -f docker-compose.hub.yml run --rm test-client
```

**Native Python:**
```bash
pip install -r requirements.txt
./setup_vcan.sh
python mock_ecu.py  # Terminal 1
python test_client.py  # Terminal 2
```

---

## Monitoring

```bash
# View CAN traffic
candump vcan0

# Filter by ID
candump vcan0,7E0:7FF

# Docker logs
docker compose logs -f mock-ecu
```

---

## Troubleshooting

### vcan0 not found
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

### WSL: vcan module not available
```bash
# Check kernel version (need 5.10+)
uname -r

# Update WSL kernel
wsl --update
```

### Docker network issues
Ensure `network_mode: host` and `privileged: true` in docker-compose.yml

### Permission denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

---

## Contributing

Contributions welcome! Areas for improvement:
- Additional OBD-II PIDs
- More DTC codes
- Additional ECU types
- Protocol enhancements
- Documentation improvements

---

## References

- [ISO 15765-2 (ISO-TP)](https://en.wikipedia.org/wiki/ISO_15765-2)
- [OBD-II PIDs](https://en.wikipedia.org/wiki/OBD-II_PIDs)
- [Unified Diagnostic Services (UDS)](https://en.wikipedia.org/wiki/Unified_Diagnostic_Services)
- [python-can Documentation](https://python-can.readthedocs.io/)

---

## License

[Your License]

---

**Made with ❤️ for the automotive developer community**

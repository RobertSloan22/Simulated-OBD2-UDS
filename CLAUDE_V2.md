# CLAUDE.md - Mock OBD-II System v2.0

This file provides guidance to Claude Code when working with this codebase.

## Project Overview

**Production-grade Mock OBD-II/UDS system** for testing automotive applications. Simulates a complete vehicle network with multiple ECUs, full OBD-II compliance, advanced UDS services, and realistic vehicle behavior.

## Major Upgrade: v2.0

Version 2.0 is a complete rewrite with professional-grade features:

### Key Features

- ✅ **Complete ISO-TP Support**: Multi-frame messages up to 4095 bytes
- ✅ **All 10 OBD-II Modes**: Comprehensive PID coverage (30+)
- ✅ **Advanced UDS**: 15+ services including security access, I/O control, routines
- ✅ **DTC Management**: 30+ fault codes with freeze frames and MIL logic
- ✅ **Multi-ECU**: Engine, Transmission, and ABS ECUs on same bus
- ✅ **Realistic Simulation**: Physics-based sensors with correlations
- ✅ **Control API**: HTTP REST API for runtime control
- ✅ **Drive Cycles**: Readiness monitor tracking
- ✅ **Configuration**: JSON-based vehicle profiles

## Architecture

### Modular Design

```
mockobd/
├── lib/                           # Core library modules
│   ├── isotp.py                  # ISO-TP protocol (SF, FF, CF, FC)
│   ├── vehicle_simulator.py     # Vehicle physics and state machine
│   ├── dtc_manager.py            # Fault code management
│   ├── obd_services.py           # OBD-II Mode 01-0A handlers
│   ├── uds_services.py           # UDS service handlers
│   ├── multi_ecu.py              # Multi-ECU coordinator
│   └── config.py                 # Configuration management
├── vehicle_profiles/              # JSON vehicle configurations
│   ├── default.json
│   ├── honda_civic_2018.json
│   └── ford_f150_2020.json
├── mock_ecu_v2.py                # Main ECU server (NEW)
├── control_api.py                # HTTP REST API
├── elm327_emulator.py            # ELM327 adapter (updated)
├── test_client_v2.py             # Test client (NEW)
└── [legacy files]                # Original v1 files preserved
```

### Component Interaction

```
Your App → ELM327 Emulator → ISO-TP → Mock ECU v2 → Service Handlers
                                                    ↓
                                            Vehicle Simulator
                                                    ↓
                                              DTC Manager
```

## Core Components

### 1. ISO-TP Protocol (lib/isotp.py)

Handles all frame types:
- **Single Frame (SF)**: ≤7 bytes
- **First Frame (FF)**: Initiates multi-frame (payload 8-4095 bytes)
- **Consecutive Frame (CF)**: Continues multi-frame with sequence numbers
- **Flow Control (FC)**: Manages frame flow (CTS/Wait/Overflow)

**Key Classes:**
- `ISOTPHandler`: Combined sender/receiver
- `ISOTPSender`: Fragmentation and transmission
- `ISOTPReceiver`: Reassembly with timeout

### 2. Vehicle Simulator (lib/vehicle_simulator.py)

Realistic vehicle behavior:
- **Engine States**: OFF → CRANKING → RUNNING → STALLING
- **Sensor Correlations**: RPM ↔ MAF ↔ Load, Throttle → Speed → Distance
- **Time-Based**: Warmup (coolant temp rises), fuel consumption, drive cycle tracking
- **Readiness Monitors**: 10 OBD-II monitors with completion tracking

**Key Classes:**
- `VehicleSimulator`: Main coordinator
- `SensorData`: Current sensor readings (dataclass)
- `DriveCycle`: Readiness monitor state

### 3. DTC Manager (lib/dtc_manager.py)

Complete fault code system:
- **States**: Pending → Confirmed → Permanent (emission-related)
- **Freeze Frames**: Sensor snapshot when fault occurs
- **MIL Logic**: Check Engine Light illumination rules
- **Fault Healing**: Pending DTCs clear after clean drive cycles

**Supported DTCs:** P0300 (misfire), P0420 (catalyst), P0171/P0172 (fuel trim), P0443 (EVAP), and 25+ more

### 4. OBD Services (lib/obd_services.py)

All 10 OBD-II modes:
- **Mode 01**: Current data (30+ PIDs including critical PID 01 for readiness)
- **Mode 02**: Freeze frame data
- **Mode 03/07/0A**: Read DTCs (stored/pending/permanent)
- **Mode 04**: Clear DTCs and reset monitors
- **Mode 06**: Test results (O2 monitoring)
- **Mode 08**: Control systems (bidirectional)
- **Mode 09**: Vehicle info (VIN, calibration IDs)

### 5. UDS Services (lib/uds_services.py)

Professional diagnostic services:
- **0x10**: Session control (default/programming/extended/safety)
- **0x27**: Security access with seed/key (key = seed XOR 0x12345678)
- **0x22/0x2E**: Read/Write Data By Identifier (10+ DIDs)
- **0x19/0x14**: Read/Clear DTC information
- **0x2F**: I/O Control (actuator testing)
- **0x31**: Routine Control (diagnostic tests)
- **0x3E**: Tester Present (session keep-alive)
- **0x85**: Control DTC Setting

### 6. Multi-ECU System (lib/multi_ecu.py)

Simulates complete vehicle network:
- **Engine ECU** (0x7E0/0x7E8): Full OBD-II + UDS
- **Transmission ECU** (0x7E1/0x7E9): UDS + limited OBD
- **ABS ECU** (0x7E2/0x7EA): UDS focused
- **Functional Addressing**: Broadcast 0x7DF supported

### 7. Control API (control_api.py)

HTTP REST API (Flask) for runtime control:

**Endpoints:**
```
GET  /api/health                  - Health check
GET  /api/ecu/info                - ECU status
POST /api/dtc/inject              - Inject fault code
POST /api/dtc/clear               - Clear fault codes
GET  /api/dtc/list                - List active DTCs
GET  /api/vehicle/state           - Get sensor data
POST /api/vehicle/set             - Set RPM/speed/throttle
POST /api/vehicle/engine/start    - Start engine
POST /api/readiness/reset         - Reset monitors
POST /api/actuator/control        - Control actuators
```

## Usage

### Quick Start

```bash
# Easiest way
./quick-start.sh

# Or manually with Docker
docker compose up -d mock-ecu elm327-emulator

# Or native Python
python mock_ecu_v2.py
```

### Running Tests

```bash
# All tests
python test_client_v2.py --test all

# Specific test suite
python test_client_v2.py --test obd       # OBD-II basic tests
python test_client_v2.py --test dtc       # DTC tests
python test_client_v2.py --test multiframe # Multi-frame tests
python test_client_v2.py --test uds       # UDS service tests
```

### Using Control API

```bash
# Inject a DTC
curl -X POST http://localhost:5001/api/dtc/inject \
  -H 'Content-Type: application/json' \
  -d '{"ecu": "Engine Control Unit", "code": "P0420", "freeze_frame": true}'

# Get vehicle state
curl http://localhost:5001/api/vehicle/state

# Set vehicle parameters
curl -X POST http://localhost:5001/api/vehicle/set \
  -H 'Content-Type: application/json' \
  -d '{"rpm": 2500, "speed": 80, "throttle": 45}'

# Clear all DTCs
curl -X POST http://localhost:5001/api/dtc/clear \
  -H 'Content-Type: application/json' \
  -d '{}'

# Reset readiness monitors
curl -X POST http://localhost:5001/api/readiness/reset \
  -H 'Content-Type: application/json' \
  -d '{"ecu": "Engine Control Unit"}'
```

### Connecting Your App

Your OBD-II app connects to the ELM327 emulator:
- **Host:** `server-ip:35000`
- **Protocol:** ELM327 over TCP/IP (WiFi OBD mode)

The emulator handles:
- AT command processing
- OBD-II query translation
- Multi-frame response formatting

## Configuration

### Vehicle Profiles

Create custom vehicles by editing JSON files in `vehicle_profiles/`:

```json
{
  "vehicle": {
    "make": "Honda",
    "model": "Civic",
    "year": 2018,
    "vin": "19XFC2F59JE012345"
  },
  "sensors": {
    "rpm_idle": 750,
    "rpm_max": 6500,
    "coolant_temp_normal": 92,
    "fuel_capacity": 46.9
  },
  "dtcs": [
    {
      "code": "P0420",
      "description": "Catalyst System Efficiency Below Threshold",
      "trigger_condition": "random",
      "probability": 0.03,
      "mil_illuminate": true
    }
  ]
}
```

Load custom profile:
```bash
python mock_ecu_v2.py --config honda_civic_2018.json
```

## Extension Points

### Adding OBD-II PIDs

Edit `lib/obd_services.py`:

```python
def _mode_01_current_data(self, request: bytes) -> bytes:
    # ...
    elif pid == 0x5C:  # Engine oil temperature
        oil_temp = int(sensors.coolant_temp + 10 + 40)
        return bytes([0x41, 0x5C, oil_temp])
```

### Adding UDS Services

Edit `lib/uds_services.py`:

```python
def process(self, request: bytes) -> Optional[bytes]:
    # ...
    elif service == 0x86:  # Response On Event
        return self._service_86_response_on_event(request)
```

### Adding DTCs

Edit `lib/dtc_manager.py` in `DTC_DEFINITIONS`:

```python
'P0505': ('Idle Control System Malfunction', True, False),
```

### Custom ECU

Create new ECU identity in `lib/multi_ecu.py`:

```python
BODY_ECU = ECUIdentity(
    ecu_type=ECUType.BODY,
    name="Body Control Module",
    request_id=0x7E3,
    response_id=0x7EB,
    dtc_prefix="B0"
)
```

## Testing Strategy

### Unit Testing

Each module is independently testable:
```python
from lib.isotp import ISOTPFrame
frame = ISOTPFrame.create_first_frame(20, b'test'*5)
```

### Integration Testing

Use test client:
```bash
python test_client_v2.py --test all
```

### App Testing

1. Start system: `./quick-start.sh`
2. Configure app to connect to `server-ip:35000`
3. Use Control API to inject faults and control vehicle state
4. Test app's DTC handling, live data display, etc.

## Monitoring

### View Logs

```bash
# Docker
docker compose logs -f mock-ecu
docker compose logs -f elm327-emulator

# Native
tail -f mock_ecu.log
tail -f elm327.log

# CAN traffic
candump vcan0
```

### API Monitoring

```bash
# Health check
curl http://localhost:5001/api/health

# ECU status
curl http://localhost:5001/api/ecu/info | jq

# Vehicle state
watch -n 1 'curl -s http://localhost:5001/api/vehicle/state | jq'
```

## Troubleshooting

### Issue: Multi-frame not working

**Solution:** Ensure ISO-TP is properly initialized:
```python
isotp = ISOTPHandler(bus, tx_id, rx_id, ISOTPConfig())
```

### Issue: DTCs not appearing

**Solution:** Check DTC state (may be pending, not confirmed):
```bash
curl http://localhost:5001/api/dtc/list?ecu=Engine%20Control%20Unit
```

### Issue: Readiness monitors incomplete

**Solution:** Monitors require drive cycles. Use API to complete:
```python
# Simulate extended driving
vehicle.update(dt=300)  # 5 minutes of operation
```

## Performance

- **Latency**: <10ms for single-frame requests
- **Throughput**: 100+ requests/second
- **Memory**: ~50MB per ECU
- **CPU**: <5% on modern systems

## Compatibility

- **OBD-II Apps**: Torque, Car Scanner, OBD Fusion, etc.
- **Protocols**: OBD-II (ISO 15765-4), UDS (ISO 14229)
- **Python**: 3.8+
- **Platforms**: Linux (vcan required), Docker

## Future Enhancements

- CAN-FD support (higher bandwidth)
- J1939 (heavy-duty vehicles)
- Additional ECUs (airbag, steering, climate)
- Replay mode (record/playback CAN traffic)
- Web dashboard for Control API
- Bluetooth support for ELM327 emulator

## License

[Your license here]

## Support

For issues or questions:
- GitHub Issues: [repo URL]
- Documentation: See APP_TESTING.md for app-specific testing guide

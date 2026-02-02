# KOEO Testing Guide

**Key On Engine Off (KOEO)** testing guide for advanced UDS diagnostics.

## What is KOEO?

KOEO (Key On Engine Off) is a diagnostic state where:
- ✅ Ignition is ON (key turned to ON position)
- ✅ ECU is fully powered and responsive
- ✅ Engine is NOT running (RPM = 0)
- ✅ All UDS diagnostic services are available

This state is required for many advanced diagnostics like:
- Actuator tests (relays, solenoids, motors)
- Self-tests and routines
- Component validation
- Some DTC operations
- Security access procedures

---

## Quick Start: KOEO Mode

### Method 1: Using Web Dashboard (Easiest)

Open your browser and navigate to **http://localhost:5000** (or your server IP):

1. Click the **🟢 ON (KOEO)** button in the Ignition Control card
2. Or click the **🔧 KOEO Mode** button for quick activation
3. Monitor the Vehicle Status card to confirm:
   - Ignition State shows "ON (KOEO)"
   - Engine RPM is 0
   - ECU is responsive

The dashboard provides visual feedback and real-time status updates.

### Method 2: Using Control API (Command Line)

```bash
# Set vehicle to KOEO mode (one command)
curl -X POST http://localhost:5000/api/vehicle/koeo

# Response:
{
  "status": "ok",
  "message": "KOEO mode activated",
  "ignition_state": "on",
  "engine_state": "off",
  "diagnostics_available": true
}
```

### Method 3: Manual Ignition Control

```bash
# Turn ignition to ON position
curl -X POST http://localhost:5000/api/vehicle/ignition/on

# Verify state
curl http://localhost:5000/api/vehicle/state
```

---

## Ignition States

The system supports 4 ignition states:

| State | Description | Engine | ECU | Diagnostics |
|-------|-------------|--------|-----|-------------|
| **OFF** | Key off | OFF | Powered Down | ❌ None |
| **ACCESSORY** | Accessories only | OFF | Limited | ⚠️ Basic only |
| **ON** | Key on, engine off (KOEO) | OFF | Fully Powered | ✅ All available |
| **START** | Cranking | Cranking | Fully Powered | ⚠️ Limited |

---

## API Endpoints for Ignition Control

### Set Ignition State

```bash
# Turn key OFF (powers down ECU)
curl -X POST http://localhost:5000/api/vehicle/ignition/off

# Turn key to ACCESSORY
curl -X POST http://localhost:5000/api/vehicle/ignition/acc

# Turn key to ON (KOEO mode)
curl -X POST http://localhost:5000/api/vehicle/ignition/on

# Turn key to START (cranking)
curl -X POST http://localhost:5000/api/vehicle/ignition/start
```

### Quick KOEO Mode

```bash
# Single command to enter KOEO
curl -X POST http://localhost:5000/api/vehicle/koeo
```

### Engine Control (Respects Ignition State)

```bash
# Start engine (requires ignition ON or START)
curl -X POST http://localhost:5000/api/vehicle/engine/start

# Stop engine (returns to KOEO mode)
curl -X POST http://localhost:5000/api/vehicle/engine/stop
```

---

## Testing KOEO-Specific UDS Services

### 1. Actuator Tests (UDS 0x2F - I/O Control)

**Scenario:** Test fuel pump relay

```bash
# 1. Enter KOEO mode
curl -X POST http://localhost:5000/api/vehicle/koeo

# 2. Start extended diagnostic session
# (via OBD client or direct CAN)
echo "10 03" | # UDS 0x10 sub 0x03

# 3. Activate fuel pump relay (UDS 0x2F)
curl -X POST http://localhost:5000/api/actuator/control \
  -H 'Content-Type: application/json' \
  -d '{
    "ecu": "Engine Control Unit",
    "did": "0x0110",
    "state": "on"
  }'

# 4. Listen for fuel pump activation
# (your app should detect relay click/activation)

# 5. Deactivate
curl -X POST http://localhost:5000/api/actuator/control \
  -H 'Content-Type: application/json' \
  -d '{"did": "0x0110", "state": "off"}'
```

### 2. Self-Test Routines (UDS 0x31 - Routine Control)

**Scenario:** Run ECU self-test

```python
# Python test script
from test_client_v2 import AdvancedOBDClient

client = AdvancedOBDClient()

# Enter KOEO mode first
import requests
requests.post('http://localhost:5000/api/vehicle/koeo')

# Start extended diagnostic session
response = client.send_request(bytes([0x10, 0x03]))
print(f"Session started: {response.hex()}")

# Start self-test routine (0x0201)
response = client.send_request(bytes([0x31, 0x01, 0x02, 0x01]))
print(f"Self-test started: {response.hex()}")

# Request results
response = client.send_request(bytes([0x31, 0x03, 0x02, 0x01]))
print(f"Self-test results: {response.hex()}")
```

### 3. Security Access (UDS 0x27)

**Scenario:** Unlock ECU for protected operations

```bash
# 1. Enter KOEO mode
curl -X POST http://localhost:5000/api/vehicle/koeo

# 2. Start extended diagnostic session
# Send: 10 03
# Expect: 50 03 ...

# 3. Request seed (level 1)
# Send: 27 01
# Expect: 67 01 [4-byte seed]

# 4. Calculate key (seed XOR 0x12345678)
# Send: 27 02 [4-byte key]
# Expect: 67 02 (unlocked)

# Now you can perform protected operations
```

### 4. Component Validation

**Scenario:** Test O2 sensor heater

```bash
# KOEO mode
curl -X POST http://localhost:5000/api/vehicle/koeo

# Read O2 sensor status (UDS 0x22)
# DID 0x0130 (example)
# Send: 22 01 30
# Expect: 62 01 30 [data]

# Enable heater (UDS 0x2F)
# Send: 2F 01 30 03 01
# Expect: 6F 01 30 03

# Monitor temperature rise via continuous reads
```

---

## Test Workflow Examples

### Complete KOEO Test Sequence

```bash
#!/bin/bash
# KOEO test automation script

# 1. Power cycle
echo "Powering off ECU..."
curl -X POST http://localhost:5000/api/vehicle/ignition/off
sleep 2

# 2. Enter KOEO
echo "Entering KOEO mode..."
curl -X POST http://localhost:5000/api/vehicle/koeo

# 3. Clear DTCs
echo "Clearing DTCs..."
curl -X POST http://localhost:5000/api/dtc/clear

# 4. Start extended diagnostic session
echo "Starting diagnostic session..."
python -c "
from test_client_v2 import AdvancedOBDClient
client = AdvancedOBDClient()
response = client.send_request(bytes([0x10, 0x03]))
print(f'Session: {response.hex()}')
"

# 5. Run self-tests
echo "Running self-tests..."
# Your test commands here

# 6. Read DTCs
echo "Checking for new DTCs..."
curl http://localhost:5000/api/dtc/list

# 7. Power off
echo "Test complete, powering off..."
curl -X POST http://localhost:5000/api/vehicle/ignition/off
```

### Testing Actuator Control

```python
#!/usr/bin/env python3
"""KOEO actuator test script"""

import requests
import time
from test_client_v2 import AdvancedOBDClient

API_BASE = "http://localhost:5000/api"

def test_actuator(actuator_did, name):
    """Test an actuator in KOEO mode"""
    print(f"\nTesting {name} (DID: {actuator_did})...")

    # Activate
    print(f"  Activating...")
    requests.post(f"{API_BASE}/actuator/control", json={
        "ecu": "Engine Control Unit",
        "did": actuator_did,
        "state": "on"
    })
    time.sleep(2)

    # Deactivate
    print(f"  Deactivating...")
    requests.post(f"{API_BASE}/actuator/control", json={
        "did": actuator_did,
        "state": "off"
    })
    time.sleep(1)

    print(f"  ✓ {name} test complete")

# Main test
if __name__ == "__main__":
    # Enter KOEO
    print("Setting KOEO mode...")
    requests.post(f"{API_BASE}/vehicle/koeo")

    # Test actuators
    test_actuator("0x0110", "Fuel Pump Relay")
    test_actuator("0x0111", "Cooling Fan Relay")
    test_actuator("0x0112", "A/C Compressor Clutch")

    print("\n✓ All actuator tests complete")
```

---

## Verifying KOEO Mode

### Check Vehicle State

```bash
# Check current state
curl http://localhost:5000/api/vehicle/state | jq

# Look for:
{
  "status": "ok",
  "state": {
    "rpm": 0,                    # Engine is OFF
    "battery_voltage": 12.6,     # Key is ON
    "engine_runtime": 0          # Not running
  }
}
```

### Via Test Client

```python
from test_client_v2 import AdvancedOBDClient

client = AdvancedOBDClient()

# Read RPM (should be 0)
response = client.send_request(bytes([0x01, 0x0C]))
if response and response[0] == 0x41:
    rpm = ((response[2] << 8) | response[3]) / 4
    print(f"RPM: {rpm} (should be 0 for KOEO)")

# ECU should still respond to all requests
response = client.send_request(bytes([0x3E, 0x00]))  # Tester Present
if response and response[0] == 0x7E:
    print("✓ ECU is responsive in KOEO mode")
```

---

## Common KOEO Test Scenarios

### 1. Pre-Delivery Inspection (PDI)

```bash
# Enter KOEO
curl -X POST http://localhost:5000/api/vehicle/koeo

# Run all self-tests
# Check for DTCs
# Verify all systems ready
```

### 2. After-Repair Verification

```bash
# Clear DTCs
curl -X POST http://localhost:5000/api/dtc/clear

# Enter KOEO
curl -X POST http://localhost:5000/api/vehicle/koeo

# Run component tests
# Verify repair successful
```

### 3. Component Replacement Validation

```bash
# KOEO mode
curl -X POST http://localhost:5000/api/vehicle/koeo

# Security access (if needed)
# Component adaptation
# Verify new component functional
```

---

## Troubleshooting

### Engine Won't Start After KOEO Tests

```bash
# This is normal - ignition may have timed out
# Solution: Turn key to START
curl -X POST http://localhost:5000/api/vehicle/ignition/start
```

### UDS Services Rejected in KOEO

```bash
# Some services require extended diagnostic session
# Solution: Start session first
python -c "
from test_client_v2 import AdvancedOBDClient
client = AdvancedOBDClient()
client.send_request(bytes([0x10, 0x03]))  # Extended session
"
```

### Actuator Not Responding

```bash
# May require security access
# 1. Enter KOEO
# 2. Start extended session
# 3. Perform security access
# 4. Then control actuator
```

---

## Best Practices

1. **Always enter KOEO explicitly** - Don't assume state
2. **Verify RPM = 0** before running tests
3. **Use extended diagnostic session** for advanced features
4. **Security access** may be required for some operations
5. **Clear DTCs before testing** to isolate new faults
6. **Power cycle between tests** for clean state
7. **Monitor timeouts** - some tests take time

---

## Integration with Your App

### Example: App Testing Workflow

```python
# Your app test suite
def test_koeo_diagnostics(app):
    """Test app's KOEO diagnostic features"""

    # 1. Setup - Enter KOEO
    setup_koeo_mode()

    # 2. Test app connects
    assert app.connect()

    # 3. Test app reads live data (RPM should be 0)
    data = app.read_live_data()
    assert data['rpm'] == 0
    assert data['ecu_responsive'] == True

    # 4. Test app can perform actuator tests
    result = app.test_fuel_pump()
    assert result == "PASS"

    # 5. Cleanup
    teardown_koeo_mode()
```

---

## API Reference Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/vehicle/koeo` | POST | Enter KOEO mode (one step) |
| `/api/vehicle/ignition/on` | POST | Turn key to ON |
| `/api/vehicle/ignition/off` | POST | Turn key OFF |
| `/api/vehicle/engine/stop` | POST | Stop engine (stay in KOEO) |
| `/api/vehicle/state` | GET | Check current state |
| `/api/actuator/control` | POST | Control actuators |
| `/api/dtc/clear` | POST | Clear DTCs |

---

**For more information:**
- Main Documentation: [README_V2.md](README_V2.md)
- Control API Guide: [README_V2.md#control-api](README_V2.md#control-api)
- Test Examples: [test_client_v2.py](test_client_v2.py)

# Web Dashboard Guide

The Mock OBD-II system includes a modern web-based control dashboard for easy vehicle simulation and diagnostics testing.

## Accessing the Dashboard

When the system is running, open your browser and navigate to:
```
http://localhost:5000
```

Or if running on a remote server:
```
http://your-server-ip:5000
```

The dashboard is accessible from any device on your network - laptop, tablet, or phone.

---

## Dashboard Features

### 1. Vehicle Status Card

Real-time monitoring of vehicle parameters:
- **Ignition State**: Current ignition position (OFF/ACCESSORY/ON/START)
- **Engine RPM**: Current engine speed
- **Speed**: Vehicle speed in km/h
- **Coolant Temp**: Engine coolant temperature in Celsius
- **Throttle**: Throttle position percentage
- **MIL Status**: Malfunction Indicator Lamp (Check Engine Light)

Status updates automatically every 2 seconds.

### 2. Ignition Control Card

Control the vehicle's ignition state with visual buttons:

- **🔴 OFF**: Powers down the ECU completely
- **🟡 ACCESSORY**: Accessories only, limited diagnostics
- **🟢 ON (KOEO)**: Key On Engine Off - full diagnostics available
- **⚡ START**: Cranking position
- **🔧 KOEO Mode**: Quick button to enter KOEO state

**Use Case**: Testing KOEO-specific UDS features like actuator tests and self-diagnostics.

### 3. Engine Control Card

Start and stop the engine:

- **▶️ Start Engine**: Cranks and starts the engine (requires ignition ON or START)
- **⏹️ Stop Engine**: Stops engine and returns to KOEO mode

### 4. Vehicle Parameters Card

Manually set vehicle operating parameters:

- **RPM**: Engine speed (0-7000)
- **Speed**: Vehicle speed in km/h (0-250)
- **Throttle**: Throttle position (0-100%)

**Apply Changes** button commits all parameter changes at once.

**Use Case**: Simulating specific driving conditions for testing app behavior.

### 5. DTC Management Card

Inject and manage diagnostic trouble codes:

**Pre-configured DTCs:**
- **P0420**: Catalyst System Efficiency Below Threshold
- **P0300**: Random Misfire Detected
- **P0171**: System Too Lean (Bank 1)
- **P0172**: System Too Rich (Bank 1)
- **P0128**: Coolant Thermostat (Coolant Temp Below Threshold)
- **P0562**: System Voltage Low
- **P0443**: EVAP Purge Control Valve Circuit

**Actions:**
- **➕ Inject DTC**: Adds selected DTC with freeze frame
- **🗑️ Clear All DTCs**: Removes all active DTCs from all ECUs

**DTC List**: Displays all active DTCs with code, description, state, occurrence count, and MIL status.

**Use Case**: Testing app DTC handling, error displays, and MIL indicator.

### 6. ECU Information Card

Shows all registered ECUs in the system:

- Engine Control Unit (0x7E0 → 0x7E8)
- Transmission Control Unit (0x7E1 → 0x7E9)
- ABS Control Unit (0x7E2 → 0x7EA)

Displays CAN IDs for each ECU (request ID → response ID).

---

## Common Workflows

### Testing Your App with Injected Faults

1. **Start clean**:
   - Click **🗑️ Clear All DTCs**
   - Set ignition to **🟢 ON (KOEO)**

2. **Inject a fault**:
   - Select **P0420** from dropdown
   - Click **➕ Inject DTC**

3. **Verify in your app**:
   - Your OBD-II app should now display the P0420 code
   - Check that MIL (Check Engine Light) is illuminated

4. **Test clearing**:
   - Use your app to clear the DTC
   - Verify the DTC disappears from dashboard

### Simulating Driving Conditions

1. **Start the vehicle**:
   - Click **🟢 ON (KOEO)**
   - Click **▶️ Start Engine**
   - Verify RPM shows idle speed (~750)

2. **Simulate acceleration**:
   - Set RPM: **3000**
   - Set Speed: **80**
   - Set Throttle: **50**
   - Click **Apply Changes**

3. **Monitor in your app**:
   - Verify live data updates match dashboard values
   - Test your app's gauge displays

### KOEO Diagnostic Testing

1. **Enter KOEO mode**:
   - Click **🔧 KOEO Mode** button
   - Verify: Ignition = ON, RPM = 0

2. **Run UDS diagnostics** (via your app or test client):
   - Extended diagnostic session (0x10 0x03)
   - Actuator tests (0x2F)
   - Self-test routines (0x31)

3. **Monitor results**:
   - Check Vehicle Status for any changes
   - Verify no unwanted DTCs are triggered

---

## Auto-Refresh

The dashboard automatically refreshes vehicle status every 2 seconds. You can manually refresh all data at any time by clicking the **🔄 Refresh** button in the bottom-right corner.

---

## Alerts and Feedback

The dashboard provides instant feedback for all operations:

- **✅ Green alerts**: Successful operations
- **❌ Red alerts**: Errors or failures

Alerts automatically disappear after 3 seconds.

---

## Browser Compatibility

The dashboard works on all modern browsers:
- Chrome/Chromium
- Firefox
- Safari
- Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

**Recommended**: Chrome or Firefox for best performance.

---

## Network Access

The dashboard is accessible from any device on your network:

**Same machine:**
```
http://localhost:5000
```

**Other devices on network:**
```
http://192.168.1.100:5000  # Replace with your server IP
```

**Docker deployment:**
Make sure port 5000 is mapped in docker-compose.yml:
```yaml
ports:
  - "5000:5000"
```

---

## Troubleshooting

### Dashboard not loading

**Check API is running:**
```bash
curl http://localhost:5000/api/health
# Should return: {"status": "ok", "timestamp": ...}
```

**Check Docker port mapping:**
```bash
docker compose ps
# Verify port 5000:5000 is mapped
```

### Connection errors

**Check firewall:**
```bash
# Allow port 5000
sudo ufw allow 5000
```

**Check Docker network:**
```bash
docker compose logs control-api
# Look for "Control API started on http://0.0.0.0:5000"
```

### Values not updating

**Verify ECU is running:**
```bash
docker compose ps
# mock-ecu should be "Up"
```

**Check vcan0 interface:**
```bash
ip link show vcan0
# Should show state UP
```

---

## API Integration

The dashboard uses the Control API REST endpoints. You can use the same endpoints in your own automation:

**Example: Inject DTC via curl**
```bash
curl -X POST http://localhost:5000/api/dtc/inject \
  -H 'Content-Type: application/json' \
  -d '{"code": "P0420", "ecu": "Engine Control Unit"}'
```

**Example: Get vehicle state**
```bash
curl http://localhost:5000/api/vehicle/state | jq
```

See [KOEO_TESTING.md](KOEO_TESTING.md) for complete API documentation.

---

## Features

- ✅ Real-time status monitoring
- ✅ Visual ignition control
- ✅ One-click DTC injection
- ✅ Engine start/stop simulation
- ✅ Manual parameter adjustment
- ✅ Multi-ECU information display
- ✅ Responsive design (mobile-friendly)
- ✅ Auto-refresh every 2 seconds
- ✅ Instant operation feedback

---

**Made with ❤️ for automotive developers**

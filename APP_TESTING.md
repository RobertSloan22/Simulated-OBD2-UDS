# Testing Your OBD-II App with Mock ECU

This guide shows how to test your OBD-II application against the mock ECU system.

## Quick Start

### 1. Start the Mock System

On your server:

```bash
./docker-start-with-elm327.sh
```

This starts:
- Mock ECU (simulates a vehicle's ECU)
- ELM327 Emulator (mimics a Bluetooth OBD adapter)

### 2. Get Your Server's IP Address

```bash
hostname -I
```

Example output: `192.168.1.100`

### 3. Configure Your App

Instead of connecting to a Bluetooth device, configure your app to connect via **TCP/IP**:

- **Host:** `192.168.1.100` (your server's IP)
- **Port:** `35000`

Many OBD-II apps support "WiFi OBD adapters" - use that mode.

## Supported Apps

This emulator is compatible with apps that support:
- **ELM327 protocol** (industry standard)
- **WiFi/TCP OBD adapters** (vs Bluetooth)

Popular apps that work:
- Torque Pro (Android) - WiFi mode
- Car Scanner (iOS/Android) - WiFi mode
- OBD Fusion (iOS) - WiFi mode
- Custom apps using libraries like:
  - python-OBD
  - obd-parser
  - Any ELM327-compatible library

## Available OBD-II Data

The mock ECU provides realistic simulated data:

| PID | Parameter | Value Range |
|-----|-----------|-------------|
| 01 0C | Engine RPM | 800-3000 RPM (simulated) |
| 01 0D | Vehicle Speed | 0-120 km/h (simulated) |
| 01 05 | Coolant Temperature | 80-95°C |
| 01 04 | Engine Load | 20-80% |
| 01 11 | Throttle Position | 0-100% |
| 01 2F | Fuel Level | 0-100% |
| 09 02 | VIN | MOCK12345VIN67890 |

## Testing Your App's Features

### Basic Connection Test

Your app should:
1. Connect to `server-ip:35000`
2. Send `ATZ` (reset command)
3. Receive `ELM327 v1.5`
4. Initialize with AT commands (protocol selection, etc.)

### Read Live Data

Your app can query:
- **RPM:** Send `01 0C`, receive engine RPM
- **Speed:** Send `01 0D`, receive vehicle speed
- **Temperature:** Send `01 05`, receive coolant temp

### Read VIN

Send: `09 02` (OBD-II Mode 09, VIN request)

### UDS Diagnostics

Send: `22 F1 90` (Read VIN via UDS)

## Monitoring Traffic

Watch the communication between your app and the mock ECU:

```bash
# View ELM327 emulator logs
docker compose logs -f elm327-emulator

# View CAN traffic
docker compose exec mock-ecu candump vcan0
```

## Troubleshooting

### App Can't Connect

- **Firewall:** Ensure port 35000 is open on your server
  ```bash
  sudo ufw allow 35000/tcp
  ```
- **Network:** Verify your laptop can ping the server
  ```bash
  ping 192.168.1.100
  ```
- **Service Running:** Check containers are up
  ```bash
  docker compose ps
  ```

### App Connects But No Data

Check the logs:
```bash
docker compose logs elm327-emulator
docker compose logs mock-ecu
```

You should see:
- `[ELM327] Client connected: (laptop-ip, port)`
- CAN traffic on vcan0

### App Shows "Protocol Error"

Some apps are strict about protocol. Try:
1. Restart the emulator: `docker compose restart elm327-emulator`
2. Check your app's protocol setting (should be "AUTO" or "ISO 15765-4 CAN")

## Development Workflow

### Typical Development Session

1. Start mock system on server:
   ```bash
   ./docker-start-with-elm327.sh
   ```

2. Run your app on laptop, configure connection to server:35000

3. Monitor traffic while testing:
   ```bash
   docker compose logs -f elm327-emulator
   ```

4. Make changes to your app, test immediately (no real car needed!)

### Modifying Simulated Data

To change the simulated vehicle data, edit `mock_ecu.py`:

```python
# In MockECU.__init__():
self.vehicle_data = {
    'rpm': 1500,           # Engine RPM
    'speed': 50,           # Vehicle speed (km/h)
    'coolant_temp': 90,    # Coolant temp (°C)
    # ... modify as needed
}
```

Then restart:
```bash
docker compose restart mock-ecu
```

## Advanced Usage

### Using Different Port

```bash
docker compose run --rm -p 5000:5001 \
  elm327-emulator python elm327_emulator.py --port 5000
```

### Multiple Clients

The emulator supports multiple concurrent connections - test multiple apps simultaneously!

### Custom OBD Commands

The mock ECU can be extended with custom PIDs. See `CLAUDE.md` for details.

## Stopping the System

```bash
docker compose down
```

Or use the stop script:
```bash
./docker-stop.sh
```

## Next Steps

- Extend the mock ECU with custom PIDs for your specific testing needs
- Add error injection to test your app's error handling
- Implement multi-frame responses for testing complex queries

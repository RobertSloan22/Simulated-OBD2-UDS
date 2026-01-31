# Docker Quick Reference

## Quick Start

```bash
# Start the mock ECU
./docker-start.sh

# View logs
docker compose logs -f mock-ecu

# Run test client
docker compose run --rm test-client

# Stop everything
./docker-stop.sh
```

## Common Commands

### Start Mock ECU
```bash
docker compose up -d mock-ecu
```

### View Logs
```bash
# Follow logs
docker compose logs -f mock-ecu

# Last 50 lines
docker compose logs --tail=50 mock-ecu
```

### Run Test Client
```bash
docker compose run --rm test-client
```

### Interactive Shell
```bash
# Get a shell inside the container
docker compose run --rm mock-ecu bash

# From inside the container, you can:
python mock_ecu.py
python test_client.py
candump vcan0
```

### Stop and Clean Up
```bash
# Stop containers
docker compose down

# Remove images
docker compose down --rmi all

# Full cleanup (containers, images, volumes)
docker compose down --rmi all -v
```

## Monitoring CAN Traffic

From the host (outside Docker):
```bash
candump vcan0
```

From inside a container:
```bash
docker compose run --rm mock-ecu candump vcan0
```

## Custom Scripts

### Run Custom Python Script
Create a file `my_script.py` in the project directory, then:

```bash
# Mount and run
docker compose run --rm -v $(pwd)/my_script.py:/app/my_script.py mock-ecu python my_script.py
```

### Use as Development Environment
```bash
# Start bash in container
docker compose run --rm mock-ecu bash

# Inside container, edit and run
python mock_ecu.py
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs mock-ecu

# Verify vcan0 exists on host
ip link show vcan0

# Recreate vcan0
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

### Can't Access vcan0 from Container
Ensure docker-compose.yml has:
```yaml
network_mode: host
privileged: true
```

### WSL Specific

Check kernel version (need 5.10+):
```bash
uname -r
```

Update WSL if needed:
```bash
wsl --update
```

Load vcan module:
```bash
sudo modprobe vcan
```

### Permission Errors
Make sure scripts are executable:
```bash
chmod +x docker-start.sh docker-stop.sh setup_vcan.sh
```

## Port to Other Laptops

To use on another machine:

1. Copy the entire project directory
2. Install Docker and Docker Compose
3. Run `./docker-start.sh`

No need to install Python dependencies or create virtual environments!

## Building Without Cache
```bash
docker compose build --no-cache
```

## Using Different Python Version
Edit `Dockerfile` and change:
```dockerfile
FROM python:3.11-slim
```
to desired version (e.g., `python:3.12-slim`).

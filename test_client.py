#!/usr/bin/env python3
"""
OBD/UDS Test Client
Tests the mock ECU by sending various OBD-II and UDS requests
"""

import can
import time

class OBDClient:
    def __init__(self, can_interface='vcan0', request_id=0x7E0, response_id=0x7E8):
        """
        Initialize OBD Client

        Args:
            can_interface: CAN interface name
            request_id: CAN ID to send requests
            response_id: CAN ID to receive responses
        """
        self.bus = can.interface.Bus(channel=can_interface, interface='socketcan')
        self.request_id = request_id
        self.response_id = response_id

        print(f"OBD Client initialized")
        print(f"  Sending on CAN ID: 0x{request_id:03X}")
        print(f"  Receiving on CAN ID: 0x{response_id:03X}\n")

    def send_request(self, service, *params):
        """Send OBD/UDS request"""
        payload = bytes([service] + list(params))
        length = len(payload)

        if length <= 7:  # Single frame
            pci = 0x00 | length
            data = bytes([pci]) + payload + bytes([0x00] * (7 - length))

            msg = can.Message(
                arbitration_id=self.request_id,
                data=data,
                is_extended_id=False
            )

            self.bus.send(msg)
            print(f"→ Sent: {data.hex()}")

            # Wait for response
            return self._wait_for_response()

        return None

    def _wait_for_response(self, timeout=1.0):
        """Wait for response from ECU"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            msg = self.bus.recv(timeout=0.1)

            if msg and msg.arbitration_id == self.response_id:
                data = bytes(msg.data)
                print(f"← Received: {data.hex()}")

                # Parse single frame
                pci = data[0] & 0xF0
                length = data[0] & 0x0F

                if pci == 0x00:  # Single frame
                    return data[1:1+length]

        print("← Timeout: No response")
        return None

    def read_engine_rpm(self):
        """Read engine RPM (Mode 01, PID 0x0C)"""
        print("\n[Reading Engine RPM]")
        response = self.send_request(0x01, 0x0C)

        if response and len(response) >= 4 and response[0] == 0x41:
            rpm = ((response[2] << 8) | response[3]) / 4
            print(f"✓ Engine RPM: {rpm:.0f} RPM\n")
            return rpm
        else:
            print("✗ Failed to read RPM\n")
            return None

    def read_vehicle_speed(self):
        """Read vehicle speed (Mode 01, PID 0x0D)"""
        print("\n[Reading Vehicle Speed]")
        response = self.send_request(0x01, 0x0D)

        if response and len(response) >= 3 and response[0] == 0x41:
            speed = response[2]
            print(f"✓ Vehicle Speed: {speed} km/h\n")
            return speed
        else:
            print("✗ Failed to read speed\n")
            return None

    def read_coolant_temp(self):
        """Read coolant temperature (Mode 01, PID 0x05)"""
        print("\n[Reading Coolant Temperature]")
        response = self.send_request(0x01, 0x05)

        if response and len(response) >= 3 and response[0] == 0x41:
            temp = response[2] - 40
            print(f"✓ Coolant Temperature: {temp}°C\n")
            return temp
        else:
            print("✗ Failed to read temperature\n")
            return None

    def read_throttle_position(self):
        """Read throttle position (Mode 01, PID 0x11)"""
        print("\n[Reading Throttle Position]")
        response = self.send_request(0x01, 0x11)

        if response and len(response) >= 3 and response[0] == 0x41:
            throttle = (response[2] * 100) / 255
            print(f"✓ Throttle Position: {throttle:.1f}%\n")
            return throttle
        else:
            print("✗ Failed to read throttle\n")
            return None

    def read_fuel_level(self):
        """Read fuel level (Mode 01, PID 0x2F)"""
        print("\n[Reading Fuel Level]")
        response = self.send_request(0x01, 0x2F)

        if response and len(response) >= 3 and response[0] == 0x41:
            fuel = (response[2] * 100) / 255
            print(f"✓ Fuel Level: {fuel:.1f}%\n")
            return fuel
        else:
            print("✗ Failed to read fuel level\n")
            return None

    def read_engine_load(self):
        """Read engine load (Mode 01, PID 0x04)"""
        print("\n[Reading Engine Load]")
        response = self.send_request(0x01, 0x04)

        if response and len(response) >= 3 and response[0] == 0x41:
            load = (response[2] * 100) / 255
            print(f"✓ Engine Load: {load:.1f}%\n")
            return load
        else:
            print("✗ Failed to read engine load\n")
            return None

    def read_supported_pids(self):
        """Read supported PIDs (Mode 01, PID 0x00)"""
        print("\n[Reading Supported PIDs]")
        response = self.send_request(0x01, 0x00)

        if response and len(response) >= 6 and response[0] == 0x41:
            print(f"✓ Supported PIDs: {response[2:6].hex()}\n")
            return response[2:6]
        else:
            print("✗ Failed to read supported PIDs\n")
            return None

    def tester_present(self):
        """Send tester present (UDS Service 0x3E)"""
        print("\n[Sending Tester Present]")
        response = self.send_request(0x3E, 0x00)

        if response and response[0] == 0x7E:
            print("✓ Tester present acknowledged\n")
            return True
        else:
            print("✗ Tester present failed\n")
            return False

    def start_diagnostic_session(self, session_type=0x01):
        """Start diagnostic session (UDS Service 0x10)"""
        print(f"\n[Starting Diagnostic Session 0x{session_type:02X}]")
        response = self.send_request(0x10, session_type)

        if response and response[0] == 0x50:
            print(f"✓ Diagnostic session started\n")
            return True
        else:
            print("✗ Failed to start session\n")
            return False

    def close(self):
        """Close the CAN bus connection"""
        self.bus.shutdown()


def main():
    """Main test function"""
    print("=" * 60)
    print("OBD/UDS Test Client")
    print("=" * 60)
    print()

    client = OBDClient(can_interface='vcan0')

    try:
        # Test basic OBD-II requests
        print("Testing OBD-II Requests...")
        print("=" * 60)

        client.read_supported_pids()
        time.sleep(0.5)

        client.read_engine_rpm()
        time.sleep(0.5)

        client.read_vehicle_speed()
        time.sleep(0.5)

        client.read_coolant_temp()
        time.sleep(0.5)

        client.read_throttle_position()
        time.sleep(0.5)

        client.read_fuel_level()
        time.sleep(0.5)

        client.read_engine_load()
        time.sleep(0.5)

        # Test UDS requests
        print("\nTesting UDS Requests...")
        print("=" * 60)

        client.start_diagnostic_session(0x01)
        time.sleep(0.5)

        client.tester_present()
        time.sleep(0.5)

        print("\n" + "=" * 60)
        print("Testing complete!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    finally:
        client.close()


if __name__ == '__main__':
    main()

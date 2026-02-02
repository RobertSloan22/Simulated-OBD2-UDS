#!/usr/bin/env python3
"""
Advanced OBD/UDS Test Client - Version 2.0

Comprehensive test suite for Mock OBD-II/UDS system with:
- Multi-frame ISO-TP support
- All OBD-II modes testing
- Advanced UDS service testing
- DTC testing
- Readiness monitor testing
"""

import can
import time
import argparse
from typing import Optional, List
from lib.isotp import ISOTPHandler, ISOTPConfig


class AdvancedOBDClient:
    """Advanced OBD/UDS client with multi-frame support"""

    def __init__(self, can_interface='vcan0', request_id=0x7E0, response_id=0x7E8):
        """
        Initialize OBD Client

        Args:
            can_interface: CAN interface name
            request_id: CAN ID to send requests
            response_id: CAN ID to receive responses
        """
        self.bus = can.Bus(interface='socketcan', channel=can_interface)
        self.request_id = request_id
        self.response_id = response_id

        # ISO-TP handler for multi-frame support
        self.isotp = ISOTPHandler(self.bus, request_id, response_id, ISOTPConfig())

        print(f"Advanced OBD Client initialized")
        print(f"  Sending on CAN ID: 0x{request_id:03X}")
        print(f"  Receiving on CAN ID: 0x{response_id:03X}")
        print(f"  ISO-TP: Multi-frame support enabled\n")

    def send_request(self, payload: bytes, timeout: float = 2.0) -> Optional[bytes]:
        """
        Send request and wait for response (handles multi-frame)

        Args:
            payload: Request payload bytes
            timeout: Response timeout in seconds

        Returns:
            Response payload or None
        """
        # Send using ISO-TP
        success = self.isotp.send(payload)
        if not success:
            print(f"✗ Failed to send request")
            return None

        print(f"→ Sent: {payload.hex()}")

        # Wait for response (may be multi-frame)
        start_time = time.time()
        while time.time() - start_time < timeout:
            msg = self.bus.recv(timeout=0.1)

            if msg and msg.arbitration_id == self.response_id:
                response = self.isotp.receive_frame(msg)

                if response is not None:
                    print(f"← Received: {response[:20].hex()}{'...' if len(response) > 20 else ''} ({len(response)} bytes)")
                    return response

        print("✗ Timeout: No response")
        return None

    # ==================== OBD-II Mode 01 Tests ====================

    def test_monitor_status(self):
        """Test Mode 01 PID 01 - Monitor status and readiness"""
        print("\n[Mode 01 PID 01] Monitor Status")
        response = self.send_request(bytes([0x01, 0x01]))

        if response and len(response) >= 6 and response[0] == 0x41:
            mil_on = bool(response[2] & 0x80)
            dtc_count = response[2] & 0x7F

            print(f"  MIL Status: {'ON' if mil_on else 'OFF'}")
            print(f"  DTC Count: {dtc_count}")

            # Readiness monitors
            monitors = [
                "Misfire", "Fuel System", "Components",
                "Catalyst", "Heated Catalyst", "EVAP",
                "Secondary Air", "O2 Sensor", "O2 Heater", "EGR"
            ]

            print(f"  Readiness Monitors:")
            for i, name in enumerate(monitors[:3]):
                complete = not bool(response[3] & (1 << i))
                print(f"    {name}: {'✓ Complete' if complete else '✗ Incomplete'}")

            return True
        return False

    def test_engine_rpm(self):
        """Test Mode 01 PID 0C - Engine RPM"""
        print("\n[Mode 01 PID 0C] Engine RPM")
        response = self.send_request(bytes([0x01, 0x0C]))

        if response and len(response) >= 4 and response[0] == 0x41:
            rpm = ((response[2] << 8) | response[3]) / 4
            print(f"  ✓ Engine RPM: {rpm:.0f} RPM")
            return True
        return False

    def test_vehicle_speed(self):
        """Test Mode 01 PID 0D - Vehicle speed"""
        print("\n[Mode 01 PID 0D] Vehicle Speed")
        response = self.send_request(bytes([0x01, 0x0D]))

        if response and len(response) >= 3 and response[0] == 0x41:
            speed = response[2]
            print(f"  ✓ Vehicle Speed: {speed} km/h")
            return True
        return False

    def test_coolant_temp(self):
        """Test Mode 01 PID 05 - Coolant temperature"""
        print("\n[Mode 01 PID 05] Coolant Temperature")
        response = self.send_request(bytes([0x01, 0x05]))

        if response and len(response) >= 3 and response[0] == 0x41:
            temp = response[2] - 40
            print(f"  ✓ Coolant Temperature: {temp}°C")
            return True
        return False

    def test_engine_load(self):
        """Test Mode 01 PID 04 - Engine load"""
        print("\n[Mode 01 PID 04] Engine Load")
        response = self.send_request(bytes([0x01, 0x04]))

        if response and len(response) >= 3 and response[0] == 0x41:
            load = (response[2] * 100) / 255
            print(f"  ✓ Engine Load: {load:.1f}%")
            return True
        return False

    def test_maf(self):
        """Test Mode 01 PID 10 - MAF air flow rate"""
        print("\n[Mode 01 PID 10] MAF Air Flow")
        response = self.send_request(bytes([0x01, 0x10]))

        if response and len(response) >= 4 and response[0] == 0x41:
            maf = ((response[2] << 8) | response[3]) / 100
            print(f"  ✓ MAF: {maf:.2f} g/s")
            return True
        return False

    # ==================== OBD-II Mode 03/07/0A Tests ====================

    def test_read_dtcs(self):
        """Test Mode 03 - Read stored DTCs"""
        print("\n[Mode 03] Read Stored DTCs")
        response = self.send_request(bytes([0x03]))

        if response and response[0] == 0x43:
            dtc_count = response[1]
            print(f"  DTC Count: {dtc_count}")

            if dtc_count > 0:
                for i in range(dtc_count):
                    if len(response) >= 4 + i * 2:
                        byte1 = response[2 + i * 2]
                        byte2 = response[3 + i * 2]

                        # Decode DTC
                        type_map = ['P', 'C', 'B', 'U']
                        dtc_type = type_map[(byte1 >> 6) & 0x03]
                        digit1 = (byte1 >> 4) & 0x03
                        digit2 = byte1 & 0x0F
                        digit3 = (byte2 >> 4) & 0x0F
                        digit4 = byte2 & 0x0F

                        dtc_code = f"{dtc_type}{digit1}{digit2:X}{digit3:X}{digit4:X}"
                        print(f"    ✓ DTC: {dtc_code}")
            else:
                print(f"    No DTCs stored")

            return True
        return False

    def test_read_pending_dtcs(self):
        """Test Mode 07 - Read pending DTCs"""
        print("\n[Mode 07] Read Pending DTCs")
        response = self.send_request(bytes([0x07]))

        if response and response[0] == 0x47:
            dtc_count = response[1]
            print(f"  Pending DTC Count: {dtc_count}")
            return True
        return False

    def test_clear_dtcs(self):
        """Test Mode 04 - Clear DTCs"""
        print("\n[Mode 04] Clear DTCs")
        response = self.send_request(bytes([0x04]))

        if response and response[0] == 0x44:
            print(f"  ✓ DTCs cleared successfully")
            return True
        return False

    # ==================== OBD-II Mode 09 Tests ====================

    def test_read_vin(self):
        """Test Mode 09 PID 02 - Read VIN (multi-frame response)"""
        print("\n[Mode 09 PID 02] Read VIN (Multi-frame)")
        response = self.send_request(bytes([0x09, 0x02]))

        if response and response[0] == 0x49:
            # VIN is in bytes after [49 02 01]
            vin_bytes = response[3:20]  # 17 bytes
            vin = vin_bytes.decode('ascii', errors='ignore').rstrip('\x00')
            print(f"  ✓ VIN: {vin} ({len(vin)} characters)")
            return True
        return False

    # ==================== UDS Service Tests ====================

    def test_diagnostic_session(self):
        """Test UDS 0x10 - Diagnostic session control"""
        print("\n[UDS 0x10] Diagnostic Session Control")

        # Extended diagnostic session
        response = self.send_request(bytes([0x10, 0x03]))

        if response and response[0] == 0x50:
            print(f"  ✓ Extended diagnostic session started")
            return True
        return False

    def test_security_access(self):
        """Test UDS 0x27 - Security access (seed/key)"""
        print("\n[UDS 0x27] Security Access")

        # Request seed (level 1)
        print("  Requesting seed...")
        response = self.send_request(bytes([0x27, 0x01]))

        if response and response[0] == 0x67:
            seed = int.from_bytes(response[2:6], 'big')
            print(f"  ✓ Seed received: 0x{seed:08X}")

            # Calculate key (simplified: XOR with constant)
            key = seed ^ 0x12345678
            print(f"  Sending key: 0x{key:08X}")

            # Send key
            key_bytes = key.to_bytes(4, 'big')
            response = self.send_request(bytes([0x27, 0x02]) + key_bytes)

            if response and response[0] == 0x67:
                print(f"  ✓ Security access granted!")
                return True
            else:
                print(f"  ✗ Invalid key")
        return False

    def test_read_did(self):
        """Test UDS 0x22 - Read Data By Identifier"""
        print("\n[UDS 0x22] Read Data By Identifier")

        # Read VIN (DID 0xF190)
        response = self.send_request(bytes([0x22, 0xF1, 0x90]))

        if response and response[0] == 0x62:
            vin_bytes = response[3:20]
            vin = vin_bytes.decode('ascii', errors='ignore').rstrip('\x00')
            print(f"  ✓ VIN (0xF190): {vin}")

        # Read software version (DID 0xF18E)
        response = self.send_request(bytes([0x22, 0xF1, 0x8E]))

        if response and response[0] == 0x62:
            sw_version = response[3:].decode('ascii', errors='ignore').rstrip('\x00')
            print(f"  ✓ Software Version (0xF18E): {sw_version}")
            return True

        return False

    def test_read_dtc_info(self):
        """Test UDS 0x19 - Read DTC information"""
        print("\n[UDS 0x19] Read DTC Information")

        # Sub 0x01: Report number of DTCs
        response = self.send_request(bytes([0x19, 0x01, 0xFF]))

        if response and response[0] == 0x59:
            dtc_count_high = response[4] if len(response) > 4 else 0
            dtc_count_low = response[5] if len(response) > 5 else 0
            dtc_count = (dtc_count_high << 8) | dtc_count_low
            print(f"  ✓ DTC Count: {dtc_count}")
            return True
        return False

    def test_tester_present(self):
        """Test UDS 0x3E - Tester present"""
        print("\n[UDS 0x3E] Tester Present")
        response = self.send_request(bytes([0x3E, 0x00]))

        if response and response[0] == 0x7E:
            print(f"  ✓ Tester present acknowledged")
            return True
        return False

    # ==================== Test Suites ====================

    def run_obd_basic_tests(self):
        """Run basic OBD-II tests"""
        print("\n" + "=" * 60)
        print("OBD-II Basic Test Suite")
        print("=" * 60)

        tests = [
            self.test_monitor_status,
            self.test_engine_rpm,
            self.test_vehicle_speed,
            self.test_coolant_temp,
            self.test_engine_load,
            self.test_maf,
        ]

        passed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  ✗ Test failed: {e}")

        print(f"\n{'=' * 60}")
        print(f"Results: {passed}/{len(tests)} tests passed")
        print("=" * 60)

    def run_dtc_tests(self):
        """Run DTC-related tests"""
        print("\n" + "=" * 60)
        print("DTC Test Suite")
        print("=" * 60)

        tests = [
            self.test_read_dtcs,
            self.test_read_pending_dtcs,
        ]

        passed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  ✗ Test failed: {e}")

        print(f"\n{'=' * 60}")
        print(f"Results: {passed}/{len(tests)} tests passed")
        print("=" * 60)

    def run_multiframe_tests(self):
        """Run multi-frame message tests"""
        print("\n" + "=" * 60)
        print("Multi-Frame Test Suite")
        print("=" * 60)

        tests = [
            self.test_read_vin,
        ]

        passed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  ✗ Test failed: {e}")

        print(f"\n{'=' * 60}")
        print(f"Results: {passed}/{len(tests)} tests passed")
        print("=" * 60)

    def run_uds_tests(self):
        """Run UDS service tests"""
        print("\n" + "=" * 60)
        print("UDS Service Test Suite")
        print("=" * 60)

        tests = [
            self.test_tester_present,
            self.test_diagnostic_session,
            self.test_read_did,
            self.test_read_dtc_info,
            self.test_security_access,
        ]

        passed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  ✗ Test failed: {e}")

        print(f"\n{'=' * 60}")
        print(f"Results: {passed}/{len(tests)} tests passed")
        print("=" * 60)

    def run_all_tests(self):
        """Run all test suites"""
        self.run_obd_basic_tests()
        self.run_dtc_tests()
        self.run_multiframe_tests()
        self.run_uds_tests()

    def close(self):
        """Close the CAN bus connection"""
        self.bus.shutdown()


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Advanced OBD/UDS Test Client')
    parser.add_argument('--interface', default='vcan0', help='CAN interface (default: vcan0)')
    parser.add_argument('--request-id', type=lambda x: int(x, 0), default=0x7E0,
                       help='Request CAN ID (default: 0x7E0)')
    parser.add_argument('--response-id', type=lambda x: int(x, 0), default=0x7E8,
                       help='Response CAN ID (default: 0x7E8)')
    parser.add_argument('--test', choices=['all', 'obd', 'dtc', 'multiframe', 'uds'],
                       default='all', help='Test suite to run')
    args = parser.parse_args()

    print("=" * 60)
    print("Advanced OBD/UDS Test Client v2.0")
    print("=" * 60)
    print()

    client = AdvancedOBDClient(
        can_interface=args.interface,
        request_id=args.request_id,
        response_id=args.response_id
    )

    try:
        if args.test == 'all':
            client.run_all_tests()
        elif args.test == 'obd':
            client.run_obd_basic_tests()
        elif args.test == 'dtc':
            client.run_dtc_tests()
        elif args.test == 'multiframe':
            client.run_multiframe_tests()
        elif args.test == 'uds':
            client.run_uds_tests()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    finally:
        client.close()


if __name__ == '__main__':
    main()

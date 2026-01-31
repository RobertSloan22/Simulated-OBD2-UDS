#!/usr/bin/env python3
"""
Mock OBD/UDS ECU Server
Simulates an ECU responding to OBD-II and UDS requests over CAN
"""

import can
import time
from threading import Thread
import struct

class MockECU:
    def __init__(self, can_interface='vcan0', request_id=0x7E0, response_id=0x7E8):
        """
        Initialize Mock ECU

        Args:
            can_interface: CAN interface name (e.g., 'vcan0')
            request_id: CAN ID to listen for requests (default: 0x7E0)
            response_id: CAN ID to send responses (default: 0x7E8)
        """
        self.bus = can.interface.Bus(channel=can_interface, interface='socketcan')
        self.request_id = request_id
        self.response_id = response_id
        self.running = False

        # Simulated vehicle data
        self.vehicle_data = {
            'engine_rpm': 850,  # RPM
            'vehicle_speed': 0,  # km/h
            'coolant_temp': 90,  # °C
            'throttle_position': 0,  # %
            'fuel_level': 75,  # %
            'engine_load': 25,  # %
        }

        print(f"Mock ECU initialized")
        print(f"  Listening on CAN ID: 0x{request_id:03X}")
        print(f"  Responding on CAN ID: 0x{response_id:03X}")

    def start(self):
        """Start the ECU server"""
        self.running = True
        self.thread = Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print("Mock ECU started")

    def stop(self):
        """Stop the ECU server"""
        self.running = False
        self.bus.shutdown()
        print("Mock ECU stopped")

    def _run(self):
        """Main loop to handle incoming requests"""
        while self.running:
            msg = self.bus.recv(timeout=0.1)
            if msg and msg.arbitration_id == self.request_id:
                self._handle_request(msg)

    def _handle_request(self, msg):
        """Handle incoming CAN request"""
        data = bytes(msg.data)

        # ISO-TP single frame (length in first nibble, PCI type in second)
        if len(data) > 0:
            pci = data[0] & 0xF0
            length = data[0] & 0x0F

            if pci == 0x00:  # Single frame
                payload = data[1:1+length]
                response = self._process_service(payload)

                if response:
                    self._send_response(response)

    def _process_service(self, payload):
        """Process OBD/UDS service request"""
        if len(payload) < 1:
            return None

        service = payload[0]

        # Service 0x01: Show current data (OBD Mode 01)
        if service == 0x01:
            if len(payload) < 2:
                return None

            pid = payload[1]
            return self._handle_mode_01(pid)

        # Service 0x09: Vehicle information (OBD Mode 09)
        elif service == 0x09:
            if len(payload) < 2:
                return None

            pid = payload[1]
            return self._handle_mode_09(pid)

        # Service 0x22: Read Data By Identifier (UDS)
        elif service == 0x22:
            if len(payload) < 3:
                return None

            did = (payload[1] << 8) | payload[2]
            return self._handle_read_did(did)

        # Service 0x10: Diagnostic Session Control (UDS)
        elif service == 0x10:
            if len(payload) < 2:
                return None

            session_type = payload[1]
            return bytes([0x50, session_type, 0x00, 0x32, 0x01, 0xF4])

        # Service 0x3E: Tester Present (UDS)
        elif service == 0x3E:
            return bytes([0x7E, 0x00])

        # Negative response for unsupported service
        else:
            return bytes([0x7F, service, 0x11])  # Service not supported

    def _handle_mode_01(self, pid):
        """Handle OBD Mode 01 PIDs (current data)"""
        # PID 0x00: Supported PIDs
        if pid == 0x00:
            return bytes([0x41, 0x00, 0xBF, 0xBF, 0xA8, 0x91])

        # PID 0x0C: Engine RPM
        elif pid == 0x0C:
            rpm_value = int(self.vehicle_data['engine_rpm'] * 4)
            return bytes([0x41, 0x0C, (rpm_value >> 8) & 0xFF, rpm_value & 0xFF])

        # PID 0x0D: Vehicle speed
        elif pid == 0x0D:
            speed = int(self.vehicle_data['vehicle_speed'])
            return bytes([0x41, 0x0D, speed])

        # PID 0x05: Coolant temperature
        elif pid == 0x05:
            temp = int(self.vehicle_data['coolant_temp'] + 40)
            return bytes([0x41, 0x05, temp])

        # PID 0x11: Throttle position
        elif pid == 0x11:
            throttle = int(self.vehicle_data['throttle_position'] * 255 / 100)
            return bytes([0x41, 0x11, throttle])

        # PID 0x2F: Fuel level
        elif pid == 0x2F:
            fuel = int(self.vehicle_data['fuel_level'] * 255 / 100)
            return bytes([0x41, 0x2F, fuel])

        # PID 0x04: Engine load
        elif pid == 0x04:
            load = int(self.vehicle_data['engine_load'] * 255 / 100)
            return bytes([0x41, 0x04, load])

        # Unsupported PID
        else:
            return bytes([0x7F, 0x01, 0x12])  # Sub-function not supported

    def _handle_mode_09(self, pid):
        """Handle OBD Mode 09 PIDs (vehicle information)"""
        # PID 0x02: VIN
        if pid == 0x02:
            vin = b"1HGBH41JXMN109186"
            # Multi-frame response (simplified - just return first frame)
            return bytes([0x49, 0x02, 0x01] + list(vin[:4]))

        else:
            return bytes([0x7F, 0x09, 0x12])

    def _handle_read_did(self, did):
        """Handle UDS Read Data By Identifier"""
        # DID 0xF190: VIN
        if did == 0xF190:
            vin = b"1HGBH41JXMN109186"
            return bytes([0x62, 0xF1, 0x90] + list(vin[:4]))

        # DID 0xF187: Part number
        elif did == 0xF187:
            part_num = b"12345678"
            return bytes([0x62, 0xF1, 0x87] + list(part_num[:4]))

        else:
            return bytes([0x7F, 0x22, 0x31])  # Request out of range

    def _send_response(self, response_data):
        """Send response on CAN bus"""
        # ISO-TP single frame format
        length = len(response_data)

        if length <= 7:  # Single frame
            pci = 0x00 | length
            data = bytes([pci]) + response_data + bytes([0x00] * (7 - length))

            msg = can.Message(
                arbitration_id=self.response_id,
                data=data,
                is_extended_id=False
            )

            self.bus.send(msg)
            print(f"Sent response: {data.hex()}")

    def update_vehicle_data(self, **kwargs):
        """Update simulated vehicle data"""
        self.vehicle_data.update(kwargs)


def main():
    """Main function to run the mock ECU"""
    print("=" * 60)
    print("Mock OBD/UDS ECU Server")
    print("=" * 60)

    # Create and start mock ECU
    ecu = MockECU(can_interface='vcan0')
    ecu.start()

    print("\nSimulating vehicle data changes...")
    print("Press Ctrl+C to stop\n")

    try:
        # Simulate vehicle data changes
        counter = 0
        while True:
            time.sleep(2)
            counter += 1

            # Simulate varying RPM
            rpm = 850 + (counter % 10) * 100
            speed = min(counter % 120, 100)
            throttle = (counter % 10) * 10

            ecu.update_vehicle_data(
                engine_rpm=rpm,
                vehicle_speed=speed,
                throttle_position=throttle
            )

            print(f"Vehicle data: RPM={rpm}, Speed={speed} km/h, Throttle={throttle}%")

    except KeyboardInterrupt:
        print("\n\nShutting down...")
        ecu.stop()


if __name__ == '__main__':
    main()

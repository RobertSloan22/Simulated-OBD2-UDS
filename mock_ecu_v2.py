#!/usr/bin/env python3
"""
Advanced Mock OBD-II/UDS ECU Server - Version 2.0

Production-grade ECU simulation with:
- Multi-frame ISO-TP support
- Complete OBD-II (all 10 modes)
- Advanced UDS services
- Realistic vehicle simulation
- DTC management with freeze frames
- Multi-ECU support
- HTTP Control API
"""

import can
import time
import threading
from typing import Optional
import argparse

# Import library modules
from lib.isotp import ISOTPHandler, ISOTPConfig
from lib.vehicle_simulator import VehicleSimulator, EngineState
from lib.dtc_manager import DTCManager
from lib.obd_services import OBDServiceHandler
from lib.uds_services import UDSServiceHandler
from lib.multi_ecu import MultiECUCoordinator, ENGINE_ECU, TRANSMISSION_ECU, ABS_ECU
from lib.config import VehicleConfig
from control_api import ControlAPI


class MockECU:
    """Advanced Mock ECU with full OBD-II/UDS support"""

    def __init__(self, can_interface='vcan0', request_id=0x7E0, response_id=0x7E8,
                 config_file: Optional[str] = None):
        """
        Initialize Mock ECU

        Args:
            can_interface: CAN interface name
            request_id: CAN ID to listen for requests
            response_id: CAN ID to send responses
            config_file: Vehicle configuration file
        """
        # Load configuration
        self.config = VehicleConfig(config_file)

        # CAN bus
        self.bus = can.Bus(interface='socketcan', channel=can_interface)
        self.request_id = request_id
        self.response_id = response_id

        # ISO-TP handler for multi-frame support
        self.isotp = ISOTPHandler(self.bus, response_id, request_id, ISOTPConfig())

        # Vehicle simulator
        self.vehicle = VehicleSimulator(self.config.get_all())

        # DTC manager
        self.dtc_manager = DTCManager(self.config.get_all())

        # Service handlers
        self.obd_handler = OBDServiceHandler(self.vehicle, self.dtc_manager, self.config.get_all())
        self.uds_handler = UDSServiceHandler(self.vehicle, self.dtc_manager, self.config.get_all())

        # State
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.simulation_thread: Optional[threading.Thread] = None

        print(f"Mock ECU initialized")
        print(f"  Vehicle: {self.config.get_make()} {self.config.get_model()} {self.config.get_year()}")
        print(f"  VIN: {self.config.get_vin()}")
        print(f"  CAN: 0x{request_id:03X} → 0x{response_id:03X}")
        print(f"  ISO-TP: Multi-frame support enabled")

    def start(self):
        """Start the ECU server"""
        self.running = True

        # Start CAN message handler thread
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

        # Start vehicle simulation thread
        self.simulation_thread = threading.Thread(target=self._simulation_loop)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()

        # Start engine
        self.vehicle.start_engine()

        print("Mock ECU started")

    def stop(self):
        """Stop the ECU server"""
        self.running = False
        self.vehicle.stop_engine()
        self.bus.shutdown()
        print("Mock ECU stopped")

    def _run(self):
        """Main loop to handle incoming CAN requests"""
        while self.running:
            msg = self.bus.recv(timeout=0.1)

            if msg and msg.arbitration_id == self.request_id:
                self._handle_request(msg)

    def _simulation_loop(self):
        """Background loop for vehicle simulation updates"""
        last_update = time.time()

        while self.running:
            current_time = time.time()
            dt = current_time - last_update

            # Update vehicle simulation
            if dt >= 0.1:  # 10 Hz update rate
                self.vehicle.update(dt)
                last_update = current_time

            time.sleep(0.05)

    def _handle_request(self, msg: can.Message):
        """Handle incoming CAN request"""
        # Use ISO-TP to receive (handles multi-frame)
        payload = self.isotp.receive_frame(msg)

        if payload is None:
            # Waiting for more frames in multi-frame message
            return

        # Process service request
        try:
            response = self._process_service(payload)

            if response:
                self._send_response(response)

        except Exception as e:
            print(f"[ECU] Error processing request: {e}")

    def _process_service(self, payload: bytes) -> Optional[bytes]:
        """
        Route service request to appropriate handler

        Args:
            payload: Service request bytes

        Returns:
            Response bytes or None
        """
        if len(payload) < 1:
            return None

        service = payload[0]

        # OBD-II services: 0x01 - 0x0A
        if 0x01 <= service <= 0x0A:
            return self.obd_handler.process(payload)

        # UDS services: 0x10 - 0x3E, 0x85, etc.
        elif service >= 0x10:
            return self.uds_handler.process(payload)

        else:
            # Unknown service
            return bytes([0x7F, service, 0x11])  # Service not supported

    def _send_response(self, response_data: bytes):
        """
        Send response using ISO-TP (handles multi-frame)

        Args:
            response_data: Response payload bytes
        """
        try:
            success = self.isotp.sender.send(response_data)
            if success:
                print(f"[ECU] Sent response: {response_data[:20].hex()}{'...' if len(response_data) > 20 else ''}")
        except Exception as e:
            print(f"[ECU] Error sending response: {e}")


class MockOBDSystem:
    """Complete Mock OBD-II system with multiple ECUs and Control API"""

    def __init__(self, can_interface='vcan0', enable_api=True, api_port=5000):
        """
        Initialize Mock OBD-II system

        Args:
            can_interface: CAN interface name
            enable_api: Enable HTTP Control API
            api_port: API server port
        """
        self.can_interface = can_interface
        self.enable_api = enable_api

        # Multi-ECU coordinator
        self.coordinator = MultiECUCoordinator()

        # Create ECUs
        self.engine_ecu = MockECU(
            can_interface=can_interface,
            request_id=ENGINE_ECU.request_id,
            response_id=ENGINE_ECU.response_id,
            config_file='default.json'
        )

        self.transmission_ecu = MockECU(
            can_interface=can_interface,
            request_id=TRANSMISSION_ECU.request_id,
            response_id=TRANSMISSION_ECU.response_id,
            config_file='default.json'
        )

        self.abs_ecu = MockECU(
            can_interface=can_interface,
            request_id=ABS_ECU.request_id,
            response_id=ABS_ECU.response_id,
            config_file='default.json'
        )

        # Register ECUs
        self.coordinator.register_ecu(ENGINE_ECU, self.engine_ecu)
        self.coordinator.register_ecu(TRANSMISSION_ECU, self.transmission_ecu)
        self.coordinator.register_ecu(ABS_ECU, self.abs_ecu)

        # Control API
        self.api: Optional[ControlAPI] = None
        if enable_api:
            self.api = ControlAPI(self.coordinator, port=api_port)

        print("\n" + "=" * 60)
        print("Mock OBD-II System v2.0 - Multi-ECU with Advanced Features")
        print("=" * 60)

    def start(self):
        """Start all ECUs and API"""
        print("\nStarting ECUs...")
        self.engine_ecu.start()
        self.transmission_ecu.start()
        self.abs_ecu.start()

        if self.api:
            print("\nStarting Control API...")
            self.api.start()
            print(f"\n{'=' * 60}")
            print("Control API Endpoints:")
            print("  GET  /api/health                - Health check")
            print("  GET  /api/ecu/info              - ECU information")
            print("  POST /api/dtc/inject            - Inject DTC")
            print("  POST /api/dtc/clear             - Clear DTCs")
            print("  GET  /api/dtc/list              - List DTCs")
            print("  GET  /api/vehicle/state         - Get vehicle state")
            print("  POST /api/vehicle/set           - Set vehicle state")
            print("  POST /api/vehicle/engine/start  - Start engine")
            print("  POST /api/vehicle/engine/stop   - Stop engine")
            print("  GET  /api/readiness/status      - Readiness monitors")
            print("  POST /api/readiness/reset       - Reset monitors")
            print(f"{'=' * 60}\n")

        print("System ready. Press Ctrl+C to stop.\n")

    def stop(self):
        """Stop all ECUs and API"""
        print("\nShutting down...")
        self.engine_ecu.stop()
        self.transmission_ecu.stop()
        self.abs_ecu.stop()

        if self.api:
            self.api.stop()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Mock OBD-II/UDS ECU System')
    parser.add_argument('--interface', default='vcan0', help='CAN interface (default: vcan0)')
    parser.add_argument('--no-api', action='store_true', help='Disable Control API')
    parser.add_argument('--api-port', type=int, default=5000, help='API port (default: 5000)')
    parser.add_argument('--single-ecu', action='store_true', help='Run single ECU only (no multi-ECU)')
    args = parser.parse_args()

    try:
        if args.single_ecu:
            # Single ECU mode (original behavior)
            print("Running in single ECU mode...")
            ecu = MockECU(can_interface=args.interface)
            ecu.start()

            # Simple simulation loop
            while True:
                time.sleep(1)

        else:
            # Multi-ECU system with API
            system = MockOBDSystem(
                can_interface=args.interface,
                enable_api=not args.no_api,
                api_port=args.api_port
            )
            system.start()

            # Keep running
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if not args.single_ecu:
            system.stop()
        else:
            ecu.stop()


if __name__ == '__main__':
    main()

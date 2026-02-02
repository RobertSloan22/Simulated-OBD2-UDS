#!/usr/bin/env python3
"""
Control API for Mock OBD-II System

HTTP REST API for runtime control and fault injection.
Allows dynamic DTC injection, vehicle state control, and system monitoring.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
from typing import Optional, Dict, Any
import time
import os


class ControlAPI:
    """HTTP API for controlling the mock OBD system"""

    def __init__(self, multi_ecu_coordinator, host: str = '0.0.0.0', port: int = 5000):
        """
        Initialize Control API

        Args:
            multi_ecu_coordinator: MultiECUCoordinator instance
            host: Host to bind to
            port: Port to listen on
        """
        self.coordinator = multi_ecu_coordinator
        self.host = host
        self.port = port

        # Create Flask app
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for browser access

        # Register routes
        self._register_routes()

        # API server thread
        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    def _register_routes(self):
        """Register API endpoints"""

        # Dashboard UI
        @self.app.route('/', methods=['GET'])
        @self.app.route('/dashboard', methods=['GET'])
        def dashboard():
            """Serve the web dashboard UI"""
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            return send_from_directory(static_dir, 'dashboard.html')

        @self.app.route('/api/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'ok', 'timestamp': time.time()})

        # ECU Information
        @self.app.route('/api/ecu/info', methods=['GET'])
        def ecu_info():
            """Get information about all ECUs"""
            try:
                summary = self.coordinator.get_status_summary()
                return jsonify({'status': 'ok', 'ecus': summary})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/ecu/list', methods=['GET'])
        def ecu_list():
            """List all registered ECUs"""
            try:
                identities = self.coordinator.list_ecus()
                ecu_list = [
                    {
                        'name': identity.name,
                        'type': identity.ecu_type.value,
                        'request_id': f"0x{identity.request_id:03X}",
                        'response_id': f"0x{identity.response_id:03X}"
                    }
                    for identity in identities
                ]
                return jsonify({'status': 'ok', 'ecus': ecu_list})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # DTC Management
        @self.app.route('/api/dtc/inject', methods=['POST'])
        def inject_dtc():
            """Inject a DTC into specified ECU"""
            try:
                data = request.get_json()
                ecu_name = data.get('ecu', 'Engine Control Unit')
                code = data.get('code')
                freeze_frame = data.get('freeze_frame', True)

                if not code:
                    return jsonify({'status': 'error', 'message': 'Missing DTC code'}), 400

                ecu = self.coordinator.get_ecu_by_name(ecu_name)
                if not ecu:
                    return jsonify({'status': 'error', 'message': f'ECU not found: {ecu_name}'}), 404

                # Inject DTC
                sensors = ecu.vehicle.get_sensor_data()
                success = ecu.dtc_manager.inject_dtc(code, sensors, capture_freeze_frame=freeze_frame)

                if success:
                    return jsonify({
                        'status': 'ok',
                        'message': f'DTC {code} injected into {ecu_name}',
                        'freeze_frame_captured': freeze_frame
                    })
                else:
                    return jsonify({'status': 'error', 'message': f'Failed to inject DTC {code}'}), 400

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/dtc/clear', methods=['POST'])
        def clear_dtc():
            """Clear DTCs from specified ECU or all ECUs"""
            try:
                data = request.get_json() or {}
                ecu_name = data.get('ecu')
                code = data.get('code')  # Specific code or "all"

                if ecu_name:
                    # Clear from specific ECU
                    ecu = self.coordinator.get_ecu_by_name(ecu_name)
                    if not ecu:
                        return jsonify({'status': 'error', 'message': f'ECU not found: {ecu_name}'}), 404

                    cleared = ecu.dtc_manager.clear_dtcs()
                    return jsonify({'status': 'ok', 'ecu': ecu_name, 'cleared': cleared})
                else:
                    # Clear from all ECUs
                    self.coordinator.clear_all_dtcs()
                    return jsonify({'status': 'ok', 'message': 'All DTCs cleared from all ECUs'})

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/dtc/list', methods=['GET'])
        def list_dtcs():
            """List DTCs from specified ECU or all ECUs"""
            try:
                ecu_name = request.args.get('ecu')

                if ecu_name:
                    # List from specific ECU
                    ecu = self.coordinator.get_ecu_by_name(ecu_name)
                    if not ecu:
                        return jsonify({'status': 'error', 'message': f'ECU not found: {ecu_name}'}), 404

                    dtcs = ecu.dtc_manager.get_all_active_dtcs()
                    dtc_list = [
                        {
                            'code': dtc.code,
                            'description': dtc.description,
                            'state': dtc.state.value,
                            'count': dtc.detection_count,
                            'mil_illuminate': dtc.mil_illuminate
                        }
                        for dtc in dtcs
                    ]
                    return jsonify({'status': 'ok', 'ecu': ecu_name, 'dtcs': dtc_list})
                else:
                    # List from all ECUs
                    all_dtcs = {}
                    for identity in self.coordinator.list_ecus():
                        ecu = self.coordinator.get_ecu_by_name(identity.name)
                        if ecu and hasattr(ecu, 'dtc_manager'):
                            dtcs = ecu.dtc_manager.get_all_active_dtcs()
                            all_dtcs[identity.name] = [
                                {
                                    'code': dtc.code,
                                    'description': dtc.description,
                                    'state': dtc.state.value
                                }
                                for dtc in dtcs
                            ]
                    return jsonify({'status': 'ok', 'dtcs_by_ecu': all_dtcs})

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # Vehicle State Control
        @self.app.route('/api/vehicle/state', methods=['GET'])
        def get_vehicle_state():
            """Get current vehicle state"""
            try:
                # Get engine ECU (primary)
                from lib.multi_ecu import ECUType
                ecu = self.coordinator.get_ecu_by_type(ECUType.ENGINE)
                if not ecu:
                    return jsonify({'status': 'error', 'message': 'Engine ECU not found'}), 404

                sensors = ecu.vehicle.get_sensor_data()
                state = {
                    'rpm': sensors.rpm,
                    'speed': sensors.vehicle_speed,
                    'coolant_temp': sensors.coolant_temp,
                    'engine_load': sensors.engine_load,
                    'throttle_position': sensors.throttle_position,
                    'fuel_level': sensors.fuel_level,
                    'maf': sensors.maf,
                    'battery_voltage': sensors.battery_voltage,
                    'mil_status': sensors.mil_status,
                    'engine_runtime': sensors.engine_runtime,
                    'distance_traveled': sensors.distance_traveled
                }
                return jsonify({'status': 'ok', 'state': state})

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/vehicle/set', methods=['POST'])
        def set_vehicle_state():
            """Set vehicle state parameters"""
            try:
                data = request.get_json()

                # Get engine ECU
                from lib.multi_ecu import ECUType
                ecu = self.coordinator.get_ecu_by_type(ECUType.ENGINE)
                if not ecu:
                    return jsonify({'status': 'error', 'message': 'Engine ECU not found'}), 404

                # Set parameters
                if 'rpm' in data:
                    ecu.vehicle.set_rpm(float(data['rpm']))
                if 'speed' in data:
                    ecu.vehicle.set_speed(float(data['speed']))
                if 'throttle' in data:
                    ecu.vehicle.set_throttle(float(data['throttle']))

                return jsonify({
                    'status': 'ok',
                    'message': 'Vehicle state updated',
                    'updated': list(data.keys())
                })

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/vehicle/engine/<action>', methods=['POST'])
        def engine_control(action):
            """Control engine (start/stop)"""
            try:
                from lib.multi_ecu import ECUType
                ecu = self.coordinator.get_ecu_by_type(ECUType.ENGINE)
                if not ecu:
                    return jsonify({'status': 'error', 'message': 'Engine ECU not found'}), 404

                if action == 'start':
                    success = ecu.vehicle.start_engine()
                    if success:
                        return jsonify({'status': 'ok', 'message': 'Engine started'})
                    else:
                        return jsonify({'status': 'error', 'message': 'Cannot start engine - check ignition state'}), 400
                elif action == 'stop':
                    ecu.vehicle.stop_engine()
                    return jsonify({'status': 'ok', 'message': 'Engine stopped (KOEO mode)'})
                else:
                    return jsonify({'status': 'error', 'message': f'Unknown action: {action}'}), 400

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/vehicle/ignition/<state>', methods=['POST'])
        def ignition_control(state):
            """Control ignition state (off/acc/on/start)"""
            try:
                from lib.multi_ecu import ECUType
                from lib.vehicle_simulator import IgnitionState

                ecu = self.coordinator.get_ecu_by_type(ECUType.ENGINE)
                if not ecu:
                    return jsonify({'status': 'error', 'message': 'Engine ECU not found'}), 404

                # Map string to IgnitionState
                state_map = {
                    'off': IgnitionState.OFF,
                    'accessory': IgnitionState.ACCESSORY,
                    'acc': IgnitionState.ACCESSORY,
                    'on': IgnitionState.ON,
                    'start': IgnitionState.START
                }

                if state.lower() not in state_map:
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid state: {state}. Use: off, acc, on, start'
                    }), 400

                ignition_state = state_map[state.lower()]
                ecu.vehicle.set_ignition(ignition_state)

                return jsonify({
                    'status': 'ok',
                    'ignition_state': ignition_state.value,
                    'engine_state': ecu.vehicle.engine_state.value
                })

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/vehicle/koeo', methods=['POST'])
        def koeo_mode():
            """Set vehicle to Key On Engine Off (KOEO) mode for diagnostics"""
            try:
                from lib.multi_ecu import ECUType
                ecu = self.coordinator.get_ecu_by_type(ECUType.ENGINE)
                if not ecu:
                    return jsonify({'status': 'error', 'message': 'Engine ECU not found'}), 404

                ecu.vehicle.key_on_engine_off()

                return jsonify({
                    'status': 'ok',
                    'message': 'KOEO mode activated',
                    'ignition_state': 'on',
                    'engine_state': 'off',
                    'diagnostics_available': True
                })

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # Readiness Monitors
        @self.app.route('/api/readiness/status', methods=['GET'])
        def readiness_status():
            """Get readiness monitor status"""
            try:
                from lib.multi_ecu import ECUType
                ecu = self.coordinator.get_ecu_by_type(ECUType.ENGINE)
                if not ecu:
                    return jsonify({'status': 'error', 'message': 'Engine ECU not found'}), 404

                drive_cycle = ecu.vehicle.get_drive_cycle()
                status = {
                    'misfire_complete': drive_cycle.misfire_monitor_complete,
                    'fuel_system_complete': drive_cycle.fuel_system_monitor_complete,
                    'component_complete': drive_cycle.component_monitor_complete,
                    'catalyst_complete': drive_cycle.catalyst_monitor_complete,
                    'evap_complete': drive_cycle.evap_system_monitor_complete,
                    'oxygen_sensor_complete': drive_cycle.oxygen_sensor_monitor_complete,
                    'egr_complete': drive_cycle.egr_system_monitor_complete
                }
                return jsonify({'status': 'ok', 'readiness': status})

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/readiness/reset', methods=['POST'])
        def readiness_reset():
            """Reset readiness monitors"""
            try:
                data = request.get_json() or {}
                ecu_name = data.get('ecu')

                if ecu_name:
                    ecu = self.coordinator.get_ecu_by_name(ecu_name)
                    if not ecu:
                        return jsonify({'status': 'error', 'message': f'ECU not found: {ecu_name}'}), 404
                    ecu.vehicle.reset_drive_cycle()
                    return jsonify({'status': 'ok', 'ecu': ecu_name, 'monitors_reset': True})
                else:
                    # Reset all ECUs
                    for identity in self.coordinator.list_ecus():
                        ecu = self.coordinator.get_ecu_by_name(identity.name)
                        if ecu:
                            ecu.vehicle.reset_drive_cycle()
                    return jsonify({'status': 'ok', 'message': 'All readiness monitors reset'})

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # Actuator Control
        @self.app.route('/api/actuator/control', methods=['POST'])
        def actuator_control():
            """Control an actuator"""
            try:
                data = request.get_json()
                ecu_name = data.get('ecu', 'Engine Control Unit')
                did = data.get('did')
                state = data.get('state')

                if not did or state is None:
                    return jsonify({'status': 'error', 'message': 'Missing DID or state'}), 400

                ecu = self.coordinator.get_ecu_by_name(ecu_name)
                if not ecu:
                    return jsonify({'status': 'error', 'message': f'ECU not found: {ecu_name}'}), 404

                # Record actuator state
                if not hasattr(ecu, 'actuator_states'):
                    ecu.actuator_states = {}

                ecu.actuator_states[did] = state

                return jsonify({
                    'status': 'ok',
                    'ecu': ecu_name,
                    'actuator': did,
                    'state': state
                })

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

    def start(self):
        """Start API server in background thread"""
        if self.running:
            print("[API] Already running")
            return

        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        print(f"[API] Control API started on http://{self.host}:{self.port}")
        print(f"[API] Web Dashboard available at http://{self.host}:{self.port}/")
        print(f"[API] API health check at http://{self.host}:{self.port}/api/health")

    def _run_server(self):
        """Run Flask server"""
        self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

    def stop(self):
        """Stop API server"""
        self.running = False
        print("[API] Control API stopped")


def main():
    """Standalone API server for testing"""
    print("Control API Test Server")
    print("This requires a running MockECU system")

    # Create mock coordinator for testing
    from lib.multi_ecu import MultiECUCoordinator
    coordinator = MultiECUCoordinator()

    api = ControlAPI(coordinator)
    api.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        api.stop()


if __name__ == '__main__':
    main()

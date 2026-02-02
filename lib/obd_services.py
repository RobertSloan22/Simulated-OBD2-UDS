"""
Complete OBD-II Service Handler

Implements all 10 OBD-II modes (01-0A) with comprehensive PID support.
"""

from typing import Optional, List
from lib.vehicle_simulator import VehicleSimulator
from lib.dtc_manager import DTCManager


class OBDServiceHandler:
    """Handles all OBD-II service requests (Modes 01-0A)"""

    def __init__(self, vehicle: VehicleSimulator, dtc_manager: DTCManager, config: Optional[dict] = None):
        """
        Initialize OBD service handler

        Args:
            vehicle: Vehicle simulator instance
            dtc_manager: DTC manager instance
            config: Configuration dictionary
        """
        self.vehicle = vehicle
        self.dtc_manager = dtc_manager
        self.config = config or {}

        # VIN from config or default
        self.vin = self.config.get('vin', '1HGBH41JXMN109186')
        self.calibration_id = self.config.get('calibration_id', 'CALIB12345678')
        self.ecu_name = self.config.get('ecu_name', 'ENGINE-ECU')

    def process(self, request: bytes) -> Optional[bytes]:
        """
        Process OBD-II service request

        Args:
            request: Service request bytes

        Returns:
            Response bytes or None for invalid request
        """
        if len(request) < 2:
            return None

        mode = request[0]

        if mode == 0x01:
            return self._mode_01_current_data(request)
        elif mode == 0x02:
            return self._mode_02_freeze_frame(request)
        elif mode == 0x03:
            return self._mode_03_read_dtcs(request)
        elif mode == 0x04:
            return self._mode_04_clear_dtcs(request)
        elif mode == 0x06:
            return self._mode_06_test_results(request)
        elif mode == 0x07:
            return self._mode_07_pending_dtcs(request)
        elif mode == 0x08:
            return self._mode_08_control_systems(request)
        elif mode == 0x09:
            return self._mode_09_vehicle_info(request)
        elif mode == 0x0A:
            return self._mode_0A_permanent_dtcs(request)
        else:
            # Negative response: service not supported
            return bytes([0x7F, mode, 0x11])

    # Mode 01: Show Current Data
    def _mode_01_current_data(self, request: bytes) -> bytes:
        """Mode 01 - Current data PIDs"""
        if len(request) < 2:
            return bytes([0x7F, 0x01, 0x12])  # Sub-function not supported

        pid = request[1]
        sensors = self.vehicle.get_sensor_data()
        drive_cycle = self.vehicle.get_drive_cycle()

        # PID 0x00: Supported PIDs [01-20]
        if pid == 0x00:
            # Bitmask of supported PIDs 01-20
            return bytes([0x41, 0x00, 0xBF, 0xBF, 0xA8, 0x91])

        # PID 0x01: Monitor status (CRITICAL - MIL, DTC count, readiness)
        elif pid == 0x01:
            dtc_count = min(127, self.dtc_manager.get_dtc_count())
            mil_on = 0x80 if self.dtc_manager.is_mil_on() else 0x00
            byte_a = mil_on | dtc_count

            # Readiness monitors (simplified)
            # Byte B: Test availability/completion
            # Bits: 0=Misfire, 1=Fuel, 2=Components
            byte_b = 0x07  # All tests available
            if drive_cycle.misfire_monitor_complete:
                byte_b &= ~0x01
            if drive_cycle.fuel_system_monitor_complete:
                byte_b &= ~0x02
            if drive_cycle.component_monitor_complete:
                byte_b &= ~0x04

            # Byte C: Catalyst, Heated catalyst, EVAP, Secondary air
            byte_c = 0x0F
            if drive_cycle.catalyst_monitor_complete:
                byte_c &= ~0x01
            if drive_cycle.heated_catalyst_monitor_complete:
                byte_c &= ~0x02
            if drive_cycle.evap_system_monitor_complete:
                byte_c &= ~0x04

            # Byte D: O2 sensor, O2 heater, EGR
            byte_d = 0x07
            if drive_cycle.oxygen_sensor_monitor_complete:
                byte_d &= ~0x01
            if drive_cycle.oxygen_sensor_heater_complete:
                byte_d &= ~0x02
            if drive_cycle.egr_system_monitor_complete:
                byte_d &= ~0x04

            return bytes([0x41, 0x01, byte_a, byte_b, byte_c, byte_d])

        # PID 0x03: Fuel system status
        elif pid == 0x03:
            # 0x02 = Closed loop, using oxygen sensor
            return bytes([0x41, 0x03, 0x02, 0x00])

        # PID 0x04: Engine load
        elif pid == 0x04:
            load = int(sensors.engine_load * 255 / 100)
            return bytes([0x41, 0x04, load])

        # PID 0x05: Coolant temperature
        elif pid == 0x05:
            temp = int(sensors.coolant_temp + 40)
            return bytes([0x41, 0x05, temp])

        # PID 0x06: Short term fuel trim (Bank 1)
        elif pid == 0x06:
            trim = int((sensors.short_term_fuel_trim + 100) * 128 / 100)
            return bytes([0x41, 0x06, max(0, min(255, trim))])

        # PID 0x07: Long term fuel trim (Bank 1)
        elif pid == 0x07:
            trim = int((sensors.long_term_fuel_trim + 100) * 128 / 100)
            return bytes([0x41, 0x07, max(0, min(255, trim))])

        # PID 0x0B: Intake manifold pressure
        elif pid == 0x0B:
            # Simplified: based on load
            pressure = int(30 + sensors.engine_load * 0.7)
            return bytes([0x41, 0x0B, pressure])

        # PID 0x0C: Engine RPM
        elif pid == 0x0C:
            rpm_value = int(sensors.rpm * 4)
            return bytes([0x41, 0x0C, (rpm_value >> 8) & 0xFF, rpm_value & 0xFF])

        # PID 0x0D: Vehicle speed
        elif pid == 0x0D:
            speed = int(sensors.vehicle_speed)
            return bytes([0x41, 0x0D, speed])

        # PID 0x0E: Timing advance
        elif pid == 0x0E:
            advance = int((sensors.timing_advance + 64) * 2)
            return bytes([0x41, 0x0E, max(0, min(255, advance))])

        # PID 0x0F: Intake air temperature
        elif pid == 0x0F:
            temp = int(sensors.intake_air_temp + 40)
            return bytes([0x41, 0x0F, temp])

        # PID 0x10: MAF air flow rate
        elif pid == 0x10:
            maf_value = int(sensors.maf * 100)
            return bytes([0x41, 0x10, (maf_value >> 8) & 0xFF, maf_value & 0xFF])

        # PID 0x11: Throttle position
        elif pid == 0x11:
            throttle = int(sensors.throttle_position * 255 / 100)
            return bytes([0x41, 0x11, throttle])

        # PID 0x1C: OBD standard
        elif pid == 0x1C:
            # 0x07 = OBD-II as defined by CARB
            return bytes([0x41, 0x1C, 0x07])

        # PID 0x1F: Runtime since engine start
        elif pid == 0x1F:
            runtime = int(sensors.engine_runtime)
            return bytes([0x41, 0x1F, (runtime >> 8) & 0xFF, runtime & 0xFF])

        # PID 0x20: Supported PIDs [21-40]
        elif pid == 0x20:
            return bytes([0x41, 0x20, 0xA0, 0x05, 0xB0, 0x11])

        # PID 0x21: Distance traveled with MIL on
        elif pid == 0x21:
            dist = int(sensors.distance_with_mil)
            return bytes([0x41, 0x21, (dist >> 8) & 0xFF, dist & 0xFF])

        # PID 0x23: Fuel rail pressure
        elif pid == 0x23:
            pressure_value = int(sensors.fuel_pressure * 10)
            return bytes([0x41, 0x23, (pressure_value >> 8) & 0xFF, pressure_value & 0xFF])

        # PID 0x2F: Fuel level input
        elif pid == 0x2F:
            fuel = int(sensors.fuel_level * 255 / 100)
            return bytes([0x41, 0x2F, fuel])

        # PID 0x30: Number of warmups since DTCs cleared
        elif pid == 0x30:
            return bytes([0x41, 0x30, sensors.warmups_since_clear])

        # PID 0x31: Distance traveled since DTCs cleared
        elif pid == 0x31:
            dist = int(sensors.distance_since_clear)
            return bytes([0x41, 0x31, (dist >> 8) & 0xFF, dist & 0xFF])

        # PID 0x33: Barometric pressure
        elif pid == 0x33:
            pressure = int(sensors.barometric_pressure)
            return bytes([0x41, 0x33, pressure])

        # PID 0x40: Supported PIDs [41-60]
        elif pid == 0x40:
            return bytes([0x41, 0x40, 0x40, 0x00, 0x00, 0x00])

        # PID 0x42: Control module voltage
        elif pid == 0x42:
            voltage = int(sensors.battery_voltage * 1000)
            return bytes([0x41, 0x42, (voltage >> 8) & 0xFF, voltage & 0xFF])

        # PID 0x5C: Engine oil temperature
        elif pid == 0x5C:
            # Approximate from coolant temp
            oil_temp = int(sensors.coolant_temp + 10 + 40)
            return bytes([0x41, 0x5C, oil_temp])

        else:
            # Unsupported PID
            return bytes([0x7F, 0x01, 0x12])

    # Mode 02: Freeze Frame Data
    def _mode_02_freeze_frame(self, request: bytes) -> bytes:
        """Mode 02 - Freeze frame data"""
        if len(request) < 3:
            return bytes([0x7F, 0x02, 0x12])

        pid = request[1]
        frame_num = request[2]

        # Get first confirmed DTC with freeze frame
        confirmed_dtcs = self.dtc_manager.get_confirmed_dtcs()
        if not confirmed_dtcs or frame_num > 0:
            return bytes([0x7F, 0x02, 0x12])

        dtc = confirmed_dtcs[0]
        freeze_frame = dtc.freeze_frame

        if not freeze_frame:
            return bytes([0x7F, 0x02, 0x12])

        # Return requested PID from freeze frame
        if pid == 0x0C:  # RPM
            rpm_value = int(freeze_frame.rpm * 4)
            return bytes([0x42, 0x0C, frame_num, (rpm_value >> 8) & 0xFF, rpm_value & 0xFF])
        elif pid == 0x0D:  # Speed
            return bytes([0x42, 0x0D, frame_num, int(freeze_frame.speed)])
        elif pid == 0x05:  # Coolant temp
            return bytes([0x42, 0x05, frame_num, int(freeze_frame.coolant_temp + 40)])
        elif pid == 0x04:  # Load
            return bytes([0x42, 0x04, frame_num, int(freeze_frame.engine_load * 255 / 100)])
        else:
            return bytes([0x7F, 0x02, 0x12])

    # Mode 03: Read Stored DTCs
    def _mode_03_read_dtcs(self, request: bytes) -> bytes:
        """Mode 03 - Read confirmed/stored DTCs"""
        confirmed_dtcs = self.dtc_manager.get_confirmed_dtcs()
        permanent_dtcs = self.dtc_manager.get_permanent_dtcs()
        all_dtcs = confirmed_dtcs + permanent_dtcs

        if not all_dtcs:
            return bytes([0x43, 0x00])  # No DTCs

        response = bytearray([0x43, len(all_dtcs)])
        for dtc in all_dtcs:
            response.extend(dtc.to_bytes())

        return bytes(response)

    # Mode 04: Clear DTCs
    def _mode_04_clear_dtcs(self, request: bytes) -> bytes:
        """Mode 04 - Clear diagnostic information"""
        # Clear DTCs and reset monitors
        self.dtc_manager.clear_dtcs(clear_permanent=False)
        self.vehicle.reset_drive_cycle()

        # Reset distance/warmup counters
        sensors = self.vehicle.get_sensor_data()
        sensors.distance_since_clear = 0.0
        sensors.distance_with_mil = 0.0
        sensors.warmups_since_clear = 0

        return bytes([0x44])  # Positive response

    # Mode 06: Test Results
    def _mode_06_test_results(self, request: bytes) -> bytes:
        """Mode 06 - On-board test results for O2 sensors"""
        # Simplified: Return O2 sensor test result
        # TID 0x01: O2 Sensor Monitor Bank 1 Sensor 1
        # Format: [Mode+0x40][TID][TestID][Min][Max][Value][Limit]
        return bytes([0x46, 0x01, 0x01, 0x00, 0x0A, 0x00, 0xFF, 0x00, 0x45, 0x00, 0xFA])

    # Mode 07: Pending DTCs
    def _mode_07_pending_dtcs(self, request: bytes) -> bytes:
        """Mode 07 - Read pending DTCs"""
        pending_dtcs = self.dtc_manager.get_pending_dtcs()

        if not pending_dtcs:
            return bytes([0x47, 0x00])  # No pending DTCs

        response = bytearray([0x47, len(pending_dtcs)])
        for dtc in pending_dtcs:
            response.extend(dtc.to_bytes())

        return bytes(response)

    # Mode 08: Control On-Board Systems
    def _mode_08_control_systems(self, request: bytes) -> bytes:
        """Mode 08 - Request control of on-board system"""
        # Simplified: Just acknowledge
        if len(request) < 2:
            return bytes([0x7F, 0x08, 0x12])

        tid = request[1]
        return bytes([0x48, tid])  # Echo back TID

    # Mode 09: Vehicle Information
    def _mode_09_vehicle_info(self, request: bytes) -> bytes:
        """Mode 09 - Request vehicle information"""
        if len(request) < 2:
            return bytes([0x7F, 0x09, 0x12])

        pid = request[1]

        # PID 0x00: Supported PIDs
        if pid == 0x00:
            return bytes([0x49, 0x00, 0x55])  # Support 02, 04, 06, 0A

        # PID 0x02: VIN (requires multi-frame - 17 bytes)
        elif pid == 0x02:
            vin_bytes = self.vin.encode('ascii')[:17]
            # Pad to 17 bytes if needed
            vin_bytes = vin_bytes.ljust(17, b'\x00')
            # Response: 49 02 01 [VIN 17 bytes]
            return bytes([0x49, 0x02, 0x01]) + vin_bytes

        # PID 0x04: Calibration ID (requires multi-frame - up to 16 bytes)
        elif pid == 0x04:
            cal_id = self.calibration_id.encode('ascii')[:16]
            cal_id = cal_id.ljust(16, b'\x00')
            return bytes([0x49, 0x04, 0x01]) + cal_id

        # PID 0x06: CVN (Calibration Verification Numbers)
        elif pid == 0x06:
            # 4-byte CVN
            cvn = b'\x12\x34\x56\x78'
            return bytes([0x49, 0x06, 0x01]) + cvn

        # PID 0x0A: ECU name
        elif pid == 0x0A:
            ecu_name = self.ecu_name.encode('ascii')[:20]
            ecu_name = ecu_name.ljust(20, b'\x00')
            return bytes([0x49, 0x0A, 0x01]) + ecu_name

        else:
            return bytes([0x7F, 0x09, 0x12])

    # Mode 0A: Permanent DTCs
    def _mode_0A_permanent_dtcs(self, request: bytes) -> bytes:
        """Mode 0A - Read permanent DTCs"""
        permanent_dtcs = self.dtc_manager.get_permanent_dtcs()

        if not permanent_dtcs:
            return bytes([0x4A, 0x00])  # No permanent DTCs

        response = bytearray([0x4A, len(permanent_dtcs)])
        for dtc in permanent_dtcs:
            response.extend(dtc.to_bytes())

        return bytes(response)

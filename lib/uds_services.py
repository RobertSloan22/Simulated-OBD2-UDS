"""
Advanced UDS (Unified Diagnostic Services) Handler

Implements professional-grade UDS services as per ISO 14229 standard.
"""

import time
import random
from typing import Optional, Dict
from enum import Enum
from lib.vehicle_simulator import VehicleSimulator
from lib.dtc_manager import DTCManager


class DiagnosticSession(Enum):
    """UDS diagnostic session types"""
    DEFAULT = 0x01
    PROGRAMMING = 0x02
    EXTENDED = 0x03
    SAFETY_SYSTEM = 0x04


class SecurityLevel(Enum):
    """Security access levels"""
    LOCKED = 0x00
    LEVEL_1 = 0x01  # Basic access
    LEVEL_2 = 0x02  # Extended access


class UDSServiceHandler:
    """Handles all UDS service requests"""

    def __init__(self, vehicle: VehicleSimulator, dtc_manager: DTCManager, config: Optional[dict] = None):
        """
        Initialize UDS service handler

        Args:
            vehicle: Vehicle simulator instance
            dtc_manager: DTC manager instance
            config: Configuration dictionary
        """
        self.vehicle = vehicle
        self.dtc_manager = dtc_manager
        self.config = config or {}

        # Session state
        self.current_session = DiagnosticSession.DEFAULT
        self.security_level = SecurityLevel.LOCKED
        self.session_start_time = 0.0
        self.session_timeout = 5.0  # S3 server timeout (seconds)

        # Security access
        self.current_seed = None
        self.security_attempts = 0
        self.max_security_attempts = 3

        # I/O Control state
        self.io_controls: Dict[int, bool] = {}  # DID -> state

        # Routine state
        self.active_routines: Dict[int, str] = {}  # Routine ID -> status

        # DIDs (Data Identifiers)
        self.dids = self._initialize_dids()

    def _initialize_dids(self) -> Dict[int, bytes]:
        """Initialize supported Data Identifiers"""
        vin = self.config.get('vin', '1HGBH41JXMN109186').encode('ascii')[:17].ljust(17, b'\x00')

        return {
            0xF187: b'12345678',  # Spare part number
            0xF18A: b'SUPPLIER',  # System supplier ID
            0xF18B: b'20250101',  # ECU manufacturing date (YYYYMMDD)
            0xF18C: b'SN123456789012',  # ECU serial number
            0xF18E: b'v2.0.0',  # ECU software version
            0xF190: vin,  # VIN
            0xF191: b'HW1.0',  # ECU hardware version
            0xF19E: b'ENGINE-ECU',  # System name or ECU name
            # Custom DIDs
            0x0100: b'\x00\x01',  # Custom data 1
            0x0101: b'\x00\x02',  # Custom data 2
        }

    def process(self, request: bytes) -> Optional[bytes]:
        """
        Process UDS service request

        Args:
            request: Service request bytes

        Returns:
            Response bytes or None for invalid request
        """
        if len(request) < 1:
            return None

        service = request[0]

        # Check session timeout (except for tester present)
        if service != 0x3E:
            if self.current_session != DiagnosticSession.DEFAULT:
                if time.time() - self.session_start_time > self.session_timeout:
                    # Session timed out
                    self.current_session = DiagnosticSession.DEFAULT
                    self.security_level = SecurityLevel.LOCKED

        # Route to service handlers
        if service == 0x10:
            return self._service_10_diagnostic_session(request)
        elif service == 0x11:
            return self._service_11_ecu_reset(request)
        elif service == 0x14:
            return self._service_14_clear_dtc(request)
        elif service == 0x19:
            return self._service_19_read_dtc_info(request)
        elif service == 0x22:
            return self._service_22_read_data_by_id(request)
        elif service == 0x27:
            return self._service_27_security_access(request)
        elif service == 0x28:
            return self._service_28_communication_control(request)
        elif service == 0x2E:
            return self._service_2E_write_data_by_id(request)
        elif service == 0x2F:
            return self._service_2F_io_control(request)
        elif service == 0x31:
            return self._service_31_routine_control(request)
        elif service == 0x34:
            return self._service_34_request_download(request)
        elif service == 0x36:
            return self._service_36_transfer_data(request)
        elif service == 0x37:
            return self._service_37_transfer_exit(request)
        elif service == 0x3E:
            return self._service_3E_tester_present(request)
        elif service == 0x85:
            return self._service_85_control_dtc_setting(request)
        else:
            # Service not supported
            return self._negative_response(service, 0x11)

    def _negative_response(self, service: int, nrc: int) -> bytes:
        """Generate negative response"""
        return bytes([0x7F, service, nrc])

    # Service 0x10: Diagnostic Session Control
    def _service_10_diagnostic_session(self, request: bytes) -> bytes:
        """Service 0x10 - Diagnostic session control"""
        if len(request) < 2:
            return self._negative_response(0x10, 0x13)  # Incorrect message length

        session_type = request[1]

        # Validate session type
        if session_type not in [0x01, 0x02, 0x03, 0x04]:
            return self._negative_response(0x10, 0x12)  # Sub-function not supported

        self.current_session = DiagnosticSession(session_type)
        self.session_start_time = time.time()

        # Reset security level when changing sessions (except extended)
        if session_type != DiagnosticSession.EXTENDED.value:
            self.security_level = SecurityLevel.LOCKED

        # Response: service+0x40, session type, P2 timing (00 32 = 50ms), P2* timing (01 F4 = 500ms)
        return bytes([0x50, session_type, 0x00, 0x32, 0x01, 0xF4])

    # Service 0x11: ECU Reset
    def _service_11_ecu_reset(self, request: bytes) -> bytes:
        """Service 0x11 - ECU reset"""
        if len(request) < 2:
            return self._negative_response(0x11, 0x13)

        reset_type = request[1]

        # 0x01 = Hard reset, 0x02 = Key off/on, 0x03 = Soft reset
        if reset_type not in [0x01, 0x02, 0x03]:
            return self._negative_response(0x11, 0x12)

        # In simulation, just acknowledge
        return bytes([0x51, reset_type])

    # Service 0x14: Clear Diagnostic Information
    def _service_14_clear_dtc(self, request: bytes) -> bytes:
        """Service 0x14 - Clear diagnostic information"""
        if len(request) < 4:
            return self._negative_response(0x14, 0x13)

        # Group of DTC (e.g., 0xFFFFFF = all)
        dtc_group = (request[1] << 16) | (request[2] << 8) | request[3]

        # Clear DTCs
        if dtc_group == 0xFFFFFF:
            self.dtc_manager.clear_dtcs(clear_permanent=False)
        # Could implement filtering by group here

        return bytes([0x54])

    # Service 0x19: Read DTC Information
    def _service_19_read_dtc_info(self, request: bytes) -> bytes:
        """Service 0x19 - Read DTC information"""
        if len(request) < 2:
            return self._negative_response(0x19, 0x13)

        sub_function = request[1]

        # Sub 0x01: Report number of DTCs by status mask
        if sub_function == 0x01:
            dtc_count = self.dtc_manager.get_dtc_count()
            # Format: [59 01] [StatusAvailabilityMask] [DTCFormatIdentifier] [DTCCount High] [DTCCount Low]
            return bytes([0x59, 0x01, 0xFF, 0x00, (dtc_count >> 8) & 0xFF, dtc_count & 0xFF])

        # Sub 0x02: Report DTC by status mask
        elif sub_function == 0x02:
            if len(request) < 3:
                return self._negative_response(0x19, 0x13)

            status_mask = request[2]
            # Get all active DTCs
            dtcs = self.dtc_manager.get_all_active_dtcs()

            response = bytearray([0x59, 0x02, status_mask])
            for dtc in dtcs:
                response.extend(dtc.to_bytes())
                response.append(0x08)  # Status: confirmed, test failed

            return bytes(response)

        # Sub 0x0A: Report supported DTC
        elif sub_function == 0x0A:
            # Return all known DTCs (even if not currently active)
            from lib.dtc_manager import DTC_DEFINITIONS
            response = bytearray([0x59, 0x0A])

            for code in list(DTC_DEFINITIONS.keys())[:10]:  # Limit to 10 for response size
                # Convert code to bytes
                type_map = {'P': 0, 'C': 1, 'B': 2, 'U': 3}
                code_type = type_map.get(code[0], 0)
                digits = code[1:]

                byte1 = (code_type << 6) | (int(digits[0]) << 4) | int(digits[1])
                byte2 = (int(digits[2]) << 4) | int(digits[3])

                response.extend([byte1, byte2, 0x00])  # Status byte

            return bytes(response)

        else:
            return self._negative_response(0x19, 0x12)

    # Service 0x22: Read Data By Identifier
    def _service_22_read_data_by_id(self, request: bytes) -> bytes:
        """Service 0x22 - Read data by identifier"""
        if len(request) < 3:
            return self._negative_response(0x22, 0x13)

        did = (request[1] << 8) | request[2]

        if did not in self.dids:
            return self._negative_response(0x22, 0x31)  # Request out of range

        data = self.dids[did]
        return bytes([0x62, request[1], request[2]]) + data

    # Service 0x27: Security Access
    def _service_27_security_access(self, request: bytes) -> bytes:
        """Service 0x27 - Security access"""
        if len(request) < 2:
            return self._negative_response(0x27, 0x13)

        sub_function = request[1]

        # Odd sub-functions = request seed
        if sub_function % 2 == 1:
            level = (sub_function + 1) // 2

            # Check if already unlocked
            if self.security_level.value >= level:
                # Already unlocked - return zero seed
                return bytes([0x67, sub_function, 0x00, 0x00, 0x00, 0x00])

            # Check attempts
            if self.security_attempts >= self.max_security_attempts:
                return self._negative_response(0x27, 0x36)  # Exceeded number of attempts

            # Generate seed (simplified: random 4 bytes)
            self.current_seed = random.randint(0x10000000, 0xFFFFFFFF)
            seed_bytes = self.current_seed.to_bytes(4, 'big')

            return bytes([0x67, sub_function]) + seed_bytes

        # Even sub-functions = send key
        elif sub_function % 2 == 0:
            if len(request) < 6:
                return self._negative_response(0x27, 0x13)

            level = sub_function // 2
            provided_key = int.from_bytes(request[2:6], 'big')

            # Check if seed was requested
            if self.current_seed is None:
                return self._negative_response(0x27, 0x24)  # Request sequence error

            # Calculate expected key (simplified: XOR with constant)
            expected_key = self.current_seed ^ 0x12345678

            if provided_key == expected_key:
                # Correct key
                self.security_level = SecurityLevel(level)
                self.security_attempts = 0
                self.current_seed = None
                return bytes([0x67, sub_function])
            else:
                # Incorrect key
                self.security_attempts += 1
                self.current_seed = None
                return self._negative_response(0x27, 0x35)  # Invalid key

        else:
            return self._negative_response(0x27, 0x12)

    # Service 0x28: Communication Control
    def _service_28_communication_control(self, request: bytes) -> bytes:
        """Service 0x28 - Communication control"""
        if len(request) < 3:
            return self._negative_response(0x28, 0x13)

        control_type = request[1]
        communication_type = request[2]

        # 0x00 = Enable RX and TX
        # 0x01 = Enable RX, disable TX
        # 0x02 = Disable RX, enable TX
        # 0x03 = Disable RX and TX

        # In simulation, just acknowledge
        return bytes([0x68, control_type])

    # Service 0x2E: Write Data By Identifier
    def _service_2E_write_data_by_id(self, request: bytes) -> bytes:
        """Service 0x2E - Write data by identifier"""
        if len(request) < 4:
            return self._negative_response(0x2E, 0x13)

        # Security check
        if self.security_level == SecurityLevel.LOCKED:
            return self._negative_response(0x2E, 0x33)  # Security access denied

        did = (request[1] << 8) | request[2]
        data = request[3:]

        if did not in self.dids:
            return self._negative_response(0x2E, 0x31)  # Request out of range

        # Update DID value
        self.dids[did] = data

        return bytes([0x6E, request[1], request[2]])

    # Service 0x2F: Input/Output Control By Identifier
    def _service_2F_io_control(self, request: bytes) -> bytes:
        """Service 0x2F - I/O control by identifier"""
        if len(request) < 4:
            return self._negative_response(0x2F, 0x13)

        # Security/session check
        if self.current_session != DiagnosticSession.EXTENDED:
            return self._negative_response(0x2F, 0x7F)  # Service not supported in active session

        did = (request[1] << 8) | request[2]
        control_param = request[3]

        # 0x00 = Return control to ECU
        # 0x01 = Reset to default
        # 0x02 = Freeze current state
        # 0x03 = Short term adjustment

        if control_param == 0x00:
            # Return control to ECU
            if did in self.io_controls:
                del self.io_controls[did]
        else:
            # Take control
            control_state = request[4] if len(request) > 4 else 0
            self.io_controls[did] = bool(control_state)

        return bytes([0x6F, request[1], request[2], control_param])

    # Service 0x31: Routine Control
    def _service_31_routine_control(self, request: bytes) -> bytes:
        """Service 0x31 - Routine control"""
        if len(request) < 4:
            return self._negative_response(0x31, 0x13)

        sub_function = request[1]
        routine_id = (request[2] << 8) | request[3]

        # Sub-functions: 0x01 = Start, 0x02 = Stop, 0x03 = Request results

        if sub_function == 0x01:  # Start routine
            # Check session
            if self.current_session == DiagnosticSession.DEFAULT:
                return self._negative_response(0x31, 0x7F)

            self.active_routines[routine_id] = "running"
            return bytes([0x71, 0x01, request[2], request[3], 0x00])  # Routine started

        elif sub_function == 0x02:  # Stop routine
            if routine_id in self.active_routines:
                self.active_routines[routine_id] = "stopped"
            return bytes([0x71, 0x02, request[2], request[3], 0x00])

        elif sub_function == 0x03:  # Request results
            status = 0x00 if routine_id in self.active_routines else 0x01
            return bytes([0x71, 0x03, request[2], request[3], status])

        else:
            return self._negative_response(0x31, 0x12)

    # Service 0x34: Request Download
    def _service_34_request_download(self, request: bytes) -> bytes:
        """Service 0x34 - Request download (firmware update)"""
        # Requires programming session and security
        if self.current_session != DiagnosticSession.PROGRAMMING:
            return self._negative_response(0x34, 0x7F)

        if self.security_level == SecurityLevel.LOCKED:
            return self._negative_response(0x34, 0x33)

        # In simulation, just acknowledge
        # Real implementation would setup memory addresses
        return bytes([0x74, 0x20, 0x10, 0x00])  # Max block length = 0x1000

    # Service 0x36: Transfer Data
    def _service_36_transfer_data(self, request: bytes) -> bytes:
        """Service 0x36 - Transfer data"""
        if len(request) < 2:
            return self._negative_response(0x36, 0x13)

        block_seq = request[1]
        # In simulation, just acknowledge
        return bytes([0x76, block_seq])

    # Service 0x37: Request Transfer Exit
    def _service_37_transfer_exit(self, request: bytes) -> bytes:
        """Service 0x37 - Request transfer exit"""
        # In simulation, just acknowledge
        return bytes([0x77])

    # Service 0x3E: Tester Present
    def _service_3E_tester_present(self, request: bytes) -> bytes:
        """Service 0x3E - Tester present"""
        if len(request) < 2:
            return self._negative_response(0x3E, 0x13)

        sub_function = request[1]

        # Refresh session timeout
        self.session_start_time = time.time()

        # Sub-function 0x00 = send response, 0x80 = suppress response
        if sub_function == 0x00:
            return bytes([0x7E, 0x00])
        else:
            return None  # Suppress response

    # Service 0x85: Control DTC Setting
    def _service_85_control_dtc_setting(self, request: bytes) -> bytes:
        """Service 0x85 - Control DTC setting"""
        if len(request) < 2:
            return self._negative_response(0x85, 0x13)

        # Requires extended session
        if self.current_session != DiagnosticSession.EXTENDED:
            return self._negative_response(0x85, 0x7F)

        control_type = request[1]

        # 0x01 = On, 0x02 = Off
        # In simulation, just acknowledge
        return bytes([0xC5, control_type])

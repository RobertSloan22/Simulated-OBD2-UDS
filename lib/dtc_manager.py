"""
Diagnostic Trouble Code (DTC) Management System

Manages fault codes with states (pending/confirmed/permanent), freeze frames,
MIL (Check Engine Light) logic, and fault healing.
"""

import time
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from lib.vehicle_simulator import SensorData


class DTCState(Enum):
    """DTC lifecycle states"""
    PENDING = "pending"  # Detected once, not confirmed
    CONFIRMED = "confirmed"  # Detected multiple times, stored
    PERMANENT = "permanent"  # Emission-related, cannot be cleared
    HISTORY = "history"  # Cleared but stored for analysis


class DTCType(Enum):
    """DTC classification"""
    POWERTRAIN = "P"  # P0xxx, P2xxx, P3xxx
    CHASSIS = "C"  # C0xxx, C1xxx, C2xxx, C3xxx
    BODY = "B"  # B0xxx, B1xxx, B2xxx, B3xxx
    NETWORK = "U"  # U0xxx, U1xxx, U2xxx, U3xxx


@dataclass
class FreezeFrame:
    """Sensor snapshot when DTC was set"""
    timestamp: float
    rpm: float
    speed: float
    coolant_temp: float
    engine_load: float
    throttle_position: float
    fuel_pressure: float
    maf: float
    short_term_fuel_trim: float
    long_term_fuel_trim: float
    timing_advance: float

    @classmethod
    def capture(cls, sensors: SensorData) -> 'FreezeFrame':
        """Capture freeze frame from current sensor data"""
        return cls(
            timestamp=time.time(),
            rpm=sensors.rpm,
            speed=sensors.vehicle_speed,
            coolant_temp=sensors.coolant_temp,
            engine_load=sensors.engine_load,
            throttle_position=sensors.throttle_position,
            fuel_pressure=sensors.fuel_pressure,
            maf=sensors.maf,
            short_term_fuel_trim=sensors.short_term_fuel_trim,
            long_term_fuel_trim=sensors.long_term_fuel_trim,
            timing_advance=sensors.timing_advance
        )


@dataclass
class DiagnosticTroubleCode:
    """Represents a single DTC with metadata"""
    code: str  # e.g., "P0420"
    description: str
    state: DTCState = DTCState.PENDING
    detection_count: int = 0
    first_detected: float = field(default_factory=time.time)
    last_detected: float = field(default_factory=time.time)
    freeze_frame: Optional[FreezeFrame] = None
    mil_illuminate: bool = False  # Should this DTC turn on Check Engine Light
    is_emission_related: bool = False  # Can it become permanent?

    def get_type(self) -> DTCType:
        """Get DTC type from code"""
        if self.code.startswith('P'):
            return DTCType.POWERTRAIN
        elif self.code.startswith('C'):
            return DTCType.CHASSIS
        elif self.code.startswith('B'):
            return DTCType.BODY
        elif self.code.startswith('U'):
            return DTCType.NETWORK
        else:
            return DTCType.POWERTRAIN

    def to_bytes(self) -> bytes:
        """Convert DTC code to OBD-II bytes format"""
        # Convert "P0420" to bytes [0x04, 0x20]
        # First nibble: type (P=0, C=1, B=2, U=3) + first digit
        # Remaining nibbles: other digits

        type_map = {'P': 0, 'C': 1, 'B': 2, 'U': 3}
        code_type = type_map.get(self.code[0], 0)

        # Extract digits
        digits = self.code[1:]  # e.g., "0420"
        if len(digits) != 4:
            return bytes([0x00, 0x00])

        # First byte: [type + first_digit][second_digit]
        first_digit = int(digits[0])
        second_digit = int(digits[1])
        byte1 = (code_type << 6) | (first_digit << 4) | second_digit

        # Second byte: [third_digit][fourth_digit]
        third_digit = int(digits[2])
        fourth_digit = int(digits[3])
        byte2 = (third_digit << 4) | fourth_digit

        return bytes([byte1, byte2])


# Common DTC definitions
DTC_DEFINITIONS = {
    # Misfire codes
    'P0300': ('Random/Multiple Cylinder Misfire Detected', True, True),
    'P0301': ('Cylinder 1 Misfire Detected', True, True),
    'P0302': ('Cylinder 2 Misfire Detected', True, True),
    'P0303': ('Cylinder 3 Misfire Detected', True, True),
    'P0304': ('Cylinder 4 Misfire Detected', True, True),

    # Fuel system
    'P0171': ('System Too Lean (Bank 1)', True, True),
    'P0172': ('System Too Rich (Bank 1)', True, True),
    'P0174': ('System Too Lean (Bank 2)', True, True),
    'P0175': ('System Too Rich (Bank 2)', True, True),

    # Coolant/thermostat
    'P0128': ('Coolant Thermostat (Coolant Temperature Below Thermostat Regulating Temperature)', True, True),

    # Catalyst
    'P0420': ('Catalyst System Efficiency Below Threshold (Bank 1)', True, True),
    'P0430': ('Catalyst System Efficiency Below Threshold (Bank 2)', True, True),

    # EVAP system
    'P0440': ('Evaporative Emission Control System Malfunction', True, True),
    'P0442': ('Evaporative Emission Control System Leak Detected (Small Leak)', True, True),
    'P0443': ('Evaporative Emission Control System Purge Control Valve Circuit Malfunction', True, True),
    'P0446': ('Evaporative Emission Control System Vent Control Circuit Malfunction', True, True),

    # O2 sensors
    'P0130': ('O2 Sensor Circuit Malfunction (Bank 1, Sensor 1)', True, True),
    'P0131': ('O2 Sensor Circuit Low Voltage (Bank 1, Sensor 1)', True, True),
    'P0132': ('O2 Sensor Circuit High Voltage (Bank 1, Sensor 1)', True, True),
    'P0133': ('O2 Sensor Circuit Slow Response (Bank 1, Sensor 1)', True, True),
    'P0134': ('O2 Sensor Circuit No Activity Detected (Bank 1, Sensor 1)', True, True),

    # MAF/MAP sensors
    'P0100': ('Mass or Volume Air Flow Circuit Malfunction', True, False),
    'P0101': ('Mass or Volume Air Flow Circuit Range/Performance Problem', True, False),
    'P0102': ('Mass or Volume Air Flow Circuit Low Input', True, False),
    'P0103': ('Mass or Volume Air Flow Circuit High Input', True, False),

    # Electrical
    'P0562': ('System Voltage Low', True, False),
    'P0563': ('System Voltage High', True, False),

    # EGR
    'P0401': ('Exhaust Gas Recirculation Flow Insufficient Detected', True, True),
    'P0402': ('Exhaust Gas Recirculation Flow Excessive Detected', True, True),

    # Transmission (if present)
    'P0700': ('Transmission Control System Malfunction', False, False),
    'P0715': ('Input/Turbine Speed Sensor Circuit Malfunction', False, False),
    'P0720': ('Output Speed Sensor Circuit Malfunction', False, False),

    # Manufacturer specific
    'P1000': ('OBD System Readiness Test Not Complete', False, False),
}


class DTCManager:
    """Manages all diagnostic trouble codes"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize DTC manager

        Args:
            config: Configuration with DTC settings
        """
        self.config = config or {}
        self.dtcs: Dict[str, DiagnosticTroubleCode] = {}

        # MIL (Malfunction Indicator Lamp / Check Engine Light) state
        self.mil_on = False

        # Thresholds
        self.pending_to_confirmed_threshold = 2  # Detections needed
        self.healing_drive_cycles = 40  # Drive cycles to clear pending DTC

        # Drive cycle tracking
        self.drive_cycle_count = 0

    def inject_dtc(self, code: str, sensors: SensorData, capture_freeze_frame: bool = True) -> bool:
        """
        Inject/trigger a DTC

        Args:
            code: DTC code (e.g., "P0420")
            sensors: Current sensor data for freeze frame
            capture_freeze_frame: Whether to capture freeze frame

        Returns:
            True if DTC was injected successfully
        """
        if code not in DTC_DEFINITIONS:
            print(f"[DTC] Unknown DTC code: {code}")
            return False

        if code in self.dtcs:
            # Existing DTC - update
            dtc = self.dtcs[code]
            dtc.detection_count += 1
            dtc.last_detected = time.time()

            # Transition pending to confirmed
            if dtc.state == DTCState.PENDING and \
               dtc.detection_count >= self.pending_to_confirmed_threshold:
                dtc.state = DTCState.CONFIRMED
                print(f"[DTC] {code} confirmed after {dtc.detection_count} detections")

                # Make permanent if emission-related
                if dtc.is_emission_related:
                    dtc.state = DTCState.PERMANENT

        else:
            # New DTC
            description, mil_illuminate, is_emission = DTC_DEFINITIONS[code]
            freeze_frame = FreezeFrame.capture(sensors) if capture_freeze_frame else None

            dtc = DiagnosticTroubleCode(
                code=code,
                description=description,
                state=DTCState.PENDING,
                detection_count=1,
                freeze_frame=freeze_frame,
                mil_illuminate=mil_illuminate,
                is_emission_related=is_emission
            )
            self.dtcs[code] = dtc
            print(f"[DTC] {code} detected (pending): {description}")

        # Update MIL status
        self._update_mil()
        return True

    def clear_dtcs(self, clear_permanent: bool = False) -> List[str]:
        """
        Clear DTCs

        Args:
            clear_permanent: If True, also clear permanent DTCs (not OBD-II compliant)

        Returns:
            List of cleared DTC codes
        """
        cleared = []

        for code, dtc in list(self.dtcs.items()):
            if dtc.state == DTCState.PERMANENT and not clear_permanent:
                continue  # Cannot clear permanent DTCs normally

            if dtc.state in [DTCState.PENDING, DTCState.CONFIRMED]:
                # Move to history instead of deleting
                dtc.state = DTCState.HISTORY
                cleared.append(code)
            elif clear_permanent and dtc.state == DTCState.PERMANENT:
                dtc.state = DTCState.HISTORY
                cleared.append(code)

        # Clean up history (keep only recent)
        self._cleanup_history()

        # Reset MIL
        self._update_mil()

        if cleared:
            print(f"[DTC] Cleared {len(cleared)} DTCs: {', '.join(cleared)}")

        return cleared

    def get_dtcs_by_state(self, state: DTCState) -> List[DiagnosticTroubleCode]:
        """Get all DTCs in a specific state"""
        return [dtc for dtc in self.dtcs.values() if dtc.state == state]

    def get_pending_dtcs(self) -> List[DiagnosticTroubleCode]:
        """Get pending DTCs (Mode 07)"""
        return self.get_dtcs_by_state(DTCState.PENDING)

    def get_confirmed_dtcs(self) -> List[DiagnosticTroubleCode]:
        """Get confirmed/stored DTCs (Mode 03)"""
        return self.get_dtcs_by_state(DTCState.CONFIRMED)

    def get_permanent_dtcs(self) -> List[DiagnosticTroubleCode]:
        """Get permanent DTCs (Mode 0A)"""
        return self.get_dtcs_by_state(DTCState.PERMANENT)

    def get_all_active_dtcs(self) -> List[DiagnosticTroubleCode]:
        """Get all active DTCs (pending + confirmed + permanent)"""
        return [dtc for dtc in self.dtcs.values()
                if dtc.state in [DTCState.PENDING, DTCState.CONFIRMED, DTCState.PERMANENT]]

    def get_dtc_count(self) -> int:
        """Get count of confirmed DTCs (for OBD PID 01)"""
        return len(self.get_confirmed_dtcs()) + len(self.get_permanent_dtcs())

    def is_mil_on(self) -> bool:
        """Check if MIL (Check Engine Light) is on"""
        return self.mil_on

    def drive_cycle_complete(self):
        """Called when a drive cycle completes - handles fault healing"""
        self.drive_cycle_count += 1

        # Heal pending DTCs that haven't been detected recently
        current_time = time.time()
        for code, dtc in list(self.dtcs.items()):
            if dtc.state == DTCState.PENDING:
                # If not detected in last several drive cycles, heal it
                time_since_last = current_time - dtc.last_detected
                if time_since_last > (self.healing_drive_cycles * 600):  # Assume 10min/cycle
                    print(f"[DTC] {code} healed after {self.healing_drive_cycles} clean cycles")
                    del self.dtcs[code]

        self._update_mil()

    def _update_mil(self):
        """Update MIL status based on current DTCs"""
        # MIL turns on if any confirmed/permanent DTC has mil_illuminate=True
        self.mil_on = any(
            dtc.mil_illuminate and dtc.state in [DTCState.CONFIRMED, DTCState.PERMANENT]
            for dtc in self.dtcs.values()
        )

    def _cleanup_history(self, max_history: int = 10):
        """Remove old history entries"""
        history_dtcs = self.get_dtcs_by_state(DTCState.HISTORY)
        if len(history_dtcs) > max_history:
            # Sort by last detected and remove oldest
            history_dtcs.sort(key=lambda d: d.last_detected)
            for dtc in history_dtcs[:-max_history]:
                del self.dtcs[dtc.code]

    def format_dtc_response(self, dtcs: List[DiagnosticTroubleCode]) -> bytes:
        """
        Format DTCs for OBD-II response

        Returns:
            Bytes with DTC count + DTC codes
        """
        if not dtcs:
            return bytes([0x00])  # No DTCs

        response = bytearray([len(dtcs)])
        for dtc in dtcs:
            response.extend(dtc.to_bytes())

        return bytes(response)

    def get_freeze_frame(self, dtc_code: str) -> Optional[FreezeFrame]:
        """Get freeze frame for specific DTC"""
        if dtc_code in self.dtcs:
            return self.dtcs[dtc_code].freeze_frame
        return None

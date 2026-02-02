"""
Multi-ECU Coordinator

Manages multiple ECUs on the same CAN bus, enabling realistic vehicle network simulation
with engine, transmission, and ABS ECUs.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ECUType(Enum):
    """ECU types in vehicle"""
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    ABS = "abs"
    BODY = "body"


@dataclass
class ECUIdentity:
    """Defines an ECU's identity and capabilities"""
    ecu_type: ECUType
    name: str
    request_id: int  # Physical address for requests
    response_id: int  # Physical address for responses
    functional_address: int = 0x7DF  # Broadcast address

    # ECU capabilities
    supports_obd: bool = True
    supports_uds: bool = True

    # Configuration
    vin: str = ""
    serial_number: str = ""
    software_version: str = ""
    hardware_version: str = ""

    # DTC-specific codes this ECU handles
    dtc_prefix: str = "P0"  # e.g., "P0" for engine, "P07" for transmission, "C0" for ABS

    def matches_address(self, address: int) -> bool:
        """Check if this ECU responds to given address"""
        return address == self.request_id or address == self.functional_address


# Predefined ECU configurations
ENGINE_ECU = ECUIdentity(
    ecu_type=ECUType.ENGINE,
    name="Engine Control Unit",
    request_id=0x7E0,
    response_id=0x7E8,
    supports_obd=True,
    supports_uds=True,
    serial_number="ENG-SN-123456",
    software_version="ENG-SW-2.0.0",
    hardware_version="ENG-HW-1.0",
    dtc_prefix="P0"  # Powertrain codes
)

TRANSMISSION_ECU = ECUIdentity(
    ecu_type=ECUType.TRANSMISSION,
    name="Transmission Control Unit",
    request_id=0x7E1,
    response_id=0x7E9,
    supports_obd=False,  # Limited OBD support
    supports_uds=True,
    serial_number="TCM-SN-789012",
    software_version="TCM-SW-1.5.0",
    hardware_version="TCM-HW-1.0",
    dtc_prefix="P07"  # Transmission codes
)

ABS_ECU = ECUIdentity(
    ecu_type=ECUType.ABS,
    name="ABS/ESP Control Unit",
    request_id=0x7E2,
    response_id=0x7EA,
    supports_obd=False,
    supports_uds=True,
    serial_number="ABS-SN-345678",
    software_version="ABS-SW-3.0.0",
    hardware_version="ABS-HW-2.0",
    dtc_prefix="C0"  # Chassis codes
)


class MultiECUCoordinator:
    """Coordinates multiple ECUs on a single CAN bus"""

    def __init__(self):
        """Initialize multi-ECU coordinator"""
        self.ecus: Dict[str, 'MockECU'] = {}  # name -> ECU instance
        self.ecu_identities: Dict[str, ECUIdentity] = {}  # name -> identity

    def register_ecu(self, identity: ECUIdentity, ecu_instance: 'MockECU'):
        """
        Register an ECU with the coordinator

        Args:
            identity: ECU identity configuration
            ecu_instance: The MockECU instance
        """
        self.ecu_identities[identity.name] = identity
        self.ecus[identity.name] = ecu_instance
        print(f"[Multi-ECU] Registered {identity.name} (0x{identity.request_id:03X}/0x{identity.response_id:03X})")

    def get_ecu_for_address(self, address: int) -> Optional['MockECU']:
        """
        Get ECU that responds to given CAN address

        Args:
            address: CAN ID from request

        Returns:
            ECU instance or None
        """
        for name, identity in self.ecu_identities.items():
            if identity.matches_address(address):
                return self.ecus.get(name)
        return None

    def get_all_ecus_for_broadcast(self) -> List['MockECU']:
        """
        Get all ECUs that respond to functional addressing (broadcast)

        Returns:
            List of ECU instances
        """
        return list(self.ecus.values())

    def get_ecu_by_name(self, name: str) -> Optional['MockECU']:
        """Get ECU by name"""
        return self.ecus.get(name)

    def get_ecu_by_type(self, ecu_type: ECUType) -> Optional['MockECU']:
        """Get ECU by type"""
        for name, identity in self.ecu_identities.items():
            if identity.ecu_type == ecu_type:
                return self.ecus.get(name)
        return None

    def list_ecus(self) -> List[ECUIdentity]:
        """Get list of all registered ECU identities"""
        return list(self.ecu_identities.values())

    def inject_dtc_to_ecu(self, ecu_name: str, dtc_code: str, sensors) -> bool:
        """
        Inject DTC to specific ECU

        Args:
            ecu_name: Name of ECU
            dtc_code: DTC code to inject
            sensors: Sensor data for freeze frame

        Returns:
            True if successful
        """
        ecu = self.ecus.get(ecu_name)
        if ecu and hasattr(ecu, 'dtc_manager'):
            return ecu.dtc_manager.inject_dtc(dtc_code, sensors)
        return False

    def get_total_dtc_count(self) -> int:
        """Get total DTC count across all ECUs"""
        total = 0
        for ecu in self.ecus.values():
            if hasattr(ecu, 'dtc_manager'):
                total += ecu.dtc_manager.get_dtc_count()
        return total

    def clear_all_dtcs(self):
        """Clear DTCs from all ECUs"""
        for ecu in self.ecus.values():
            if hasattr(ecu, 'dtc_manager'):
                ecu.dtc_manager.clear_dtcs()

    def get_status_summary(self) -> Dict:
        """Get status summary of all ECUs"""
        summary = {}
        for name, identity in self.ecu_identities.items():
            ecu = self.ecus[name]
            status = {
                'type': identity.ecu_type.value,
                'request_id': f"0x{identity.request_id:03X}",
                'response_id': f"0x{identity.response_id:03X}",
                'obd_support': identity.supports_obd,
                'uds_support': identity.supports_uds,
            }

            # Add DTC count if available
            if hasattr(ecu, 'dtc_manager'):
                status['dtc_count'] = ecu.dtc_manager.get_dtc_count()
                status['mil_on'] = ecu.dtc_manager.is_mil_on()

            summary[name] = status

        return summary


# Transmission-specific sensor data additions
@dataclass
class TransmissionData:
    """Transmission-specific sensor data"""
    gear_position: int = 0  # 0=P, 1=R, 2=N, 3=D, 4-9=gears
    transmission_temp: float = 80.0  # °C
    clutch_position: float = 0.0  # 0-100%
    torque_converter_lockup: bool = False
    shift_pressure: float = 500.0  # kPa


@dataclass
class ABSData:
    """ABS-specific sensor data"""
    wheel_speed_fl: float = 0.0  # km/h - Front Left
    wheel_speed_fr: float = 0.0  # km/h - Front Right
    wheel_speed_rl: float = 0.0  # km/h - Rear Left
    wheel_speed_rr: float = 0.0  # km/h - Rear Right
    brake_pressure: float = 0.0  # bar
    abs_active: bool = False
    esp_active: bool = False
    steering_angle: float = 0.0  # degrees

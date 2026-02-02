"""
Vehicle Configuration Management

Loads and manages vehicle profiles from JSON configuration files.
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path


class VehicleConfig:
    """Manages vehicle configuration from JSON profiles"""

    def __init__(self, config_file: Optional[str] = None):
        """
        Load vehicle configuration

        Args:
            config_file: Path to JSON config file (default: default.json)
        """
        if config_file is None:
            config_file = "default.json"

        # Find config file
        self.config_path = self._find_config_file(config_file)

        # Load configuration
        self.config = self._load_config()

    def _find_config_file(self, filename: str) -> Path:
        """Find configuration file in vehicle_profiles directory"""
        # Try relative to current directory
        profiles_dir = Path("vehicle_profiles")
        if not profiles_dir.exists():
            # Try relative to script location
            script_dir = Path(__file__).parent.parent
            profiles_dir = script_dir / "vehicle_profiles"

        config_path = profiles_dir / filename

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        return config_path

    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            print(f"[Config] Loaded vehicle profile: {self.config_path.name}")
            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    # Vehicle information
    def get_vehicle_info(self) -> Dict:
        """Get vehicle information"""
        return self.get('vehicle', {})

    def get_vin(self) -> str:
        """Get VIN"""
        return self.get('vehicle.vin', '1HGBH41JXMN109186')

    def get_make(self) -> str:
        """Get vehicle make"""
        return self.get('vehicle.make', 'Generic')

    def get_model(self) -> str:
        """Get vehicle model"""
        return self.get('vehicle.model', 'Vehicle')

    def get_year(self) -> int:
        """Get vehicle year"""
        return self.get('vehicle.year', 2020)

    # Sensor parameters
    def get_sensor_params(self) -> Dict:
        """Get sensor parameters"""
        return self.get('sensors', {})

    def get_rpm_idle(self) -> int:
        """Get idle RPM"""
        return self.get('sensors.rpm_idle', 750)

    def get_rpm_max(self) -> int:
        """Get maximum RPM"""
        return self.get('sensors.rpm_max', 6500)

    def get_coolant_temp_normal(self) -> int:
        """Get normal operating coolant temperature"""
        return self.get('sensors.coolant_temp_normal', 90)

    def get_fuel_capacity(self) -> float:
        """Get fuel tank capacity (liters)"""
        return self.get('sensors.fuel_capacity', 50.0)

    # DTCs
    def get_dtc_configs(self) -> List[Dict]:
        """Get DTC configurations"""
        return self.get('dtcs', [])

    # Supported PIDs
    def get_supported_pids(self) -> List[str]:
        """Get list of supported OBD PIDs"""
        return self.get('supported_pids', [])

    # UDS DIDs
    def get_uds_dids(self) -> Dict[str, str]:
        """Get UDS Data Identifiers"""
        return self.get('uds_dids', {})

    # ECU information
    def get_ecu_info(self) -> Dict:
        """Get ECU information"""
        return {
            'serial_number': self.get('ecu.serial_number', 'SN-123456789'),
            'software_version': self.get('ecu.software_version', 'v2.0.0'),
            'hardware_version': self.get('ecu.hardware_version', 'v1.0'),
            'calibration_id': self.get('ecu.calibration_id', 'CALIB12345678'),
            'ecu_name': self.get('ecu.name', 'ENGINE-ECU')
        }

    # Full configuration
    def get_all(self) -> Dict:
        """Get full configuration dictionary"""
        return self.config

    def update(self, key: str, value: Any):
        """Update configuration value (runtime only, not saved)"""
        keys = key.split('.')
        current = self.config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value


class ConfigManager:
    """Manages configurations for multiple ECUs"""

    def __init__(self):
        """Initialize configuration manager"""
        self.configs: Dict[str, VehicleConfig] = {}

    def load_ecu_config(self, ecu_name: str, config_file: Optional[str] = None) -> VehicleConfig:
        """
        Load configuration for an ECU

        Args:
            ecu_name: Name identifier for ECU
            config_file: Config file to load (default: default.json)

        Returns:
            Loaded VehicleConfig instance
        """
        config = VehicleConfig(config_file)
        self.configs[ecu_name] = config
        return config

    def get_config(self, ecu_name: str) -> Optional[VehicleConfig]:
        """Get configuration for an ECU"""
        return self.configs.get(ecu_name)

    def list_available_profiles(self) -> List[str]:
        """List all available vehicle profiles"""
        profiles_dir = Path("vehicle_profiles")
        if not profiles_dir.exists():
            script_dir = Path(__file__).parent.parent
            profiles_dir = script_dir / "vehicle_profiles"

        if not profiles_dir.exists():
            return []

        return [f.name for f in profiles_dir.glob("*.json")]

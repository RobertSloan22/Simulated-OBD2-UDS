"""
Realistic Vehicle State Simulator

Simulates vehicle behavior including engine state machine, sensor correlations,
time-based evolution, and drive cycle tracking for OBD-II readiness monitors.
"""

import time
import math
import random
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass, field


class EngineState(Enum):
    """Engine operating states"""
    OFF = "off"
    CRANKING = "cranking"
    RUNNING = "running"
    STALLING = "stalling"


@dataclass
class SensorData:
    """Current sensor readings"""
    # Engine
    rpm: float = 0.0
    engine_load: float = 0.0
    coolant_temp: float = 20.0  # °C
    intake_air_temp: float = 25.0  # °C
    maf: float = 0.0  # g/s (Mass Air Flow)
    timing_advance: float = 0.0  # degrees

    # Throttle & Fuel
    throttle_position: float = 0.0  # 0-100%
    fuel_level: float = 75.0  # 0-100%
    fuel_pressure: float = 380.0  # kPa
    fuel_rate: float = 0.0  # L/h

    # Speed & Distance
    vehicle_speed: float = 0.0  # km/h
    distance_traveled: float = 0.0  # km
    distance_with_mil: float = 0.0  # km
    distance_since_clear: float = 0.0  # km

    # Electrical
    battery_voltage: float = 12.6  # V

    # O2 Sensors (simplified - bank 1 sensor 1)
    o2_voltage: float = 0.45  # V (0.1-0.9 typical)
    short_term_fuel_trim: float = 0.0  # -100 to +100%
    long_term_fuel_trim: float = 0.0  # -100 to +100%

    # Emissions
    catalyst_temp: float = 400.0  # °C
    evap_vapor_pressure: float = 0.0  # kPa
    barometric_pressure: float = 101.3  # kPa

    # Runtime
    engine_runtime: float = 0.0  # seconds
    warmups_since_clear: int = 0

    # State
    mil_status: bool = False  # Check Engine Light


@dataclass
class DriveCycle:
    """Drive cycle tracking for readiness monitors"""
    # Readiness monitor completion flags
    misfire_monitor_complete: bool = False
    fuel_system_monitor_complete: bool = False
    component_monitor_complete: bool = False
    catalyst_monitor_complete: bool = False
    heated_catalyst_monitor_complete: bool = False
    evap_system_monitor_complete: bool = False
    secondary_air_monitor_complete: bool = False
    oxygen_sensor_monitor_complete: bool = False
    oxygen_sensor_heater_complete: bool = False
    egr_system_monitor_complete: bool = False

    # Drive cycle requirements tracking
    idle_time: float = 0.0
    cruise_time: float = 0.0
    accel_count: int = 0
    decel_count: int = 0
    cold_start_count: int = 0

    def reset(self):
        """Reset all monitors to incomplete"""
        self.misfire_monitor_complete = False
        self.fuel_system_monitor_complete = False
        self.component_monitor_complete = False
        self.catalyst_monitor_complete = False
        self.heated_catalyst_monitor_complete = False
        self.evap_system_monitor_complete = False
        self.secondary_air_monitor_complete = False
        self.oxygen_sensor_monitor_complete = False
        self.oxygen_sensor_heater_complete = False
        self.egr_system_monitor_complete = False

        self.idle_time = 0.0
        self.cruise_time = 0.0
        self.accel_count = 0
        self.decel_count = 0
        self.cold_start_count = 0

    def get_completion_mask(self) -> int:
        """Get readiness monitor completion as bitmask"""
        mask = 0
        if self.misfire_monitor_complete:
            mask |= (1 << 0)
        if self.fuel_system_monitor_complete:
            mask |= (1 << 1)
        if self.component_monitor_complete:
            mask |= (1 << 2)
        if self.catalyst_monitor_complete:
            mask |= (1 << 3)
        if self.heated_catalyst_monitor_complete:
            mask |= (1 << 4)
        if self.evap_system_monitor_complete:
            mask |= (1 << 5)
        if self.secondary_air_monitor_complete:
            mask |= (1 << 6)
        if self.oxygen_sensor_monitor_complete:
            mask |= (1 << 7)
        if self.oxygen_sensor_heater_complete:
            mask |= (1 << 8)
        if self.egr_system_monitor_complete:
            mask |= (1 << 9)
        return mask


class VehicleSimulator:
    """Simulates realistic vehicle behavior with sensor correlations"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize vehicle simulator

        Args:
            config: Configuration dictionary with vehicle parameters
        """
        self.config = config or self._default_config()

        # State
        self.engine_state = EngineState.OFF
        self.sensors = SensorData()
        self.drive_cycle = DriveCycle()

        # Timing
        self.last_update = time.time()
        self.engine_start_time = 0.0
        self.ambient_temp = 20.0  # °C

        # Simulation parameters
        self.rpm_idle = self.config.get('rpm_idle', 750)
        self.rpm_max = self.config.get('rpm_max', 6500)
        self.fuel_capacity = self.config.get('fuel_capacity', 50)  # liters
        self.gear_ratio = 3.5  # Simplified - affects speed/RPM relationship

        # Previous state for derivative calculations
        self.prev_speed = 0.0
        self.prev_throttle = 0.0

    def _default_config(self) -> Dict:
        """Default vehicle configuration"""
        return {
            'rpm_idle': 750,
            'rpm_max': 6500,
            'coolant_temp_normal': 90,
            'fuel_capacity': 50,
            'make': 'Generic',
            'model': 'Vehicle',
            'year': 2020
        }

    def update(self, dt: Optional[float] = None):
        """
        Update vehicle state based on elapsed time

        Args:
            dt: Time delta in seconds (auto-calculated if None)
        """
        if dt is None:
            current_time = time.time()
            dt = current_time - self.last_update
            self.last_update = current_time

        # Update based on engine state
        if self.engine_state == EngineState.RUNNING:
            self._update_running_state(dt)
            self._update_readiness_monitors(dt)
        elif self.engine_state == EngineState.CRANKING:
            self._update_cranking_state(dt)
        elif self.engine_state == EngineState.OFF:
            self._update_off_state(dt)

    def _update_running_state(self, dt: float):
        """Update vehicle in running state"""
        # Update engine runtime
        self.sensors.engine_runtime += dt

        # Calculate target RPM based on throttle and load
        throttle_factor = self.sensors.throttle_position / 100.0
        target_rpm = self.rpm_idle + (self.rpm_max - self.rpm_idle) * throttle_factor

        # Smooth RPM changes (first-order lag)
        rpm_tau = 0.5  # Time constant
        self.sensors.rpm += (target_rpm - self.sensors.rpm) * (dt / rpm_tau)

        # Add realistic RPM variation
        self.sensors.rpm += random.gauss(0, 10)
        self.sensors.rpm = max(self.rpm_idle * 0.9, min(self.rpm_max, self.sensors.rpm))

        # Calculate engine load (simplified model)
        # Load depends on throttle, RPM, and speed
        base_load = throttle_factor * 100
        rpm_factor = (self.sensors.rpm - self.rpm_idle) / (self.rpm_max - self.rpm_idle)
        speed_factor = min(1.0, self.sensors.vehicle_speed / 120.0)
        self.sensors.engine_load = base_load * (0.5 + 0.5 * rpm_factor) * (0.7 + 0.3 * speed_factor)
        self.sensors.engine_load = max(0, min(100, self.sensors.engine_load))

        # Update speed based on RPM and gear ratio
        # Simplified: speed = RPM / gear_ratio / 60 (converts to km/h)
        if self.sensors.rpm > self.rpm_idle:
            target_speed = (self.sensors.rpm - self.rpm_idle) / self.gear_ratio / 60.0 * 10
            self.sensors.vehicle_speed += (target_speed - self.sensors.vehicle_speed) * (dt / 1.0)
        else:
            # Deceleration when not throttling
            self.sensors.vehicle_speed = max(0, self.sensors.vehicle_speed - 5 * dt)

        # Update distance traveled
        distance_km = self.sensors.vehicle_speed * (dt / 3600.0)  # Convert to km
        self.sensors.distance_traveled += distance_km
        self.sensors.distance_since_clear += distance_km
        if self.sensors.mil_status:
            self.sensors.distance_with_mil += distance_km

        # Update MAF (Mass Air Flow) based on RPM and load
        # Simplified: MAF ∝ RPM × Load
        self.sensors.maf = (self.sensors.rpm / 1000.0) * (self.sensors.engine_load / 100.0) * 5.0
        self.sensors.maf += random.gauss(0, 0.1)
        self.sensors.maf = max(0, self.sensors.maf)

        # Update coolant temperature (warmup simulation)
        target_temp = self.config.get('coolant_temp_normal', 90)
        if self.sensors.coolant_temp < target_temp:
            # Warmup - faster at high load
            warmup_rate = 2.0 + (self.sensors.engine_load / 100.0) * 3.0
            self.sensors.coolant_temp += warmup_rate * dt
        else:
            # Maintain operating temperature
            temp_variation = random.gauss(0, 0.5)
            self.sensors.coolant_temp = target_temp + temp_variation

        # Intake air temp follows ambient but increases with load
        intake_temp_rise = self.sensors.engine_load * 0.3
        self.sensors.intake_air_temp = self.ambient_temp + intake_temp_rise

        # Update timing advance based on RPM and load
        # Higher RPM and lower load = more advance
        rpm_advance = (self.sensors.rpm / self.rpm_max) * 30
        load_reduction = (100 - self.sensors.engine_load) / 100.0 * 10
        self.sensors.timing_advance = rpm_advance + load_reduction

        # Update fuel consumption
        # Consumption increases with load and RPM
        consumption_rate = self.sensors.engine_load * 0.01 + (self.sensors.rpm / 1000.0) * 0.05
        fuel_consumed_liters = consumption_rate * (dt / 3600.0)
        self.sensors.fuel_level -= (fuel_consumed_liters / self.fuel_capacity) * 100
        self.sensors.fuel_level = max(0, self.sensors.fuel_level)
        self.sensors.fuel_rate = consumption_rate

        # Update O2 sensor (lambda oscillation around stoichiometric)
        lambda_target = 0.45  # Stoichiometric
        oscillation = math.sin(self.sensors.engine_runtime * 2) * 0.05
        self.sensors.o2_voltage = lambda_target + oscillation

        # Update fuel trims based on load and O2
        # Simplified: trims compensate for lean/rich conditions
        if self.sensors.o2_voltage < 0.4:  # Lean
            self.sensors.short_term_fuel_trim = min(25, self.sensors.short_term_fuel_trim + dt * 2)
        elif self.sensors.o2_voltage > 0.5:  # Rich
            self.sensors.short_term_fuel_trim = max(-25, self.sensors.short_term_fuel_trim - dt * 2)

        # Long-term trim slowly follows short-term
        self.sensors.long_term_fuel_trim += (self.sensors.short_term_fuel_trim - self.sensors.long_term_fuel_trim) * dt * 0.1

        # Update catalyst temperature (follows coolant temp but higher)
        if self.sensors.coolant_temp > 70:
            target_catalyst_temp = 400 + self.sensors.engine_load * 2
            self.sensors.catalyst_temp += (target_catalyst_temp - self.sensors.catalyst_temp) * dt * 0.1

        # Update battery voltage (drops slightly under load)
        base_voltage = 14.2 if self.sensors.rpm > self.rpm_idle else 12.6
        load_drop = (self.sensors.engine_load / 100.0) * 0.3
        self.sensors.battery_voltage = base_voltage - load_drop

        # Track acceleration/deceleration for drive cycle
        speed_change = self.sensors.vehicle_speed - self.prev_speed
        if speed_change > 5:  # Accelerating
            self.drive_cycle.accel_count += 1
        elif speed_change < -5:  # Decelerating
            self.drive_cycle.decel_count += 1

        # Track idle vs cruise time
        if self.sensors.vehicle_speed < 5:
            self.drive_cycle.idle_time += dt
        elif 50 < self.sensors.vehicle_speed < 80:
            self.drive_cycle.cruise_time += dt

        # Store previous values
        self.prev_speed = self.sensors.vehicle_speed
        self.prev_throttle = self.sensors.throttle_position

    def _update_cranking_state(self, dt: float):
        """Update vehicle in cranking state"""
        # RPM builds up during cranking
        self.sensors.rpm = min(400, self.sensors.rpm + 200 * dt)

        # Transition to running after brief cranking
        if self.sensors.rpm >= 300:
            self.engine_state = EngineState.RUNNING
            self.sensors.rpm = self.rpm_idle
            self.engine_start_time = time.time()

            # Cold start detection
            if self.sensors.coolant_temp < 50:
                self.drive_cycle.cold_start_count += 1
                self.sensors.warmups_since_clear += 1

    def _update_off_state(self, dt: float):
        """Update vehicle in off state"""
        # Engine cools down slowly
        if self.sensors.coolant_temp > self.ambient_temp:
            cooldown_rate = 0.5  # °C per second
            self.sensors.coolant_temp = max(self.ambient_temp,
                                           self.sensors.coolant_temp - cooldown_rate * dt)

        # Everything else goes to zero
        self.sensors.rpm = 0
        self.sensors.vehicle_speed = 0
        self.sensors.engine_load = 0
        self.sensors.maf = 0
        self.sensors.fuel_rate = 0
        self.sensors.battery_voltage = 12.6
        self.sensors.engine_runtime = 0

    def _update_readiness_monitors(self, dt: float):
        """Update OBD-II readiness monitor completion status"""
        # Monitors complete after specific drive cycle requirements are met

        # Component monitor - completes quickly
        if self.sensors.engine_runtime > 10:
            self.drive_cycle.component_monitor_complete = True

        # Fuel system monitor - needs stable operation
        if self.sensors.engine_runtime > 30 and self.sensors.coolant_temp > 70:
            self.drive_cycle.fuel_system_monitor_complete = True

        # Misfire monitor - needs varied RPM
        if self.sensors.engine_runtime > 60:
            self.drive_cycle.misfire_monitor_complete = True

        # O2 sensor monitors - need operating temperature
        if self.sensors.coolant_temp > 80 and self.sensors.engine_runtime > 45:
            self.drive_cycle.oxygen_sensor_monitor_complete = True
            self.drive_cycle.oxygen_sensor_heater_complete = True

        # Catalyst monitor - needs prolonged operation at temp
        if self.sensors.catalyst_temp > 400 and self.drive_cycle.cruise_time > 120:
            self.drive_cycle.catalyst_monitor_complete = True
            self.drive_cycle.heated_catalyst_monitor_complete = True

        # EVAP monitor - needs specific drive pattern
        if self.drive_cycle.cruise_time > 60 and self.drive_cycle.idle_time > 30:
            self.drive_cycle.evap_system_monitor_complete = True

        # EGR monitor - needs highway driving
        if self.drive_cycle.cruise_time > 180:
            self.drive_cycle.egr_system_monitor_complete = True

    # Control methods

    def start_engine(self):
        """Start the engine"""
        if self.engine_state == EngineState.OFF:
            self.engine_state = EngineState.CRANKING
            self.sensors.rpm = 100

    def stop_engine(self):
        """Stop the engine"""
        self.engine_state = EngineState.OFF
        self.sensors.rpm = 0

    def set_throttle(self, position: float):
        """Set throttle position (0-100%)"""
        self.sensors.throttle_position = max(0, min(100, position))

    def set_speed(self, speed: float):
        """Directly set vehicle speed (for testing)"""
        self.sensors.vehicle_speed = max(0, speed)
        # Adjust RPM accordingly
        if speed > 0 and self.engine_state == EngineState.RUNNING:
            self.sensors.rpm = self.rpm_idle + speed * self.gear_ratio * 6

    def set_rpm(self, rpm: float):
        """Directly set engine RPM (for testing)"""
        self.sensors.rpm = max(0, min(self.rpm_max, rpm))

    def get_sensor_data(self) -> SensorData:
        """Get current sensor readings"""
        return self.sensors

    def get_drive_cycle(self) -> DriveCycle:
        """Get drive cycle status"""
        return self.drive_cycle

    def reset_drive_cycle(self):
        """Reset drive cycle monitors"""
        self.drive_cycle.reset()

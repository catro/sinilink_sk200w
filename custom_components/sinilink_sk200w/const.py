"""Constants for the Sinilink SK200W integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "sinilink_sk200w"
MANUFACTURER: Final = "Sinilink"
MODEL: Final = "XY-SK200W"

LOGGER = logging.getLogger(__package__)
PLATFORMS: Final = ["binary_sensor", "sensor", "switch"]

# Configuration / option keys
CONF_SLAVE: Final = "slave"

DEFAULT_PORT: Final = 1024
DEFAULT_SLAVE: Final = 1
DEFAULT_SCAN_INTERVAL: Final = 5
DEFAULT_TIMEOUT: Final = 3
DEFAULT_RETRIES: Final = 3

# Register scaling factors
VOLTAGE_SCALE: Final = 0.01  # 0.01 V per unit
CURRENT_SCALE: Final = 0.001  # 0.001 A per unit
POWER_SCALE: Final = 0.01  # 0.01 W per unit
TEMPERATURE_SCALE: Final = 0.1  # 0.1 °C per unit
CAPACITY_SCALE: Final = 0.001  # 0.001 Ah / Wh per unit

# Holding register addresses (Sinilink XY-SK family)
REG_VOLTAGE_SET: Final = 0x0000  # output voltage setpoint
REG_CURRENT_SET: Final = 0x0001  # output current setpoint
REG_VOLTAGE_OUT: Final = 0x0002  # measured output voltage
REG_CURRENT_OUT: Final = 0x0003  # measured output current
REG_POWER_OUT: Final = 0x0004  # measured output power
REG_VOLTAGE_IN: Final = 0x0005  # measured input voltage
REG_CAPACITY: Final = 0x0006  # battery capacity (32-bit, low word first)
REG_ENERGY: Final = 0x0008  # battery energy (32-bit, low word first)
REG_ON_HOURS: Final = 0x000A  # output on-time, hours
REG_ON_MINUTES: Final = 0x000B  # output on-time, minutes
REG_ON_SECONDS: Final = 0x000C  # output on-time, seconds
REG_TEMPERATURE: Final = 0x000D  # internal temperature (signed)
REG_TEMPERATURE_EXTERNAL: Final = 0x000E  # external temperature (signed)
REG_PROTECTION: Final = 0x0010  # latched protection cause
REG_REGULATION_MODE: Final = 0x0011  # CV/CC regulation mode
REG_OUTPUT_ENABLE: Final = 0x0012  # output enable flag
REG_TEMPERATURE_UNIT: Final = 0x0013  # temperature unit selection

# Single contiguous block read covering registers 0x0000-0x0012 (19 registers),
# matching the transaction used by the reference XY-series driver.
POLL_START: Final = REG_VOLTAGE_SET
POLL_COUNT: Final = REG_OUTPUT_ENABLE - REG_VOLTAGE_SET + 1

# Bit masks
MASK_OUTPUT_ENABLE: Final = 0x0001
MASK_CONSTANT_CURRENT: Final = 0x0001

# Sentinel raw values reported by the device when a temperature probe is not
# connected (e.g. raw 8888 -> 888.8 °C).  Reported as "unknown" instead.
TEMPERATURE_INVALID_SENTINELS: Final = frozenset({8888, -8888, 32767, -32768})

# Writable setpoint limits used by the number entities.  Adjust these to match
# your specific XY-SK model (the device clamps out-of-range values itself).
MAX_VOLTAGE_SET: Final = 60.0  # V
MAX_CURRENT_SET: Final = 20.0  # A

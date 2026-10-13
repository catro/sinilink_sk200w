"""Data update coordinator for the Sinilink SK200W integration."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import Any

from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CAPACITY_SCALE,
    CURRENT_SCALE,
    DOMAIN,
    LOGGER,
    MASK_CONSTANT_CURRENT,
    MASK_OUTPUT_ENABLE,
    POLL_COUNT,
    POLL_START,
    POWER_SCALE,
    REG_CAPACITY,
    REG_CURRENT_OUT,
    REG_CURRENT_SET,
    REG_ENERGY,
    REG_ON_HOURS,
    REG_ON_MINUTES,
    REG_ON_SECONDS,
    REG_OUTPUT_ENABLE,
    REG_POWER_OUT,
    REG_PROTECTION,
    REG_REGULATION_MODE,
    REG_TEMPERATURE,
    REG_TEMPERATURE_EXTERNAL,
    REG_VOLTAGE_IN,
    REG_VOLTAGE_OUT,
    REG_VOLTAGE_SET,
    TEMPERATURE_INVALID_SENTINELS,
    TEMPERATURE_SCALE,
    VOLTAGE_SCALE,
)
from .modbus_client import SinilinkModbusClient

# ``config_entry`` was added to ``DataUpdateCoordinator`` in newer Home Assistant
# releases.  Detect support so the integration also runs on older versions.
_SUPPORTS_CONFIG_ENTRY = (
    "config_entry" in inspect.signature(DataUpdateCoordinator.__init__).parameters
)


@dataclass(slots=True)
class SinilinkData:
    """Snapshot of all values read from the device."""

    voltage_set: float
    current_set: float
    voltage_out: float
    current_out: float
    power_out: float
    voltage_in: float
    capacity: float
    energy: float
    on_hours: int
    on_minutes: int
    on_seconds: int
    temperature: float | None
    temperature_external: float | None
    protection: int
    regulation_mode: int
    output_enable: int

    @property
    def output_on(self) -> bool:
        """Return True when the output is enabled."""
        return bool(self.output_enable & MASK_OUTPUT_ENABLE)

    @property
    def constant_current(self) -> bool:
        """Return True when the device regulates in constant-current mode."""
        return bool(self.regulation_mode & MASK_CONSTANT_CURRENT)

    @property
    def constant_voltage(self) -> bool:
        """Return True when the device regulates in constant-voltage mode."""
        return not self.constant_current

    @property
    def protection_active(self) -> bool:
        """Return True when a latched protection is active."""
        return self.protection != 0

    @property
    def on_time(self) -> str:
        """Return the output on-time formatted as HH:MM:SS."""
        return f"{self.on_hours:02d}:{self.on_minutes:02d}:{self.on_seconds:02d}"


class SinilinkDataUpdateCoordinator(DataUpdateCoordinator[SinilinkData]):
    """Coordinator polling the device over Modbus RTU over UDP."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SinilinkModbusClient,
        scan_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        self.client = client
        self.entry = entry
        self.scan_interval = timedelta(seconds=scan_interval)
        self._polling_enabled = True

        kwargs: dict[str, Any] = {}
        if _SUPPORTS_CONFIG_ENTRY:
            kwargs["config_entry"] = entry

        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}-{entry.title}",
            update_interval=self.scan_interval,
            **kwargs,
        )

    @property
    def polling_enabled(self) -> bool:
        """Return True when periodic polling is enabled."""
        return self._polling_enabled

    async def async_set_polling(self, enable: bool) -> None:
        """Enable or disable periodic polling of the device.

        When disabled the coordinator stops issuing Modbus requests entirely,
        the last known values are kept and no further updates are performed.
        """
        self._polling_enabled = enable
        self.update_interval = self.scan_interval if enable else None
        self.async_update_listeners()
        if enable and self.data is not None:
            await self.async_request_refresh()

    async def async_write_setpoint(
        self, *, voltage: float | None = None, current: float | None = None
    ) -> None:
        """Write the voltage and/or current setpoint(s) to the device.

        The values are converted to raw register units.  After a successful
        write the cached data is updated optimistically so the number entities
        reflect the new setpoint immediately; the next poll reconciles it.
        """
        if voltage is not None:
            await self.client.async_write_register(
                REG_VOLTAGE_SET, round(voltage / VOLTAGE_SCALE)
            )
        if current is not None:
            await self.client.async_write_register(
                REG_CURRENT_SET, round(current / CURRENT_SCALE)
            )

        if self.data is not None:
            self.async_set_updated_data(
                replace(
                    self.data,
                    voltage_set=(voltage if voltage is not None else self.data.voltage_set),
                    current_set=(current if current is not None else self.data.current_set),
                )
            )

    async def _async_update_data(self) -> SinilinkData:
        """Fetch the latest values from the device."""
        if not self._polling_enabled and self.data is not None:
            return self.data

        try:
            registers = await self.client.async_read_holding_registers(
                POLL_START, POLL_COUNT
            )
        except (ModbusException, OSError) as err:
            msg = f"Error communicating with Sinilink SK200W: {err}"
            raise UpdateFailed(msg) from err

        if len(registers) < POLL_COUNT:
            msg = (
                f"Incomplete response from device: got {len(registers)} "
                f"registers, expected {POLL_COUNT}"
            )
            raise UpdateFailed(msg)

        return self._parse(registers)

    @staticmethod
    def _parse(registers: list[int]) -> SinilinkData:
        """Convert a raw register block into a :class:`SinilinkData`."""

        def reg(address: int) -> int:
            return registers[address - POLL_START]

        def s16(value: int) -> int:
            return value - 0x10000 if value >= 0x8000 else value

        def u32(address: int) -> int:
            # 32-bit values are stored low word first (ESPHome U_DWORD_R).
            return reg(address) | (reg(address + 1) << 16)

        def temp(address: int) -> float | None:
            raw = s16(reg(address))
            if raw in TEMPERATURE_INVALID_SENTINELS:
                return None
            return raw * TEMPERATURE_SCALE

        return SinilinkData(
            voltage_set=reg(REG_VOLTAGE_SET) * VOLTAGE_SCALE,
            current_set=reg(REG_CURRENT_SET) * CURRENT_SCALE,
            voltage_out=reg(REG_VOLTAGE_OUT) * VOLTAGE_SCALE,
            current_out=reg(REG_CURRENT_OUT) * CURRENT_SCALE,
            power_out=reg(REG_POWER_OUT) * POWER_SCALE,
            voltage_in=reg(REG_VOLTAGE_IN) * VOLTAGE_SCALE,
            capacity=u32(REG_CAPACITY) * CAPACITY_SCALE,
            energy=u32(REG_ENERGY) * CAPACITY_SCALE,
            on_hours=reg(REG_ON_HOURS),
            on_minutes=reg(REG_ON_MINUTES),
            on_seconds=reg(REG_ON_SECONDS),
            temperature=temp(REG_TEMPERATURE),
            temperature_external=temp(REG_TEMPERATURE_EXTERNAL),
            protection=reg(REG_PROTECTION),
            regulation_mode=reg(REG_REGULATION_MODE),
            output_enable=reg(REG_OUTPUT_ENABLE),
        )

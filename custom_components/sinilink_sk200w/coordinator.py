"""Data update coordinator for the Sinilink SK200W integration."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import Any, Final

from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CAPACITY_SCALE,
    CURRENT_SCALE,
    DOMAIN,
    ENERGY_LIMIT_SCALE,
    LOGGER,
    MASK_CONSTANT_CURRENT,
    MASK_OUTPUT_ENABLE,
    PARAM_COUNT,
    PARAM_START,
    POLL_COUNT,
    POLL_START,
    POWER_PROTECTION_SCALE,
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
    REG_S_ETP,
    REG_S_INI,
    REG_S_LVP,
    REG_S_OAH_H,
    REG_S_OAH_L,
    REG_S_OCP,
    REG_S_OHP_H,
    REG_S_OHP_M,
    REG_S_OPP,
    REG_S_OTP,
    REG_S_OVP,
    REG_S_OWH_H,
    REG_S_OWH_L,
    REG_TEMPERATURE,
    REG_TEMPERATURE_EXTERNAL,
    REG_VOLTAGE_IN,
    REG_VOLTAGE_OUT,
    REG_VOLTAGE_SET,
    TEMPERATURE_INVALID_SENTINELS,
    TEMPERATURE_LIMIT_SCALE,
    TEMPERATURE_SCALE,
    VOLTAGE_SCALE,
)
from .modbus_client import SinilinkModbusClient

# ``config_entry`` was added to ``DataUpdateCoordinator`` in newer Home Assistant
# releases.  Detect support so the integration also runs on older versions.
_SUPPORTS_CONFIG_ENTRY = (
    "config_entry" in inspect.signature(DataUpdateCoordinator.__init__).parameters
)

_PARAM_FIELDS: Final = (
    "undervoltage_protection",
    "overvoltage_protection",
    "overcurrent_protection",
    "overpower_protection",
    "time_limit_minutes",
    "capacity_limit",
    "energy_limit",
    "overtemp_protection",
    "probe_overtemp_protection",
    "power_on_output",
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

    # Protections / limits (M0 parameter set); None when not available.
    undervoltage_protection: float | None = None
    overvoltage_protection: float | None = None
    overcurrent_protection: float | None = None
    overpower_protection: float | None = None
    time_limit_minutes: float | None = None
    capacity_limit: float | None = None
    energy_limit: float | None = None
    overtemp_protection: float | None = None
    probe_overtemp_protection: float | None = None
    power_on_output: bool | None = None

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
        self._optional_read_failed: set[int] = set()

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

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a single holding register on the device."""
        await self.client.async_write_register(address, value)

    @callback
    def async_update_field(self, field: str, value: Any) -> None:
        """Optimistically update a single cached field after a write."""
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, **{field: value}))

    async def async_set_output(self, enable: bool) -> None:
        """Enable or disable the power supply output.

        A latched protection must be cleared before the output can be enabled
        again, so write ``0`` to ``PROTECT`` (0x0010) first when switching on.
        """
        if enable:
            await self.client.async_write_register(REG_PROTECTION, 0)
        await self.client.async_write_register(
            REG_OUTPUT_ENABLE, MASK_OUTPUT_ENABLE if enable else 0
        )

        if self.data is not None:
            self.async_set_updated_data(
                replace(
                    self.data,
                    output_enable=MASK_OUTPUT_ENABLE if enable else 0,
                    protection=0 if enable else self.data.protection,
                )
            )

    async def async_write_setpoint(
        self, *, voltage: float | None = None, current: float | None = None
    ) -> None:
        """Write the voltage and/or current setpoint(s) to the device.

        The values are converted to raw register units.  After a successful
        write the cached data is updated optimistically so the number entities
        reflect the new setpoint immediately; the next poll reconciles it.
        """
        if (
            voltage is not None
            and self.data is not None
            and self.data.overvoltage_protection is not None
            and voltage > self.data.overvoltage_protection
        ):
            # Writing a setpoint above S-OVP makes the device latch an OVP trip.
            LOGGER.warning(
                "Requested voltage %.2f V is above the over-voltage protection "
                "threshold of %.2f V; the device may latch an OVP protection",
                voltage,
                self.data.overvoltage_protection,
            )

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

        if len(registers) != POLL_COUNT:
            msg = (
                f"Incomplete response from device: got {len(registers)} "
                f"registers, expected {POLL_COUNT}"
            )
            raise UpdateFailed(msg)

        data = self._parse(registers)

        # The parameter block is not present on every model, so a failed read
        # there must not fail the whole update cycle.
        params = await self._async_read_optional(PARAM_START, PARAM_COUNT)
        if params is not None:
            data = replace(data, **self._parse_params(params))
        elif self.data is not None:
            data = replace(data, **self._carry(self.data, _PARAM_FIELDS))

        return data

    async def _async_read_optional(self, address: int, count: int) -> list[int] | None:
        """Read a register block that may not exist on this model."""
        try:
            registers = await self.client.async_read_holding_registers(address, count)
        except (ModbusException, OSError) as err:
            if address not in self._optional_read_failed:
                self._optional_read_failed.add(address)
                LOGGER.warning(
                    "Register block 0x%04X is not available on this device (%s); "
                    "entities using it will show no value",
                    address,
                    err,
                )
            else:
                LOGGER.debug("Optional read at 0x%04X failed: %s", address, err)
            return None
        # An exact length is required: RTU over UDP has no transaction id, so a
        # mismatched reply must never be accepted as if it were ours.
        if len(registers) != count:
            LOGGER.debug(
                "Ignoring reply with %d registers for block 0x%04X (%d expected)",
                len(registers),
                address,
                count,
            )
            return None
        return registers

    @staticmethod
    def _carry(previous: SinilinkData, fields: tuple[str, ...]) -> dict[str, Any]:
        """Return the previous values for the given cached fields."""
        return {field: getattr(previous, field) for field in fields}

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

    @staticmethod
    def _parse_params(registers: list[int]) -> dict[str, Any]:
        """Parse the M0 parameter block (0x0052-0x005E)."""

        def reg(address: int) -> int:
            return registers[address - PARAM_START]

        def u32(low: int) -> int:
            # 32-bit values are stored low word first.
            return reg(low) | (reg(low + 1) << 16)

        return {
            "undervoltage_protection": reg(REG_S_LVP) * VOLTAGE_SCALE,
            "overvoltage_protection": reg(REG_S_OVP) * VOLTAGE_SCALE,
            "overcurrent_protection": reg(REG_S_OCP) * CURRENT_SCALE,
            "overpower_protection": reg(REG_S_OPP) * POWER_PROTECTION_SCALE,
            "time_limit_minutes": float(
                reg(REG_S_OHP_H) * 60 + reg(REG_S_OHP_M)
            ),
            "capacity_limit": u32(REG_S_OAH_L) * CAPACITY_SCALE,
            "energy_limit": u32(REG_S_OWH_L) * ENERGY_LIMIT_SCALE,
            "overtemp_protection": reg(REG_S_OTP) * TEMPERATURE_LIMIT_SCALE,
            "probe_overtemp_protection": reg(REG_S_ETP) * TEMPERATURE_LIMIT_SCALE,
            "power_on_output": bool(reg(REG_S_INI)),
        }

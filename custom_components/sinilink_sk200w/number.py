"""Number platform for the Sinilink SK200W integration.

Exposes the writable output setpoints, protection thresholds and battery
charging parameters of the device.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SinilinkConfigEntry, get_coordinator
from .const import (
    CAPACITY_SCALE,
    CURRENT_SCALE,
    ENERGY_LIMIT_SCALE,
    MAX_CAPACITY_LIMIT,
    MAX_CURRENT_SET,
    MAX_ENERGY_LIMIT,
    MAX_POWER_SET,
    MAX_TEMPERATURE_LIMIT,
    MAX_TIME_LIMIT,
    MAX_VOLTAGE_SET,
    POWER_PROTECTION_SCALE,
    REG_CURRENT_SET,
    REG_S_ETP,
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
    REG_VOLTAGE_SET,
    TEMPERATURE_LIMIT_SCALE,
    VOLTAGE_SCALE,
)
from .coordinator import SinilinkData, SinilinkDataUpdateCoordinator
from .entity import SinilinkEntity


@dataclass(frozen=True, kw_only=True)
class SinilinkNumberEntityDescription(NumberEntityDescription):
    """Describes a writable Sinilink SK200W value."""

    value_fn: Callable[[SinilinkData], float | None]
    decimals: int
    field: str
    scale: float = 1.0
    register: int | None = None
    high_register: int | None = None
    is_time_minutes: bool = False
    is_setpoint: bool = False


NUMBER_DESCRIPTIONS: tuple[SinilinkNumberEntityDescription, ...] = (
    SinilinkNumberEntityDescription(
        key="voltage_set",
        device_class=NumberDeviceClass.VOLTAGE,
        native_unit_of_measurement="V",
        native_min_value=0.0,
        native_max_value=MAX_VOLTAGE_SET,
        native_step=VOLTAGE_SCALE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:tune-vertical",
        value_fn=lambda data: data.voltage_set,
        decimals=2,
        field="voltage_set",
        scale=VOLTAGE_SCALE,
        register=REG_VOLTAGE_SET,
        is_setpoint=True,
    ),
    SinilinkNumberEntityDescription(
        key="current_set",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement="A",
        native_min_value=0.0,
        native_max_value=MAX_CURRENT_SET,
        native_step=CURRENT_SCALE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:tune-vertical",
        value_fn=lambda data: data.current_set,
        decimals=3,
        field="current_set",
        scale=CURRENT_SCALE,
        register=REG_CURRENT_SET,
        is_setpoint=True,
    ),
    # --- protection thresholds -------------------------------------------
    SinilinkNumberEntityDescription(
        key="undervoltage_protection",
        device_class=NumberDeviceClass.VOLTAGE,
        native_unit_of_measurement="V",
        native_min_value=0.0,
        native_max_value=MAX_VOLTAGE_SET,
        native_step=VOLTAGE_SCALE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:arrow-collapse-down",
        value_fn=lambda data: data.undervoltage_protection,
        decimals=2,
        field="undervoltage_protection",
        scale=VOLTAGE_SCALE,
        register=REG_S_LVP,
    ),
    SinilinkNumberEntityDescription(
        key="overvoltage_protection",
        device_class=NumberDeviceClass.VOLTAGE,
        native_unit_of_measurement="V",
        native_min_value=0.0,
        native_max_value=MAX_VOLTAGE_SET,
        native_step=VOLTAGE_SCALE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:arrow-collapse-up",
        value_fn=lambda data: data.overvoltage_protection,
        decimals=2,
        field="overvoltage_protection",
        scale=VOLTAGE_SCALE,
        register=REG_S_OVP,
    ),
    SinilinkNumberEntityDescription(
        key="overcurrent_protection",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement="A",
        native_min_value=0.0,
        native_max_value=MAX_CURRENT_SET,
        native_step=CURRENT_SCALE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:current-dc",
        value_fn=lambda data: data.overcurrent_protection,
        decimals=3,
        field="overcurrent_protection",
        scale=CURRENT_SCALE,
        register=REG_S_OCP,
    ),
    SinilinkNumberEntityDescription(
        key="max_power",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement="W",
        native_min_value=0.0,
        native_max_value=MAX_POWER_SET,
        native_step=POWER_PROTECTION_SCALE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:flash-alert",
        value_fn=lambda data: data.overpower_protection,
        decimals=1,
        field="overpower_protection",
        scale=POWER_PROTECTION_SCALE,
        register=REG_S_OPP,
    ),
    SinilinkNumberEntityDescription(
        key="max_time",
        native_unit_of_measurement="min",
        native_min_value=0.0,
        native_max_value=MAX_TIME_LIMIT,
        native_step=1.0,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:timer-outline",
        value_fn=lambda data: data.time_limit_minutes,
        decimals=0,
        field="time_limit_minutes",
        register=REG_S_OHP_H,
        is_time_minutes=True,
    ),
    SinilinkNumberEntityDescription(
        key="max_capacity",
        native_unit_of_measurement="Ah",
        native_min_value=0.0,
        native_max_value=MAX_CAPACITY_LIMIT,
        native_step=0.001,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:battery-charging",
        value_fn=lambda data: data.capacity_limit,
        decimals=3,
        field="capacity_limit",
        scale=CAPACITY_SCALE,
        register=REG_S_OAH_L,
        high_register=REG_S_OAH_H,
    ),
    SinilinkNumberEntityDescription(
        key="max_energy",
        native_unit_of_measurement="Wh",
        native_min_value=0.0,
        native_max_value=MAX_ENERGY_LIMIT,
        native_step=1.0,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:battery-heart-variant",
        value_fn=lambda data: data.energy_limit,
        decimals=2,
        field="energy_limit",
        scale=ENERGY_LIMIT_SCALE,
        register=REG_S_OWH_L,
        high_register=REG_S_OWH_H,
    ),
    SinilinkNumberEntityDescription(
        key="overtemp_protection",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        native_min_value=0.0,
        native_max_value=MAX_TEMPERATURE_LIMIT,
        native_step=1.0,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:thermometer-alert",
        value_fn=lambda data: data.overtemp_protection,
        decimals=0,
        field="overtemp_protection",
        scale=TEMPERATURE_LIMIT_SCALE,
        register=REG_S_OTP,
    ),
    SinilinkNumberEntityDescription(
        key="probe_overtemp_protection",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        native_min_value=0.0,
        native_max_value=MAX_TEMPERATURE_LIMIT,
        native_step=1.0,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:thermometer-probe",
        value_fn=lambda data: data.probe_overtemp_protection,
        decimals=0,
        field="probe_overtemp_protection",
        scale=TEMPERATURE_LIMIT_SCALE,
        register=REG_S_ETP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SinilinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the numbers."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities(
        SinilinkNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS
    )


class SinilinkNumber(SinilinkEntity, NumberEntity):
    """A writable setpoint of the power supply."""

    entity_description: SinilinkNumberEntityDescription

    def __init__(
        self,
        coordinator: SinilinkDataUpdateCoordinator,
        description: SinilinkNumberEntityDescription,
    ) -> None:
        """Initialise the number."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.key

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        data: SinilinkData | None = self.coordinator.data
        if data is None:
            return None
        value = self.entity_description.value_fn(data)
        if value is None:
            return None
        return round(value, self.entity_description.decimals)

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value to the device."""
        desc = self.entity_description

        if desc.is_setpoint:
            if desc.field == "voltage_set":
                await self.coordinator.async_write_setpoint(voltage=value)
            else:
                await self.coordinator.async_write_setpoint(current=value)
            return

        if desc.is_time_minutes:
            total = int(round(value))
            await self.coordinator.async_write_register(REG_S_OHP_H, total // 60)
            await self.coordinator.async_write_register(REG_S_OHP_M, total % 60)
        elif desc.register is not None and desc.high_register is not None:
            raw = round(value / desc.scale)
            await self.coordinator.async_write_register(
                desc.register, raw & 0xFFFF
            )
            await self.coordinator.async_write_register(
                desc.high_register, (raw >> 16) & 0xFFFF
            )
        elif desc.register is not None:
            await self.coordinator.async_write_register(
                desc.register, round(value / desc.scale)
            )

        self.coordinator.async_update_field(desc.field, value)

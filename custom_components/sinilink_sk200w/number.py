"""Number platform for the Sinilink SK200W integration.

Exposes the writable output voltage and current setpoints.
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

from . import SinilinkConfigEntry
from .const import (
    CURRENT_SCALE,
    MAX_CURRENT_SET,
    MAX_VOLTAGE_SET,
    VOLTAGE_SCALE,
)
from .coordinator import SinilinkData, SinilinkDataUpdateCoordinator
from .entity import SinilinkEntity


@dataclass(frozen=True, kw_only=True)
class SinilinkNumberEntityDescription(NumberEntityDescription):
    """Describes a writable Sinilink SK200W setpoint."""

    value_fn: Callable[[SinilinkData], float]
    decimals: int
    is_voltage: bool


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
        is_voltage=True,
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
        is_voltage=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SinilinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the numbers."""
    coordinator = entry.runtime_data
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
        """Return the current setpoint."""
        data: SinilinkData | None = self.coordinator.data
        if data is None:
            return None
        return round(
            self.entity_description.value_fn(data), self.entity_description.decimals
        )

    async def async_set_native_value(self, value: float) -> None:
        """Write a new setpoint to the device."""
        if self.entity_description.is_voltage:
            await self.coordinator.async_write_setpoint(voltage=value)
        else:
            await self.coordinator.async_write_setpoint(current=value)

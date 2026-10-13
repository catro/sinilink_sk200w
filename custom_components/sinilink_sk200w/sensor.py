"""Sensor platform for the Sinilink SK200W integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SinilinkConfigEntry
from .coordinator import SinilinkData, SinilinkDataUpdateCoordinator
from .entity import SinilinkEntity


@dataclass(frozen=True, kw_only=True)
class SinilinkSensorEntityDescription(SensorEntityDescription):
    """Describes a Sinilink SK200W sensor."""

    value_fn: Callable[[SinilinkData], float | int | None]


SENSOR_DESCRIPTIONS: tuple[SinilinkSensorEntityDescription, ...] = (
    SinilinkSensorEntityDescription(
        key="voltage_out",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:sine-wave",
        value_fn=lambda data: data.voltage_out,
    ),
    SinilinkSensorEntityDescription(
        key="current_out",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement="A",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:current-dc",
        value_fn=lambda data: data.current_out,
    ),
    SinilinkSensorEntityDescription(
        key="power_out",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement="W",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:flash",
        value_fn=lambda data: data.power_out,
    ),
    SinilinkSensorEntityDescription(
        key="voltage_in",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:transmission-tower",
        value_fn=lambda data: data.voltage_in,
    ),
    SinilinkSensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer",
        value_fn=lambda data: data.temperature,
    ),
    SinilinkSensorEntityDescription(
        key="temperature_external",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        value_fn=lambda data: data.temperature_external,
    ),
    SinilinkSensorEntityDescription(
        key="capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:battery-medium",
        value_fn=lambda data: data.capacity,
    ),
    SinilinkSensorEntityDescription(
        key="energy",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement="Wh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:battery-charging",
        value_fn=lambda data: data.energy,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SinilinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SinilinkSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class SinilinkSensor(SinilinkEntity, SensorEntity):
    """A sensor exposing a numeric value of the power supply."""

    entity_description: SinilinkSensorEntityDescription

    def __init__(
        self,
        coordinator: SinilinkDataUpdateCoordinator,
        description: SinilinkSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.key

    @property
    def native_value(self) -> float | int | None:
        """Return the current value."""
        data: SinilinkData | None = self.coordinator.data
        if data is None:
            return None
        return self.entity_description.value_fn(data)

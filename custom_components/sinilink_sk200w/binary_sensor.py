"""Binary sensor platform for the Sinilink SK200W integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SinilinkConfigEntry, get_coordinator
from .coordinator import SinilinkData, SinilinkDataUpdateCoordinator
from .entity import SinilinkEntity

# Keys map to translation keys under ``entity.binary_sensor``.
BINARY_SENSOR_KEYS: tuple[str, ...] = (
    "output",
    "constant_current",
    "constant_voltage",
    "protection",
    "connectivity",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SinilinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities(
        SinilinkBinarySensor(coordinator, key) for key in BINARY_SENSOR_KEYS
    )


class SinilinkBinarySensor(SinilinkEntity, BinarySensorEntity):
    """A binary sensor exposing a boolean state of the power supply."""

    def __init__(self, coordinator: SinilinkDataUpdateCoordinator, key: str) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, key)
        self._key = key
        self._attr_translation_key = key

        match key:
            case "output":
                self._attr_device_class = BinarySensorDeviceClass.POWER
                self._attr_icon = "mdi:power"
            case "constant_current":
                self._attr_icon = "mdi:current-dc"
            case "constant_voltage":
                self._attr_icon = "mdi:sine-wave"
            case "protection":
                self._attr_device_class = BinarySensorDeviceClass.PROBLEM
                self._attr_icon = "mdi:alert-outline"
            case "connectivity":
                self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def available(self) -> bool:
        """Return True if the entity is available.

        The connectivity sensor stays available even when the device cannot be
        reached, so that it can report the loss of communication.
        """
        if self._key == "connectivity":
            return True
        return super().available

    @property
    def is_on(self) -> bool:
        """Return the binary state."""
        if self._key == "connectivity":
            return self.coordinator.last_update_success

        data: SinilinkData | None = self.coordinator.data
        if data is None:
            return False

        match self._key:
            case "output":
                return data.output_on
            case "constant_current":
                return data.constant_current
            case "constant_voltage":
                return data.constant_voltage
            case "protection":
                return data.protection_active
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose all measured values as attributes on the output sensor."""
        if self._key != "output":
            return None

        data: SinilinkData | None = self.coordinator.data
        if data is None:
            return None

        return {
            "voltage_set": data.voltage_set,
            "current_set": data.current_set,
            "voltage_out": data.voltage_out,
            "current_out": data.current_out,
            "power_out": data.power_out,
            "voltage_in": data.voltage_in,
            "capacity": data.capacity,
            "energy": data.energy,
            "on_time": data.on_time,
            "temperature": data.temperature,
            "temperature_external": data.temperature_external,
            "protection_code": data.protection,
            "regulation_mode": data.regulation_mode,
        }

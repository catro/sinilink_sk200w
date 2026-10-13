"""Switch platform for the Sinilink SK200W integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SinilinkConfigEntry, get_coordinator
from .coordinator import SinilinkDataUpdateCoordinator
from .entity import SinilinkEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SinilinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities([SinilinkPollingSwitch(coordinator)])


class SinilinkPollingSwitch(SinilinkEntity, SwitchEntity):
    """Switch used to start or stop the periodic Modbus updates."""

    _attr_translation_key = "update"
    _attr_icon = "mdi:sync"

    def __init__(self, coordinator: SinilinkDataUpdateCoordinator) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, "update")

    @property
    def is_on(self) -> bool:
        """Return True while periodic Modbus updates are running."""
        return self.coordinator.polling_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start polling the device."""
        await self.coordinator.async_set_polling(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop polling the device."""
        await self.coordinator.async_set_polling(False)

"""Base entity for the Sinilink SK200W integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SinilinkDataUpdateCoordinator


class SinilinkEntity(CoordinatorEntity[SinilinkDataUpdateCoordinator]):
    """Base class for Sinilink SK200W entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SinilinkDataUpdateCoordinator, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        host = entry.data[CONF_HOST]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
            configuration_url=f"http://{host}",
        )

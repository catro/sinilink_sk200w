"""Switch platform for the Sinilink SK200W integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SinilinkConfigEntry, get_coordinator
from .const import REG_S_INI
from .coordinator import SinilinkData, SinilinkDataUpdateCoordinator
from .entity import SinilinkEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SinilinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities(
        [
            SinilinkOutputSwitch(coordinator),
            SinilinkParameterSwitch(
                coordinator,
                "power_on_output",
                REG_S_INI,
                "power_on_output",
                "mdi:restart",
            ),
            SinilinkPollingSwitch(coordinator),
        ]
    )


class SinilinkOutputSwitch(SinilinkEntity, SwitchEntity):
    """Switch controlling the power supply output (register 0x0012)."""

    _attr_translation_key = "output"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: SinilinkDataUpdateCoordinator) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, "output")

    @property
    def is_on(self) -> bool:
        """Return True when the output is enabled."""
        data: SinilinkData | None = self.coordinator.data
        return bool(data.output_on) if data is not None else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the output (a latched protection is cleared first)."""
        await self.coordinator.async_set_output(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the output."""
        await self.coordinator.async_set_output(False)


class SinilinkParameterSwitch(SinilinkEntity, SwitchEntity):
    """Switch backed by a single 0/1 register."""

    def __init__(
        self,
        coordinator: SinilinkDataUpdateCoordinator,
        key: str,
        register: int,
        field: str,
        icon: str,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._attr_icon = icon
        self._register = register
        self._field = field

    @property
    def is_on(self) -> bool | None:
        """Return the current state, or None when not available."""
        data: SinilinkData | None = self.coordinator.data
        if data is None:
            return None
        return getattr(data, self._field)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the setting on."""
        await self._async_write(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the setting off."""
        await self._async_write(0)

    async def _async_write(self, value: int) -> None:
        """Write the raw value and update the cached state."""
        await self.coordinator.async_write_register(self._register, value)
        self.coordinator.async_update_field(self._field, bool(value))


class SinilinkPollingSwitch(SinilinkEntity, SwitchEntity):
    """Switch used to start or stop the periodic Modbus updates."""

    _available_when_polling_disabled = True
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

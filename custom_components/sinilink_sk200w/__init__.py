"""The Sinilink SK200W integration."""

from __future__ import annotations

from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_RETRIES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_TIMEOUT,
)
from .coordinator import SinilinkDataUpdateCoordinator
from .modbus_client import SinilinkModbusClient

type SinilinkConfigEntry = ConfigEntry[SinilinkDataUpdateCoordinator]

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: SinilinkConfigEntry) -> bool:
    """Set up Sinilink SK200W from a config entry."""
    client = SinilinkModbusClient(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        slave=entry.data.get(CONF_SLAVE, DEFAULT_SLAVE),
        timeout=DEFAULT_TIMEOUT,
        retries=DEFAULT_RETRIES,
    )

    try:
        await client.async_connect()
    except (ModbusException, OSError) as err:
        client.close()
        raise ConfigEntryNotReady(
            f"Unable to connect to {entry.data[CONF_HOST]}:"
            f"{entry.data.get(CONF_PORT, DEFAULT_PORT)}: {err}"
        ) from err

    coordinator = SinilinkDataUpdateCoordinator(
        hass,
        entry,
        client,
        scan_interval=entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SinilinkConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.client.close()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: SinilinkConfigEntry
) -> None:
    """Handle options update by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)

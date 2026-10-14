"""Config flow for the Sinilink SK200W integration."""

from __future__ import annotations

from typing import Any

from pymodbus.exceptions import ModbusException
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_RETRIES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MODEL,
    REG_VOLTAGE_OUT,
)
from .modbus_client import SinilinkModbusClient

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=3600)
        ),
    }
)


class SinilinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sinilink SK200W."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:"
                f"{user_input[CONF_SLAVE]}"
            )
            self._abort_if_unique_id_configured()

            try:
                await self._async_test_connection(user_input)
            except ModbusException:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - guard against any transport error
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=MODEL, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def _async_test_connection(self, data: dict[str, Any]) -> None:
        """Verify the device is reachable and answers a Modbus request."""
        client = SinilinkModbusClient(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            slave=data[CONF_SLAVE],
            timeout=DEFAULT_TIMEOUT,
            retries=DEFAULT_RETRIES,
        )
        try:
            await client.async_connect()
            await client.async_read_holding_registers(REG_VOLTAGE_OUT, 1)
        finally:
            client.close()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SinilinkOptionsFlow:
        """Return the options flow."""
        return SinilinkOptionsFlow(config_entry)


class SinilinkOptionsFlow(OptionsFlow):
    """Handle options for Sinilink SK200W."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise the options flow.

        The config entry is passed in explicitly rather than relying on the
        ``OptionsFlow.config_entry`` attribute/property, whose behaviour and
        availability differ between Home Assistant versions.
        """
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        entry = self._entry
        current = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
                }
            ),
        )

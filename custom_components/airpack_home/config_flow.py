"""Config flow for AirPack Home."""
from __future__ import annotations

import logging
from typing import Any

import serial.tools.list_ports
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import usb
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_BAUDRATE, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_SLAVE, DOMAIN
from .modbus_client import get_serial_by_id

_LOGGER = logging.getLogger(__name__)


class AirPackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AirPack Home."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._discovered_device: str | None = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Resolve stable path if possible
            user_input["port"] = await self.hass.async_add_executor_job(
                get_serial_by_id, user_input["port"]
            )
            
            # Try to connect
            from .modbus_client import AirPackModbusClient

            def try_connect():
                client = AirPackModbusClient(
                    port=user_input["port"],
                    slave=user_input["slave"],
                    baudrate=user_input["baudrate"],
                )
                if client.connect():
                    fw = client.get_firmware_version()
                    model = client.get_device_name()
                    client.close()
                    return fw, model
                client.close()
                return None, None

            fw, model = await self.hass.async_add_executor_job(try_connect)
            if fw is None:
                errors["base"] = "cannot_connect"
            else:
                # Use model name in title if possible
                title = f"AirPack {model}" if model else f"AirPack Home ({user_input['port']})"
                
                # Unique ID: use port and slave to allow multiple devices
                # but use the stable port path
                await self.async_set_unique_id(f"{user_input['port']}_{user_input['slave']}")
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        # List available serial ports
        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        list_of_ports = {port.device: f"{port.device} ({port.description})" for port in ports}
        
        if not list_of_ports:
            # Fallback to manual entry if no ports found
            data_schema = vol.Schema(
                {
                    vol.Required("port", default=DEFAULT_PORT): str,
                    vol.Required("slave", default=DEFAULT_SLAVE): vol.All(int, vol.Range(min=1, max=247)),
                    vol.Required("baudrate", default=DEFAULT_BAUDRATE): vol.In([4800, 9600, 19200, 38400, 57600, 115200]),
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required("port"): vol.In(list_of_ports),
                    vol.Required("slave", default=DEFAULT_SLAVE): vol.All(int, vol.Range(min=1, max=247)),
                    vol.Required("baudrate", default=DEFAULT_BAUDRATE): vol.In([4800, 9600, 19200, 38400, 57600, 115200]),
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_usb(self, discovery_info: usb.UsbServiceInfo) -> FlowResult:
        """Handle USB discovery."""
        device = discovery_info.device
        _LOGGER.debug("Discovered USB device: %s", device)
        
        # Resolve stable path
        stable_path = await self.hass.async_add_executor_job(get_serial_by_id, device)
        
        await self.async_set_unique_id(f"airpack_usb_{discovery_info.vid}_{discovery_info.pid}_{discovery_info.serial_number}")
        self._abort_if_unique_id_configured()
        
        self._discovered_device = stable_path
        self.context["title_placeholders"] = {"name": f"AirPack USB ({stable_path})"}
        
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm discovery."""
        errors = {}
        if user_input is not None:
            user_input["port"] = self._discovered_device
            
            # Try to connect
            from .modbus_client import AirPackModbusClient
            def try_connect():
                client = AirPackModbusClient(
                    port=user_input["port"],
                    slave=user_input["slave"],
                    baudrate=user_input["baudrate"],
                )
                if client.connect():
                    fw = client.get_firmware_version()
                    model = client.get_device_name()
                    client.close()
                    return fw, model
                client.close()
                return None, None

            fw, model = await self.hass.async_add_executor_job(try_connect)
            if fw is None:
                errors["base"] = "cannot_connect"
            else:
                title = f"AirPack {model}" if model else f"AirPack Home ({user_input['port']})"
                await self.async_set_unique_id(f"{user_input['port']}_{user_input['slave']}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({
                vol.Required("slave", default=DEFAULT_SLAVE): vol.All(int, vol.Range(min=1, max=247)),
                vol.Required("baudrate", default=DEFAULT_BAUDRATE): vol.In([4800, 9600, 19200, 38400, 57600, 115200]),
            }),
            errors=errors,
            description_placeholders={"device": self._discovered_device}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AirPackOptionsFlow(config_entry)


class AirPackOptionsFlow(config_entries.OptionsFlow):
    """Options flow for scan interval."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "scan_interval",
                        default=self._config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                    ): vol.All(int, vol.Range(min=5, max=300))
                }
            ),
        )

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

from .const import DEFAULT_BAUDRATE, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_SLAVE, DOMAIN, SUPPORTED_BAUDRATES
from .modbus_client import (
    DEFAULT_TCP_PORT,
    FRAMER_AUTO,
    TRANSPORT_SERIAL,
    TRANSPORT_TCP,
    get_serial_by_id,
)

_LOGGER = logging.getLogger(__name__)

# Dropdown labels; values are what ends up in ConfigEntry.data.
TRANSPORT_CHOICES = {
    TRANSPORT_SERIAL: "USB / RS485 adapter (serial port)",
    TRANSPORT_TCP: "Ethernet — Modbus TCP gateway (RS485↔ETH)",
}
FRAMER_CHOICES = {
    FRAMER_AUTO: "Auto-detect (recommended)",
    "socket": "Modbus TCP (MBAP) — gateway in Modbus TCP↔RTU mode",
    "rtu": "Modbus RTU over TCP — gateway in transparent mode",
}


class AirPackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AirPack Home."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._discovered_device: str | None = None

    async def async_step_user(self, user_input=None):
        """Choose the connection type, then continue to that transport's step."""
        if user_input is not None:
            if user_input.get("transport") == TRANSPORT_TCP:
                return await self.async_step_tcp()
            return await self.async_step_serial()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("transport", default=TRANSPORT_SERIAL): vol.In(TRANSPORT_CHOICES),
                }
            ),
        )

    async def async_step_serial(self, user_input=None):
        """Handle the serial (USB RS485 adapter) connection."""
        errors = {}

        if user_input is not None:
            transport = TRANSPORT_SERIAL
            try:
                port = user_input["port"]
            except KeyError:
                port = None
            if not port:
                errors["base"] = "cannot_connect"
            else:
                # Resolve stable path
                if transport == "serial":
                    port = await self.hass.async_add_executor_job(
                        get_serial_by_id, port
                    )

                # Try to connect
                from .modbus_client import AirPackModbusClient

                def try_connect():
                    try:
                        client = AirPackModbusClient(
                            port=port,
                            slave=user_input["slave"],
                            baudrate=user_input.get("baudrate", DEFAULT_BAUDRATE),
                            hass=self.hass,
                        )
                        ok = client.connect()
                        if ok:
                            fw = client.get_firmware_version()
                            model = client.get_device_name()
                            client.close()
                            if fw is None and (model is None or model == ""):
                                _LOGGER.error("Connection successful but device did not respond to Modbus queries at port %s", port)
                                return None, None
                            return fw, model
                        client.close()
                        return None, None
                    except Exception as exc:  # noqa: BLE001 - surface connection setup failure
                        _LOGGER.exception("AirPack connection probe failed at %s", port)
                        return None, None

                fw, model = await self.hass.async_add_executor_job(try_connect)
                if fw is None:
                    errors["base"] = "cannot_connect"
                else:
                    # Use model name in title if possible
                    title = f"AirPack {model}" if model else f"AirPack Home ({port})"

                    # Unique ID: stable per port + slave
                    await self.async_set_unique_id(f"{port}_{user_input['slave']}")
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=title,
                        data={
                            "transport": transport,
                            "port": port,
                            "slave": user_input["slave"],
                            "baudrate": user_input.get("baudrate", DEFAULT_BAUDRATE),
                            "has_gwc": user_input.get("has_gwc", False),
                        },
                    )

        # transport defaults to serial.
        transport = (user_input or {}).get("transport", "serial")
        list_of_ports = {}

        # Local /dev/tty* ports
        try:
            ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
            for port in ports:
                list_of_ports[port.device] = f"{port.device} ({port.description})"
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Unable to list local serial ports: %s", exc)


        if not list_of_ports:
            # Fallback to manual entry
            data_schema = vol.Schema(
                {
                    vol.Required("port", default=DEFAULT_PORT): str,
                    vol.Required("slave", default=DEFAULT_SLAVE): vol.All(int, vol.Range(min=1, max=247)),
                    vol.Required("baudrate", default=DEFAULT_BAUDRATE): vol.In(SUPPORTED_BAUDRATES),
                    vol.Required("has_gwc", default=False): bool,
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required("port"): vol.In(list_of_ports),
                    vol.Required("slave", default=DEFAULT_SLAVE): vol.All(int, vol.Range(min=1, max=247)),
                    vol.Required("baudrate", default=DEFAULT_BAUDRATE): vol.In(SUPPORTED_BAUDRATES),
                    vol.Required("has_gwc", default=False): bool,
                }
            )

        return self.async_show_form(
            step_id="serial",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_tcp(self, user_input=None):
        """Handle the Modbus TCP connection (RS485↔Ethernet gateway)."""
        errors = {}

        if user_input is not None:
            host = (user_input.get("host") or "").strip()
            tcp_port = user_input.get("tcp_port", DEFAULT_TCP_PORT)
            framer = user_input.get("framer", FRAMER_AUTO)
            if not host:
                errors["base"] = "cannot_connect"
            else:
                from .modbus_client import AirPackModbusClient

                def try_connect():
                    # Probe the gateway and report the framing it answered with.
                    try:
                        client = AirPackModbusClient(
                            port=host,
                            slave=user_input["slave"],
                            transport=TRANSPORT_TCP,
                            tcp_host=host,
                            tcp_port=tcp_port,
                            framer=framer,
                            hass=self.hass,
                        )
                        try:
                            if not client.connect():
                                return None, None, None
                            fw = client.get_firmware_version()
                            model = client.get_device_name()
                            return fw, model, client.framer_mode
                        finally:
                            client.close()
                    except Exception:  # noqa: BLE001 - surface connection setup failure
                        _LOGGER.exception("AirPack TCP probe failed at %s:%s", host, tcp_port)
                        return None, None, None

                fw, model, detected = await self.hass.async_add_executor_job(try_connect)
                if fw is None:
                    errors["base"] = "cannot_connect"
                else:
                    _LOGGER.info(
                        "AirPack at %s:%s answered with %s framing (requested: %s)",
                        host, tcp_port, detected, framer,
                    )
                    title = f"AirPack {model}" if model else f"AirPack Home ({host})"

                    await self.async_set_unique_id(f"{host}:{tcp_port}_{user_input['slave']}")
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=title,
                        data={
                            "transport": TRANSPORT_TCP,
                            "host": host,
                            "tcp_port": tcp_port,
                            "framer": framer,
                            "slave": user_input["slave"],
                            "has_gwc": user_input.get("has_gwc", False),
                        },
                    )

        data_schema = vol.Schema(
            {
                vol.Required("host", default="192.168.1.254"): str,
                vol.Required("tcp_port", default=DEFAULT_TCP_PORT): vol.All(int, vol.Range(min=1, max=65535)),
                vol.Required("framer", default=FRAMER_AUTO): vol.In(FRAMER_CHOICES),
                vol.Required("slave", default=DEFAULT_SLAVE): vol.All(int, vol.Range(min=1, max=247)),
                vol.Required("has_gwc", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="tcp",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_usb(self, discovery_info: usb.UsbServiceInfo) -> FlowResult:
        """Handle USB discovery."""
        device = discovery_info.device
        _LOGGER.debug("Discovered USB device: %s", device)
        
        # Resolve stable path
        stable_path = await self.hass.async_add_executor_job(get_serial_by_id, device)
        
        # Check if any existing entry already uses this port
        for entry in self._async_current_entries():
            if entry.data.get("port") == stable_path:
                return self.async_abort(reason="already_configured")

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
            user_input["transport"] = TRANSPORT_SERIAL
            
            # Try to connect
            from .modbus_client import AirPackModbusClient
            def try_connect():
                client = AirPackModbusClient(
                    port=user_input["port"],
                    slave=user_input["slave"],
                    baudrate=user_input["baudrate"],
                )
                if client.connect():
                    # Verification: we must get a response from the device
                    fw = client.get_firmware_version()
                    model = client.get_device_name()
                    client.close()
                    if fw is None and (model is None or model == ""):
                        _LOGGER.error("Connection successful but device did not respond to Modbus queries at port %s", user_input["port"])
                        return None, None
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
                vol.Required("baudrate", default=DEFAULT_BAUDRATE): vol.In(SUPPORTED_BAUDRATES),
                vol.Required("has_gwc", default=False): bool,
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
                    ): vol.All(int, vol.Range(min=5, max=300)),
                    vol.Required(
                        "has_gwc",
                        default=self._config_entry.options.get("has_gwc", self._config_entry.data.get("has_gwc", False)),
                    ): bool,
                }
            ),
        )

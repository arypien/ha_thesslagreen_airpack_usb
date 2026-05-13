"""Data update coordinator for AirPack Home."""
from __future__ import annotations

import logging
from datetime import timedelta

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ALARM_REGISTERS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .modbus_client import AirPackModbusClient

_LOGGER = logging.getLogger(__name__)


class AirPackCoordinator(DataUpdateCoordinator):
    """Polls the AirPack unit and caches all data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._client = AirPackModbusClient(
            port=entry.data["port"],
            slave=entry.data.get("slave", 10),
            baudrate=entry.data.get("baudrate", 9600),
        )
        self._client.connect()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)),
        )

        # Sync time on startup
        hass.async_add_executor_job(self._client.set_datetime_now)

        # Sync time daily at 03:00
        self._unsub_time_sync = async_track_time_change(
            hass, self._async_sync_time, hour=3, minute=0, second=0
        )

    async def _async_sync_time(self, now=None) -> None:
        await self.hass.async_add_executor_job(self._client.set_datetime_now)
        _LOGGER.debug("AirPack: auto-synced device clock at 03:00")

    def close(self) -> None:
        self._unsub_time_sync()
        self._client.close()

    @property
    def client(self) -> AirPackModbusClient:
        return self._client

    async def _async_update_data(self) -> dict:
        """Fetch all data from the device."""
        try:
            data = await self.hass.async_add_executor_job(self._fetch_all)
        except Exception as exc:
            raise UpdateFailed(f"AirPack communication error: {exc}") from exc
        return data

    def _fetch_all(self) -> dict:
        data: dict = {}

        # 0. System / Model
        model = self._client.get_device_name()
        if model:
            data["device_model"] = model
        
        fw = self._client.get_firmware_version()
        if fw:
            data["firmware_version"] = fw

        # 1. Temperatures
        temps = self._client.get_temperatures()
        data.update(temps)
        
        # Calculate efficiency: (TN1 - TZ1) / (TP - TZ1) * 100
        # TZ1 = outside_temperature
        # TN1 = supply_temperature
        # TP  = exhaust_temperature
        tz1 = data.get("outside_temperature")
        tn1 = data.get("supply_temperature")
        tp  = data.get("exhaust_temperature")
        
        if tz1 is not None and tn1 is not None and tp is not None:
            try:
                # Avoid division by zero and unrealistic values
                if tp > tz1 + 1: # Only calculate if there's a significant diff
                    efficiency = round(((tn1 - tz1) / (tp - tz1)) * 100, 1)
                    # Cap between 0 and 100
                    data["heat_recovery_efficiency"] = max(0, min(100, efficiency))
                else:
                    data["heat_recovery_efficiency"] = 0
            except Exception:
                data["heat_recovery_efficiency"] = None

        # 2. Airflow
        airflow = self._client.get_airflow()
        data.update(airflow)

        # 3. CF live flow
        cf = self._client.get_cf_flow()
        data.update(cf)

        # 4. Operating mode
        mode = self._client.get_mode()
        if mode:
            data.update(mode)

        # 5. ON/OFF
        on_off = self._client.get_on_off()
        if on_off is not None:
            data["on_off"] = on_off

        # 6. Comfort
        comfort = self._client.get_comfort()
        if comfort:
            data.update(comfort)

        # 7. Bypass
        bypass = self._client.get_bypass()
        if bypass:
            data.update(bypass)
        bypass_mode_regs = self._client.read_holding_registers(0x10EA, 1)
        if bypass_mode_regs:
            data["bypass_mode"] = bypass_mode_regs[0]
        bypass_user_regs = self._client.read_holding_registers(0x10EB, 1)
        if bypass_user_regs:
            data["bypass_user_mode"] = bypass_user_regs[0]

        # 8. Special mode
        sm = self._client.get_special_mode()
        if sm is not None:
            data["special_mode"] = sm

        # 9. PWM voltages
        pwms = self._client.get_pwm_voltages()
        data.update(pwms)

        # 10. Nominal flows
        nominals = self._client.get_nominal_flows()
        data.update(nominals)

        # 11. Global alarm flags
        alarm_flags = self._client.get_alarm_flags()
        if alarm_flags:
            data.update(alarm_flags)

        # 12. Individual alarms (non-contiguous — read one by one)
        alarms = self._client.get_all_alarms(ALARM_REGISTERS)
        data.update(alarms)

        # 13. Antifreeze
        af_regs = self._client.read_holding_registers(0x1060, 1)
        if af_regs:
            data["antifreeze_mode"] = af_regs[0]
        afs_regs = self._client.read_holding_registers(0x1066, 1)
        if afs_regs:
            data["antifreeze_stage"] = afs_regs[0]

        # 14. Filter type
        ft = self._client.get_filter_type()
        if ft is not None:
            data["filter_change"] = ft

        # 15. Coils (relay outputs)
        coil_map = {
            "coil_info": 0x000A,
            "coil_power_supply_fans": 0x000B,
            "coil_heating_cable": 0x000C,
        }
        for key, addr in coil_map.items():
            result = self._client.read_coils(addr, 1)
            if result:
                data[key] = result[0]

        # 16. Discrete inputs
        disc_map = {
            "disc_ppoz": 0x000F,
            "disc_dp_ahu_filter_overflow": 0x0012,
            "disc_ahu_filter_protection": 0x0013,
        }
        for key, addr in disc_map.items():
            result = self._client.read_discrete_inputs(addr, 1)
            if result:
                data[key] = result[0]

        # 17. Stop alarm code
        stop_regs = self._client.read_holding_registers(0x1120, 1)
        if stop_regs:
            data["stop_ahu_code"] = stop_regs[0]

        # 18. Number entity registers - airing times, delays, coefficients
        number_map = {
            "airing_panel_mode_time":   0x1089,
            "airing_switch_mode_time":  0x108A,
            "airing_switch_on_delay":   0x108B,
            "airing_switch_off_delay":  0x108C,
            "fireplace_mode_time":      0x108D,
            "airing_bathroom_coef":     0x1085,
            "airing_coef":              0x1086,
            "contamination_coef":       0x1087,
            "empty_house_coef":         0x1088,
            "fireplace_supply_coef":    0x1084,
            "bypass_coef1":             0x10EC,
            "bypass_coef2":             0x10ED,
            "fan_speed_1_coef":         0x1078,
            "fan_speed_2_coef":         0x1079,
            "fan_speed_3_coef":         0x107A,
        }
        for key, addr in number_map.items():
            regs = self._client.read_holding_registers(addr, count=1)
            if regs:
                data[key] = regs[0]

        # 19. Device datetime
        dt = self._client.get_datetime()
        if dt:
            data["device_datetime"] = dt["datetime_str"]
            data["device_time_raw"] = dt

        # P.POZ is active-low: input=1 means NO alarm (circuit closed), 0 means alarm
        if "disc_ppoz" in data:
            data["disc_ppoz"] = not data["disc_ppoz"]

        return data

    def get_client(self) -> AirPackModbusClient:
        return self._client

"""Fan platform for AirPack Home."""
from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_MAP
from .coordinator import AirPackCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirPackCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AirPackFan(coordinator, entry)])


PRESET_BOOST = "Boost (Wietrzenie)"

class AirPackFan(CoordinatorEntity, FanEntity):
    """AirPack Fan entity."""

    _attr_name = "AirPack Home"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: AirPackCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_fan"
        self._attr_preset_modes = list(MODE_MAP.values()) + [PRESET_BOOST]
        
        model_name = coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model_name,
            "manufacturer": "Theslagreen",
            "model": model_name,
            "sw_version": coordinator.data.get("firmware_version") if coordinator.data else None,
        }

    @property
    def is_on(self) -> bool:
        d = self.coordinator.data
        return d.get("on_off", False) if d else False

    @property
    def percentage(self) -> int | None:
        d = self.coordinator.data
        if not d:
            return None
        # In temporary mode (Boost), airflow is read from air_flow_temporary (0x1073)
        if d.get("mode") == 2:
            return d.get("air_flow_temporary")
        return d.get("air_flow_manual")

    @property
    def preset_mode(self) -> str | None:
        d = self.coordinator.data
        if not d:
            return None
        raw = d.get("mode")
        if raw == 2:
            return PRESET_BOOST
        return MODE_MAP.get(raw)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        client = self.coordinator.client
        
        def _do():
            client.set_on_off(True)
            if preset_mode == PRESET_BOOST:
                # Use current manual flow or 100% if not set
                target_pct = percentage if percentage is not None else 100
                client.set_temporary_airflow(target_pct)
            else:
                if percentage is not None:
                    client.set_air_flow_manual(percentage)
                if preset_mode is not None:
                    reverse_mode = {v: k for k, v in MODE_MAP.items()}
                    raw_mode = reverse_mode.get(preset_mode)
                    if raw_mode is not None:
                        client.set_mode(raw_mode)

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_on_off, False
        )
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return

        client = self.coordinator.client
        d = self.coordinator.data
        
        def _do():
            # If currently in temporary mode, stay in temporary mode but change intensity
            if d and d.get("mode") == 2:
                client.set_temporary_airflow(percentage)
            else:
                client.set_air_flow_manual(percentage)

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        client = self.coordinator.client
        
        def _do():
            if preset_mode == PRESET_BOOST:
                # Default to 100% for boost if not already in temporary mode
                client.set_temporary_airflow(100)
            else:
                reverse_mode = {v: k for k, v in MODE_MAP.items()}
                raw_mode = reverse_mode.get(preset_mode)
                if raw_mode is not None:
                    client.set_mode(raw_mode)

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

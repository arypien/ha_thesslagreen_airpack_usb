"""Select platform for AirPack Home."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    COMFORT_MODE_MAP,
    DOMAIN,
    FILTER_TYPE_MAP,
    GWC_REGEN_MAP,
    MODE_MAP,
    SEASON_MAP,
    SPECIAL_MODE_MAP,
)
from .coordinator import AirPackCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirPackCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        AirPackModeSelect(coordinator, entry),
        AirPackSeasonSelect(coordinator, entry),
        AirPackSpecialModeSelect(coordinator, entry),
        AirPackComfortModeSelect(coordinator, entry),
        AirPackFilterTypeSelect(coordinator, entry),
    ])


class AirPackBaseSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator: AirPackCoordinator, entry: ConfigEntry,
                 key: str, name: str, mapping: dict) -> None:
        super().__init__(coordinator)
        self._key = key
        self._mapping = mapping
        self._reverse = {v: k for k, v in mapping.items()}
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}_select"
        self._attr_options = list(mapping.values())
        
        model_name = coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model_name,
            "manufacturer": "Thesslagreen",
            "model": model_name,
            "sw_version": coordinator.data.get("firmware_version") if coordinator.data else None,
        }

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._key)
        return self._mapping.get(raw) if raw is not None else None

    async def async_select_option(self, option: str) -> None:
        raw = self._reverse.get(option)
        if raw is None:
            return
        await self.hass.async_add_executor_job(self._write, raw)
        await self.coordinator.async_request_refresh()

    def _write(self, value: int) -> None:
        raise NotImplementedError


class AirPackModeSelect(AirPackBaseSelect):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "mode", "Tryb pracy", MODE_MAP)

    def _write(self, value):
        self.coordinator.client.set_mode(value)


class AirPackSeasonSelect(AirPackBaseSelect):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "season_mode", "Harmonogram (Lato/Zima)", SEASON_MAP)

    def _write(self, value):
        self.coordinator.client.set_season(value)


class AirPackSpecialModeSelect(AirPackBaseSelect):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "special_mode", "Funkcja specjalna", SPECIAL_MODE_MAP)

    def _write(self, value):
        self.coordinator.client.set_special_mode(value)


class AirPackComfortModeSelect(AirPackBaseSelect):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "comfort_mode_panel", "Tryb EKO/KOMFORT", COMFORT_MODE_MAP)

    def _write(self, value):
        self.coordinator.client.set_comfort_mode(value)


class AirPackGwcRegenSelect(AirPackBaseSelect):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "gwc_regen", "Typ regeneracji GWC", GWC_REGEN_MAP)

    def _write(self, value):
        self.coordinator.client.write_register(0x10A6, value)


class AirPackFilterTypeSelect(AirPackBaseSelect):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "filter_change", "Typ filtra", FILTER_TYPE_MAP)

    def _write(self, value):
        self.coordinator.client.set_filter_type(value)

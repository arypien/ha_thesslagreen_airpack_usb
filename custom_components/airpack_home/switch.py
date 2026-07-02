"""Switch platform for AirPack Home."""
from __future__ import annotations

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AirPackCoordinator

SPECIAL_MODE_NONE        = 0
SPECIAL_MODE_HOOD        = 1
SPECIAL_MODE_FIREPLACE   = 2
SPECIAL_MODE_AIRING_MAN  = 7
SPECIAL_MODE_OPEN_WINDOW = 10
SPECIAL_MODE_EMPTY_HOUSE = 11

SPECIAL_ICONS = {
    SPECIAL_MODE_HOOD:        "mdi:hvac",
    SPECIAL_MODE_FIREPLACE:   "mdi:fireplace",
    SPECIAL_MODE_AIRING_MAN:  "mdi:window-open",
    SPECIAL_MODE_OPEN_WINDOW: "mdi:window-open-variant",
    SPECIAL_MODE_EMPTY_HOUSE: "mdi:home-off",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirPackCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AirPackOnOffSwitch(coordinator, entry),
        AirPackAutoManualSwitch(coordinator, entry),
        AirPackBypassSwitch(coordinator, entry),
        AirPackSpecialSwitch(coordinator, entry, "switch_hood",        "Okap",         SPECIAL_MODE_HOOD),
        AirPackSpecialSwitch(coordinator, entry, "switch_fireplace",   "Kominek",       SPECIAL_MODE_FIREPLACE),
        AirPackSpecialSwitch(coordinator, entry, "switch_airing",      "Wietrzenie",    SPECIAL_MODE_AIRING_MAN),
        AirPackSpecialSwitch(coordinator, entry, "switch_open_window", "Otwarte okna",  SPECIAL_MODE_OPEN_WINDOW),
        AirPackSpecialSwitch(coordinator, entry, "switch_empty_house", "Pusty dom",     SPECIAL_MODE_EMPTY_HOUSE),
    ])


def _device_info(coordinator: AirPackCoordinator, entry: ConfigEntry):
    model_name = coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home"
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": model_name,
        "manufacturer": "Thesslagreen",
        "model": model_name,
        "sw_version": coordinator.data.get("firmware_version") if coordinator.data else None,
    }


class AirPackBaseSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}_switch"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get(self._key)
        return bool(val) if val is not None else None


class AirPackOnOffSwitch(AirPackBaseSwitch):
    _attr_icon = "mdi:power"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "on_off", "AirPack – Włącz/Wyłącz")
        self._attr_device_class = SwitchDeviceClass.OUTLET

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_on_off, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_on_off, False)
        await self.coordinator.async_request_refresh()


class AirPackAutoManualSwitch(AirPackBaseSwitch):
    """ON = tryb AUTOMATYCZNY, OFF = tryb MANUALNY."""
    _attr_icon = "mdi:auto-mode"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "mode", "Tryb AUTO/MANUAL")

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get("mode")
        return val == 0 if val is not None else None

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_mode, 0)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_mode, 1)
        await self.coordinator.async_request_refresh()


class AirPackBypassSwitch(AirPackBaseSwitch):
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "bypass_off", "Bypass aktywny")

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get("bypass_off")
        return not bool(val) if val is not None else None

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_bypass_off, False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_bypass_off, True)
        await self.coordinator.async_request_refresh()


class AirPackGwcSwitch(AirPackBaseSwitch):
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "gwc_off", "GWC aktywny")

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get("gwc_off")
        return not bool(val) if val is not None else None

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_gwc_off, False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.coordinator.client.set_gwc_off, True)
        await self.coordinator.async_request_refresh()


class AirPackSpecialSwitch(CoordinatorEntity, SwitchEntity):
    """Funkcja specjalna — wzajemnie się wykluczają.
    ON  → zapisuje mode_value do 0x1080
    OFF → zapisuje 0 (dezaktywacja) tylko gdy ta funkcja jest aktywna
    """

    def __init__(self, coordinator, entry, key, name, mode_value):
        super().__init__(coordinator)
        self._mode_value = mode_value
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}_switch"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = SPECIAL_ICONS.get(mode_value, "mdi:toggle-switch")
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        current = self.coordinator.data.get("special_mode")
        if current is None:
            return None
        return current == self._mode_value

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_special_mode, self._mode_value
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        if self.is_on:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_special_mode, SPECIAL_MODE_NONE
            )
            await self.coordinator.async_request_refresh()

"""Number platform for AirPack Home."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AirPackCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirPackCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        # Fan intensity
        AirPackNumberEntity(coordinator, entry, "air_flow_manual",    "Intensywność wentylacji (manual)",   10, 100, 1,   "%",   0x1072, 1.0,   None),
        AirPackNumberEntity(coordinator, entry, "air_flow_temporary", "Intensywność wentylacji (chwilowy)", 10, 100, 1,   "%",   0x1073, 1.0,   None),
        # Supply temperature setpoints
        AirPackNumberEntity(coordinator, entry, "supply_temp_manual",    "Temperatura nawiewu (manual)",    10, 45,  0.5, "°C",  0x1074, 0.5,   NumberDeviceClass.TEMPERATURE),
        AirPackNumberEntity(coordinator, entry, "supply_temp_temporary", "Temperatura nawiewu (chwilowy)",  10, 45,  0.5, "°C",  0x1075, 0.5,   NumberDeviceClass.TEMPERATURE),
        # AirS panel fan speed presets
        AirPackNumberEntity(coordinator, entry, "fan_speed_1_coef", "1. bieg AirS (%)", 10, 45,  1, "%", 0x1078, 1.0, None),
        AirPackNumberEntity(coordinator, entry, "fan_speed_2_coef", "2. bieg AirS (%)", 46, 75,  1, "%", 0x1079, 1.0, None),
        AirPackNumberEntity(coordinator, entry, "fan_speed_3_coef", "3. bieg AirS (%)", 76, 100, 1, "%", 0x107A, 1.0, None),
        # Airing times
        AirPackNumberEntity(coordinator, entry, "airing_panel_mode_time",  "Czas WIETRZENIE (ręczne) [min]",      1, 45, 1, "min", 0x1089, 1.0, None),
        AirPackNumberEntity(coordinator, entry, "airing_switch_mode_time", "Czas WIETRZENIE (przełącznik) [min]", 1, 45, 1, "min", 0x108A, 1.0, None),
        AirPackNumberEntity(coordinator, entry, "airing_switch_on_delay",  "Opóźnienie zał. WIETRZENIE [min]",    0, 20, 1, "min", 0x108B, 1.0, None),
        AirPackNumberEntity(coordinator, entry, "airing_switch_off_delay", "Opóźnienie wył. WIETRZENIE [min]",    0, 20, 1, "min", 0x108C, 1.0, None),
        AirPackNumberEntity(coordinator, entry, "fireplace_mode_time",     "Czas działania KOMINEK [min]",         1, 10, 1, "min", 0x108D, 1.0, None),
        # Bypass temperatures
        AirPackNumberEntity(coordinator, entry, "min_bypass_temperature",   "Min. temp. zewn. bypass",            5,  20, 0.5, "°C", 0x10E1, 0.5, NumberDeviceClass.TEMPERATURE),
        AirPackNumberEntity(coordinator, entry, "bypass_temp_freeheating",  "Temp. aktywacji bypass (grzanie)",   15, 30, 0.5, "°C", 0x10E2, 0.5, NumberDeviceClass.TEMPERATURE),
        AirPackNumberEntity(coordinator, entry, "bypass_temp_freecooling",  "Temp. aktywacji bypass (chłodzenie)",15, 30, 0.5, "°C", 0x10E3, 0.5, NumberDeviceClass.TEMPERATURE),
        # Empty house
        AirPackNumberEntity(coordinator, entry, "empty_house_coef", "Intensywność PUSTY DOM (%)", 10, 50, 1, "%", 0x1088, 1.0, None),
        # Fireplace
        AirPackNumberEntity(coordinator, entry, "fireplace_supply_coef", "Różnicowanie KOMINEK (%)", 5, 50, 1, "%", 0x1084, 1.0, None),
    ])


class AirPackNumberEntity(CoordinatorEntity, NumberEntity):
    def __init__(
        self,
        coordinator: AirPackCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        min_val: float,
        max_val: float,
        step: float,
        unit: str,
        register: int,
        scale: float,
        device_class,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._register = register
        self._scale = scale
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}_number"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_mode = NumberMode.SLIDER
        
        model_name = coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model_name,
            "manufacturer": "Theslagreen",
            "model": model_name,
            "sw_version": coordinator.data.get("firmware_version") if coordinator.data else None,
        }

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._key)
        if raw is None:
            return None
        return raw * self._scale

    async def async_set_native_value(self, value: float) -> None:
        raw = int(value / self._scale)

        def write():
            self.coordinator.client.write_register(self._register, raw)

        await self.hass.async_add_executor_job(write)
        await self.coordinator.async_request_refresh()

"""Binary sensor platform for AirPack Home."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ALARM_REGISTERS, DOMAIN
from .coordinator import AirPackCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirPackCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # ── Global alarm flags ────────────────────────────────────────────────
    entities += [
        AirPackBinarySensor(coordinator, entry, "any_warning",   "Aktywne ostrzeżenie (E)", BinarySensorDeviceClass.PROBLEM),
        AirPackBinarySensor(coordinator, entry, "any_error",     "Aktywny błąd (S)",        BinarySensorDeviceClass.PROBLEM),
    ]

    # ── Individual alarms ─────────────────────────────────────────────────
    for key, reg in ALARM_REGISTERS.items():
        entities.append(
            AirPackBinarySensor(coordinator, entry, key, reg["name"], BinarySensorDeviceClass.PROBLEM)
        )

    # ── Relay outputs (coils) & Digital inputs ────────────────────────────
    # Only keeping relevant ones for 650h
    misc_entities = [
        ("coil_info",                   "Potwierdzenie pracy (O1)",        BinarySensorDeviceClass.RUNNING),
        ("coil_power_supply_fans",      "Zasilanie wentylatorów",         BinarySensorDeviceClass.POWER),
        ("disc_ppoz",                     "Alarm pożarowy P.POZ",                  BinarySensorDeviceClass.SMOKE),
        ("disc_dp_ahu_filter_overflow",   "Presostat filtrów rekuperatora (DP1)",  BinarySensorDeviceClass.PROBLEM),
        ("disc_ahu_filter_protection",    "Zabezpieczenie termiczne nagrzewnicy FPX", BinarySensorDeviceClass.SAFETY),
        ("constant_flow_active",          "Constant Flow aktywny",      BinarySensorDeviceClass.RUNNING),
        ("antifreeze_mode",               "System FPX aktywny",         BinarySensorDeviceClass.RUNNING),
        ("on_off",                        "Urządzenie włączone",        BinarySensorDeviceClass.POWER),
    ]
    for key, name, dc in misc_entities:
        entities.append(AirPackBinarySensor(coordinator, entry, key, name, dc))

    async_add_entities(entities)


class AirPackBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: AirPackCoordinator, entry: ConfigEntry, key: str, name: str, device_class=None) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_class = device_class
        
        model_name = coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model_name,
            "manufacturer": "Theslagreen",
            "model": model_name,
            "sw_version": coordinator.data.get("firmware_version") if coordinator.data else None,
        }

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get(self._key)
        if val is None:
            return None
        return bool(val)

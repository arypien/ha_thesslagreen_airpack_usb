"""Sensor platform for AirPack Home."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ANTIFREEZE_STAGE_MAP,
    BYPASS_MODE_MAP,
    BYPASS_USER_MODE_MAP,
    COMFORT_STATUS_MAP,
    DOMAIN,
    FILTER_TYPE_MAP,
    GWC_MODE_MAP,
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

    entities: list[SensorEntity] = [
        # ── Temperatures ──────────────────────────────────────────────────
        AirPackTemperatureSensor(coordinator, entry, "outside_temperature",     "Temperatura zewnętrzna (TZ1)"),
        AirPackTemperatureSensor(coordinator, entry, "supply_temperature",      "Temperatura nawiewu (TN1)"),
        AirPackTemperatureSensor(coordinator, entry, "exhaust_temperature",     "Temperatura wywiewu (TP)"),
        AirPackTemperatureSensor(coordinator, entry, "fpx_temperature",         "Temperatura FPX (TZ2)"),
        AirPackTemperatureSensor(coordinator, entry, "ambient_temperature",     "Temperatura otoczenia (TO)"),
        # ── Efficiency ────────────────────────────────────────────────────
        AirPackFlowSensor(coordinator, entry, "heat_recovery_efficiency", "Sprawność odzysku ciepła", "%"),
        # ── Airflow ───────────────────────────────────────────────────────

        AirPackFlowSensor(coordinator, entry, "supply_percentage",   "Intensywność nawiewu",       "%"),
        AirPackFlowSensor(coordinator, entry, "exhaust_percentage",  "Intensywność wywiewu",       "%"),
        AirPackFlowSensor(coordinator, entry, "supply_flowrate",     "Strumień nawiewu (zadany)",  "m³/h"),
        AirPackFlowSensor(coordinator, entry, "exhaust_flowrate",    "Strumień wywiewu (zadany)",  "m³/h"),
        AirPackFlowSensor(coordinator, entry, "supply_air_flow_cf",  "Strumień nawiewu (CF)",      "m³/h"),
        AirPackFlowSensor(coordinator, entry, "exhaust_air_flow_cf", "Strumień wywiewu (CF)",      "m³/h"),
        AirPackFlowSensor(coordinator, entry, "min_percentage",      "Min. intensywność",          "%"),
        AirPackFlowSensor(coordinator, entry, "max_percentage",      "Max. intensywność",          "%"),
        # ── Status / mode sensors ─────────────────────────────────────────
        AirPackMappedSensor(coordinator, entry, "mode",              "Tryb pracy",         MODE_MAP),
        AirPackMappedSensor(coordinator, entry, "season_mode",       "Harmonogram",        SEASON_MAP),
        AirPackMappedSensor(coordinator, entry, "special_mode",      "Funkcja specjalna",  SPECIAL_MODE_MAP),
        AirPackMappedSensor(coordinator, entry, "bypass_mode",       "Status bypass",      BYPASS_MODE_MAP),
        AirPackMappedSensor(coordinator, entry, "bypass_user_mode",  "Tryb bypass",        BYPASS_USER_MODE_MAP),
        AirPackMappedSensor(coordinator, entry, "comfort_mode_status","Status KOMFORT",    COMFORT_STATUS_MAP),
        AirPackMappedSensor(coordinator, entry, "antifreeze_stage",  "Tryb FPX",           ANTIFREEZE_STAGE_MAP),
        AirPackMappedSensor(coordinator, entry, "filter_change",     "Typ filtra",         FILTER_TYPE_MAP),
        # ── Numeric status ────────────────────────────────────────────────
        AirPackFlowSensor(coordinator, entry, "stop_ahu_code",       "Kod alarmu blokującego", None),
        AirPackFlowSensor(coordinator, entry, "air_flow_manual",     "Intensywność (manual)", "%"),
        AirPackFlowSensor(coordinator, entry, "air_flow_temporary",  "Intensywność (chwilowy)", "%"),
        # ── PWM / DAC ─────────────────────────────────────────────────────
        AirPackFlowSensor(coordinator, entry, "dac_supply",          "Napięcie PWM nawiew",        "V"),
        AirPackFlowSensor(coordinator, entry, "dac_exhaust",         "Napięcie PWM wywiew",        "V"),
        AirPackFlowSensor(coordinator, entry, "dac_heater",          "Napięcie PWM nagrzewnica",   "V"),
        # ── Nominal ───────────────────────────────────────────────────────
        AirPackFlowSensor(coordinator, entry, "nominal_supply_flow",  "Nominalny strumień nawiewu", "m³/h"),
        AirPackFlowSensor(coordinator, entry, "nominal_exhaust_flow", "Nominalny strumień wywiewu", "m³/h"),
        # Firmware
        AirPackTextSensor(coordinator, entry, "firmware_version",    "Wersja oprogramowania"),
        AirPackTextSensor(coordinator, entry, "device_datetime",      "Czas urządzenia"),
    ]

    async_add_entities(entities)


# ── Base entity ───────────────────────────────────────────────────────────────

class AirPackBaseEntity(CoordinatorEntity):
    def __init__(self, coordinator: AirPackCoordinator, entry: ConfigEntry, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        
        # Use recognized model name if available
        model_name = coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model_name,
            "manufacturer": "Theslagreen",
            "model": model_name,
            "sw_version": coordinator.data.get("firmware_version") if coordinator.data else None,
        }


# ── Temperature sensor ────────────────────────────────────────────────────────

class AirPackTemperatureSensor(AirPackBaseEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)


# ── Flow/percentage sensor ────────────────────────────────────────────────────

class AirPackFlowSensor(AirPackBaseEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, key, name, unit) -> None:
        super().__init__(coordinator, entry, key, name)
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)


# ── Mapped sensor (int → string) ──────────────────────────────────────────────

class AirPackMappedSensor(AirPackBaseEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, mapping: dict) -> None:
        super().__init__(coordinator, entry, key, name)
        self._mapping = mapping

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._key)
        if raw is None:
            return None
        return self._mapping.get(raw, str(raw))


# ── Text sensor (string value) ────────────────────────────────────────────────

class AirPackTextSensor(AirPackBaseEntity, SensorEntity):
    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)

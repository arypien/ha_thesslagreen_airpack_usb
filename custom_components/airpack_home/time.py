"""Time entities for GWC regeneration and AirPack schedules."""
from __future__ import annotations

from datetime import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.time import TimeEntity

from .const import DOMAIN, SUMMER_SCHEDULE_START, WINTER_SCHEDULE_START
from .coordinator import AirPackCoordinator
DAY_NAMES = ("Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirPackCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    if coordinator.has_gwc:
        for key, name, address in (
            ("gwc_start_winter", "Start regeneracji GWC zima", 0x10AB),
            ("gwc_stop_winter", "Koniec regeneracji GWC zima", 0x10AC),
            ("gwc_start_summer", "Start regeneracji GWC lato", 0x10AD),
            ("gwc_stop_summer", "Koniec regeneracji GWC lato", 0x10AE),
        ):
            entities.append(AirPackTimeEntity(coordinator, entry, key, name, address))
    for season, start in (("summer", SUMMER_SCHEDULE_START), ("winter", WINTER_SCHEDULE_START)):
        for day in range(7):
            for period in range(4):
                entities.append(AirPackScheduleTime(coordinator, entry, season, day, period, start))
    async_add_entities(entities)


class AirPackTimeBase(CoordinatorEntity, TimeEntity):
    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}_time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home",
            "manufacturer": "Thesslagreen",
        }

    @property
    def native_value(self) -> time | None:
        value = self._value()
        return time(*value) if value is not None else None

    def _value(self) -> tuple[int, int] | None:
        raise NotImplementedError


class AirPackTimeEntity(AirPackTimeBase):
    def __init__(self, coordinator, entry, key, name, address):
        super().__init__(coordinator, entry, key, name)
        self._address = address

    def _value(self):
        return self.coordinator.data.get(self._key) if self.coordinator.data else None

    async def async_set_value(self, value: time) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_gwc_schedule_time,
            self._address,
            (value.hour, value.minute),
        )
        await self.coordinator.async_request_refresh()


class AirPackScheduleTime(AirPackTimeBase):
    def __init__(self, coordinator, entry, season, day, period, start_address):
        key = f"{season}_schedule_{day}_{period}"
        super().__init__(coordinator, entry, key, f"{season.title()} {DAY_NAMES[day]} odcinek {period + 1}")
        self._season = season
        self._day = day
        self._period = period
        self._start_address = start_address

    def _value(self):
        schedule = self.coordinator.data.get(f"{self._season}_schedule") if self.coordinator.data else None
        return schedule[self._day][self._period] if schedule else None

    async def async_set_value(self, value: time) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_schedule_time,
            self._start_address,
            self._day,
            self._period,
            (value.hour, value.minute),
        )
        await self.coordinator.async_request_refresh()
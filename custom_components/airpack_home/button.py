"""Button platform for AirPack Home."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    async_add_entities([AirPackSyncTimeButton(coordinator, entry)])


class AirPackSyncTimeButton(CoordinatorEntity, ButtonEntity):
    """Button that syncs the device RTC to HA system time."""

    _attr_name = "Synchronizuj czas urządzenia"
    _attr_icon = "mdi:clock-sync"

    def __init__(self, coordinator: AirPackCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sync_time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "AirPack Home",
            "manufacturer": "Thesslagreen",
            "model": "AirPack Home",
        }

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(self.coordinator.client.set_datetime_now)
        await self.coordinator.async_request_refresh()

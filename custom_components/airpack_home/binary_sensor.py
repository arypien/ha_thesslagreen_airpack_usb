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

from .const import ALARM_REGISTERS, ADDRESS_ALIASES, DOMAIN, GROUP_SENSORS_PREFIX
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

    if coordinator.has_gwc:
        entities.append(
            AirPackBinarySensor(
                coordinator, entry, "gwc_regeneration_active",
                "Regeneracja GWC aktywna", BinarySensorDeviceClass.RUNNING,
            )
        )

    async_add_entities(entities)


class AirPackBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: AirPackCoordinator, entry: ConfigEntry, key: str, name: str, device_class=None) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = GROUP_SENSORS_PREFIX + name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_class = device_class
        
        model_name = coordinator.data.get("device_model", "AirPack Home") if coordinator.data else "AirPack Home"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model_name,
            "manufacturer": "Thesslagreen",
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

    @property
    def extra_state_attributes(self) -> dict:
        """For the two global flag entities, name the alarms that are actually on.

        The registers 0x2000 / 0x2001 only say "some E / some S alarm is active";
        the cause lives in the individual alarm registers. Surface it here so the
        UI can show "which problem" instead of a bare "problem".

        Register 0x20C6 carries four codes (E196/E197/E198/E199) behind one flag
        bit, so a raised flag there identifies the register but never the code.
        For those, report every candidate and mark the register ambiguous instead
        of guessing one name.
        """
        if self._key not in ("any_warning", "any_error"):
            return {}

        data = self.coordinator.data
        if not data:
            return {"active_alarms": [], "ambiguous_registers": []}

        # Raw integers of the shared registers, always present when known: a value
        # above 1 proves the register is a bitfield (each code has its own bit)
        # instead of a single 0/1 "some alarm of this group" flag.
        raw_values = {
            f"raw_{address:04X}": data[f"raw_{address:04X}"]
            for address in ADDRESS_ALIASES
            if f"raw_{address:04X}" in data
        }

        if not bool(data.get(self._key)):
            return {"active_alarms": [], "ambiguous_registers": [], **raw_values}

        prefix = "E" if self._key == "any_warning" else "S"

        # Which individual alarm keys are currently on, grouped by address.
        on_keys: list[str] = [
            key for key, reg in ALARM_REGISTERS.items()
            if key.startswith(prefix) and data.get(key)
        ]
        if not on_keys:
            return {"active_alarms": [], "ambiguous_registers": []}

        active: list[str] = []
        ambiguous: list[str] = []

        # Alias groups first: every code of a shared register is a candidate.
        grouped: dict[int, list[str]] = {}
        for key in on_keys:
            address = ALARM_REGISTERS[key]["address"]
            if address in ADDRESS_ALIASES:
                # Every alias code that the device could have meant. Do not
                # filter by data.get(k): a single shared flag means the code is
                # genuinely ambiguous, so all candidates belong in the report.
                grouped[address] = sorted(
                    k for k in ADDRESS_ALIASES[address] if k.startswith(prefix)
                )
                continue
            grouped.setdefault(address, []).append(key)

        for address, keys in grouped.items():
            if address in ADDRESS_ALIASES or len(keys) > 1:
                names = ", ".join(f"{k} {ALARM_REGISTERS[k]['name']}" for k in keys)
                active.append(
                    f"rejestr 0x{address:04X}: {names} "
                    f"— rejestr wspólny, kod niejednoznaczny"
                )
                ambiguous.append(f"0x{address:04X}")
            else:
                key = keys[0]
                active.append(f"{key}: {ALARM_REGISTERS[key]['name']}")

        return {"active_alarms": active, "ambiguous_registers": ambiguous, **raw_values}

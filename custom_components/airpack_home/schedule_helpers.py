"""Helpers for AirPack [HHMM] BCD schedule registers."""


def decode_hhmm(raw: int) -> tuple[int, int] | None:
    """Decode AirPack schedule value; 0xA200 means disabled."""
    if raw == 0xA200:
        return None
    hour = ((raw >> 8) >> 4) * 10 + ((raw >> 8) & 0x0F)
    minute = ((raw & 0xFF) >> 4) * 10 + (raw & 0x0F)
    if hour > 23 or minute > 59:
        return None
    return hour, minute


# Airing (Wietrzenie) start-time registers use the same [HHMM] BCD layout as
# the schedule, but their "disabled" sentinel is 0x2400 (24:00), not 0xA200.
AIRING_DISABLED = 0x2400


def decode_airing_hhmm(raw: int) -> tuple[int, int] | None:
    """Decode an airing start-hour register; 0x2400 (24:00) = disabled."""
    if raw == AIRING_DISABLED:
        return None
    return decode_hhmm(raw)


def encode_airing_hhmm(hour: int | None, minute: int | None) -> int:
    """Encode an airing start time into AirPack BCD [HHMM]; None/None = disabled."""
    if hour is None and minute is None:
        return AIRING_DISABLED
    if hour is None or minute is None or not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("time must be a valid HH:MM value")
    return (((hour // 10) << 4) | (hour % 10)) << 8 | ((minute // 10) << 4) | (minute % 10)


def encode_hhmm(hour: int | None, minute: int | None) -> int:
    """Encode a Home Assistant time into AirPack BCD [HHMM]."""
    if hour is None and minute is None:
        return 0xA200
    if hour is None or minute is None or not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("time must be a valid HH:MM value")
    return (((hour // 10) << 4) | (hour % 10)) << 8 | ((minute // 10) << 4) | (minute % 10)


def decode_aatt(raw: int) -> tuple[int, float] | None:
    """Decode AirPack segment setting [AATT]: intensity [AA] in % and
    double-supply-temperature [TT] (half-degree, so *0.5 = °C)."""
    intensity = (raw >> 8) & 0xFF
    temp_raw = raw & 0xFF
    if not 10 <= intensity <= 100:
        return None
    return intensity, temp_raw * 0.5


def encode_aatt(intensity: int, temperature_c: float | None) -> int:
    """Encode intensity [%] and supply temperature [°C] into AirPack [AATT]."""
    if temperature_c is None:
        temp_raw = 0
    else:
        temp_raw = int(round(temperature_c * 2))
    if not 10 <= intensity <= 100:
        raise ValueError("intensity must be in 10..100 %")
    return ((intensity << 8) & 0xFF00) | (temp_raw & 0xFF)
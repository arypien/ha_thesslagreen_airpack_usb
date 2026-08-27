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


def encode_hhmm(hour: int | None, minute: int | None) -> int:
    """Encode a Home Assistant time into AirPack BCD [HHMM]."""
    if hour is None and minute is None:
        return 0xA200
    if hour is None or minute is None or not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("time must be a valid HH:MM value")
    return (((hour // 10) << 4) | (hour % 10)) << 8 | ((minute // 10) << 4) | (minute % 10)

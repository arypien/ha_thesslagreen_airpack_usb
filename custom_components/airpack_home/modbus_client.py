"""Modbus RTU client for AirPack Home."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import serial.tools.list_ports
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

from .schedule_helpers import decode_aatt, decode_hhmm, encode_aatt, encode_hhmm
from .const import SCHEDULE_DAYS, SCHEDULE_PERIODS

_LOGGER = logging.getLogger(__name__)

NO_READING_VALUE = 0x8000  # sensor not connected / no reading


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


class _RtuResponse:
    def __init__(self, registers=None, bits=None, error=False):
        self.registers = registers or []
        self.bits = bits or []
        self._error = error

    def isError(self):
        return self._error


class _SerialxModbusClient:
    """Synchronous facade over serialx, executed on HA's event loop."""
    def __init__(self, port: str, slave: int, baudrate: int, loop) -> None:
        self.port, self.slave, self.baudrate, self.loop = port, slave, baudrate, loop
        self.reader = self.writer = None

    def connect(self) -> bool:
        import serialx
        try:
            self.reader, self.writer = self._run(serialx.open_serial_connection(
                self.port, baudrate=self.baudrate))
            return True
        except Exception as exc:
            _LOGGER.error("serialx connect failed for %s: %s", self.port, exc)
            return False

    def close(self) -> None:
        if self.writer is not None:
            try:
                self._run(self._close_writer())
            except Exception:
                pass
        self.reader = self.writer = None

    async def _close_writer(self):
        self.writer.close()
        await self.writer.wait_closed()

    def _run(self, awaitable):
        return asyncio.run_coroutine_threadsafe(awaitable, self.loop).result(timeout=20)

    async def _exchange(self, frame: bytes) -> bytes:
        self.writer.write(frame)
        await self.writer.drain()
        return await asyncio.wait_for(self.reader.read(256), timeout=10)

    def _request(self, function: int, address: int, count: int, values=None):
        if self.reader is None or self.writer is None:
            if not self.connect():
                return _RtuResponse(error=True)
        if values is None:
            payload = bytes((self.slave, function, address >> 8, address & 255,
                             count >> 8, count & 255))
        else:
            payload = bytes((self.slave, function, address >> 8, address & 255,
                             len(values) >> 8, len(values) & 255)) + b"".join(v.to_bytes(2, "big") for v in values)
        crc = _crc16(payload)
        frame = payload + bytes((crc & 255, crc >> 8))
        raw = self._run(self._exchange(frame))
        if len(raw) < 5 or raw[0] != self.slave or raw[1] != function:
            return _RtuResponse(error=True)
        if raw[1] & 0x80:
            return _RtuResponse(error=True)
        crc_expected = _crc16(raw[:-2])
        if raw[-2] | (raw[-1] << 8) != crc_expected:
            return _RtuResponse(error=True)
        if function in (1, 2):
            return _RtuResponse(bits=[bool(raw[3 + i // 8] & (1 << (i % 8))) for i in range(count)])
        if function in (3, 4):
            return _RtuResponse(registers=[int.from_bytes(raw[3+i:5+i], "big") for i in range(0, raw[2], 2)])
        return _RtuResponse()

    def read_coils(self, address, count=1, device_id=None): return self._request(1, address, count)
    def read_discrete_inputs(self, address, count=1, device_id=None): return self._request(2, address, count)
    def read_holding_registers(self, address, count=1, device_id=None): return self._request(3, address, count)
    def read_input_registers(self, address, count=1, device_id=None): return self._request(4, address, count)
    def write_register(self, address, value, device_id=None): return self._request(6, address, 1, [value])
    def write_registers(self, address, values, device_id=None): return self._request(16, address, len(values), values)


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id path for a given device path if possible."""
    if not dev_path or not dev_path.startswith("/dev/tty"):
        return dev_path

    by_id_dir = "/dev/serial/by-id"
    if not os.path.isdir(by_id_dir):
        return dev_path

    try:
        for link in os.listdir(by_id_dir):
            full_link = os.path.join(by_id_dir, link)
            if os.path.islink(full_link):
                if os.path.realpath(full_link) == dev_path:
                    return full_link
    except Exception:
        _LOGGER.debug("Could not list %s", by_id_dir)

    return dev_path


class AirPackModbusClient:
    """Thin wrapper around pymodbus serial client."""

    def __init__(self, port: str, slave: int, baudrate: int = 9600, hass=None) -> None:
        self._port = get_serial_by_id(port)
        self._slave = slave
        self._client = ModbusSerialClient(
            port=self._port,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=3,
        )

    def connect(self) -> bool:
        return self._client.connect()

    def close(self) -> None:
        self._client.close()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _signed16(self, value: int) -> int:
        """Convert unsigned 16-bit int to signed."""
        if value >= 0x8000:
            value -= 0x10000
        return value

    def _temp_value(self, raw: int) -> float | None:
        """Return None if sensor absent (0x8000) or zero reading (0x0000), else °C × 0.1."""
        if raw == NO_READING_VALUE or raw == 0:
            return None
        return self._signed16(raw) * 0.1

    # ── read helpers ─────────────────────────────────────────────────────────

    def read_coils(self, address: int, count: int = 1) -> list[bool] | None:
        try:
            result = self._client.read_coils(address, count=count, device_id=self._slave)
            if result.isError():
                return None
            return result.bits[:count]
        except ModbusException as exc:
            _LOGGER.error("Coil read error @ 0x%04X: %s", address, exc)
            return None

    def read_discrete_inputs(self, address: int, count: int = 1) -> list[bool] | None:
        try:
            result = self._client.read_discrete_inputs(address, count=count, device_id=self._slave)
            if result.isError():
                return None
            return result.bits[:count]
        except ModbusException as exc:
            _LOGGER.error("Discrete input read error @ 0x%04X: %s", address, exc)
            return None

    def read_holding_registers(self, address: int, count: int = 1) -> list[int] | None:
        try:
            result = self._client.read_holding_registers(address, count=count, device_id=self._slave)
            if result.isError():
                return None
            return result.registers
        except ModbusException as exc:
            _LOGGER.error("Holding register read error @ 0x%04X: %s", address, exc)
            return None

    def read_input_registers(self, address: int, count: int = 1) -> list[int] | None:
        try:
            result = self._client.read_input_registers(address, count=count, device_id=self._slave)
            if result.isError():
                return None
            return result.registers
        except ModbusException as exc:
            _LOGGER.error("Input register read error @ 0x%04X: %s", address, exc)
            return None

    def write_register(self, address: int, value: int) -> bool:
        try:
            result = self._client.write_register(address, value, device_id=self._slave)
        except ModbusException as exc:
            _LOGGER.error("Register write error @ 0x%04X: %s", address, exc)
            return False
        # pymodbus returns a response object, not a plain bool.
        if isinstance(result, bool):
            return result
        return not result.isError()

    def write_registers(self, address: int, values: list[int]) -> bool:
        """Write multiple registers in one operation."""
        try:
            result = self._client.write_registers(address, values, device_id=self._slave)
        except ModbusException as exc:
            _LOGGER.error("Registers write error @ 0x%04X: %s", address, exc)
            return False
        if isinstance(result, bool):
            return result
        return not result.isError()

    # ── temporary mode activation (PDF page 14) ──────────────────────────────

    def set_temporary_airflow(self, intensity_pct: int) -> bool:
        """
        Activate temporary airflow mode (Wietrzenie).
        PDF page 14: Write 3 registers in one operation starting at 0x1130:
        [2, intensity_pct, 1]
        """
        return self.write_registers(0x1130, [2, intensity_pct, 1])

    def set_temporary_temperature(self, temp_c: float) -> bool:
        """
        Activate temporary temperature mode.
        PDF page 14: Write 3 registers in one operation starting at 0x1133:
        [2, int(temp*2), 1]
        """
        raw_temp = int(temp_c * 2)
        return self.write_registers(0x1133, [2, raw_temp, 1])

    # ── PWM voltages (PDF page 10) ───────────────────────────────────────────

    def get_pwm_voltages(self) -> dict[str, float | None]:
        regs = self.read_holding_bulk(0x0500, 4)
        if regs is None:
            return {}
        keys = ["dac_supply", "dac_exhaust", "dac_heater", "dac_cooler"]
        # Scale 4095 -> 10.0V
        return {k: round(v * 0.00244, 2) for k, v in zip(keys, regs)}

    # ── Nominal flows (PDF page 13) ──────────────────────────────────────────

    def get_nominal_flows(self) -> dict[str, int | None]:
        regs = self.read_holding_bulk(0x1102, 2)
        if regs is None:
            return {}
        return {"nominal_supply_flow": regs[0], "nominal_exhaust_flow": regs[1]}

    # ── bulk reads (max 16 registers per spec) ───────────────────────────────

    def read_holding_bulk(self, address: int, count: int) -> list[int] | None:
        """Read up to 16 holding registers at once."""
        count = min(count, 16)
        return self.read_holding_registers(address, count)

    def read_input_bulk(self, address: int, count: int) -> list[int] | None:
        """Read up to 16 input registers at once."""
        count = min(count, 16)
        return self.read_input_registers(address, count)

    # ── firmware version ─────────────────────────────────────────────────────

    def get_firmware_version(self) -> str | None:
        regs = self.read_input_registers(0x0000, 3)
        if regs is None:
            return None
        patch_regs = self.read_input_registers(0x0004, 1)
        patch = patch_regs[0] if patch_regs else 0
        return f"{regs[0]}.{regs[1]}.{patch}"

    # ── temperature group ────────────────────────────────────────────────────

    def get_temperatures(self, include_gwc: bool = True) -> dict[str, float | None]:
        """Read temperatures, optionally including the GWC sensor register."""
        if include_gwc:
            regs = self.read_input_bulk(0x0010, 7)
        else:
            regs = self.read_input_bulk(0x0010, 5)
            if regs is not None:
                ambient = self.read_input_bulk(0x0016, 1)
                if ambient:
                    regs.append(ambient[0])
        if regs is None:
            return {}
        keys = [
            "outside_temperature", "supply_temperature", "exhaust_temperature",
            "fpx_temperature", "duct_supply_temperature",
        ]
        if include_gwc:
            keys.extend(["gwc_temperature", "ambient_temperature"])
        else:
            keys.append("ambient_temperature")
        return {k: self._temp_value(v) for k, v in zip(keys, regs)}

    def get_airflow(self) -> dict[str, int]:
        regs = self.read_input_bulk(0x010F, 7)
        if regs is None:
            return {}
        keys = [
            "constant_flow_active", "supply_percentage", "exhaust_percentage",
            "supply_flowrate", "exhaust_flowrate", "min_percentage", "max_percentage",
        ]
        return dict(zip(keys, regs))

    # ── CF live flow ─────────────────────────────────────────────────────────

    def get_cf_flow(self) -> dict[str, int | None]:
        regs = self.read_holding_bulk(0x0100, 2)
        if regs is None:
            return {}
        supply = None if regs[0] == 65535 else regs[0]
        exhaust = None if regs[1] == 65535 else regs[1]
        return {"supply_air_flow_cf": supply, "exhaust_air_flow_cf": exhaust}

    # ── operating mode ───────────────────────────────────────────────────────

    def get_mode(self) -> dict[str, int] | None:
        regs = self.read_holding_bulk(0x1070, 6)
        if regs is None:
            return None
        return {
            "mode": regs[0],
            "season_mode": regs[1],
            "air_flow_manual": regs[2],
            "air_flow_temporary": regs[3],
            "supply_temp_manual": regs[4],
            "supply_temp_temporary": regs[5],
        }

    def set_mode(self, mode: int) -> bool:
        return self.write_register(0x1070, mode)

    def set_season(self, season: int) -> bool:
        return self.write_register(0x1071, season)

    def set_air_flow_manual(self, value: int) -> bool:
        return self.write_register(0x1072, value)

    def set_supply_temp_manual(self, value_c: float) -> bool:
        raw = int(value_c / 0.5)
        return self.write_register(0x1074, raw)

    # ── on/off ───────────────────────────────────────────────────────────────

    def get_on_off(self) -> bool | None:
        regs = self.read_holding_registers(0x1123, 1)
        if regs is None:
            return None
        return bool(regs[0])

    def set_on_off(self, value: bool) -> bool:
        return self.write_register(0x1123, 1 if value else 0)

    # ── comfort mode ─────────────────────────────────────────────────────────

    def get_comfort(self) -> dict[str, int] | None:
        regs = self.read_holding_bulk(0x10D0, 2)
        if regs is None:
            return None
        return {"comfort_mode_panel": regs[0], "comfort_mode_status": regs[1]}

    def set_comfort_mode(self, value: int) -> bool:
        return self.write_register(0x10D0, value)

    # ── bypass ───────────────────────────────────────────────────────────────

    def get_bypass(self) -> dict[str, int] | None:
        regs = self.read_holding_bulk(0x10E0, 4)
        if regs is None:
            return None
        return {
            "bypass_off": regs[0],
            "min_bypass_temperature": regs[1],
            "bypass_temp_freeheating": regs[2],
            "bypass_temp_freecooling": regs[3],
        }

    def set_bypass_off(self, value: bool) -> bool:
        return self.write_register(0x10E0, 1 if value else 0)

    # ── GWC ─────────────────────────────────────────────────────────────────

    def get_gwc(self) -> dict[str, int] | None:
        regs = self.read_holding_bulk(0x10A0, 3)
        if regs is None:
            return None
        extra = self.read_holding_bulk(0x10A6, 2)
        data = {
            "gwc_off": regs[0],
            "min_gwc_temperature": regs[1],
            "max_gwc_temperature": regs[2],
        }
        if extra:
            data["gwc_regen"] = extra[0]
            data["gwc_mode"] = extra[1]
        return data

    def set_gwc_off(self, value: bool) -> bool:
        return self.write_register(0x10A0, 1 if value else 0)

    def get_gwc_settings(self) -> dict[str, int | float | bool | tuple[int, int] | None]:
        period = self.read_holding_registers(0x10A8, 1)
        regs = self.read_holding_bulk(0x10AA, 6)
        if period is None or regs is None:
            return {}
        return {
            "gwc_regen_period": period[0],
            "gwc_delta_temperature": regs[0] * 0.5,
            "gwc_start_winter": decode_hhmm(regs[1]),
            "gwc_stop_winter": decode_hhmm(regs[2]),
            "gwc_start_summer": decode_hhmm(regs[3]),
            "gwc_stop_summer": decode_hhmm(regs[4]),
            "gwc_regeneration_active": bool(regs[5]),
        }

    def set_gwc_delta_temperature(self, value: float) -> bool:
        return self.write_register(0x10AA, int(round(value / 0.5)))

    def set_gwc_schedule_time(self, address: int, value: tuple[int, int] | None) -> bool:
        return self.write_register(address, encode_hhmm(*(value or (None, None))))

    def get_schedule(self, start_address: int) -> list[list[tuple[int, int] | None]] | None:
        first = self.read_holding_bulk(start_address, 16)
        second = self.read_holding_bulk(start_address + 16, 12)
        if first is None or second is None:
            return None
        regs = first + second
        return [[decode_hhmm(regs[day * 4 + period]) for period in range(4)] for day in range(7)]

    def set_schedule_time(self, start_address: int, day: int, period: int, value: tuple[int, int] | None) -> bool:
        if not 0 <= day < 7 or not 0 <= period < 4:
            raise ValueError("day and period are outside the AirPack schedule")
        return self.write_register(start_address + day * 4 + period, encode_hhmm(*(value or (None, None))))

    def get_schedule_settings(self, start_address: int) -> list[list[tuple[int, float] | None]] | None:
        """Read per-segment [AATT] settings (intensity %, supply temp °C) for 7 days × 4 periods.

        AirPack caps a single read at 16 registers, so days 0-3 and 4-6 are fetched
        in two bulk reads (mirrors get_schedule).
        """
        first = self.read_holding_bulk(start_address, 16)
        second = self.read_holding_bulk(start_address + 16, SCHEDULE_DAYS * SCHEDULE_PERIODS - 16)
        if first is None or second is None:
            return None
        regs = first + second
        return [[decode_aatt(regs[day * SCHEDULE_PERIODS + period]) for period in range(SCHEDULE_PERIODS)] for day in range(SCHEDULE_DAYS)]

    def set_schedule_setting(
        self, start_address: int, day: int, period: int, intensity: int | None, temperature_c: float | None
    ) -> bool:
        if not 0 <= day < 7 or not 0 <= period < 4:
            raise ValueError("day and period are outside the AirPack schedule")
        value = encode_aatt(intensity, temperature_c) if intensity is not None else 0
        return self.write_register(start_address + day * SCHEDULE_PERIODS + period, value)

    # ── Airing (Wietrzenie) start hour ────────────────────────────────────────
    # One BCD [HHMM] register per season/day (disabled = 0x2400), independent of
    # the schedule segments. Each season occupies a contiguous 25-register span
    # (day d -> base + d*4), so it is fetched in two sub-16 bulk reads.

    def _read_airing_block(self, base: int) -> list[int] | None:
        first = self.read_holding_bulk(base, 16)
        if first is None:
            return None
        rest = self.read_holding_bulk(base + 16, 9)
        if rest is None:
            return None
        return first + rest

    def get_airing_start_times(self) -> dict[str, list]:
        """Return {'airing_start_<season>': [(h, m) | None, ...x7]}."""
        from .const import (AIRING_SUMMER_START, AIRING_WINTER_START, AIRING_DAYS)
        from .schedule_helpers import decode_airing_hhmm

        out: dict[str, list] = {}
        for season, base in (("summer", AIRING_SUMMER_START), ("winter", AIRING_WINTER_START)):
            block = self._read_airing_block(base)
            if block and len(block) >= (AIRING_DAYS - 1) * 4 + 1:
                out[f"airing_start_{season}"] = [decode_airing_hhmm(block[day * 4]) for day in range(AIRING_DAYS)]
        return out

    def set_airing_start_time(self, season: str, day: int, value: tuple[int, int]) -> bool:
        if not 0 <= day < 7:
            raise ValueError("day outside 0..6")
        from .const import AIRING_SUMMER_START, AIRING_WINTER_START
        from .schedule_helpers import encode_airing_hhmm

        base = AIRING_SUMMER_START if season == "summer" else AIRING_WINTER_START
        return self.write_register(base + day * 4, encode_airing_hhmm(*(value or (None, None))))

    # ── special mode ─────────────────────────────────────────────────────────

    def get_special_mode(self) -> int | None:
        regs = self.read_holding_registers(0x1080, 1)
        return regs[0] if regs else None

    def set_special_mode(self, value: int) -> bool:
        return self.write_register(0x1080, value)

    # ── alarms ───────────────────────────────────────────────────────────────

    def get_alarm_flags(self) -> dict[str, int] | None:
        """Read global alarm/error flags (0x2000, 0x2001)."""
        regs = self.read_holding_bulk(0x2000, 2)
        if regs is None:
            return None
        return {"any_warning": regs[0], "any_error": regs[1]}

    def get_all_alarms(self, alarm_registers: dict) -> dict[str, bool]:
        """Read alarm registers, merging only TRULY consecutive registers into single RTU requests.

        The AirPack S-error register map is SPARSE (0x2002..0x2020 has holes where S3/S4/S5,
        S11/S12, S18, S21, S27/S28 don't exist). Requesting one contiguous block across a hole
        makes the unit answer with Modbus Exception 0x04 (Server Device Failure) and the whole
        read fails. Merging ONLY gap-free runs keeps E-type blocks batched (they are contiguous)
        while every isolated S register is read individually.
        """
        result = {key: False for key in alarm_registers}
        ordered = sorted(alarm_registers.items(), key=lambda item: item[1]["address"])
        index = 0
        while index < len(ordered):
            start = ordered[index][1]["address"]
            end = start
            block = [ordered[index]]
            index += 1
            while index < len(ordered):
                address = ordered[index][1]["address"]
                if address != end + 1:  # only merge strictly consecutive registers
                    break
                end = address
                block.append(ordered[index])
                index += 1

            regs = self.read_holding_registers(start, end - start + 1)
            if regs:
                for key, reg in block:
                    offset = reg["address"] - start
                    if offset < len(regs):
                        result[key] = bool(regs[offset])
        return result

    def reset_alarm(self, address: int) -> bool:
        return self.write_register(address, 0)

    # ── filter ───────────────────────────────────────────────────────────────

    def get_filter_type(self) -> int | None:
        regs = self.read_holding_registers(0x1FFF, 1)
        return regs[0] if regs else None

    def set_filter_type(self, value: int) -> bool:
        return self.write_register(0x1FFF, value)

    # ── RTC time ─────────────────────────────────────────────────────────────

    def get_datetime(self) -> dict | None:
        """Read device clock. Values are BCD encoded."""
        regs = self.read_holding_bulk(0x0000, 4)
        if regs is None:
            return None

        def from_bcd(val):
            """Convert BCD byte to int (e.g. 0x26 -> 26, 0x12 -> 12)."""
            return ((val >> 4) & 0xF) * 10 + (val & 0xF)

        rr = from_bcd((regs[0] >> 8) & 0xFF)
        mm = from_bcd(regs[0] & 0xFF)
        dd = from_bcd((regs[1] >> 8) & 0xFF)
        tt = regs[1] & 0xFF              # weekday plain int per spec
        hh = from_bcd((regs[2] >> 8) & 0xFF)
        mn = from_bcd(regs[2] & 0xFF)
        ss = from_bcd((regs[3] >> 8) & 0xFF)

        weekdays = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        return {
            "year": 2000 + rr,
            "month": mm,
            "day": dd,
            "weekday": weekdays[tt] if tt < 7 else "?",
            "hour": hh,
            "minute": mn,
            "second": ss,
            "datetime_str": f"{2000+rr:04d}-{mm:02d}-{dd:02d} {hh:02d}:{mn:02d}:{ss:02d}",
        }

    def set_datetime_now(self) -> bool:
        """Sync device clock to current system time. All 4 registers written at once."""
        from datetime import datetime
        now = datetime.now()

        def to_bcd(val):
            """Convert integer to BCD byte (e.g. 26 -> 0x26, 12 -> 0x12)."""
            return ((val // 10) << 4) | (val % 10)

        rr = to_bcd(now.year - 2000)   # e.g. 2026 -> 26 -> 0x26
        mm = to_bcd(now.month)
        dd = to_bcd(now.day)
        tt = now.weekday()              # 0=Mon..6=Sun, plain int per spec
        hh = to_bcd(now.hour)
        mn = to_bcd(now.minute)
        ss = to_bcd(now.second)

        reg0 = (rr << 8) | mm
        reg1 = (dd << 8) | tt
        reg2 = (hh << 8) | mn
        reg3 = (ss << 8) | 0
        try:
            # write via the bool-safe wrapper
            return self.write_registers(0x0000, [reg0, reg1, reg2, reg3])
        except Exception as exc:
            _LOGGER.error("DateTime write error: %s", exc)
            return False

    def get_device_name(self) -> str | None:
        """Read device name (model) from ASCII registers 0x1FD0-0x1FD7."""
        regs = self.read_holding_bulk(0x1FD0, 8)
        if not regs:
            return None
        
        name = ""
        for r in regs:
            # Each 16-bit register contains 2 ASCII chars
            char1 = chr((r >> 8) & 0xFF)
            char2 = chr(r & 0xFF)
            name += char1 + char2
            
        return name.strip('\x00').strip()

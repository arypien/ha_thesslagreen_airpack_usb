#!/usr/bin/env python3
"""Live probe: talk to an AirPack through a Modbus TCP (RS485↔Ethernet) gateway.

Useful for beta testing without Home Assistant — it exercises exactly the same
client code the integration uses, so the result tells you whether the transport,
framer mode and slave address are right.

    pip install pymodbus==3.13.1 pyserial
    python3 tests/tcp_gateway_probe.py --host 192.168.1.254
    python3 tests/tcp_gateway_probe.py --host 192.168.1.254 --framer rtu --polls 5

Exit codes: 0 = OK, 1 = cannot connect, 2 = connected but the unit did not answer.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
import types
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "airpack_home"


def _load_client_module():
    """Import the integration's modbus_client.py without pulling in Home Assistant."""
    package = types.ModuleType("airpack_probe")
    package.__path__ = [str(COMPONENT)]
    sys.modules["airpack_probe"] = package

    for name in ("schedule_helpers", "const", "modbus_client"):
        spec = importlib.util.spec_from_file_location(f"airpack_probe.{name}", COMPONENT / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"airpack_probe.{name}"] = module
        spec.loader.exec_module(module)
    return sys.modules["airpack_probe.modbus_client"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe an AirPack via a Modbus TCP gateway")
    parser.add_argument("--host", required=True, help="gateway IP address")
    parser.add_argument("--port", type=int, default=502, help="TCP port (default 502)")
    parser.add_argument("--slave", type=int, default=10, help="Modbus slave address (default 10)")
    parser.add_argument(
        "--framer",
        default="auto",
        choices=["auto", "socket", "rtu"],
        help="auto = detect, socket = Modbus TCP (MBAP), rtu = RTU over TCP (transparent gateway)",
    )
    parser.add_argument("--polls", type=int, default=1, help="how many poll cycles to run (default 1)")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between polls")
    args = parser.parse_args()

    mc = _load_client_module()

    client = mc.AirPackModbusClient(
        port=args.host,
        slave=args.slave,
        transport=mc.TRANSPORT_TCP,
        tcp_host=args.host,
        tcp_port=args.port,
        framer=args.framer,
    )

    started = time.monotonic()
    if not client.connect():
        print(f"FAIL: no Modbus response from {args.host}:{args.port} (requested framer: {args.framer})")
        print("      check: gateway IP/port, 'Modbus TCP <-> RTU' setting, A/B wiring, slave address, baud rate")
        return 1
    print(f"OK: connected to {args.host}:{args.port} in {time.monotonic() - started:.2f}s")
    print(f"    framing in use : {client.framer_mode}")
    print(f"    firmware       : {client.get_firmware_version()}")
    print(f"    model          : {client.get_device_name()}")
    print(f"    filter type    : {client.get_filter_type()}")

    temps = client.get_temperatures()
    if temps:
        for key, value in temps.items():
            print(f"    {key:16s}: {value}")

    ok_polls = 0
    alarm_registers = sys.modules["airpack_probe.const"].ALARM_REGISTERS
    for i in range(args.polls):
        if i:
            time.sleep(args.interval)
        alarms = client.get_all_alarms(alarm_registers)
        value = client.read_input_registers(0x0000, 1)
        healthy = value is not None
        ok_polls += 1 if healthy else 0
        active = sum(1 for v in (alarms or {}).values() if v)
        print(
            f"    poll {i + 1:3d}/{args.polls}: reg 0x0000 -> {value}, "
            f"alarms read -> {'yes' if alarms is not None else 'no'} ({active} active)"
        )

    client.close()
    print(f"RESULT: {ok_polls}/{args.polls} polls answered")
    return 0 if ok_polls else 2


if __name__ == "__main__":
    sys.exit(main())

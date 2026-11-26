"""Tests for the Modbus TCP (RS485↔Ethernet gateway) transport.

These tests run without pymodbus installed: the client module is loaded against
a fake pymodbus that simulates both gateway flavours:

  * "Modbus TCP ↔ RTU" gateway  → answers MBAP frames        (framer "socket")
  * transparent / RTU-over-TCP  → answers raw RTU frames      (framer "rtu")
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "airpack_home"

# ── fake pymodbus ────────────────────────────────────────────────────────────


class _FramerType:
    SOCKET = "socket"
    RTU = "rtu"


class FakeResponse:
    def __init__(self, error: bool = False, registers=None) -> None:
        self._error = error
        self.registers = registers or []

    def isError(self) -> bool:
        return self._error


class FakeGateway:
    """State shared by all fake clients (one simulated gateway)."""

    mode = "socket"       # which framing the gateway answers
    reachable = True
    reads = 0             # total read attempts
    connects = 0
    built = []            # (framer, timeout, retries) of every client built


class FakeTcpClient:
    def __init__(self, host=None, port=None, framer=None, timeout=3, **kwargs) -> None:
        self.host = host
        self.port = port
        self.framer = getattr(framer, "value", framer) or str(framer)
        self.timeout = timeout
        self.retries = kwargs.get("retries", 3)
        FakeGateway.built.append((self.framer, timeout, self.retries))
        self.closed = False

    def connect(self) -> bool:
        FakeGateway.connects += 1
        return FakeGateway.reachable

    def read_input_registers(self, address, count=1, device_id=None):
        FakeGateway.reads += 1
        if not FakeGateway.reachable:
            return FakeResponse(error=True)
        # A transparent gateway accepts the socket but never answers MBAP frames.
        if self.framer == FakeGateway.mode:
            return FakeResponse(registers=[0x0102] * count)
        return FakeResponse(error=True)

    def read_holding_registers(self, address, count=1, device_id=None):
        return self.read_input_registers(address, count, device_id)

    def write_register(self, address, value, device_id=None):
        return FakeResponse(error=(not FakeGateway.reachable) or self.framer != FakeGateway.mode)

    def close(self) -> None:
        self.closed = True


class FakeSerialClient:
    instances = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.connected = False
        FakeSerialClient.instances.append(self)

    def connect(self) -> bool:
        self.connected = True
        return True

    def close(self) -> None:
        self.connected = False

    def read_input_registers(self, address, count=1, device_id=None):
        return FakeResponse(registers=[0x0102] * count)

    def read_holding_registers(self, address, count=1, device_id=None):
        return self.read_input_registers(address, count, device_id)

    def write_register(self, address, value, device_id=None):
        return FakeResponse()


def _install_fake_pymodbus() -> None:
    pymodbus = types.ModuleType("pymodbus")
    pymodbus.FramerType = _FramerType
    pymodbus_client = types.ModuleType("pymodbus.client")
    pymodbus_client.ModbusTcpClient = FakeTcpClient
    pymodbus_client.ModbusSerialClient = FakeSerialClient
    pymodbus.client = pymodbus_client
    pymodbus_exceptions = types.ModuleType("pymodbus.exceptions")
    pymodbus_exceptions.ModbusException = Exception

    serial = types.ModuleType("serial")
    serial_tools = types.ModuleType("serial.tools")
    serial_list_ports = types.ModuleType("serial.tools.list_ports")
    serial_list_ports.comports = lambda: []
    serial_tools.list_ports = serial_list_ports
    serial.tools = serial_tools

    real = {}
    for name, mod in (
        ("pymodbus", pymodbus),
        ("pymodbus.client", pymodbus_client),
        ("pymodbus.exceptions", pymodbus_exceptions),
        ("serial", serial),
        ("serial.tools", serial_tools),
        ("serial.tools.list_ports", serial_list_ports),
    ):
        real[name] = sys.modules.get(name)
        sys.modules[name] = mod
    return real


def _load_client_module(name: str = "airpack_home.modbus_client_tcpfake"):
    """Import modbus_client.py from disk under its own module name."""
    package = types.ModuleType("airpack_home")
    package.__path__ = [str(PACKAGE_PATH)]
    sys.modules.setdefault("airpack_home", package)

    helper_spec = importlib.util.spec_from_file_location(
        "airpack_home.schedule_helpers", PACKAGE_PATH / "schedule_helpers.py"
    )
    helper = importlib.util.module_from_spec(helper_spec)
    sys.modules["airpack_home.schedule_helpers"] = helper
    helper_spec.loader.exec_module(helper)

    spec = importlib.util.spec_from_file_location(name, PACKAGE_PATH / "modbus_client.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_SAVED_MODULES = _install_fake_pymodbus()
mc = _load_client_module()


class TcpTransportTest(unittest.TestCase):
    def setUp(self) -> None:
        FakeGateway.mode = "socket"
        FakeGateway.reachable = True
        FakeGateway.reads = 0
        FakeGateway.connects = 0
        FakeGateway.built.clear()
        FakeSerialClient.instances.clear()

    def _client(self, **kwargs):
        return mc.AirPackModbusClient(
            port=kwargs.pop("host", "192.168.1.254"),
            slave=kwargs.pop("slave", 10),
            transport=mc.TRANSPORT_TCP,
            tcp_host=kwargs.pop("tcp_host", "192.168.1.254"),
            tcp_port=kwargs.pop("tcp_port", 502),
            framer=kwargs.pop("framer", mc.FRAMER_AUTO),
            **kwargs,
        )

    # ── auto-detection ───────────────────────────────────────────────────────

    def test_auto_detect_modbus_tcp_gateway(self):
        client = self._client()
        self.assertTrue(client.connect())
        self.assertEqual(client.framer_mode, mc.FRAMER_SOCKET)
        self.assertEqual(client.transport, mc.TRANSPORT_TCP)
        self.assertEqual(FakeGateway.reads, 1)  # answered on the first probe

    def test_auto_detect_transparent_gateway(self):
        FakeGateway.mode = "rtu"  # Waveshare default: raw RTU over TCP
        client = self._client()
        self.assertTrue(client.connect())
        self.assertEqual(client.framer_mode, mc.FRAMER_RTU)
        self.assertEqual(FakeGateway.reads, 2)  # socket probe failed, rtu probe worked

    def test_explicit_framer_does_not_probe(self):
        client = self._client(framer=mc.FRAMER_RTU)
        self.assertTrue(client.connect())
        self.assertEqual(FakeGateway.reads, 0)
        self.assertEqual(client.framer_mode, mc.FRAMER_RTU)

    def test_unreachable_gateway(self):
        FakeGateway.reachable = False
        client = self._client()
        self.assertFalse(client.connect())
        # reads must degrade to None, never raise AttributeError
        self.assertIsNone(client.read_input_registers(0x0000, 1))
        self.assertFalse(client.write_register(0x10EA, 42))

    def test_wrong_framer_returns_none(self):
        FakeGateway.mode = "rtu"
        client = self._client(framer=mc.FRAMER_SOCKET)  # forced, wrong mode
        self.assertTrue(client.connect())
        self.assertIsNone(client.read_holding_registers(0x0000, 1))

    def test_default_port_and_host_string(self):
        client = self._client(host="10.0.0.5", tcp_host=None)
        self.assertTrue(client.connect())
        self.assertEqual(client._host, "10.0.0.5")
        self.assertEqual(client._tcp_port, 502)

    def test_probe_uses_short_timeout_then_runtime_client(self):
        client = self._client()
        self.assertTrue(client.connect())
        # probe attempts are short and single-shot; no client ever retries a poll twice
        self.assertIn(mc.PROBE_TIMEOUT, [t for _, t, _ in FakeGateway.built])
        self.assertEqual({r for _, _, r in FakeGateway.built}, {1})
        self.assertEqual(FakeGateway.built[-1][1], mc.RUNTIME_TIMEOUT)
        # the client kept for polling: normal timeout, one retry (never hangs a poll)
        self.assertEqual(client._client.timeout, mc.RUNTIME_TIMEOUT)
        self.assertEqual(client._client.retries, 1)

    # ── serial transport must stay untouched ─────────────────────────────────

    def test_serial_uses_serial_client(self):
        client = mc.AirPackModbusClient(port="/dev/ttyUSB0", slave=10, baudrate=9600)
        self.assertEqual(client.transport, mc.TRANSPORT_SERIAL)
        self.assertTrue(client.connect())
        self.assertEqual(len(FakeSerialClient.instances), 1)
        self.assertEqual(FakeSerialClient.instances[0].kwargs["baudrate"], 9600)
        # legacy entries have no "transport" key: default must be serial
        legacy = mc.AirPackModbusClient(port="/dev/ttyUSB0", slave=10)
        self.assertEqual(legacy.transport, mc.TRANSPORT_SERIAL)

    def test_invalid_transport_falls_back_to_serial(self):
        client = mc.AirPackModbusClient(port="/dev/ttyUSB0", slave=10, transport="bogus")
        self.assertEqual(client.transport, mc.TRANSPORT_SERIAL)

    def test_close_is_safe_before_connect(self):
        client = mc.AirPackModbusClient(
            port="192.168.1.254", slave=10, transport=mc.TRANSPORT_TCP, tcp_host="192.168.1.254"
        )
        client.close()  # no client built yet in auto mode


if __name__ == "__main__":
    unittest.main()

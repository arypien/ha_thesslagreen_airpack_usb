import sys
import types
import unittest
from pathlib import Path

# The integration's Modbus module imports runtime dependencies unavailable in
# this standalone test environment. Provide minimal import stubs.
serial = types.ModuleType("serial")
serial_tools = types.ModuleType("serial.tools")
serial_list_ports = types.ModuleType("serial.tools.list_ports")
serial_list_ports.comports = lambda: []
serial_tools.list_ports = serial_list_ports
serial.tools = serial_tools
sys.modules.setdefault("serial", serial)
sys.modules.setdefault("serial.tools", serial_tools)
sys.modules.setdefault("serial.tools.list_ports", serial_list_ports)

pymodbus = types.ModuleType("pymodbus")
pymodbus_client = types.ModuleType("pymodbus.client")
pymodbus_client.ModbusSerialClient = object
pymodbus.client = pymodbus_client
pymodbus_exceptions = types.ModuleType("pymodbus.exceptions")
pymodbus_exceptions.ModbusException = Exception
sys.modules.setdefault("pymodbus", pymodbus)
sys.modules.setdefault("pymodbus.client", pymodbus_client)
sys.modules.setdefault("pymodbus.exceptions", pymodbus_exceptions)

import importlib.util
import types

package_path = Path(__file__).parents[1] / "custom_components" / "airpack_home"
package = types.ModuleType("airpack_home")
package.__path__ = [str(package_path)]
sys.modules.setdefault("airpack_home", package)

helper_path = package_path / "schedule_helpers.py"
helper_spec = importlib.util.spec_from_file_location("airpack_home.schedule_helpers", helper_path)
helper = importlib.util.module_from_spec(helper_spec)
sys.modules["airpack_home.schedule_helpers"] = helper
helper_spec.loader.exec_module(helper)

module_path = package_path / "modbus_client.py"
spec = importlib.util.spec_from_file_location("airpack_home.modbus_client", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules["airpack_home.modbus_client"] = module
spec.loader.exec_module(module)
AirPackModbusClient = module.AirPackModbusClient


class TestAirPackModbusClient(unittest.TestCase):
    def make_client(self):
        return AirPackModbusClient.__new__(AirPackModbusClient)

    def test_signed_temperature_values(self):
        client = self.make_client()
        self.assertEqual(client._temp_value(215), 21.5)
        self.assertEqual(client._temp_value(0xFF9C), -10.0)
        self.assertIsNone(client._temp_value(0x8000))
        self.assertIsNone(client._temp_value(0))

    def test_alarm_reads_are_grouped_and_mapped(self):
        client = self.make_client()
        calls = []

        def read(address, count=1):
            calls.append((address, count))
            return list(range(100, 100 + count))

        client.read_holding_registers = read
        alarms = {
            "S1": {"address": 10},
            "S2": {"address": 11},
            "S3": {"address": 25},
        }
        result = client.get_all_alarms(alarms)

        # Only strictly consecutive registers may be merged into one request.
        # 10,11 are consecutive -> one read; 25 is isolated (gap after 11) -> its own read.
        self.assertEqual(calls, [(10, 2), (25, 1)])
        self.assertEqual(result, {"S1": True, "S2": True, "S3": True})

    def test_schedule_settings_read_and_encode(self):
        client = self.make_client()

        # Simulate the REAL read path: read_holding_registers returns exactly `count`
        # registers, and read_holding_bulk caps each call at 16. So a 7x4 (28-reg)
        # block must be assembled from two bulk reads (16 + 12), not one.
        regs = [0x412C, 0x0000, 0x0000, 0x0000] + [0] * 24  # 28 registers
        calls = []

        def read_regs(address, count=1):
            calls.append((address, count))
            off = address - 0x0048
            return list(regs[off:off + count])

        client.read_holding_registers = read_regs
        client.read_holding_bulk = lambda a, c: read_regs(a, min(c, 16))

        settings = client.get_schedule_settings(0x0048)

        # two capped bulk reads issued (16 then 12)
        self.assertEqual(calls, [(0x0048, 16), (0x0058, 12)])
        self.assertEqual(len(settings), 7)
        self.assertEqual(len(settings[0]), 4)
        self.assertEqual(settings[0][0], (65, 22.0))
        self.assertIsNone(settings[0][1])
        # days 4-6 (index 16-27) must still be present, not IndexError
        self.assertEqual(len(settings[6]), 4)

        # encode/write path builds the right [AATT] value
        written = []
        client.write_register = lambda addr, val: written.append((addr, val)) or True
        client.set_schedule_setting(0x0048, 6, 3, 65, 22.0)
        self.assertEqual(written, [(0x0048 + 6 * 4 + 3, 0x412C)])

    def test_write_handles_both_transports(self):
        client = self.make_client()
        client._slave = 1

        class Resp:
            def __init__(self, err):
                self._err = err
            def isError(self):
                return self._err

        # pymodbus transport -> response object
        client._client = type("C", (), {"write_register": lambda self, a, v, device_id=None: Resp(False),
                                        "write_registers": lambda self, a, v, device_id=None: Resp(False)})()

        self.assertTrue(client.write_register(0x10A0, 1))
        self.assertTrue(client.write_registers(0x1130, [1, 2]))

        # fake transport returns a plain bool
        client._client = type("C", (), {"write_register": lambda self, a, v, device_id=None: True,
                                        "write_registers": lambda self, a, v, device_id=None: True})()
        self.assertTrue(client.write_register(0x10A0, 0))
        self.assertTrue(client.write_registers(0x1130, [0, 0]))

        # bool containing an error must propagate False
        client._client = type("C", (), {"write_register": lambda self, a, v, device_id=None: False})()
        self.assertFalse(client.write_register(0x10A0, 1))


if __name__ == "__main__":
    unittest.main()

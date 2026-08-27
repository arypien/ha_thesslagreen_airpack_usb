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

        self.assertEqual(calls, [(10, 16)])
        self.assertEqual(result, {"S1": True, "S2": True, "S3": True})


if __name__ == "__main__":
    unittest.main()

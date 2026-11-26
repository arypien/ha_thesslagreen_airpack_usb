"""Guard rails for the ambiguous alarm registers (0x20C6 → E196/E197/E198/E199).

Register 0x20C6 carries several alarm codes behind a single flag bit, so a raised
flag there identifies the register but never the code. ``ADDRESS_ALIASES`` in
const.py records those groups; binary_sensor.py reports every candidate instead of
picking one name. These tests keep the two tables in sync without needing Home
Assistant installed (const.py is loaded straight from disk).
"""
import importlib.util
import unittest
from pathlib import Path

CONST_PATH = Path(__file__).parents[1] / "custom_components" / "airpack_home" / "const.py"

_spec = importlib.util.spec_from_file_location("airpack_const", CONST_PATH)
assert _spec is not None and _spec.loader is not None
const = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(const)

ALARM_REGISTERS = const.ALARM_REGISTERS
ADDRESS_ALIASES = const.ADDRESS_ALIASES


class TestAddressAliases(unittest.TestCase):
    def test_alias_groups_are_not_empty(self):
        self.assertTrue(ADDRESS_ALIASES)
        for address, codes in ADDRESS_ALIASES.items():
            self.assertIsInstance(address, int)
            self.assertGreaterEqual(len(codes), 2, f"0x{address:04X} is not ambiguous")

    def test_every_alias_code_exists_in_alarm_registers(self):
        for address, codes in ADDRESS_ALIASES.items():
            for code in codes:
                self.assertIn(code, ALARM_REGISTERS, f"{code} listed for 0x{address:04X} is unknown")

    def test_no_shared_address_code_is_missing_from_its_group(self):
        """Every code assigned to an alias address must appear in that group."""
        for address, codes in ADDRESS_ALIASES.items():
            assigned = [
                key
                for key, reg in ALARM_REGISTERS.items()
                if reg["address"] == address
            ]
            self.assertTrue(assigned, f"0x{address:04X} has no alarm codes in ALARM_REGISTERS")
            for key in assigned:
                self.assertIn(key, codes, f"{key} reads shared register 0x{address:04X} but is not in ADDRESS_ALIASES")

    def test_alias_lists_have_no_duplicates(self):
        for address, codes in ADDRESS_ALIASES.items():
            self.assertEqual(len(codes), len(set(codes)), f"0x{address:04X} lists a code twice")

    def test_known_0x20c6_group(self):
        self.assertEqual(ADDRESS_ALIASES.get(0x20C6), ["E196", "E197", "E198", "E199"])


if __name__ == "__main__":
    unittest.main()

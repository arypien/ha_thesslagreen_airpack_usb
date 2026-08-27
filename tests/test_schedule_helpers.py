import unittest

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

path = Path(__file__).parents[1] / "custom_components" / "airpack_home" / "schedule_helpers.py"
spec = spec_from_file_location("schedule_helpers", path)
module = module_from_spec(spec)
spec.loader.exec_module(module)


class TestScheduleHelpers(unittest.TestCase):
    def test_bcd_hhmm_round_trip(self):
        self.assertEqual(module.decode_hhmm(0x0630), (6, 30))
        self.assertEqual(module.encode_hhmm(6, 30), 0x0630)

    def test_disabled_schedule_round_trip(self):
        self.assertIsNone(module.decode_hhmm(0xA200))
        self.assertEqual(module.encode_hhmm(None, None), 0xA200)

    def test_rejects_invalid_time(self):
        with self.assertRaises(ValueError):
            module.encode_hhmm(24, 0)
        with self.assertRaises(ValueError):
            module.encode_hhmm(12, 60)


if __name__ == "__main__":
    unittest.main()

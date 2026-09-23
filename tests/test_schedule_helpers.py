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

    def test_aatt_round_trip(self):
        # 0x142C → 20%, (0x2C * 0.5) = 22 °C per AirPack manual example
        self.assertEqual(module.decode_aatt(0x142C), (20, 22.0))
        self.assertEqual(module.encode_aatt(20, 22.0), 0x142C)
        self.assertEqual(module.encode_aatt(65, 22.0), 0x412C)

    def test_aatt_rejects_bad_intensity(self):
        self.assertIsNone(module.decode_aatt(0x0000))
        with self.assertRaises(ValueError):
            module.encode_aatt(5, 22.0)   # below 10 %
        with self.assertRaises(ValueError):
            module.encode_aatt(101, 22.0)  # above 100 %

    def test_airing_bcd_round_trip(self):
        # 0x1745 = 17:45 (the daily airing hour the user observed)
        self.assertEqual(module.decode_airing_hhmm(0x1745), (17, 45))
        self.assertEqual(module.encode_airing_hhmm(17, 45), 0x1745)
        self.assertEqual(module.encode_airing_hhmm(19, 0), 0x1900)
        self.assertEqual(module.decode_airing_hhmm(0x1900), (19, 0))

    def test_airing_disabled_sentinel(self):
        # 0x2400 (24:00) = airing disabled; None/None encodes back to 0x2400
        self.assertIsNone(module.decode_airing_hhmm(0x2400))
        self.assertEqual(module.encode_airing_hhmm(None, None), 0x2400)

    def test_airing_rejects_bad_time(self):
        with self.assertRaises(ValueError):
            module.encode_airing_hhmm(30, 0)
        with self.assertRaises(ValueError):
            module.encode_airing_hhmm(12, 75)


if __name__ == "__main__":
    unittest.main()

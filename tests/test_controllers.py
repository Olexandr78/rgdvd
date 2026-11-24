import unittest

from rgdvd.controllers import (
    PRESETS, WheelControls, apply_deadzone, detect_preset,
)


class ControllerPresetTests(unittest.TestCase):
    def test_esperanza_name_selects_egw102_preset(self):
        self.assertEqual(
            detect_preset("Esperanza Nitro EGW102"), "esperanza_nitro_egw102")

    def test_manual_preset_overrides_device_name(self):
        self.assertEqual(
            detect_preset("USB Gamepad", "esperanza_nitro_egw102"),
            "esperanza_nitro_egw102")

    def test_generic_preset_is_available(self):
        self.assertIn("generic", PRESETS)

    def test_deadzone_and_normalization(self):
        self.assertEqual(apply_deadzone(0.02, 0.04), 0.0)
        self.assertAlmostEqual(apply_deadzone(1.0, 0.04), 1.0)
        self.assertAlmostEqual(apply_deadzone(-1.0, 0.04), -1.0)

    def test_wheel_controls_have_safe_keyboard_fallback_defaults(self):
        controls = WheelControls()
        self.assertEqual(controls.throttle, 0.0)
        self.assertEqual(controls.brake, 0.0)
        self.assertEqual(controls.steer, 0.0)
        self.assertFalse(controls.handbrake)
        self.assertFalse(controls.connected)


if __name__ == "__main__":
    unittest.main()

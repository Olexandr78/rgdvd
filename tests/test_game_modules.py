"""Smoke tests for optional presentation and vehicle modules."""
import unittest


class GameModuleImportTests(unittest.TestCase):
    def test_map_audio_and_volga_modules_import(self):
        from rgdvd.audio import VehicleAudio
        from rgdvd.map_screen import WorldMapScreen
        from rgdvd.vehicle import VolgaCar

        self.assertTrue(callable(VehicleAudio))
        self.assertTrue(callable(WorldMapScreen))
        self.assertTrue(issubclass(VolgaCar, __import__(
            "rgdvd.vehicle", fromlist=["SportsCar"]).SportsCar))


if __name__ == "__main__":
    unittest.main()

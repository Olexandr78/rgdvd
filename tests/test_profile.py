import tempfile
import unittest
from pathlib import Path

from rgdvd.profile import CareerProfile


class CareerProfileTests(unittest.TestCase):
    def test_profile_starts_with_starter_car_and_credits(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = CareerProfile(Path(folder) / "career.json")
            self.assertEqual(profile.credits, CareerProfile.STARTING_CREDITS)
            self.assertTrue(profile.is_unlocked("street_gt"))
            self.assertFalse(profile.is_unlocked("touring_v8"))

    def test_race_payout_and_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "career.json"
            profile = CareerProfile(path)
            result = profile.record_race(120.5, 3.2, 1, 55.2)
            self.assertGreater(result["payout"], 1800)
            self.assertEqual(profile.data["wins"], 1)
            reloaded = CareerProfile(path)
            self.assertEqual(reloaded.credits, profile.credits)
            self.assertAlmostEqual(reloaded.data["best_lap_seconds"], 55.2)

    def test_unlocks_car_after_required_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = CareerProfile(Path(folder) / "career.json")
            for _ in range(5):
                profile.record_race(100, 2.0, 1, None)
            self.assertTrue(profile.is_unlocked("touring_v8"))


if __name__ == "__main__":
    unittest.main()

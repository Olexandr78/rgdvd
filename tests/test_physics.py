import unittest

from rgdvd.physics import Controls, VehiclePhysics


class VehiclePhysicsTests(unittest.TestCase):
    def test_default_spawn_matches_city_start(self):
        car = VehiclePhysics()
        self.assertEqual((car.x, car.y, car.heading), (0.0, -120.0, 0.0))

    def test_throttle_accelerates_and_upshifts(self):
        car = VehiclePhysics()
        for _ in range(60 * 10):
            car.update(Controls(throttle=1.0), 1 / 60)
        self.assertGreater(car.speed_kmh, 150)
        self.assertGreaterEqual(car.gear, 3)
        self.assertLessEqual(car.speed, car.MAX_FORWARD_MPS)

    def test_brake_stops_and_then_reverses(self):
        car = VehiclePhysics()
        for _ in range(60 * 4):
            car.update(Controls(throttle=1.0), 1 / 60)
        self.assertGreater(car.speed, 0)
        for _ in range(60 * 6):
            car.update(Controls(brake=1.0), 1 / 60)
        self.assertLess(car.speed, 0)
        self.assertGreaterEqual(car.speed, -car.MAX_REVERSE_MPS)

    def test_steering_changes_heading(self):
        car = VehiclePhysics()
        for _ in range(60 * 4):
            car.update(Controls(throttle=1.0, steer=1.0), 1 / 60)
        self.assertGreater(car.heading, -1.57079632679)
        self.assertNotAlmostEqual(car.y, -120.0)

    def test_reset_restores_start_state(self):
        car = VehiclePhysics()
        for _ in range(60 * 3):
            car.update(Controls(throttle=1.0), 1 / 60)
        car.reset()
        self.assertAlmostEqual(car.x, 0.0)
        self.assertAlmostEqual(car.y, -120.0)
        self.assertAlmostEqual(car.heading, 0.0)
        self.assertAlmostEqual(car.speed, 0.0)
        self.assertEqual(car.gear, 1)

    def test_dt_is_clamped_and_finite(self):
        car = VehiclePhysics()
        car.update(Controls(throttle=1.0), 20.0)
        self.assertTrue(abs(car.speed) < 2.0)


if __name__ == "__main__":
    unittest.main()

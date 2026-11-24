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


    def test_handbrake_slows_car_without_service_brake(self):
        handbrake_car = VehiclePhysics()
        coasting_car = VehiclePhysics()
        for _ in range(60 * 3):
            handbrake_car.update(Controls(throttle=1.0), 1 / 60)
            coasting_car.update(Controls(throttle=1.0), 1 / 60)
        initial_speed = handbrake_car.speed
        for _ in range(60):
            handbrake_car.update(Controls(handbrake=True), 1 / 60)
            coasting_car.update(Controls(), 1 / 60)
        self.assertLess(handbrake_car.speed, initial_speed)
        self.assertLess(handbrake_car.speed, coasting_car.speed)

    def test_handbrake_builds_lateral_slip_while_turning(self):
        car = VehiclePhysics()
        for _ in range(60 * 2):
            car.update(Controls(throttle=1.0), 1 / 60)
        for _ in range(60):
            car.update(Controls(throttle=0.2, steer=0.8, handbrake=True), 1 / 60)
        self.assertGreater(abs(car.lateral_speed), 1.0)

    def test_manual_transmission_does_not_auto_shift(self):
        car = VehiclePhysics()
        car.set_transmission_mode("manual")
        for _ in range(60 * 10):
            car.update(Controls(throttle=1.0), 1 / 60)
        self.assertEqual(car.gear, 1)
        car.shift_up()
        self.assertEqual(car.gear, 2)
        car.shift_down()
        self.assertEqual(car.gear, 1)

    def test_automatic_transmission_still_shifts(self):
        car = VehiclePhysics()
        for _ in range(60 * 10):
            car.update(Controls(throttle=1.0), 1 / 60)
        self.assertGreaterEqual(car.gear, 3)

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

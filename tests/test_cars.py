import unittest

from rgdvd.cars import CAR_SPECS, unlocked_cars
from rgdvd.physics import Controls, VehiclePhysics


class VehicleGarageTests(unittest.TestCase):
    def test_starter_vehicle_is_available(self):
        self.assertIn("street_gt", unlocked_cars(["street_gt"]))
        self.assertEqual(CAR_SPECS["street_gt"]["required_wins"], 0)

    def test_volga_is_a_starter_car_with_classic_sedan_performance(self):
        self.assertEqual(CAR_SPECS["volga_2410"]["name"], "Volga GAZ-24-10")
        volga = VehiclePhysics(car_id="volga_2410")
        street = VehiclePhysics(car_id="street_gt")
        self.assertLess(volga.MAX_FORWARD_MPS, street.MAX_FORWARD_MPS)
        self.assertLess(volga.GRIP_MULTIPLIER, street.GRIP_MULTIPLIER)

    def test_locked_cars_do_not_appear_in_garage(self):
        self.assertEqual(unlocked_cars(["street_gt"]), ["street_gt"])

    def test_unlocked_cars_are_ordered_by_catalogue(self):
        self.assertEqual(
            unlocked_cars(["prototype_x", "street_gt", "touring_v8"]),
            ["street_gt", "touring_v8", "prototype_x"],
        )

    def test_car_presets_change_speed_and_grip(self):
        street = VehiclePhysics(car_id="street_gt")
        prototype = VehiclePhysics(car_id="prototype_x")
        self.assertGreater(prototype.MAX_FORWARD_MPS, street.MAX_FORWARD_MPS)
        self.assertGreater(prototype.TORQUE_MULTIPLIER, street.TORQUE_MULTIPLIER)
        for _ in range(60 * 5):
            street.update(Controls(throttle=1.0), 1/60)
            prototype.update(Controls(throttle=1.0), 1/60)
        self.assertGreater(prototype.speed, street.speed)

    def test_reset_keeps_selected_car(self):
        car = VehiclePhysics(car_id="track_special")
        car.reset()
        self.assertEqual(car.car_id, "track_special")
        self.assertGreater(car.GRIP_MULTIPLIER, 1.0)


if __name__ == "__main__":
    unittest.main()

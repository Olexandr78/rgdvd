import unittest

from rgdvd.city import UrbanCity


class UrbanCityRoadTests(unittest.TestCase):
    def setUp(self):
        # contains() only needs class constants; no scene graph is needed.
        self.city = UrbanCity.__new__(UrbanCity)

    def test_street_centrelines_are_drivable(self):
        self.assertTrue(self.city.contains(0.0, 0.0))
        self.assertTrue(self.city.contains(0.0, 120.0))
        self.assertTrue(self.city.contains(120.0, -240.0))

    def test_space_between_streets_is_not_road(self):
        self.assertFalse(self.city.contains(40.0, 40.0))
        self.assertFalse(self.city.contains(14.0, 60.0))

    def test_city_bounds_are_enforced(self):
        self.assertFalse(self.city.contains(961.0, 0.0))
        self.assertFalse(self.city.contains(0.0, -961.0))


if __name__ == "__main__":
    unittest.main()

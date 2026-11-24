import unittest

from rgdvd.events import EVENTS


class CityEventCatalogueTests(unittest.TestCase):
    def test_carbon_sized_event_catalogue(self):
        self.assertEqual(len(EVENTS), 53)
        self.assertEqual(sum(e.event_type == "CIRCUIT" for e in EVENTS), 24)
        self.assertEqual(sum(e.event_type == "SPRINT" for e in EVENTS), 29)

    def test_every_route_uses_existing_city_roads(self):
        for event in EVENTS:
            self.assertGreaterEqual(len(event.route), 4)
            for x, y in event.route:
                self.assertEqual(x % 120, 0)
                self.assertEqual(y % 120, 0)
                self.assertLessEqual(abs(x), 960)
                self.assertLessEqual(abs(y), 960)

    def test_circuits_have_two_laps_and_sprints_one(self):
        for event in EVENTS:
            if event.event_type == "CIRCUIT":
                self.assertEqual(event.laps, 2)
            else:
                self.assertEqual(event.laps, 1)


if __name__ == "__main__":
    unittest.main()

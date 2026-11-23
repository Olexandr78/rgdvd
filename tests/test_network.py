import unittest

from rgdvd.network import PROTOCOL, _decode, _encode


class NetworkProtocolTests(unittest.TestCase):
    def test_packet_round_trip(self):
        packet = {
            "protocol": PROTOCOL,
            "kind": "state",
            "id": "abc123",
            "state": {"x": 1.25, "y": -10.0},
        }
        self.assertEqual(_decode(_encode(packet)), packet)

    def test_rejects_other_protocol(self):
        self.assertIsNone(_decode(b'{"protocol":"other","kind":"state"}'))

    def test_rejects_invalid_json(self):
        self.assertIsNone(_decode(b"not json"))


if __name__ == "__main__":
    unittest.main()

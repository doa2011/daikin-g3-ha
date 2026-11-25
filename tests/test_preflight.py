import unittest

from daikin_g3.preflight import probe, validate_g3_identity


GOOD_INFO = {
    "model": "daikin",
    "device_id": "private-device-id",
    "firmware_version": "1.0.0-test",
    "protocol": "tmcp",
    "protocol_version": 2,
    "wire_version": 1,
    "default_wire_format": "msgpack",
    "wire_formats": ["msgpack"],
}


class FakeAdapter:
    def __init__(self):
        self.calls = []

    async def info(self):
        self.calls.append("info")
        return dict(GOOD_INFO)

    async def status(self):
        self.calls.append("status")
        return {"private_value": "do-not-export"}

    async def capabilities(self):
        self.calls.append("capabilities")
        return frozenset({"status.get", "screen.page.get"})

    async def call(self, *_args):
        raise AssertionError("authentication probe must never send commands")


class TestG3Authentication(unittest.IsolatedAsyncioTestCase):
    async def test_requires_real_community_g3_wire_identity(self):
        self.assertEqual(validate_g3_identity(GOOD_INFO), ("daikin", "1.0.0-test"))

    async def test_rejects_wrong_model_or_protocol(self):
        for key, value in (
            ("model", "m1"),
            ("protocol", "json"),
            ("protocol_version", 1),
            ("wire_version", 2),
            ("default_wire_format", "json"),
            ("wire_formats", ["json"]),
        ):
            info = dict(GOOD_INFO)
            info[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_g3_identity(info)

    async def test_probe_authenticates_and_checks_all_read_only_endpoints(self):
        adapter = FakeAdapter()
        result = await probe(adapter)
        self.assertEqual(adapter.calls, ["info", "status", "capabilities"])
        self.assertTrue(result.protocol_reachable)
        self.assertEqual(result.model, "daikin")
        self.assertEqual(result.firmware_version, "1.0.0-test")
        self.assertEqual(result.actions, frozenset({"status.get", "screen.page.get"}))
        self.assertNotIn("private-device-id", repr(result))
        self.assertNotIn("do-not-export", repr(result))

    async def test_empty_capabilities_are_preserved(self):
        adapter = FakeAdapter()
        async def empty():
            adapter.calls.append("capabilities")
            return frozenset()
        adapter.capabilities = empty
        self.assertEqual((await probe(adapter)).actions, frozenset())

    async def test_auth_failure_propagates_without_fallback_or_command(self):
        adapter = FakeAdapter()
        async def unauthorized():
            adapter.calls.append("info")
            raise PermissionError("unauthorized")
        adapter.info = unauthorized
        with self.assertRaises(PermissionError):
            await probe(adapter)
        self.assertEqual(adapter.calls, ["info"])

    async def test_invalid_status_stops_before_capabilities(self):
        adapter = FakeAdapter()
        async def invalid_status():
            adapter.calls.append("status")
            return ["not a map"]
        adapter.status = invalid_status
        with self.assertRaises(ValueError):
            await probe(adapter)
        self.assertEqual(adapter.calls, ["info", "status"])

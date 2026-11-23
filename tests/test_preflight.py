import unittest

from daikin_g3.preflight import probe


class FakeAdapter:
    def __init__(self):
        self.calls = []

    async def info(self):
        self.calls.append("info")
        return {"device_id": "private-device-id", "firmware_version": "v1.0.0"}

    async def status(self):
        self.calls.append("status")
        return {"private_value": "do-not-export"}

    async def capabilities(self):
        self.calls.append("capabilities")
        return frozenset({"status.get", "screen.page.get"})

    async def call(self, *_args):
        raise AssertionError("preflight must never send commands")


class TestPreflight(unittest.IsolatedAsyncioTestCase):
    async def test_only_read_only_endpoints_and_no_private_values(self):
        adapter = FakeAdapter()
        result = await probe(adapter)
        self.assertEqual(adapter.calls, ["info", "status", "capabilities"])
        self.assertTrue(result.protocol_reachable)
        self.assertEqual(result.actions, frozenset({"status.get", "screen.page.get"}))
        self.assertEqual(result.info_keys, ("device_id", "firmware_version"))
        self.assertEqual(result.status_keys, ("private_value",))
        self.assertNotIn("private-device-id", repr(result))
        self.assertNotIn("do-not-export", repr(result))

    async def test_empty_capabilities_are_not_fabricated(self):
        adapter = FakeAdapter()
        async def empty():
            return frozenset()
        adapter.capabilities = empty
        self.assertEqual((await probe(adapter)).actions, frozenset())

    async def test_invalid_info_rejected(self):
        adapter = FakeAdapter()
        async def invalid():
            adapter.calls.append("info")
            return ["not a map"]
        adapter.info = invalid
        with self.assertRaisesRegex(ValueError, "expected info and status maps"):
            await probe(adapter)
        self.assertEqual(adapter.calls, ["info"])

    async def test_auth_error_propagates_without_fallback(self):
        adapter = FakeAdapter()
        async def unauthorized():
            raise PermissionError("unauthorized")
        adapter.info = unauthorized
        with self.assertRaises(PermissionError):
            await probe(adapter)
        self.assertEqual(adapter.calls, [])

    async def test_invalid_status_rejected_without_capability_request(self):
        adapter = FakeAdapter()
        async def invalid_status():
            adapter.calls.append("status")
            return ["not a map"]
        adapter.status = invalid_status
        with self.assertRaisesRegex(ValueError, "expected info and status maps"):
            await probe(adapter)
        self.assertEqual(adapter.calls, ["info", "status"])

    async def test_invalid_capabilities_rejected_without_guessing(self):
        adapter = FakeAdapter()
        async def invalid_capabilities():
            adapter.calls.append("capabilities")
            return {"screen.page.get"}
        adapter.capabilities = invalid_capabilities
        with self.assertRaisesRegex(ValueError, "expected validated capability action set"):
            await probe(adapter)
        self.assertEqual(adapter.calls, ["info", "status", "capabilities"])

    async def test_protocol_error_propagates_without_fallback(self):
        adapter = FakeAdapter()
        async def bad_encoding():
            adapter.calls.append("status")
            raise ValueError("unexpected response encoding")
        adapter.status = bad_encoding
        with self.assertRaisesRegex(ValueError, "unexpected response encoding"):
            await probe(adapter)
        self.assertEqual(adapter.calls, ["info", "status"])

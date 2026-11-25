import unittest

from daikin_g3.preflight import probe, validate_g3_identity


class FakeAdapter:
    def __init__(self, info=None, actions=None, capability_error=None):
        self.info_data = {"model": "daikin"}
        if info is not None:
            self.info_data = info
        self.actions = frozenset({"status.get"}) if actions is None else actions
        self.capability_error = capability_error
        self.calls = []

    async def info(self):
        self.calls.append("info")
        return dict(self.info_data)

    async def capabilities(self):
        self.calls.append("capabilities")
        if self.capability_error:
            raise self.capability_error
        return self.actions

    async def status(self):
        raise AssertionError("status is not an onboarding requirement")

    async def call(self, *_args):
        raise AssertionError("onboarding must never send write commands")


class TestG3Authentication(unittest.IsolatedAsyncioTestCase):
    async def test_minimal_identity_requires_only_daikin_model(self):
        self.assertEqual(validate_g3_identity({"model": "daikin"}), ("daikin", ""))
        self.assertEqual(
            validate_g3_identity({"model": "daikin", "version": "community-test"}),
            ("daikin", "community-test"),
        )

    async def test_rejects_non_g3_model(self):
        for info in ({}, {"model": "m1"}, {"model": None}):
            with self.subTest(info=info), self.assertRaises(ValueError):
                validate_g3_identity(info)

    async def test_info_messagepack_map_is_core_authentication(self):
        adapter = FakeAdapter(info={"model": "daikin"})
        result = await probe(adapter)
        self.assertEqual(adapter.calls, ["info", "capabilities"])
        self.assertTrue(result.protocol_reachable)
        self.assertEqual(result.model, "daikin")
        self.assertEqual(result.firmware_version, "")
        self.assertEqual(result.actions, frozenset({"status.get"}))

    async def test_missing_optional_capabilities_does_not_block_setup(self):
        adapter = FakeAdapter(capability_error=RuntimeError("endpoint unavailable"))
        result = await probe(adapter)
        self.assertEqual(result.actions, frozenset())
        self.assertTrue(result.protocol_reachable)

    async def test_empty_capabilities_are_valid(self):
        adapter = FakeAdapter(actions=frozenset())
        self.assertEqual((await probe(adapter)).actions, frozenset())

    async def test_malformed_capabilities_are_ignored(self):
        adapter = FakeAdapter(actions=["not", "a", "frozenset"])
        self.assertEqual((await probe(adapter)).actions, frozenset())

    async def test_info_transport_or_auth_failure_still_propagates(self):
        adapter = FakeAdapter()
        async def unauthorized():
            adapter.calls.append("info")
            raise PermissionError("unauthorized")
        adapter.info = unauthorized
        with self.assertRaises(PermissionError):
            await probe(adapter)
        self.assertEqual(adapter.calls, ["info"])

    async def test_status_is_not_requested(self):
        adapter = FakeAdapter()
        await probe(adapter)
        self.assertNotIn("status", adapter.calls)

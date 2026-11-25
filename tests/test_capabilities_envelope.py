"""G3 capabilities command response validation (mocked, not device validation)."""
import unittest
from unittest.mock import AsyncMock

from daikin_g3.community import CommunityAdapter
from daikin_g3.protocol import ProtocolError


class TestCapabilitiesEnvelope(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = CommunityAdapter("http://127.0.0.1", "test")
        self.adapter.call = AsyncMock()

    def set_response(self, data):
        self.adapter.call.return_value = {
            "request_id": "test",
            "code": "ok",
            "data": data,
        }

    async def test_command_envelope(self):
        self.set_response({"actions": ["status.get", "screen.page.set"]})
        self.assertEqual(
            await self.adapter.capabilities(),
            frozenset({"status.get", "screen.page.set"}),
        )
        self.adapter.call.assert_awaited_once_with("capabilities.get", {})

    async def test_missing_data_map_is_rejected(self):
        self.adapter.call.return_value = {"request_id": "test", "code": "ok"}
        with self.assertRaisesRegex(ProtocolError, "invalid capabilities response"):
            await self.adapter.capabilities()

    async def test_unrelated_nested_actions_are_not_guessed(self):
        self.set_response({"other": {"actions": ["screen.page.set"]}})
        with self.assertRaisesRegex(ProtocolError, "unsupported actions format"):
            await self.adapter.capabilities()

    async def test_invalid_actions_are_rejected(self):
        for actions in (None, "status.get", ["status.get", ""], [42], {"status.get": True}):
            with self.subTest(actions=actions):
                self.set_response({"actions": actions})
                with self.assertRaisesRegex(ProtocolError, "unsupported actions format"):
                    await self.adapter.capabilities()

    async def test_empty_actions_is_valid_and_does_not_enable_features(self):
        self.set_response({"actions": []})
        self.assertEqual(await self.adapter.capabilities(), frozenset())

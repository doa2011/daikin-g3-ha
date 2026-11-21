"""G3 能力发现边界回归（模拟响应，不代表实机验证）。

同时验证上游普通 HTTP map 与命令响应 envelope 的兼容性，
并拒绝畸形 actions，防止误启用未确认的设备功能。
"""
import unittest
from unittest.mock import AsyncMock

from daikin_g3.community import CommunityAdapter
from daikin_g3.protocol import ProtocolError


class TestCapabilitiesEnvelope(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = CommunityAdapter("http://127.0.0.1", "test")

    async def test_plain_map(self):
        self.adapter._get = AsyncMock(return_value={"actions": ["status.get", "screen.page.set"]})
        self.assertEqual(
            await self.adapter.capabilities(),
            frozenset({"status.get", "screen.page.set"}),
        )
        self.adapter._get.assert_awaited_once_with("/api/v1/capabilities")

    async def test_command_envelope(self):
        self.adapter._get = AsyncMock(
            return_value={"code": "accepted", "data": {"actions": ["status.get"]}}
        )
        self.assertEqual(await self.adapter.capabilities(), frozenset({"status.get"}))

    async def test_unrelated_nested_actions_are_not_guessed(self):
        self.adapter._get = AsyncMock(
            return_value={"other": {"actions": ["screen.page.set"]}}
        )
        with self.assertRaisesRegex(ProtocolError, "unsupported actions format"):
            await self.adapter.capabilities()

    async def test_invalid_actions_are_rejected(self):
        for actions in (None, "status.get", ["status.get", ""], [42], {"status.get": True}):
            with self.subTest(actions=actions):
                self.adapter._get = AsyncMock(return_value={"actions": actions})
                with self.assertRaisesRegex(ProtocolError, "unsupported actions format"):
                    await self.adapter.capabilities()

    async def test_empty_actions_is_valid_and_does_not_enable_features(self):
        self.adapter._get = AsyncMock(return_value={"actions": []})
        self.assertEqual(await self.adapter.capabilities(), frozenset())

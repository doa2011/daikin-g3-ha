"""能力发现到模块授权的组合测试（模拟能力，不代表 G3 实机验证）。"""
import unittest
from unittest.mock import AsyncMock

from daikin_g3.community import CommunityAdapter
from daikin_g3.core import Core, Module
from daikin_g3.protocol import ProtocolError


class TestCapabilityModuleIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = CommunityAdapter("http://127.0.0.1", "test")
        self.adapter.capabilities = AsyncMock()
        self.adapter.call = AsyncMock(return_value={"code": "accepted"})
        self.core = Core(self.adapter)
        self.core.register(Module(
            "screen", frozenset({"screen.page.set"}),
            frozenset({"screen.page.set"}),
        ))

    async def test_supported_action_enables_module_and_dispatches(self):
        self.adapter.capabilities.return_value = frozenset({"status.get", "screen.page.set"})
        await self.core.enable("screen")
        await self.core.call("screen", "screen.page.set", {"page": 1})
        self.assertEqual(self.adapter.capabilities.await_count, 2)  # enable + pre-dispatch revalidation
        self.adapter.call.assert_awaited_once_with("screen.page.set", {"page": 1})

    async def test_unsupported_action_cannot_enable_module(self):
        self.adapter.capabilities.return_value = frozenset({"status.get"})
        with self.assertRaisesRegex(RuntimeError, "unsupported capabilities"):
            await self.core.enable("screen")
        with self.assertRaisesRegex(RuntimeError, "module disabled"):
            await self.core.call("screen", "screen.page.set", {"page": 1})
        self.adapter.call.assert_not_awaited()

    async def test_malformed_capabilities_never_enable_module(self):
        self.adapter.capabilities.side_effect = ProtocolError("unsupported actions format")
        with self.assertRaises(ProtocolError):
            await self.core.enable("screen")
        self.assertNotIn("screen", self.core.enabled)
        self.adapter.call.assert_not_awaited()

    async def test_unlisted_action_is_blocked_after_enable(self):
        self.adapter.capabilities.return_value = frozenset({"screen.page.set", "status.get"})
        await self.core.enable("screen")
        with self.assertRaisesRegex(RuntimeError, "action not allowed"):
            await self.core.call("screen", "status.get", {})
        self.adapter.call.assert_not_awaited()

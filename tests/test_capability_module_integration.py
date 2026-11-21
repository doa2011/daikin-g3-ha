"""能力发现到模块授权的组合测试（模拟响应，非 G3 实机验证）。

确保上游返回的能力列表真正限制模块启用及可执行动作。
不改动生产代码，不发送设备写命令。
"""
import unittest
from unittest.mock import AsyncMock

from daikin_g3.community import CommunityAdapter
from daikin_g3.core import Core, Module
from daikin_g3.protocol import ProtocolError


class TestCapabilityModuleIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = CommunityAdapter("http://127.0.0.1", "test")
        self.adapter._get = AsyncMock()
        self.adapter.call = AsyncMock(return_value={"code": "accepted"})
        self.core = Core(self.adapter)
        self.core.register(Module(
            "screen", frozenset({"screen.page.set"}),
            frozenset({"screen.page.set"}),
        ))

    async def test_supported_action_enables_module_and_dispatches(self):
        self.adapter._get.return_value = {"actions": ["status.get", "screen.page.set"]}
        await self.core.enable("screen")
        await self.core.call("screen", "screen.page.set", {"page": 1})
        self.adapter.call.assert_awaited_once_with("screen.page.set", {"page": 1})

    async def test_unsupported_action_cannot_enable_module(self):
        self.adapter._get.return_value = {"actions": ["status.get"]}
        with self.assertRaisesRegex(RuntimeError, "unsupported capabilities"):
            await self.core.enable("screen")
        with self.assertRaisesRegex(RuntimeError, "module disabled"):
            await self.core.call("screen", "screen.page.set", {"page": 1})
        self.adapter.call.assert_not_awaited()

    async def test_malformed_capabilities_never_enable_module(self):
        self.adapter._get.return_value = {"actions": ["screen.page.set", 7]}
        with self.assertRaises(ProtocolError):
            await self.core.enable("screen")
        self.assertNotIn("screen", self.core.enabled)
        self.adapter.call.assert_not_awaited()

    async def test_unlisted_action_is_blocked_after_enable(self):
        self.adapter._get.return_value = {"actions": ["screen.page.set", "status.get"]}
        await self.core.enable("screen")
        with self.assertRaisesRegex(RuntimeError, "action not allowed"):
            await self.core.call("screen", "status.get", {})
        self.adapter.call.assert_not_awaited()

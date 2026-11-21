"""G3 动态能力撤销回归测试（模拟设备，不代表实机验证）。

验证已启用模块在能力变化时不会继续发送写命令；能力恢复后须重新启用。
对应 Core.call 的发送前能力复核保护。
"""
import unittest
from unittest.mock import AsyncMock

from daikin_g3.core import Core, Module


class TestCapabilityRevocation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = AsyncMock()
        self.adapter.capabilities.return_value = frozenset({"screen.page.set"})
        self.adapter.call.return_value = {"code": "accepted"}
        self.core = Core(self.adapter)
        self.core.register(Module(
            "screen", frozenset({"screen.page.set"}),
            frozenset({"screen.page.set"}),
        ))

    async def test_capability_revoked_blocks_dispatch_and_disables_module(self):
        await self.core.enable("screen")
        self.adapter.capabilities.return_value = frozenset({"status.get"})
        with self.assertRaisesRegex(RuntimeError, "module capabilities revoked"):
            await self.core.call("screen", "screen.page.set", {"page": 1})
        self.assertNotIn("screen", self.core.enabled)
        self.adapter.call.assert_not_awaited()

    async def test_capability_restoration_requires_explicit_reenable(self):
        await self.core.enable("screen")
        self.adapter.capabilities.return_value = frozenset()
        with self.assertRaisesRegex(RuntimeError, "module capabilities revoked"):
            await self.core.call("screen", "screen.page.set", {"page": 1})
        self.adapter.capabilities.return_value = frozenset({"screen.page.set"})
        with self.assertRaisesRegex(RuntimeError, "module disabled"):
            await self.core.call("screen", "screen.page.set", {"page": 2})
        await self.core.enable("screen")
        await self.core.call("screen", "screen.page.set", {"page": 3})
        self.adapter.call.assert_awaited_once_with("screen.page.set", {"page": 3})

    async def test_capability_query_failure_never_dispatches(self):
        await self.core.enable("screen")
        self.adapter.capabilities.side_effect = ConnectionError("device offline")
        with self.assertRaisesRegex(ConnectionError, "device offline"):
            await self.core.call("screen", "screen.page.set", {"page": 1})
        self.adapter.call.assert_not_awaited()

    async def test_still_supported_dispatches_once(self):
        await self.core.enable("screen")
        await self.core.call("screen", "screen.page.set", {"page": 4})
        self.adapter.call.assert_awaited_once_with("screen.page.set", {"page": 4})
        self.assertEqual(self.adapter.capabilities.await_count, 2)

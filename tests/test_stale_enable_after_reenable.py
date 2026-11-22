"""验证禁用后重新启用时，旧能力查询不能覆盖新一轮启用。仅模拟测试。"""
import asyncio
import unittest

from daikin_g3.core import Core, Module


class OrderedCapabilityAdapter:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.queries = 0
        self.calls = []

    async def capabilities(self):
        self.queries += 1
        if self.queries == 1:
            self.started.set()
            await self.release.wait()
        return frozenset({"screen.page.set"})

    async def call(self, action, params):
        self.calls.append((action, params))
        return {"code": "accepted"}


class TestStaleEnableAfterReenable(unittest.IsolatedAsyncioTestCase):
    async def test_old_enable_cannot_override_new_enable(self):
        adapter = OrderedCapabilityAdapter()
        core = Core(adapter)
        core.register(Module("screen", frozenset({"screen.page.set"}),
                             frozenset({"screen.page.set"})))
        old_task = asyncio.create_task(core.enable("screen"))
        try:
            await asyncio.wait_for(adapter.started.wait(), 2)
            core.disable("screen")
            await asyncio.wait_for(core.enable("screen"), 2)
            self.assertIn("screen", core.enabled)
            adapter.release.set()
            with self.assertRaisesRegex(RuntimeError, "module enable cancelled"):
                await asyncio.wait_for(old_task, 2)
            self.assertIn("screen", core.enabled)
            self.assertEqual(
                await core.call("screen", "screen.page.set", {"page": 1}),
                {"code": "accepted"},
            )
            self.assertEqual(adapter.calls, [("screen.page.set", {"page": 1})])
        finally:
            adapter.release.set()
            if not old_task.done():
                old_task.cancel()
                await asyncio.gather(old_task, return_exceptions=True)

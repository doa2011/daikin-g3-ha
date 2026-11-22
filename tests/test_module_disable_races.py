"""确定性异步竞争回归：仅使用模拟适配器，不代表 G3 实机验证。"""
import asyncio
import unittest

from daikin_g3.core import Core, Module


CAP = "screen.page.set"


class GatedAdapter:
    def __init__(self):
        self.capabilities_started = asyncio.Event()
        self.capabilities_release = asyncio.Event()
        self.dispatch_started = asyncio.Event()
        self.dispatch_release = asyncio.Event()
        self.gate_capabilities = False
        self.gate_dispatch = False
        self.calls = []

    async def capabilities(self):
        if self.gate_capabilities:
            self.capabilities_started.set()
            await self.capabilities_release.wait()
        return frozenset({CAP})

    async def call(self, action, params):
        self.calls.append((action, params))
        self.dispatch_started.set()
        if self.gate_dispatch:
            await self.dispatch_release.wait()
        return {"code": "accepted"}


class TestModuleDisableRaces(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = GatedAdapter()
        self.core = Core(self.adapter)
        self.core.register(Module("screen", frozenset({CAP}), frozenset({CAP})))

    async def test_disable_during_enable_cannot_resurrect_module(self):
        self.adapter.gate_capabilities = True
        task = asyncio.create_task(self.core.enable("screen"))
        try:
            await asyncio.wait_for(self.adapter.capabilities_started.wait(), 2)
            self.core.disable("screen")
            self.adapter.capabilities_release.set()
            with self.assertRaisesRegex(RuntimeError, "module enable cancelled"):
                await asyncio.wait_for(task, 2)
            self.assertNotIn("screen", self.core.enabled)
        finally:
            self.adapter.capabilities_release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_disable_during_command_capability_check_blocks_dispatch(self):
        await self.core.enable("screen")
        self.adapter.gate_capabilities = True
        task = asyncio.create_task(self.core.call("screen", CAP, {"page": 1}))
        try:
            await asyncio.wait_for(self.adapter.capabilities_started.wait(), 2)
            self.core.disable("screen")
            self.adapter.capabilities_release.set()
            with self.assertRaisesRegex(RuntimeError, "module disabled"):
                await asyncio.wait_for(task, 2)
            self.assertEqual(self.adapter.calls, [])
        finally:
            self.adapter.capabilities_release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_disable_after_dispatch_does_not_retroactively_cancel_io(self):
        await self.core.enable("screen")
        self.adapter.gate_dispatch = True
        task = asyncio.create_task(self.core.call("screen", CAP, {"page": 2}))
        try:
            await asyncio.wait_for(self.adapter.dispatch_started.wait(), 2)
            self.core.disable("screen")
            self.adapter.dispatch_release.set()
            self.assertEqual(await asyncio.wait_for(task, 2), {"code": "accepted"})
            self.assertEqual(self.adapter.calls, [(CAP, {"page": 2})])
            self.assertNotIn("screen", self.core.enabled)
            with self.assertRaisesRegex(RuntimeError, "module disabled"):
                await self.core.call("screen", CAP, {"page": 3})
            self.assertEqual(len(self.adapter.calls), 1)
        finally:
            self.adapter.dispatch_release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

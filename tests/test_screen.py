import unittest
from daikin_g3.screen import Screen
from daikin_g3.protocol import ProtocolError

class Fake:
    def __init__(self):
        self.actions = {"screen.page.get","screen.page.set"}
        self.available = True
        self.calls = []
    async def capabilities(self):
        return frozenset(self.actions)
    async def call(self, action, params):
        self.calls.append((action, params))
        if action == "screen.page.get":
            return {"code":"ok","data":{"supported":True,"available":self.available}}
        return {"code":"accepted","data":{}}

class TestScreen(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = Fake()
        self.screen = Screen(self.adapter)
    async def test_next_previous(self):
        self.assertEqual((await self.screen.next())["code"],"accepted")
        self.assertEqual(self.adapter.calls[-1],("screen.page.set",{"direction":"next"}))
        await self.screen.previous()
        self.assertEqual(self.adapter.calls[-1],("screen.page.set",{"direction":"previous"}))
    async def test_page(self):
        await self.screen.goto(3)
        self.assertEqual(self.adapter.calls[-1],("screen.page.set",{"page":3}))
        for invalid in (0,9,True,3.0,"3"):
            with self.assertRaises(ValueError):
                await self.screen.goto(invalid)
    async def test_unsupported(self):
        self.adapter.actions.remove("screen.page.set")
        with self.assertRaises(ProtocolError): await self.screen.next()
        self.assertEqual(self.adapter.calls,[])
    async def test_unavailable(self):
        self.adapter.available = False
        with self.assertRaises(ProtocolError): await self.screen.next()
        self.assertEqual(len(self.adapter.calls),1)

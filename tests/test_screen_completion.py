import unittest
from daikin_g3.screen import Screen
from daikin_g3.protocol import ProtocolError

class Fake:
    def __init__(self, states):
        self.states = iter(states)
        self.writes = 0
    async def capabilities(self):
        return {"screen.page.get","screen.page.set"}
    async def call(self, action, params):
        if action == "screen.page.set":
            self.writes += 1
            return {"code":"accepted","data":{"request":7}}
        return {"code":"ok","data":next(self.states)}

def state(status, request=7, **kw):
    return {"supported":True,"available":True,"state":status,"request":request,**kw}

class Completion(unittest.IsolatedAsyncioTestCase):
    async def test_confirm(self):
        f = Fake([state("idle"),state("pending"),state("complete",current=3)])
        self.assertEqual((await Screen(f).goto(3,confirm=True))["current"],3)
        self.assertEqual(f.writes,1)
    async def test_errors(self):
        for status in ("invalid_page","mcu_busy","timeout"):
            f = Fake([state("idle"),state(status)])
            with self.assertRaisesRegex(ProtocolError,status):
                await Screen(f).next(confirm=True)
            self.assertEqual(f.writes,1)
    async def test_superseded(self):
        f = Fake([state("idle"),state("complete",request=8)])
        with self.assertRaisesRegex(ProtocolError,"superseded"):
            await Screen(f).next(confirm=True)
    async def test_disabled(self):
        f = Fake([state("idle",enabled_mask=1)])
        with self.assertRaisesRegex(ProtocolError,"disabled"):
            await Screen(f).goto(3)
        self.assertEqual(f.writes,0)
    async def test_timeout(self):
        f = Fake([state("pending")])
        with self.assertRaises(TimeoutError):
            await Screen(f).wait({"code":"accepted","data":{"request":7}},timeout=.01,interval=1)
    async def test_missing_request(self):
        with self.assertRaises(ProtocolError):
            await Screen(Fake([])).wait({"code":"accepted","data":{}})

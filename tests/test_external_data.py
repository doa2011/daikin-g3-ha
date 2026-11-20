import unittest
from daikin_g3.external_data import ExternalData,payload
from daikin_g3.protocol import ProtocolError

class Fake:
    def __init__(self,supported=True):
        self.supported=supported
        self.calls=[]
    async def capabilities(self):
        return {"screen.data.push"} if self.supported else set()
    async def call(self,action,params):
        self.calls.append((action,params))
        return {"code":"ok","data":{}}

class TestExternalData(unittest.IsolatedAsyncioTestCase):
    async def test_push(self):
        f=Fake()
        await ExternalData(f).push(1,[23.6],"客厅温度",120)
        self.assertEqual(f.calls,[("screen.data.push",{"id":1,"values":[23.6],"text":"客厅温度","ttl":120})])
    async def test_unsupported(self):
        f=Fake(False)
        with self.assertRaises(ProtocolError):
            await ExternalData(f).push(1)
        self.assertEqual(f.calls,[])
    def test_limits(self):
        self.assertEqual(len(payload(65535,[1e9]*64,"中"*64,86400)["values"]),64)
        for args in [(0,), (True,), (65536,), (1,[True]), (1,[float("nan")]), (1,[float("inf")]), (1,[1e10]), (1,[0]*65), (1,[],"中"*65), (1,[],"a\x00b"), (1,[],"",0), (1,[],"",86401)]:
            with self.subTest(args=args),self.assertRaises(ValueError):
                payload(*args)
    def test_empty_not_zero(self):
        self.assertEqual(payload(1)["values"],[])

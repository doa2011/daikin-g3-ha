import unittest
from daikin_g3.diagnostics import Diagnostics
from daikin_g3.protocol import ProtocolError

class Fake:
    def __init__(self):
        self.rid=0
        self.offset=0
        self.change=False
        self.writes=[]
    async def capabilities(self):
        return {"screen.diagnostics."+x for x in ("get","start","stop","read")}
    async def call(self,action,params):
        if action!="screen.diagnostics.get":
            self.rid+=1
            self.offset=params.get("offset",0)
            self.writes.append((action,params))
            return {"code":"accepted","data":{"request":self.rid}}
        n=min(8,10-self.offset)
        return {"data":{"request":self.rid,"reply_request":self.rid,"available":True,"pending":False,"status":0,"generation":2 if self.change and self.offset else 1,"stored":10,"offset":self.offset,"returned":n,"records":[{"index":i} for i in range(self.offset,self.offset+n)]}}

class Tests(unittest.IsolatedAsyncioTestCase):
    async def test_read(self):
        f=Fake()
        result=await Diagnostics(f).read()
        self.assertEqual([x["index"] for x in result["records"]],list(range(10)))
        self.assertEqual(len(f.writes),2)
    async def test_generation(self):
        f=Fake()
        f.change=True
        with self.assertRaisesRegex(ProtocolError,"capture changed"):
            await Diagnostics(f).read()
    async def test_start_stop(self):
        f=Fake()
        d=Diagnostics(f)
        await d.start("page",3)
        await d.stop()
        self.assertEqual(f.writes[0][1],{"mode":"page","page":3})
    async def test_invalid(self):
        with self.assertRaises(ValueError):
            await Diagnostics(Fake()).start("page",True)

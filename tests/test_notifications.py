import asyncio
import unittest
from io import BytesIO
from PIL import Image
from daikin_g3.notifications import Notifications,notification_payload
from daikin_g3.protocol import ProtocolError

class Fake:
    def __init__(self):
        self.adapter=self
        self.lock=asyncio.Lock()
        self.calls=[]
        self.duplicate=False
    async def capabilities(self): return {"screen.media.get","screen.push.send","screen.push.dismiss"}
    async def status(self): return {"available":True,"messages":[{"id":1}] if self.duplicate else []}
    async def upload(self,ident,image): self.calls.append(("upload",ident))
    async def command(self,action,params):
        self.calls.append((action,params))
        return {"ok":True}

class Tests(unittest.IsolatedAsyncioTestCase):
    def test_validation(self):
        for settings in ({"title":"中"*22},{"text":"x"*513},{"seconds":0},{"wake":1},{}):
            with self.assertRaises(ValueError): notification_payload(1,**settings)
    async def test_text(self):
        f=Fake()
        await Notifications(f).send(1,title="Alarm",confirm=True)
        self.assertEqual(f.calls[0][1]["mode"],"confirm")
    async def test_snapshot(self):
        out=BytesIO()
        Image.new("RGB",(20,20)).save(out,format="PNG")
        f=Fake()
        await Notifications(f).send(1,source=out.getvalue(),image_id=2)
        self.assertEqual(f.calls[0],("upload",2))
        self.assertEqual(f.calls[1][1]["image_id"],2)
    async def test_duplicate(self):
        f=Fake()
        f.duplicate=True
        with self.assertRaises(ProtocolError): await Notifications(f).send(1,title="Alarm")
    async def test_dismiss(self):
        f=Fake()
        await Notifications(f).dismiss(1)
        self.assertEqual(f.calls,[("screen.push.dismiss",{"id":1})])

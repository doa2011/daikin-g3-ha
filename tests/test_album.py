import asyncio
import tempfile
import unittest
from pathlib import Path
from io import BytesIO
from PIL import Image
from daikin_g3.album import Album,photos
from daikin_g3.protocol import ProtocolError

class Fake:
    def __init__(self):
        self.adapter=self
        self.lock=asyncio.Lock()
        self.notice=None
        self.cancelled=[]
        self.busy=False
    async def capabilities(self): return {"screen.push.send","screen.media.cancel"}
    async def status(self):
        return {"active_id":1 if self.busy else 0,"messages":[{"id":self.notice,"state":"timedout"}] if self.notice else []}
    async def upload(self,ident,image): self.image_id=ident
    async def command(self,action,params):
        self.notice=params["id"]
        self.params=params
    async def cancel(self,ident): self.cancelled.append(ident)

def source():
    out=BytesIO()
    Image.new("RGB",(20,20)).save(out,format="PNG")
    return out.getvalue()

class Tests(unittest.IsolatedAsyncioTestCase):
    async def test_show(self):
        f=Fake()
        self.assertEqual(await Album(f).show(source(),seconds=5),"timedout")
        self.assertEqual(f.params["duration_ms"],5000)
        self.assertFalse(f.params["wake"])
        self.assertEqual(f.cancelled,[f.image_id])
    async def test_busy(self):
        f=Fake()
        f.busy=True
        with self.assertRaises(ProtocolError): await Album(f).show(source())
    async def test_invalid(self):
        with self.assertRaises(ValueError): await Album(Fake()).show(source(),seconds=0)
    def test_photos(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("b.JPG","a.png","c.txt"): Path(d,n).touch()
            self.assertEqual([p.name for p in photos(d)],["a.png","b.JPG"])

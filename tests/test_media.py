import unittest
import base64
import zlib
from daikin_g3.images import PreparedImage
from daikin_g3.media import Media
from daikin_g3.protocol import ProtocolError

class Fake:
    def __init__(self):
        self.seq=0
        self.id=0
        self.phase="complete"
        self.calls=[]
        self.images=[]
        self.data=b""
        self.reject=False
    async def capabilities(self):
        return {"screen.media."+x for x in ("get","begin","chunk","commit","cancel")}
    async def call(self,action,params):
        if action=="screen.media.get":
            return {"data":{"available":True,"request":{"sequence":self.seq,"id":self.id,"state":self.phase,"result":0},"images":self.images}}
        self.calls.append((action,params))
        self.seq+=1
        self.id=params["id"]
        if action.endswith("chunk"):
            self.assert_offset(params)
            self.data+=base64.b64decode(params["bytes"])
            if self.reject: self.phase="rejected"
        if action.endswith("commit"):
            self.images=[{"id":self.id,"state":"ready","offset":len(self.data),"total":len(self.data),"crc32":zlib.crc32(self.data)&0xffffffff}]
        return {"code":"accepted","data":{"request":self.seq,"id":self.id}}
    def assert_offset(self,params):
        assert params["offset"]==len(self.data)

def image():
    data=b"x"*1025
    return PreparedImage(data,480,854,zlib.crc32(data)&0xffffffff)

class Tests(unittest.IsolatedAsyncioTestCase):
    async def test_upload(self):
        f=Fake()
        result=await Media(f).upload(7,image())
        self.assertEqual(result["state"],"ready")
        self.assertEqual([len(base64.b64decode(p["bytes"])) for a,p in f.calls if a.endswith("chunk")],[512,512,1])
        self.assertEqual(f.data,image().data)
    async def test_rejected(self):
        f=Fake()
        f.reject=True
        with self.assertRaises(ProtocolError): await Media(f).upload(7,image())
        self.assertEqual(len(f.calls),2)
    async def test_duplicate(self):
        f=Fake()
        f.images=[{"id":7}]
        with self.assertRaises(ProtocolError): await Media(f).upload(7,image())
        self.assertEqual(f.calls,[])
    async def test_cancel(self):
        f=Fake()
        await Media(f).cancel(7)
        self.assertEqual(f.calls[0],("screen.media.cancel",{"id":7}))

import unittest
import base64
import zlib
import struct
from unittest.mock import patch
from daikin_g3.community import CommunityAdapter
import msgpack
from daikin_g3.images import PreparedImage
from daikin_g3.media import Media
from daikin_g3.protocol import ProtocolError, AlbumPreempted

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

class BinaryFake(Fake):
    def __init__(self):
        super().__init__()
        self.binary_calls=[]
        self.bad=False
        self.fail=False

    async def call(self, action, params):
        reply=await super().call(action, params)
        if action=="screen.media.get":
            reply["data"]["binary_upload_supported"]=True
        return reply

    async def upload_jpeg(self, ident, prepared):
        self.binary_calls.append((ident, prepared))
        if self.fail:
            raise ProtocolError("interrupted upload")
        return {"id":ident,"state":"ready","total":len(prepared.data),
                "offset":len(prepared.data),"crc32":0 if self.bad else prepared.crc32}

class BinaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_fast_route_uses_one_upload(self):
        f=BinaryFake()
        result=await Media(f).upload(7,image())
        self.assertEqual(result["state"],"ready")
        self.assertEqual(f.binary_calls,[(7,image())])
        self.assertEqual(f.calls,[])

    async def test_integrity_failure_does_not_retry_legacy(self):
        f=BinaryFake()
        f.bad=True
        with self.assertRaisesRegex(ProtocolError,"integrity mismatch"):
            await Media(f).upload(7,image())
        self.assertEqual(len(f.binary_calls),1)
        self.assertEqual(f.calls,[])

    async def test_ambiguous_upload_does_not_retry_legacy(self):
        f=BinaryFake()
        f.fail=True
        with self.assertRaisesRegex(ProtocolError,"interrupted"):
            await Media(f).upload(7,image())
        self.assertEqual(f.calls,[])

    async def test_binary_envelope(self):
        a=CommunityAdapter("http://192.0.2.1")
        prepared=image()
        data={"id":7,"state":"ready","total":len(prepared.data),
              "offset":len(prepared.data),"crc32":prepared.crc32}
        with patch.object(a,"_request",return_value=msgpack.packb({"code":"ok","data":data},use_bin_type=True)) as request:
            self.assertEqual(await a.upload_jpeg(7,prepared),data)
        args,kwargs=request.call_args
        self.assertEqual(args[0],"/api/v1/screen/media/jpeg")
        self.assertEqual(struct.unpack("<IIIHH",args[1][:16]),(7,len(prepared.data),prepared.crc32,480,854))
        self.assertEqual(args[1][16:],prepared.data)
        self.assertEqual(kwargs["content_type"],"application/octet-stream")

class BatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_47732_bytes_use_twelve_bounded_requests(self):
        a=CommunityAdapter("http://192.0.2.1")
        raw=b"x"*47732
        photo=PreparedImage(raw,480,854,zlib.crc32(raw)&0xffffffff)
        calls=[]
        def request(path,body,**kw):
            ident,total,crc,w,h,at,epoch=struct.unpack("<IIIHHII",body[:24])
            self.assertEqual((ident,total,crc,w,h,epoch),(7,len(raw),photo.crc32,480,854,99))
            self.assertEqual(path,"/api/v1/screen/media/jpeg/batch")
            self.assertEqual(body[24:],raw[at:at+4096])
            self.assertLessEqual(len(body),4120)
            calls.append(at)
            end=at+len(body)-24
            return msgpack.packb({"code":"ok","data":{"id":ident,"total":total,
                "crc32":crc,"offset":end,"album_epoch":epoch,
                "state":"ready" if end==total else "receiving"}},use_bin_type=True)
        with patch.object(a,"_request",side_effect=request):
            receipt=await a.upload_album_batches(7,photo,99,4096)
        self.assertEqual(calls,list(range(0,len(raw),4096)))
        self.assertEqual(len(calls),12)
        self.assertEqual(receipt["state"],"ready")

    async def test_stale_epoch_rejected_before_upload(self):
        f=BinaryFake()
        original=f.call
        async def call(action,params):
            reply=await original(action,params)
            if action=="screen.media.get":
                reply["data"].update(album_epoch=2,binary_album_batch_bytes=4096)
            return reply
        f.call=call
        with self.assertRaises(AlbumPreempted):
            await Media(f).upload(7,image(),album_epoch=1)
        self.assertFalse(f.binary_calls)
        self.assertFalse(f.calls)

    async def test_batch_integrity_failure_not_replayed(self):
        a=CommunityAdapter("http://192.0.2.1")
        with patch.object(a,"_request",return_value=msgpack.packb({"code":"ok","data":{}},use_bin_type=True)) as req:
            with self.assertRaisesRegex(ProtocolError,"integrity mismatch"):
                await a.upload_album_batches(7,image(),99,512)
        self.assertEqual(req.call_count,1)

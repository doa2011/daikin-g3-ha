"""Sequential JPEG upload with MCU acknowledgement."""
import asyncio
import base64
import zlib
from .protocol import ProtocolError

class Media:
    def __init__(self, adapter):
        self.adapter=adapter
        self.lock=asyncio.Lock()

    async def status(self):
        return (await self.adapter.call("screen.media.get",{}))["data"]

    async def command(self, action, params):
        receipt=await self.adapter.call(action,params)
        data=receipt.get("data",{})
        seq=data.get("request")
        ident=data.get("id")
        if receipt.get("code")!="accepted" or type(seq) is not int or not 0<seq<=0xffffffff or ident!=params.get("id"):
            raise ProtocolError("invalid media receipt")
        async def poll():
            while True:
                state=await self.status()
                req=state.get("request",{})
                if req.get("sequence")!=seq or req.get("id")!=ident:
                    raise ProtocolError("media request superseded")
                phase=req.get("state")
                if phase=="complete" and req.get("result")==0:
                    return state
                if phase!="pending":
                    raise ProtocolError("media "+str(phase))
                await asyncio.sleep(.05)
        return await asyncio.wait_for(poll(),8)

    async def upload(self, image_id, image):
        if type(image_id) is not int or not 0<image_id<=0xffffffff:
            raise ValueError("invalid image ID")
        data=image.data
        if not isinstance(data,bytes) or not 1<=len(data)<=131072 or not 1<=image.width<=480 or not 1<=image.height<=854 or image.crc32!=(zlib.crc32(data)&0xffffffff):
            raise ValueError("invalid prepared image")
        async with self.lock:
            actions=await self.adapter.capabilities()
            if not {"screen.media.get","screen.media.begin","screen.media.chunk","screen.media.commit"}<=actions:
                raise ProtocolError("media upload unsupported")
            state=await self.status()
            if not state.get("available"):
                raise ProtocolError("media unavailable")
            if any(x.get("id")==image_id for x in state.get("images",[])):
                raise ProtocolError("image ID already exists")
            if state.get("binary_upload_supported") is True and callable(getattr(self.adapter, "upload_jpeg", None)):
                entry = await self.adapter.upload_jpeg(image_id, image)
                if (entry.get("id"), entry.get("state"), entry.get("total"),
                        entry.get("offset"), entry.get("crc32")) != (
                        image_id, "ready", len(data), len(data), image.crc32):
                    raise ProtocolError("binary image integrity mismatch")
                return entry
            await self.command("screen.media.begin",{"id":image_id,"total":len(data),"crc32":image.crc32,"width":image.width,"height":image.height})
            for offset in range(0,len(data),512):
                await self.command("screen.media.chunk",{"id":image_id,"offset":offset,"bytes":base64.b64encode(data[offset:offset+512]).decode("ascii")})
            await self.command("screen.media.commit",{"id":image_id})
            async def ready():
                while True:
                    state=await self.status()
                    for entry in state.get("images",[]):
                        if entry.get("id")==image_id and entry.get("state")=="ready":
                            if (entry.get("total"),entry.get("offset"),entry.get("crc32"))!=(len(data),len(data),image.crc32):
                                raise ProtocolError("image integrity mismatch")
                            return entry
                    await asyncio.sleep(.1)
            return await asyncio.wait_for(ready(),5)

    async def cancel(self,image_id):
        if type(image_id) is not int or not 0<image_id<=0xffffffff:
            raise ValueError("invalid image ID")
        async with self.lock:
            if "screen.media.cancel" not in await self.adapter.capabilities():
                raise ProtocolError("cancel unsupported")
            return await self.command("screen.media.cancel",{"id":image_id})

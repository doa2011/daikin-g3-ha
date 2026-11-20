"""Text and snapshot notifications over acknowledged media commands."""
import asyncio
from .images import prepare_image
from .protocol import ProtocolError

def notification_payload(notice_id, *, title="", text="", image_id=0, seconds=10, confirm=False, wake=True, brightness=30):
    for ident,minimum in ((notice_id,1),(image_id,0)):
        if type(ident) is not int or not minimum<=ident<=0xffffffff:
            raise ValueError("invalid ID")
    for value,limit in ((title,64),(text,512)):
        if not isinstance(value,str) or "\x00" in value or len(value.encode("utf-8"))>limit:
            raise ValueError("invalid notification text")
    if not (title or text or image_id):
        raise ValueError("empty notification")
    if type(seconds) is not int or not 1<=seconds<=3600 or type(brightness) is not int or not 1<=brightness<=100 or type(confirm) is not bool or type(wake) is not bool:
        raise ValueError("invalid notification settings")
    return {"id":notice_id,"image_id":image_id,"title":title,"text":text,"duration_ms":seconds*1000,"mode":"confirm" if confirm else "timed","wake":wake,"brightness":brightness}

class Notifications:
    def __init__(self,media):
        self.media=media
        self.lock=asyncio.Lock()

    async def send(self,notice_id, *, source=None, image_id=0, **settings):
        if (source is None)!=(image_id==0):
            raise ValueError("snapshot source and nonzero image ID must be supplied together")
        params=notification_payload(notice_id,image_id=image_id,**settings)
        async with self.lock:
            actions=await self.media.adapter.capabilities()
            if not {"screen.media.get","screen.push.send"}<=actions:
                raise ProtocolError("notifications unsupported")
            state=await self.media.status()
            if not state.get("available"):
                raise ProtocolError("media unavailable")
            if any(x.get("id")==notice_id for key in ("queue","messages") for x in state.get(key,[])):
                raise ProtocolError("notice ID already exists")
            if source is not None:
                image=await asyncio.to_thread(prepare_image,source)
                await self.media.upload(image_id,image)
            async with self.media.lock:
                return await self.media.command("screen.push.send",params)

    async def dismiss(self,notice_id):
        if type(notice_id) is not int or not 1<=notice_id<=0xffffffff:
            raise ValueError("invalid notice ID")
        async with self.lock:
            if "screen.push.dismiss" not in await self.media.adapter.capabilities():
                raise ProtocolError("dismiss unsupported")
            async with self.media.lock:
                return await self.media.command("screen.push.dismiss",{"id":notice_id})

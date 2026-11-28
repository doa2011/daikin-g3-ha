"""Persistent album notification using acknowledged in-place image replacement."""
import asyncio
import secrets
from .images import prepare_image
from .protocol import ProtocolError
from .screen import Screen

REQUIRED = {"screen.push.send", "screen.push.update", "screen.push.dismiss",
            "screen.media.get", "screen.media.begin", "screen.media.chunk",
            "screen.media.commit", "screen.media.cancel"}

class ContinuousAlbum:
    def __init__(self, media):
        self.media = media
        self.notice = None
        self.current = None
        self.pending = None

    async def prepare(self, source):
        if self.pending is not None:
            raise ProtocolError("album already has a prepared image")
        image = await asyncio.to_thread(prepare_image, source, fit="cover", max_bytes=65536)
        ident = secrets.randbelow(0x7fffffff) + 1
        epoch = getattr(self, "album_epoch", None)
        if epoch is None:
            await self.media.upload(ident, image)
        else:
            await self.media.upload(ident, image, album_epoch=epoch)
        self.pending = (ident, image)
        return image

    async def discard(self):
        if self.pending is not None:
            ident, _ = self.pending
            await self.media.cancel(ident)
            self.pending = None

    async def present(self, *, brightness, wake):
        if self.pending is None:
            raise ProtocolError("album image not prepared")
        ident, image = self.pending
        old = self.current
        first = self.notice is None
        # Once an operation is submitted, its outcome may be uncertain. Do not
        # cancel its image until a later explicit dismissal or confirmed swap.
        async with self.media.lock:
            state = await self.media.status()
            if first:
                if state.get("active_id") or state.get("queue"):
                    raise ProtocolError("screen occupied")
                await Screen(self.media.adapter).goto(6, confirm=True)
                self.notice = secrets.randbelow(0x7fffffff) + 1
            elif state.get("active_id") != self.notice:
                raise ProtocolError("album no longer visible")
            self.pending = None
            params = {"id": self.notice, "image_id": ident, "mode": "timed",
                      "duration_ms": 3600000, "brightness": brightness, "wake": wake}
            # Long duration is a bounded fail-safe if HA disappears. Updating
            # the same notice retains its queue position and existing overlay.
            await self.media.command("screen.push.send" if first else "screen.push.update", params)
            self.current = ident
            async def displayed():
                while True:
                    state = await self.media.status()
                    if state.get("active_id") == self.notice and any(
                        item.get("id") == self.notice and item.get("state") == "displayed"
                        for item in state.get("messages", [])):
                        return
                    await asyncio.sleep(.1)
            await asyncio.wait_for(displayed(), 30)
        if old is not None:
            await self.media.cancel(old)
        return image.data

    async def close(self):
        await self.discard()
        if self.notice is not None:
            async with self.media.lock:
                state = await self.media.status()
                # Never dismiss someone else's notification.
                if state.get("active_id") == self.notice or any(
                    item.get("id") == self.notice for item in state.get("queue", [])):
                    await self.media.command("screen.push.dismiss", {"id": self.notice})
            self.notice = None
        if self.current is not None:
            await self.media.cancel(self.current)
            self.current = None

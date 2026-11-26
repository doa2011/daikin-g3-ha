"""Native page-six album; uploaded JPEG IDs remain MCU-owned until replaced."""
import asyncio
from .continuous_album import ContinuousAlbum
from .protocol import ProtocolError
from .screen import Screen

NATIVE_REQUIRED = {"screen.album.set", "screen.album.clear", "screen.page.get",
                   "screen.media.get", "screen.media.begin", "screen.media.chunk",
                   "screen.media.commit", "screen.media.cancel"}

class NativeAlbum(ContinuousAlbum):
    def __init__(self, media):
        super().__init__(media)
        self.attempted = None

    async def present(self, *, brightness, wake):
        # Native page obeys the existing screen policy; do not change global
        # brightness, wake the panel, or steal the user's selected page.
        if self.pending is None:
            raise ProtocolError("album image not prepared")
        ident, image = self.pending
        if self.current is None:
            page = await Screen(self.media.adapter).state()
            if not page.get("available") or not page.get("supported") or not page.get("enabled_mask", 0) & (1 << 5):
                raise ProtocolError("enable page six before starting native album")
        old = self.current
        # The ordinary notification owns the common RGB arena until dismissed.
        # Do not hold the lock while waiting for another service to dismiss it.
        deadline = asyncio.get_running_loop().time() + 30
        while True:
            async with self.media.lock:
                state = await self.media.status()
                if not state.get("active_id") and not state.get("suspended"):
                    self.attempted = ident
                    await self.media.command("screen.album.set", {"id": ident})
                    self.current, self.pending, self.attempted = ident, None, None
                    break
            if asyncio.get_running_loop().time() >= deadline:
                raise ProtocolError("native album paused by screen notification")
            await asyncio.sleep(.25)
        if old is not None:
            await self.media.cancel(old)
        # ACK means decoded and pinned, not proof that the physical LCD is
        # displaying the image when the user is on a different page.
        return image.data

    async def close(self):
        # If set failed after submission its outcome may be uncertain. Try
        # only IDs belonging to this session; clear rejects mismatched IDs.
        ids = list(dict.fromkeys(x for x in (self.attempted, self.current) if x))
        if ids:
            failure = None
            for ident in ids:
                try:
                    async with self.media.lock:
                        await self.media.command("screen.album.clear", {"id": ident})
                    failure = None
                    break
                except ProtocolError as exc:
                    failure = exc
            if failure is not None:
                raise failure
        await self.discard()
        for ident in ids:
            await self.media.cancel(ident)
        self.current = self.attempted = None

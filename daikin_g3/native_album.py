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
        self.screen = Screen(media.adapter)
        self.previous_page = None

    async def present(self, *, brightness, wake):
        # Native JPEG is rendered only while MCU page six is selected. Select
        # it once for this session, then respect a manual page change by the
        # user rather than stealing the page back on every frame.
        if self.pending is None:
            raise ProtocolError("album image not prepared")
        ident, image = self.pending
        old = self.current
        first = self.current is None
        deadline = asyncio.get_running_loop().time() + 30
        while True:
            async with self.media.lock:
                state = await self.media.status()
                if (not state.get("active_id") and not state.get("queue")
                        and not state.get("suspended")):
                    page = await self.screen.state()
                    if (page.get("available") is not True
                            or page.get("supported") is not True
                            or not page.get("enabled_mask", 0) & (1 << 5)):
                        raise ProtocolError("enable page six before starting native album")
                    current_page = page.get("current")
                    if type(current_page) is not int or not 1 <= current_page <= 8:
                        raise ProtocolError("invalid current screen page")
                    if first:
                        if current_page != 6:
                            self.previous_page = current_page
                            # Wait for the MCU page ACK before asking it to
                            # render a native album frame on page six.
                            await self.screen.goto(6, confirm=True)
                    elif current_page != 6:
                        raise ProtocolError("album page changed by user")
                    self.attempted = ident
                    await self.media.command("screen.album.set", {"id": ident})
                    self.current, self.pending, self.attempted = ident, None, None
                    break
            if asyncio.get_running_loop().time() >= deadline:
                raise ProtocolError("native album paused by screen notification")
            await asyncio.sleep(.25)

        if old is not None:
            await self.media.cancel(old)
        # The MCU ACK confirms decode/pinning, not physical LCD scanout.
        return image.data

    async def close(self):
        # If set failed after submission its outcome may be uncertain. Clear
        # only IDs belonging to this session. Keep the old image pinned if
        # clear fails; never cancel an image that the MCU may still display.
        ids = list(dict.fromkeys(x for x in (self.attempted, self.current) if x))
        if ids or self.previous_page is not None:
            async with self.media.lock:
                if ids:
                    failure = None
                    for ident in ids:
                        try:
                            await self.media.command("screen.album.clear", {"id": ident})
                            failure = None
                            break
                        except ProtocolError as exc:
                            failure = exc
                    if failure is not None:
                        raise failure

                # Restore the page only if the user has not navigated away.
                # A manual page change always wins over the album's saved page.
                if self.previous_page is not None:
                    page = await self.screen.state()
                    if page.get("current") == 6:
                        await self.screen.goto(self.previous_page, confirm=True)
                    self.previous_page = None

        pending_id = self.pending[0] if self.pending is not None else None
        self.pending = None
        self.current = self.attempted = None
        for ident in dict.fromkeys(ids + ([pending_id] if pending_id else [])):
            await self.media.cancel(ident)

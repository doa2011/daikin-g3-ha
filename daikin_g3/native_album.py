"""Native page-six album; uploaded JPEG IDs remain MCU-owned until replaced."""
import asyncio
from .continuous_album import ContinuousAlbum
from .protocol import ProtocolError, AlbumPreempted
from .screen import Screen

NATIVE_REQUIRED = {"screen.album.set", "screen.album.clear", "screen.page.get", "screen.page.set",
                   "screen.media.get", "screen.media.begin", "screen.media.chunk",
                   "screen.media.commit", "screen.media.cancel"}


class NativeAlbum(ContinuousAlbum):
    def __init__(self, media):
        super().__init__(media)
        self.attempted = None
        self.screen = Screen(media.adapter)
        self.previous_page = None
        self.entered = False
        self.album_epoch = None
        self.preempted = False

    def _check_epoch(self, state):
        if state.get("ota_preparing") is True or (self.album_epoch is not None and
                state.get("album_epoch") != self.album_epoch):
            self.preempted = True
            raise AlbumPreempted("album stopped by device")
        if self.album_epoch is None and state.get("binary_album_batch_bytes"):
            epoch = state.get("album_epoch")
            if type(epoch) is not int or not 0 < epoch <= 0xffffffff:
                raise ProtocolError("album epoch unavailable")
            self.album_epoch = epoch

    async def check_ownership(self):
        self._check_epoch(await self.media.status())

    async def prepare(self, source):
        await self.check_ownership()
        try:
            return await super().prepare(source)
        except AlbumPreempted:
            self.preempted = True
            raise

    async def enter(self, *, wake=True):
        """Select page six before the first potentially long JPEG upload."""
        if self.entered:
            return
        deadline = asyncio.get_running_loop().time() + 30
        while True:
            async with self.media.lock:
                state = await self.media.status()
                self._check_epoch(state)
                if not state.get("active_id") and not state.get("queue") and not state.get("suspended"):
                    page = await self.screen.state()
                    if (page.get("available") is not True
                            or page.get("supported") is not True
                            or not page.get("enabled_mask", 0) & (1 << 5)):
                        raise ProtocolError("enable page six before starting native album")
                    current = page.get("current")
                    if type(current) is not int or not 1 <= current <= 8:
                        raise ProtocolError("invalid current screen page")
                    if current != 6:
                        self.previous_page = current
                    # A same-page request is deliberately sent when asleep:
                    # the MCU page request sets reminder_wake and the display
                    # policy consumes it on the next power tick.
                    if current != 6 or (wake and page.get("asleep") is True):
                        result = await self.screen.goto(6, confirm=True)
                        if result.get("current") != 6:
                            raise ProtocolError("MCU did not select album page six")
                    self.entered = True
                    return
            if asyncio.get_running_loop().time() >= deadline:
                raise ProtocolError("native album paused by screen notification")
            await asyncio.sleep(.25)

    async def present(self, *, brightness, wake):
        # Native JPEG is rendered only while MCU page six is selected. Select
        # it once for this session, then respect a manual page change by the
        # user rather than stealing the page back on every frame.
        if self.pending is None:
            raise ProtocolError("album image not prepared")
        ident, image = self.pending
        old = self.current
        await self.enter(wake=wake)
        deadline = asyncio.get_running_loop().time() + 30
        while True:
            async with self.media.lock:
                state = await self.media.status()
                self._check_epoch(state)
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
                    if current_page != 6:
                        raise ProtocolError("album page changed by user or display policy")
                    # The first JPEG upload can outlast the idle timeout.
                    # Recheck at presentation, not just at initial page entry.
                    # Do not wake for every later frame or override schedules.
                    if old is None and wake and page.get("asleep") is True:
                        result = await self.screen.goto(6, confirm=True)
                        if result.get("current") != 6 or result.get("asleep") is True:
                            raise ProtocolError("MCU did not wake for native album")
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
        if self.album_epoch is not None and not self.preempted:
            try:
                await self.check_ownership()
            except AlbumPreempted:
                pass
        if self.preempted:
            # The device now owns cancellation and cleanup. Never send a
            # stale clear/page request into a later album or OTA session.
            self.pending = self.current = self.attempted = None
            self.previous_page = None
            self.entered = False
            return
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
        self.entered = False
        for ident in dict.fromkeys(ids + ([pending_id] if pending_id else [])):
            await self.media.cancel(ident)

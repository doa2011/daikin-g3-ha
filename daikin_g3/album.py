"""Photo rotation on G3 layout page six using the firmware media overlay."""
import asyncio
from pathlib import Path
import random
import secrets

from .images import prepare_image
from .protocol import ProtocolError
from .screen import Screen

ALBUM_PAGE = 6


def photos(directory, *, shuffle=False):
    root = Path(directory)
    if not root.is_dir():
        raise ValueError("photo directory does not exist")
    paths = sorted(
        p for p in root.iterdir()
        if p.is_file() and not p.is_symlink()
        and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    )
    if shuffle:
        random.shuffle(paths)
    return paths


class Album:
    def __init__(self, media):
        self.media = media
        self.screen = Screen(media.adapter)
        self.lock = asyncio.Lock()

    async def show(self, source, *, seconds=30, brightness=30, wake=False, fit="cover"):
        if type(seconds) is not int or not 1 <= seconds <= 3600:
            raise ValueError("invalid album duration")
        if type(brightness) is not int or not 1 <= brightness <= 100:
            raise ValueError("invalid album brightness")
        if type(wake) is not bool:
            raise ValueError("invalid album wake setting")
        async with self.lock:
            actions = await self.media.adapter.capabilities()
            required = {"screen.push.send", "screen.media.cancel"}
            if not required <= actions:
                raise ProtocolError("photo media push unsupported")

            # Keep the user's normal page layout intact. Page six must already
            # exist and be enabled; we never rewrite the SCN3 layout implicitly.
            await self.screen.goto(ALBUM_PAGE, confirm=True)

            state = await self.media.status()
            if state.get("active_id") or state.get("queue") or state.get("request", {}).get("state") == "pending":
                raise ProtocolError("screen occupied")

            image = await asyncio.to_thread(prepare_image, source, fit=fit)
            image_id = secrets.randbelow(0x7fffffff) + 1
            notice_id = secrets.randbelow(0x7fffffff) + 1
            await self.media.upload(image_id, image)

            # Firmware displays uploaded photos through its timed media-push
            # view. The normal layout page remains set to page six underneath.
            # Do not resend or delete after ambiguous errors: a notice may
            # still reference its image.
            async with self.media.lock:
                await self.media.command(
                    "screen.push.send",
                    {
                        "id": notice_id,
                        "image_id": image_id,
                        "mode": "timed",
                        "duration_ms": seconds * 1000,
                        "brightness": brightness,
                        "wake": wake,
                    },
                )

                async def finished():
                    while True:
                        status = await self.media.status()
                        for item in status.get("messages", []):
                            if item.get("id") == notice_id:
                                phase = item.get("state")
                                if phase in (
                                    "timedout", "confirmed", "dismissed",
                                    "failed", "expired", "dropped", "evicted",
                                ):
                                    return phase
                        await asyncio.sleep(0.5)

                phase = await asyncio.wait_for(finished(), seconds + 30)

            await self.media.cancel(image_id)
            if phase not in ("timedout", "confirmed", "dismissed"):
                raise ProtocolError("album notice " + phase)
            return phase

    async def rotate(self, directory, *, shuffle=False, stop=None, **settings):
        paths = await asyncio.to_thread(photos, directory, shuffle=shuffle)
        if not paths:
            raise ValueError("no photos")
        while stop is None or not stop.is_set():
            for path in paths:
                if stop is not None and stop.is_set():
                    return

                def load():
                    with path.open("rb") as f:
                        data = f.read(25 * 1024 * 1024 + 1)
                    if len(data) > 25 * 1024 * 1024:
                        raise ValueError("photo file too large")
                    return data

                source = await asyncio.to_thread(load)
                await self.show(source, **settings)
            if shuffle:
                random.shuffle(paths)

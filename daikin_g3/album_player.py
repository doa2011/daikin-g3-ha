"""Per-device album playback, navigation and in-memory preview."""
import asyncio
from datetime import datetime, timezone
import random
import logging
from urllib.error import HTTPError
from .album import photos

_LOGGER = logging.getLogger(__name__)

def read_photo(path):
    with path.open("rb") as f:
        data = f.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        raise ValueError("photo file too large")
    return data

def _error_summary(exc):
    """Return actionable, credential-free diagnostics for album failures."""
    if isinstance(exc, HTTPError):
        parts = [f"HTTP {exc.code} {exc.reason}"]
        action = getattr(exc, "g3_action", "")
        path = getattr(exc, "g3_path", "")
        content_type = getattr(exc, "g3_content_type", "")
        body = " ".join(str(getattr(exc, "g3_body", "")).split())
        if action:
            parts.append(f"action={action}")
        if path:
            parts.append(f"path={path}")
        if content_type:
            parts.append(f"type={content_type}")
        if body:
            parts.append(f"response={body}")
        if getattr(exc, "g3_body_truncated", False):
            parts.append("response_truncated=true")
        return " ".join(parts)[:200]
    detail = str(exc).strip()
    return (f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__)[:200]


class AlbumPlayer:
    def __init__(self, album, *, scan=photos, changed=lambda: None, settings=None):
        self.album, self.scan, self.changed = album, scan, changed
        self.settings = {"directory": "/media/g3-album", "seconds": 30,
                         "brightness": 60, "shuffle": True, "wake": True}
        self.settings.update(settings or {})
        self.count, self.status, self.last_error = 0, "idle", None
        self.current, self.updated = None, None
        self._task, self._stop = None, False
        self._interrupt, self._lock = asyncio.Event(), asyncio.Lock()
        self._step = 1

    @property
    def running(self):
        return self._task is not None and not self._task.done()

    async def refresh(self):
        try:
            self.count = len(await asyncio.to_thread(self.scan, self.settings["directory"]))
        except (ValueError, OSError):
            self.count = 0
        self.changed()

    def _preview(self, data):
        self.current = data
        self.updated = datetime.now(timezone.utc)
        if not self._stop:
            self.status = "display_requested"
        self.changed()

    async def start_album(self, directory, *, shuffle=True, **settings):
        async with self._lock:
            if self.running:
                raise RuntimeError("album already running")
            paths = await asyncio.to_thread(self.scan, directory)
            if not paths:
                raise ValueError("no photos in selected album")
            self.settings.update(directory=directory, shuffle=shuffle, **settings)
            self.count, self._stop, self.last_error = len(paths), False, None
            self.status = "loading"
            self._task = asyncio.create_task(self._run(paths), name="g3-album-player")
            self.changed()
            return {"state": "running"}

    async def _run(self, paths):
        index = 0
        shuffled = bool(self.settings["shuffle"])
        if shuffled:
            random.shuffle(paths)
        try:
            while not self._stop:
                self._interrupt.clear()
                self._step = 1
                self.status = "loading"
                self.changed()
                source = await asyncio.to_thread(read_photo, paths[index])
                if self._stop:
                    break
                await self.album.show(source, seconds=self.settings["seconds"],
                    brightness=self.settings["brightness"], wake=self.settings["wake"],
                    interrupt=self._interrupt, on_display=self._preview)
                if self._stop:
                    break
                if shuffled != bool(self.settings["shuffle"]):
                    current = paths[index]
                    shuffled = bool(self.settings["shuffle"])
                    paths.sort()
                    if shuffled:
                        random.shuffle(paths)
                    index = paths.index(current)
                if shuffled and self._step == 1 and index == len(paths)-1 and len(paths)>1:
                    last = paths[index]
                    random.shuffle(paths)
                    if paths[0] == last:
                        paths[0], paths[1] = paths[1], paths[0]
                    index = 0
                else:
                    index = (index + self._step) % len(paths)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.last_error = _error_summary(exc)
            self.status = "error"
            _LOGGER.warning("G3 album playback stopped: %s", self.last_error)
        finally:
            if self.status != "error":
                self.status = "idle"
            self._task = None
            self.changed()

    def navigate(self, step):
        if not self.running or self._stop:
            raise RuntimeError("album is not running")
        self._step = step
        self._interrupt.set()

    async def stop_album(self):
        async with self._lock:
            task = self._task
            if task is not None:
                self._stop = True
                self.status = "stopping"
                self._interrupt.set()
                self.changed()
                await task
            return {"state": "stopped"}

    async def foreground(self):
        return await self.stop_album()

    async def close(self):
        await self.stop_album()

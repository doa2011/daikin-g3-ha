"""Per-device media task lifecycle for album playback and foreground events."""
import asyncio


class MediaTaskQueue:
    """Run one background album and let foreground services stop it safely.

    A stop request takes effect between photos. The in-flight G3 display command
    is allowed to reach a terminal state before another media operation starts.
    """

    def __init__(self, album):
        self.album = album
        self._lock = asyncio.Lock()
        self._task = None
        self._stop = None
        self.last_error = None

    async def start_album(self, directory, *, shuffle=False, **settings):
        async with self._lock:
            if self._task is not None and not self._task.done():
                raise RuntimeError("album already running")
            stop = asyncio.Event()
            self._stop = stop
            self.last_error = None
            self._task = asyncio.create_task(
                self._run(directory, shuffle=shuffle, stop=stop, **settings),
                name="daikin-g3-photo-album",
            )
            return {"state": "running"}

    async def _run(self, directory, *, shuffle, stop, **settings):
        try:
            await self.album.rotate(directory, shuffle=shuffle, stop=stop, **settings)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.last_error = exc

    async def stop_album(self):
        async with self._lock:
            task = self._task
            stop = self._stop
            if task is None:
                return {"state": "idle"}
            if not task.done() and stop is not None:
                stop.set()
        await task
        async with self._lock:
            if self._task is task:
                self._task = None
                self._stop = None
        if self.last_error is not None:
            raise RuntimeError("album playback failed") from self.last_error
        return {"state": "stopped"}

    async def foreground(self):
        """Stop background rotation before camera, dashboard or notification."""
        return await self.stop_album()

    async def close(self):
        await self.stop_album()

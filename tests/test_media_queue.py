"""Deterministic tests for album lifecycle and foreground handoff."""
import asyncio
import unittest
from unittest.mock import AsyncMock
from daikin_g3.media_queue import MediaTaskQueue

class TestMediaTaskQueue(unittest.IsolatedAsyncioTestCase):
    async def test_start_and_stop_album(self):
        class Album:
            async def rotate(self, directory, *, stop, **settings):
                self.started = directory
                await stop.wait()
        album=Album()
        queue=MediaTaskQueue(album)
        self.assertEqual(await queue.start_album("/media/photos",shuffle=True,seconds=10),{"state":"running"})
        await asyncio.sleep(0)
        self.assertEqual(album.started,"/media/photos")
        self.assertEqual(await queue.stop_album(),{"state":"stopped"})
        self.assertIsNone(queue._task)

    async def test_foreground_stops_album(self):
        album=AsyncMock()
        queue=MediaTaskQueue(album)
        await queue.foreground()
        album.rotate.assert_not_awaited()

    async def test_duplicate_start_rejected(self):
        class Album:
            async def rotate(self, directory, *, stop, **settings):
                await stop.wait()
        queue=MediaTaskQueue(Album())
        await queue.start_album("/photos")
        with self.assertRaisesRegex(RuntimeError,"already running"):
            await queue.start_album("/photos")
        await queue.close()

    async def test_album_error_propagates_on_stop(self):
        class Album:
            async def rotate(self, directory, **settings):
                raise ValueError("bad directory")
        queue=MediaTaskQueue(Album())
        await queue.start_album("/missing")
        await asyncio.sleep(0)
        with self.assertRaisesRegex(RuntimeError,"playback failed"):
            await queue.stop_album()

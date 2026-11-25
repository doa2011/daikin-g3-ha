import asyncio
import tempfile
import unittest
from pathlib import Path
from daikin_g3.album_player import AlbumPlayer

class FakeAlbum:
    def __init__(self):
        self.calls = asyncio.Queue()
    async def show(self, source, *, interrupt, on_display, **settings):
        on_display(source)
        await self.calls.put(source)
        await interrupt.wait()

class TestPlayer(unittest.IsolatedAsyncioTestCase):
    async def test_navigation_preview_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "a.jpg").write_bytes(b"a")
            Path(directory, "b.jpg").write_bytes(b"b")
            album = FakeAlbum()
            player = AlbumPlayer(album)
            await player.start_album(directory, shuffle=False)
            try:
                self.assertEqual(await asyncio.wait_for(album.calls.get(), 2), b"a")
                self.assertEqual(player.current, b"a")
                self.assertEqual(player.count, 2)
                player.navigate(1)
                self.assertEqual(await asyncio.wait_for(album.calls.get(), 2), b"b")
                player.navigate(-1)
                self.assertEqual(await asyncio.wait_for(album.calls.get(), 2), b"a")
            finally:
                await asyncio.wait_for(player.stop_album(), 2)
            self.assertFalse(player.running)
            self.assertEqual(player.status, "idle")
    async def test_empty_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            player = AlbumPlayer(FakeAlbum())
            with self.assertRaises(ValueError):
                await player.start_album(directory)

import asyncio
import tempfile
import unittest
from pathlib import Path
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError
from daikin_g3.album_player import AlbumPlayer

class FakeAlbum:
    def __init__(self):
        self.calls = asyncio.Queue()
    async def show(self, source, *, interrupt, on_display, **settings):
        on_display(source)
        await self.calls.put(source)
        await interrupt.wait()

class FailingAlbum:
    async def show(self, source, **settings):
        headers = Message()
        headers["Content-Type"] = "application/json"
        error = HTTPError(
            "http://192.0.2.1/api/v1/command", 404, "Not Found",
            headers, BytesIO(b'{"code":"unsupported_action"}')
        )
        error.g3_action = "screen.media.begin"
        error.g3_path = "/api/v1/command"
        error.g3_content_type = "application/json"
        error.g3_body = '{"code":"unsupported_action"}'
        raise error


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

    async def test_http_error_details_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "a.jpg").write_bytes(b"photo")
            player = AlbumPlayer(FailingAlbum())
            await player.start_album(directory, shuffle=False)
            task = player._task
            await asyncio.wait_for(task, 2)
            self.assertEqual(player.status, "error")
            self.assertIn("HTTP 404 Not Found", player.last_error)
            self.assertIn("action=screen.media.begin", player.last_error)
            self.assertIn("unsupported_action", player.last_error)

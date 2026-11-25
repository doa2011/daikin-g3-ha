import asyncio
import tempfile
import unittest
from pathlib import Path
from io import BytesIO

from PIL import Image

from daikin_g3.album import ALBUM_PAGE, Album, photos
from daikin_g3.protocol import ProtocolError


class Fake:
    def __init__(self, enabled_mask=0xFF):
        self.adapter = self
        self.lock = asyncio.Lock()
        self.notice = None
        self.cancelled = []
        self.busy = False
        self.enabled_mask = enabled_mask
        self.page = 1
        self.page_request = 0
        self.events = []

    async def capabilities(self):
        return {
            "screen.push.send", "screen.media.cancel",
            "screen.page.get", "screen.page.set",
        }

    async def status(self):
        return {
            "active_id": 1 if self.busy else 0,
            "messages": [{"id": self.notice, "state": "timedout"}] if self.notice else [],
        }

    async def upload(self, ident, image):
        self.events.append("upload")
        self.image_id = ident

    async def command(self, action, params):
        self.events.append(action)
        if action == "screen.page.get":
            return {
                "code": "ok",
                "data": {
                    "supported": True, "available": True,
                    "current": self.page, "enabled_mask": self.enabled_mask,
                    "count": self.enabled_mask.bit_count(),
                    "request": self.page_request, "state": "complete",
                },
            }
        if action == "screen.page.set":
            self.page = params["page"]
            self.page_request += 1
            return {"code": "accepted", "data": {"request": self.page_request}}
        if action == "screen.push.send":
            self.notice = params["id"]
            self.params = params
            return {"code": "accepted", "data": {"request": 1, "id": params["id"]}}
        raise AssertionError("unexpected command: " + action)

    async def cancel(self, ident):
        self.cancelled.append(ident)


def source():
    out = BytesIO()
    Image.new("RGB", (20, 20)).save(out, format="PNG")
    return out.getvalue()


class Tests(unittest.IsolatedAsyncioTestCase):
    async def test_show_selects_page_six_before_upload_and_push(self):
        f = Fake()
        self.assertEqual(await Album(f).show(source(), seconds=5), "timedout")
        self.assertEqual(f.page, ALBUM_PAGE)
        self.assertLess(f.events.index("screen.page.set"), f.events.index("upload"))
        self.assertEqual(f.params["duration_ms"], 5000)
        self.assertFalse(f.params["wake"])
        self.assertEqual(f.cancelled, [f.image_id])

    async def test_page_six_must_be_enabled(self):
        f = Fake(enabled_mask=0x1F)
        with self.assertRaisesRegex(ProtocolError, "page disabled"):
            await Album(f).show(source())
        self.assertNotIn("upload", f.events)

    async def test_busy(self):
        f = Fake()
        f.busy = True
        with self.assertRaises(ProtocolError):
            await Album(f).show(source())

    async def test_invalid(self):
        with self.assertRaises(ValueError):
            await Album(Fake()).show(source(), seconds=0)

    def test_photos(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("b.JPG", "a.png", "c.txt"):
                Path(d, n).touch()
            self.assertEqual([p.name for p in photos(d)], ["a.png", "b.JPG"])

    def test_missing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                photos(Path(d) / "missing")

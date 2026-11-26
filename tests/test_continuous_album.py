import asyncio
import unittest
from io import BytesIO
from PIL import Image
from daikin_g3.continuous_album import ContinuousAlbum
from test_album import Fake

class Media(Fake):
    def __init__(self):
        super().__init__()
        self.active = 0
        self.image = None
        self.events = []
    async def status(self):
        return {"active_id": self.active, "queue": [],
                "messages": [{"id": self.active, "state": "displayed"}] if self.active else []}
    async def upload(self, ident, image):
        self.events.append(("upload", ident, self.active))
    async def command(self, action, params):
        self.events.append((action, params["id"], self.active))
        if action == "screen.push.dismiss":
            self.active = 0
        else:
            self.active = params["id"]
            self.image = params["image_id"]

def photo(color):
    out = BytesIO()
    Image.new("RGB", (20,20), color).save(out, "PNG")
    return out.getvalue()

class Tests(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_and_swap_without_dismiss(self):
        media = Media()
        album = ContinuousAlbum(media)
        await album.prepare(photo("red"))
        await album.present(brightness=30, wake=True)
        old, notice = album.current, album.notice
        await album.prepare(photo("blue"))
        self.assertEqual(media.active, notice)
        self.assertEqual(media.image, old)
        self.assertEqual(media.cancelled, [])
        await album.present(brightness=30, wake=True)
        self.assertEqual(media.active, notice)
        self.assertNotEqual(media.image, old)
        self.assertEqual(media.cancelled, [old])
        self.assertTrue(any(isinstance(e, tuple) and e[0] == "screen.push.update" for e in media.events))
        await album.close()
        self.assertEqual(media.active, 0)
    async def test_discard_does_not_remove_current(self):
        media = Media()
        album = ContinuousAlbum(media)
        await album.prepare(photo("red"))
        await album.present(brightness=30, wake=True)
        old = album.current
        await album.prepare(photo("blue"))
        await album.discard()
        self.assertEqual(media.image, old)
        self.assertNotIn(old, media.cancelled)
        await album.close()

import unittest
from daikin_g3.native_album import NativeAlbum
from daikin_g3.protocol import ProtocolError
from test_continuous_album import Media, photo

class NativeMedia(Media):
    def __init__(self):
        super().__init__()
        self.fail = False

    async def command(self, action, params):
        ident = params["id"]
        self.events.append((action, ident, self.active))
        if action == "screen.album.set":
            if self.fail:
                raise ProtocolError("decode failed")
            self.image = ident
        elif action == "screen.album.clear":
            if self.image is not None and self.image != ident:
                raise ProtocolError("not owned")
            self.image = None
        else:
            raise AssertionError("not a native album command")

class TestNative(unittest.IsolatedAsyncioTestCase):
    async def test_swap_and_stop_without_notification_or_page_change(self):
        media = NativeMedia()
        album = NativeAlbum(media)
        await album.prepare(photo("red"))
        await album.present(brightness=60, wake=True)
        old = album.current
        await album.prepare(photo("blue"))
        self.assertEqual(media.image, old)
        self.assertEqual(media.cancelled, [])
        await album.present(brightness=60, wake=True)
        self.assertNotEqual(media.image, old)
        self.assertEqual(media.cancelled, [old])
        self.assertEqual(media.page, 1)
        await album.close()
        self.assertIsNone(media.image)

    async def test_failed_decode_keeps_old_and_can_stop(self):
        media = NativeMedia()
        album = NativeAlbum(media)
        await album.prepare(photo("red"))
        await album.present(brightness=60, wake=True)
        old = album.current
        await album.prepare(photo("blue"))
        media.fail = True
        with self.assertRaises(ProtocolError):
            await album.present(brightness=60, wake=True)
        self.assertEqual(media.image, old)
        self.assertNotIn(old, media.cancelled)
        await album.close()
        self.assertIsNone(media.image)

    async def test_disabled_page_rejected_without_switching(self):
        media = NativeMedia()
        media.enabled_mask = 0x1f
        album = NativeAlbum(media)
        await album.prepare(photo("red"))
        with self.assertRaisesRegex(ProtocolError, "enable page six"):
            await album.present(brightness=60, wake=True)
        self.assertIsNone(media.image)
        await album.close()

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
    async def test_swap_selects_page_six_and_restores_previous_page(self):
        media = NativeMedia()
        album = NativeAlbum(media)
        await album.prepare(photo("red"))
        await album.present(brightness=60, wake=True)
        old = album.current
        self.assertEqual(media.page, 6)
        self.assertEqual(media.image, old)
        await album.prepare(photo("blue"))
        self.assertEqual(media.image, old)
        self.assertEqual(media.cancelled, [])
        await album.present(brightness=60, wake=True)
        self.assertNotEqual(media.image, old)
        self.assertEqual(media.cancelled, [old])
        self.assertEqual(media.page, 6)
        await album.close()
        self.assertIsNone(media.image)
        self.assertEqual(media.page, 1)

    async def test_failed_decode_keeps_old_and_restores_page_on_stop(self):
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
        self.assertEqual(media.page, 1)

    async def test_disabled_page_rejected_without_switching(self):
        media = NativeMedia()
        media.enabled_mask = 0x1f
        album = NativeAlbum(media)
        await album.prepare(photo("red"))
        with self.assertRaisesRegex(ProtocolError, "enable page six"):
            await album.present(brightness=60, wake=True)
        self.assertEqual(media.page, 1)
        self.assertIsNone(media.image)
        await album.close()

    async def test_manual_page_change_wins_and_is_not_reverted(self):
        media = NativeMedia()
        album = NativeAlbum(media)
        await album.prepare(photo("red"))
        await album.present(brightness=60, wake=True)
        media.page = 2
        await album.prepare(photo("blue"))
        with self.assertRaisesRegex(ProtocolError, "album page changed by user"):
            await album.present(brightness=60, wake=True)
        await album.close()
        self.assertEqual(media.page, 2)
        self.assertIsNone(media.image)

    async def test_already_selected_page_six_is_not_changed_on_close(self):
        media = NativeMedia()
        media.page = 6
        album = NativeAlbum(media)
        await album.prepare(photo("red"))
        await album.present(brightness=60, wake=True)
        await album.close()
        self.assertEqual(media.page, 6)

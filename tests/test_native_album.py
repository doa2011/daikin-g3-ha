import unittest
from daikin_g3.native_album import NativeAlbum, NATIVE_REQUIRED
from daikin_g3.album_player import select_album_session
from daikin_g3.protocol import ProtocolError
from test_continuous_album import Media, photo


class NativeMedia(Media):
    def __init__(self):
        super().__init__()
        self.fail = False
        self.asleep = False
        self.ignore_wake = False

    async def call(self, action, params):
        reply = await super().call(action, params)
        if action == "screen.page.set" and not self.ignore_wake:
            self.asleep = False
        if action == "screen.page.get":
            reply["data"]["asleep"] = self.asleep
        return reply

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
    async def test_restart_on_sleeping_album_page_wakes_without_changing_saved_page(self):
        media = NativeMedia()
        media.page = 6
        media.asleep = True
        album = NativeAlbum(media)
        await album.enter(wake=True)
        self.assertFalse(media.asleep)
        self.assertIsNone(album.previous_page)
        await album.prepare(photo("red"))
        await album.present(brightness=60, wake=True)
        self.assertEqual(media.events.count("screen.page.set"), 1)
        await album.close()
        self.assertEqual(media.page, 6)

    async def test_first_upload_can_expire_idle_timer(self):
        media = NativeMedia()
        album = NativeAlbum(media)
        await album.enter(wake=True)
        await album.prepare(photo("red"))
        media.asleep = True
        await album.present(brightness=60, wake=True)
        self.assertFalse(media.asleep)
        self.assertEqual(media.events.count("screen.page.set"), 2)
        await album.prepare(photo("blue"))
        media.asleep = True
        await album.present(brightness=60, wake=True)
        # Subsequent frames do not repeatedly override display policy.
        self.assertTrue(media.asleep)
        self.assertEqual(media.events.count("screen.page.set"), 2)
        await album.close()

    async def test_wake_disabled_does_not_rewake_same_page(self):
        media = NativeMedia()
        media.page = 6
        media.asleep = True
        album = NativeAlbum(media)
        await album.enter(wake=False)
        await album.prepare(photo("red"))
        await album.present(brightness=60, wake=False)
        self.assertTrue(media.asleep)
        self.assertNotIn("screen.page.set", media.events)
        await album.close()

    async def test_first_frame_reports_unconfirmed_wake(self):
        media = NativeMedia()
        media.page = 6
        album = NativeAlbum(media)
        await album.enter()
        await album.prepare(photo("red"))
        media.asleep = True
        media.ignore_wake = True
        with self.assertRaisesRegex(ProtocolError, "did not wake"):
            await album.present(brightness=60, wake=True)
        self.assertIsNone(media.image)
        await album.close()


    async def test_enter_before_upload(self):
        media = NativeMedia()
        album = NativeAlbum(media)
        await album.enter()
        self.assertEqual(media.page, 6)
        await album.prepare(photo("red"))
        self.assertLess(media.events.index("screen.page.set"),
                        next(i for i, e in enumerate(media.events)
                             if isinstance(e, tuple) and e[0] == "upload"))
        await album.present(brightness=60, wake=True)
        self.assertEqual(media.events.count("screen.page.set"), 1)
        await album.close()

    async def test_negotiation_waits_for_ready_mcu(self):
        media = NativeMedia()
        states = iter([{"available": False, "native_album_supported": False},
                       {"available": True, "native_album_supported": True}])
        async def capabilities():
            return NATIVE_REQUIRED
        async def status():
            return next(states)
        media.capabilities = capabilities
        media.status = status
        self.assertIsInstance(await select_album_session(media, interval=.001), NativeAlbum)

    async def test_missing_page_set_not_silent_fallback(self):
        media = NativeMedia()
        async def capabilities():
            return NATIVE_REQUIRED - {"screen.page.set"}
        media.capabilities = capabilities
        with self.assertRaisesRegex(ProtocolError, "actions incomplete"):
            await select_album_session(media)

    async def test_not_ready_does_not_fallback(self):
        media = NativeMedia()
        async def capabilities():
            return NATIVE_REQUIRED
        async def status():
            return {"available": False, "native_album_supported": False}
        media.capabilities = capabilities
        media.status = status
        with self.assertRaisesRegex(ProtocolError, "negotiation timed out"):
            await select_album_session(media, timeout=0)

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
        with self.assertRaisesRegex(ProtocolError, "album page changed by user or display policy"):
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

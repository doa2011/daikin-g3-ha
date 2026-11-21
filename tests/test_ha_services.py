import unittest
from unittest.mock import AsyncMock
from daikin_g3.ha_services import dispatch

class TestServices(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.r={k:AsyncMock() for k in ("bridge","album","notifications")}
    async def test_message(self):
        await dispatch(self.r,"show_message",{"notice_id":1,"text":"hello","seconds":5})
        self.r["notifications"].send.assert_awaited_once_with(1,title="",text="hello",seconds=5)
    async def test_camera(self):
        await dispatch(self.r,"show_camera",{"camera":"camera.front","notice_id":2})
        args=self.r["bridge"].snapshot.await_args.args
        self.assertEqual(args[:3],(self.r["notifications"],"camera.front",2))
        self.assertGreater(args[3],0)
    async def test_dashboard(self):
        await dispatch(self.r,"show_dashboard",{"entities":["sensor.temp"]})
        self.r["bridge"].dashboard.assert_awaited_once_with(self.r["album"],"Dashboard",["sensor.temp"])
    async def test_dismiss(self):
        await dispatch(self.r,"dismiss",{"notice_id":3})
        self.r["notifications"].dismiss.assert_awaited_once_with(3)
    async def test_unknown(self):
        with self.assertRaises(ValueError):
            await dispatch(self.r,"unknown",{})

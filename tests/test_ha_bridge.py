import unittest
from unittest.mock import AsyncMock
from daikin_g3.ha_bridge import HABridge

class TestHABridge(unittest.IsolatedAsyncioTestCase):
    async def test_tiles(self):
        bridge=HABridge(AsyncMock(side_effect=[{"state":"23","attributes":{"unit_of_measurement":"C"}},None]),AsyncMock())
        tiles=await bridge.tiles(["sensor.temp","sensor.missing"])
        self.assertEqual((tiles[0].value,tiles[0].unit,tiles[1].value),("23","C","unavailable"))

    async def test_snapshot(self):
        camera=AsyncMock(return_value=b"image")
        bridge=HABridge(AsyncMock(),camera)
        notice=AsyncMock()
        await bridge.snapshot(notice,"camera.front",1,2,title="Door")
        notice.send.assert_awaited_once_with(1,source=b"image",image_id=2,title="Door")

    async def test_invalid_camera(self):
        camera=AsyncMock()
        bridge=HABridge(AsyncMock(),camera)
        with self.assertRaises(ValueError):
            await bridge.snapshot(AsyncMock(),"sensor.temp",1,2)
        camera.assert_not_awaited()

    async def test_empty_image(self):
        bridge=HABridge(AsyncMock(),AsyncMock(return_value=b""))
        with self.assertRaises(ValueError):
            await bridge.snapshot(AsyncMock(),"camera.front",1,2)

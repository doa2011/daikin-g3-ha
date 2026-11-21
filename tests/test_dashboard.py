import unittest
from io import BytesIO
from PIL import Image
from daikin_g3.dashboard import Tile,render_dashboard,show_dashboard

class Tests(unittest.IsolatedAsyncioTestCase):
    def test_dimensions(self):
        result=render_dashboard("Home",[Tile("Temperature","23.5","C")])
        self.assertLessEqual(len(result.data),131072)
        with Image.open(BytesIO(result.data)) as im:
            self.assertEqual(im.size,(480,854))
    def test_eight_tiles(self):
        result=render_dashboard("Energy",[Tile("Power","1234","W")]*8,theme="light")
        self.assertTrue(result.data.startswith(b"\xff\xd8"))
    def test_invalid(self):
        for tiles in ([],[Tile("a","b")]*9):
            with self.assertRaises(ValueError): render_dashboard("Home",tiles)
        with self.assertRaises(ValueError): render_dashboard("家庭",[Tile("a","b")])
    async def test_show(self):
        class Fake:
            async def show(self,data,**kwargs): return data,kwargs
        data,kwargs=await show_dashboard(Fake(),"Home",[Tile("CO2","400","ppm")],seconds=20)
        self.assertTrue(data.startswith(b"\xff\xd8"))
        self.assertEqual(kwargs["seconds"],20)

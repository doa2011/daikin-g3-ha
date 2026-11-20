import unittest
from io import BytesIO
import zlib
from PIL import Image
from daikin_g3.images import prepare_image

def source():
    out=BytesIO()
    Image.new("RGBA",(100,50),(255,0,0,128)).save(out,format="PNG")
    return out.getvalue()

class Tests(unittest.TestCase):
    def test_baseline(self):
        result=prepare_image(source())
        with Image.open(BytesIO(result.data)) as image:
            self.assertEqual(image.size,(480,854))
            self.assertEqual(image.format,"JPEG")
            self.assertFalse(image.info.get("progressive",False))
            self.assertEqual(image.mode,"RGB")
        self.assertLessEqual(len(result.data),131072)
        self.assertEqual(result.crc32,zlib.crc32(result.data)&0xffffffff)
    def test_cover(self):
        result=prepare_image(source(),width=160,height=120,fit="cover")
        self.assertEqual((result.width,result.height),(160,120))
    def test_budget(self):
        with self.assertRaises(ValueError): prepare_image(source(),max_bytes=10)
    def test_invalid(self):
        for kwargs in ({"width":481},{"height":855},{"fit":"stretch"},{"max_bytes":131073}):
            with self.assertRaises(ValueError): prepare_image(source(),**kwargs)

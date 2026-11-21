import unittest
from daikin_g3.core import Core, Module
class Fake:
    async def capabilities(self): return frozenset({'display'})
    async def call(self, action, params): return action, params
class TestCore(unittest.IsolatedAsyncioTestCase):
    async def test_lifecycle(self):
        c=Core(Fake()); c.register(Module('display',frozenset({'display'})))
        await c.enable('display'); self.assertEqual(await c.call('display','test',{}),('test',{}))
        c.disable('display')
        with self.assertRaises(RuntimeError): await c.call('display','test',{})
    async def test_capabilities(self):
        c=Core(Fake()); c.register(Module('album',frozenset({'media'})))
        with self.assertRaises(RuntimeError): await c.enable('album')
    async def test_duplicate(self):
        c=Core(Fake()); c.register(Module('display'))
        with self.assertRaises(ValueError): c.register(Module('display'))

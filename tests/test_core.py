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

class RestrictedFake:
    def __init__(self): self.calls = []
    async def capabilities(self): return frozenset({'screen.page.get', 'screen.page.set'})
    async def call(self, action, params):
        self.calls.append(action)
        return {'code': 'ok'}

class TestModuleActionIsolation(unittest.IsolatedAsyncioTestCase):
    async def test_restricted_module_cannot_send_unlisted_action(self):
        fake = RestrictedFake()
        core = Core(fake)
        core.register(Module('screen', frozenset({'screen.page.get', 'screen.page.set'}),
                             frozenset({'screen.page.get'})))
        await core.enable('screen')
        await core.call('screen', 'screen.page.get', {})
        with self.assertRaisesRegex(RuntimeError, 'not allowed'):
            await core.call('screen', 'screen.page.set', {'page': 2})
        self.assertEqual(fake.calls, ['screen.page.get'])

    async def test_invalid_module_policy_fails_at_registration(self):
        core = Core(RestrictedFake())
        with self.assertRaises(ValueError):
            core.register(Module('bad', frozenset({'screen.page.get'}),
                                 frozenset({'firmware.update'})))

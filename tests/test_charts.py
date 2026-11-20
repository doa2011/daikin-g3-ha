import unittest
from daikin_g3.charts import Charts,series_payload
from daikin_g3.protocol import ProtocolError

def series(values,unit="°C"):
    return {"name":"Room","unit":unit,"values":values}

class Tests(unittest.IsolatedAsyncioTestCase):
    def test_gaps(self):
        self.assertEqual(series_payload(1,[series([21,None,22])])["series"][0]["values"],[21,None,22])
    def test_bounds(self):
        for values in ([],[0]*33,[float("nan")],[1e10],[True]):
            with self.assertRaises(ValueError): series_payload(1,[series(values)])
        with self.assertRaises(ValueError): series_payload(1,[series([1])]*4)
    def test_additive(self):
        with self.assertRaises(ValueError): series_payload(1,[series([-1])],additive=True)
        with self.assertRaises(ValueError): series_payload(1,[series([1]),series([2],"W")],additive=True)
    async def test_push(self):
        class Fake:
            async def capabilities(self): return {"screen.data.series"}
            async def call(self,action,params): return action,params
        action,params=await Charts(Fake()).push(1,[series([1,None])])
        self.assertEqual(action,"screen.data.series")
        self.assertEqual(params["ttl"],60)
    async def test_unsupported(self):
        class Fake:
            async def capabilities(self): return set()
        with self.assertRaises(ProtocolError): await Charts(Fake()).push(1,[series([1])])

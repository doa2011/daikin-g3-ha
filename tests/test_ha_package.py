import tempfile
import unittest
import json
from scripts.package_ha import package

class TestPackage(unittest.TestCase):
    def test_package(self):
        with tempfile.TemporaryDirectory() as d:
            target=package(d)
            self.assertTrue((target/"daikin_g3"/"ha_native.py").is_file())
            self.assertTrue((target/"config_flow.py").is_file())
            self.assertEqual(json.loads((target/"manifest.json").read_text())["domain"],"daikin_g3")
            for p in target.rglob("*.py"):
                compile(p.read_text(),str(p),"exec")

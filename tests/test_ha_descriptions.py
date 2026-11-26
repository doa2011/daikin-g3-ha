import json
import unittest
from pathlib import Path

class TestDescriptions(unittest.TestCase):
    def test_service_descriptions(self):
        root=Path(__file__).resolve().parents[1]/"custom_components"/"daikin_g3"
        services=json.loads((root/"services.yaml").read_text())
        self.assertEqual(set(services),{"show_message","show_camera","show_dashboard","dismiss","start_album","stop_album"})
        for language in ("en","zh-Hans"):
            labels=json.loads((root/"translations"/(language+".json")).read_text())["services"]
            for name,service in services.items():
                self.assertEqual(set(service["fields"]),set(labels[name]["fields"]))
                self.assertTrue(service["fields"]["entry_id"]["required"])
        self.assertTrue(services["show_dashboard"]["fields"]["entities"]["selector"]["entity"]["multiple"])
        self.assertTrue(services["start_album"]["fields"]["directory"]["required"])

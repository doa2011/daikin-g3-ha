"""Install optional camera/stream prerequisites from the installed HA manifests.

The standalone CI harness does not invoke HA's integration dependency loader.
"""
from importlib.util import find_spec
from pathlib import Path
import json
import subprocess
import sys

def main():
    root=Path(find_spec("homeassistant").origin).parent/"components"
    requirements=set()
    for domain in ("camera","stream"):
        manifest=json.loads((root/domain/"manifest.json").read_text())
        requirements.update(manifest.get("requirements",[]))
    if not requirements:
        raise RuntimeError("Missing HA camera/stream requirements")
    print("HA camera/stream requirements:", sorted(requirements),flush=True)
    subprocess.run([sys.executable,"-m","pip","install",*sorted(requirements)],check=True)

if __name__=="__main__":
    main()

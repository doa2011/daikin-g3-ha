"""Stage a self-contained custom component without duplicating core sources in git."""
from pathlib import Path
from shutil import copytree
import sys

def package(destination):
    root=Path(__file__).resolve().parents[1]
    target=Path(destination)/"custom_components"/"daikin_g3"
    copytree(root/"custom_components"/"daikin_g3",target)
    copytree(root/"daikin_g3",target/"daikin_g3",ignore=lambda path,names: {"__pycache__"} & set(names))
    return target

if __name__=="__main__":
    package(sys.argv[1])

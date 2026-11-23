"""Put the plugin's scripts and assets on the import path for every test."""
import pathlib
import sys

BASE = pathlib.Path(__file__).parent.parent / "plugins/financial-skills"
for sub in ("scripts", "assets"):
    path = str(BASE / sub)
    if path not in sys.path:
        sys.path.insert(0, path)

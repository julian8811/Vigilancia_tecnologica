import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root / "apps" / "api"))
sys.path.insert(0, str(_root / "apps" / "worker"))

from app.main import app

import sys
from pathlib import Path


def pytest_configure():
    _api_app = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "api"
    if str(_api_app) not in sys.path:
        sys.path.insert(0, str(_api_app))

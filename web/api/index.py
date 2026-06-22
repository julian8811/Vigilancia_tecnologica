import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root / "api"))

try:
    from app.main import app as fastapi_app
    app = fastapi_app
except Exception as e:
    async def app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": f'{{"error":"{str(e)}"}}'.encode(),
        })

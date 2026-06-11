"""Quick test for whatsapp webhook"""
import asyncio
import sys
sys.path.insert(0, ".")

from starlette.datastructures import FormData

async def main():
    from app.main import app
    from app.config import get_settings
    from app.database import get_supabase_client
    from app.routers.webhooks import whatsapp_webhook
    from fastapi import Request

    s = get_settings()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/webhook/whatsapp",
        "raw_path": b"/webhook/whatsapp",
        "scheme": "http",
        "server": ("localhost", 8000),
        "headers": [
            (b"host", b"localhost:8000"),
            (b"content-type", b"application/x-www-form-urlencoded"),
            (b"x-twilio-signature", b"invalid"),
        ],
        "query_string": b"",
        "app": app,
    }
    req = Request(scope)

    async def mock_form():
        fd = FormData()
        fd._dict = {"Body": "cuantas frases hay de Einstein", "From": "whatsapp:+14155238886"}
        return fd

    req.form = mock_form
    req.app = app
    req.app.state.settings = s
    req.app.state.supabase = get_supabase_client(s)

    try:
        result = await whatsapp_webhook(req)
        print(f"Status: {result.status_code}")
        print(f"Body: {result.body[:300]}")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())

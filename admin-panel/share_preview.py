"""Capability-link gateway for sharing the local demo through an HTTPS tunnel.

Run locally on 127.0.0.1:8082; the application remains on 127.0.0.1:8080.
The private link is stored in data/share-preview.json. Rotating that file's
token and restarting this gateway revokes existing links and gate cookies.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "data" / "share-preview.json"
if not CONFIG.exists():
    CONFIG.parent.mkdir(exist_ok=True)
    CONFIG.write_text(json.dumps({"token": secrets.token_urlsafe(32)}, indent=2), encoding="utf-8")
TOKEN = json.loads(CONFIG.read_text(encoding="utf-8"))["token"]
COOKIE = "__Host-aq_preview"
UPSTREAM = "http://127.0.0.1:8080"
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade", "content-length"}


def signature(value: str) -> str:
    return hmac.new(TOKEN.encode(), value.encode(), hashlib.sha256).hexdigest()


def permitted(cookies) -> bool:
    value = cookies.get(COOKIE, "")
    expiry, _, digest = value.partition(".")
    return (len(expiry) == 10 and expiry.isascii() and expiry.isdigit() and len(digest) == 64
            and int(expiry) > time.time() and hmac.compare_digest(digest.encode(), signature(expiry).encode()))


@asynccontextmanager
async def lifespan(app):
    # No shared cookie jar: every visitor retains their own application session.
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
        app.state.client = client
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(request: Request, path: str):
    if request.method == "GET" and path.startswith("open/"):
        if not hmac.compare_digest(path[5:].encode(), TOKEN.encode()):
            return PlainTextResponse("Havola topilmadi.", status_code=404)
        expiry = str(int(time.time()) + 12 * 60 * 60)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(COOKIE, expiry + "." + signature(expiry), max_age=12 * 60 * 60,
                            secure=True, httponly=True, samesite="lax", path="/")
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex, nofollow, noarchive"})
        return response
    if not permitted(request.cookies):
        return PlainTextResponse("Maxsus kirish havolasidan foydalaning.", status_code=404,
                                 headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})
    raw_path = request.scope.get("raw_path", request.url.path.encode()).decode("ascii")
    target = UPSTREAM + raw_path
    if request.url.query:
        target += "?" + request.url.query
    headers = {key: value for key, value in request.headers.items()
               if key.lower() not in HOP_HEADERS and not key.lower().startswith("x-forwarded-")}
    headers["x-forwarded-proto"] = "https"
    headers["accept-encoding"] = "identity"
    # An explicit Request avoids using AsyncClient's stored response cookies.
    outbound = httpx.Request(request.method, target, headers=headers, content=await request.body())
    try:
        upstream = await request.app.state.client.send(outbound)
    except httpx.HTTPError:
        return PlainTextResponse("Panel vaqtincha mavjud emas.", status_code=502)
    response = Response(upstream.content, status_code=upstream.status_code)
    for key, value in upstream.headers.multi_items():
        if key.lower() not in HOP_HEADERS | {"content-encoding"}:
            response.headers.append(key, value)
    response.headers["Cache-Control"] = "no-store"
    # "no-referrer" faqat maxsus havola javobida qoladi: sahifalarga "no-referrer" qo'yilsa
    # brauzer forma POST'ida Origin: null yuboradi va ilovaning CSRF tekshiruvi rad etadi.
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@app.websocket("/ws/live")
async def live(socket: WebSocket):
    if not permitted(socket.cookies):
        await socket.close(code=4403)
        return
    if socket.headers.get("origin") != "https://" + socket.headers.get("host", ""):
        await socket.close(code=4403)
        return
    headers = {"Cookie": socket.headers.get("cookie", "")}
    try:
        async with connect("ws://127.0.0.1:8080/ws/live", additional_headers=headers) as upstream:
            await socket.accept()

            async def receive():
                while True:
                    await upstream.send(await socket.receive_text())

            async def send():
                async for message in upstream:
                    if isinstance(message, str):
                        await socket.send_text(message)

            tasks = [asyncio.create_task(receive()), asyncio.create_task(send())]
            try:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except (WebSocketDisconnect, ConnectionClosed, InvalidStatus, OSError):
        pass
    finally:
        try:
            await socket.close()
        except RuntimeError:
            pass


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8082, access_log=False)

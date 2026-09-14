"""Jonli yangilanish: WebSocket mijozlarga hodisa xabarlarini tarqatish."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket
from ..db import SessionLocal
from ..i18n import t
from .auth_svc import COOKIE, session_user
from .kpi import armory_ids_for_scope


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def authorized(self, ws: WebSocket) -> bool:
        with SessionLocal() as db:
            user, _ = session_user(db, ws.cookies.get(COOKIE))
            return user is not None

    async def connect(self, ws: WebSocket) -> bool:
        from urllib.parse import urlsplit
        origin = ws.headers.get("origin")
        if origin and urlsplit(origin).netloc != ws.url.netloc:
            await ws.close(code=4403)
            return False
        if not self.authorized(ws):
            await ws.close(code=4401)
            return False
        await ws.accept()
        self.clients.add(ws)
        self.loop = asyncio.get_running_loop()
        return True

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, msg: dict[str, Any]) -> None:
        dead = []
        for c in list(self.clients):
            try:
                with SessionLocal() as db:
                    user, _ = session_user(db, c.cookies.get(COOKIE))
                    if not user:
                        dead.append(c)
                        await c.close(code=4401)
                        continue
                    ids = armory_ids_for_scope(db, user.scope_kind, user.scope_id)
                    if ids is not None and msg.get("armory_id") not in ids:
                        continue
                display_msg = dict(msg)
                if isinstance(display_msg.get("title"), str):
                    display_msg["title"] = t(display_msg["title"], c.cookies.get("aq_lang", "lat"))
                await c.send_text(json.dumps(display_msg, ensure_ascii=False, default=str))
            except Exception:
                dead.append(c)
        for c in dead:
            self.disconnect(c)

    def broadcast_threadsafe(self, msg: dict[str, Any]) -> None:
        """Sinxron kod (masalan, so'rov ishlovchisi) ichidan chaqirish uchun."""
        if self.loop and self.clients:
            asyncio.run_coroutine_threadsafe(self.broadcast(msg), self.loop)


hub = Hub()

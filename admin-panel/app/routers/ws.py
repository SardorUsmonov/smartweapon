from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.live import hub

router = APIRouter()


@router.websocket("/ws/live")
async def live(ws: WebSocket):
    if not await hub.connect(ws):
        return
    try:
        while True:
            await ws.receive_text()  # ping/pong; mijoz xabarlari e'tiborga olinmaydi
            if not hub.authorized(ws):
                await ws.close(code=4401)
                break
    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:
        hub.disconnect(ws)
    finally:
        hub.disconnect(ws)

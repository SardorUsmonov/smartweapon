"""Fresh-demo integration checks; only a temporary database is ever written."""
import asyncio
import ast
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_integration_"))
sys.path.insert(0, str(ROOT))
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")
os.environ["AQ_SEED"] = "small"
os.environ["AQ_SEED_DAYS"] = "30"
os.environ["AQ_DEMO"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from starlette.websockets import WebSocketDisconnect
from app.main import app, templates
from app.db import SessionLocal
from app.models import Armory, Cabinet, Event, User
from app.services.auth_svc import COOKIE, revoke_sessions
from app.services.events import record_event, verify_chain
from app.services.kpi import armory_ids_for_scope
from app.services.live import hub


def login(client, name):
    assert client.get("/kirish").status_code == 200
    token = client.cookies["aq_csrf"]
    result = client.post("/kirish", data={"username": name, "password": "demo", "csrf_token": token}, follow_redirects=False)
    assert result.status_code == 303, result.text
    result = client.post("/kirish/mfa", data={"code": "123456", "csrf_token": token}, follow_redirects=False)
    assert result.status_code == 303, result.text


with TestClient(app) as client:
    for path in ["/api/kpi", "/api/map", "/jurnal", "/qurilmalar", "/yacheykalar", "/profil"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code in (303, 401), (path, response.status_code)
    try:
        with client.websocket_connect("/ws/live"):
            raise AssertionError("Anonymous WebSocket accepted")
    except WebSocketDisconnect as error:
        assert error.code == 4401
    login(client, "admin")
    with SessionLocal() as db:
        result = verify_chain(db)
        assert result["ok"] and result["checked"] > 10000, result
        for cab_id in [1, 2]:
            record_event(db, "texnik_xizmat", cabinet=db.get(Cabinet, cab_id), title="Integration audit fixture")
        db.commit()
        assert verify_chain(db)["ok"]
        fixture = db.scalars(select(Event).order_by(Event.id.desc())).first()
        fixture.reason = "tamper-test"
        db.flush()
        assert verify_chain(db)["broken"] == 1
        db.rollback()
        assert verify_chain(db)["ok"]
        assert armory_ids_for_scope(db, "unknown", 1) == []
        assert armory_ids_for_scope(db, "hudud", None) == []
    print("Fresh 30-day demo audit chain, append and tamper detection passed")

    pages = ["/", "/hududlar", "/hudud/1", "/hudud/1/bolinma/1", "/qurolxonalar", "/qurolxona/1",
             "/qurolxona/1/smenalar", "/yacheykalar", "/yacheyka/1", "/xodimlar", "/xodim/1",
             "/inventar", "/jihoz/1", "/inventarizatsiya", "/jurnal", "/jurnal/1", "/jurnal/favqulodda",
             "/jurnal/yaxlitlik", "/jurnal/eksport", "/signallar", "/signal/1", "/rejimlar",
             "/hisobotlar", "/hisobotlar/eksportlar", "/qurilmalar", "/qurilma/1", "/qurilmalar/zaxira",
             "/sozlamalar", "/sozlamalar/foydalanuvchi/yangi", "/profil", "/simulyator", "/qidiruv?q=Ali",
             "/partials/kpi", "/partials/map", "/partials/feed", "/partials/regions", "/partials/chart", "/partials/topbar"]
    from app.services.hisobot_svc import REPORTS
    pages += ["/hisobotlar/" + key for key in REPORTS]
    for path in pages:
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code, response.text[:200])
    client.get("/til/cyr")
    for path in ["/", "/yacheykalar", "/yacheyka/1", "/jurnal/1", "/sozlamalar", "/profil"]:
        response = client.get(path)
        assert response.status_code == 200 and 'lang="uz-Cyrl"' in response.text, path
    client.get("/til/lat")
    assert client.post("/chiqish", data={"csrf_token": client.cookies["aq_csrf"]}, headers={"origin": "https://foreign.example"}).status_code == 403
    assert client.get("/profil").status_code == 200
    print(f"{len(pages)} page/API views, Cyrillic and cross-origin CSRF checks passed")

    with client.websocket_connect("/ws/live") as socket:
        client.portal.call(hub.broadcast, {"armory_id": 1, "title": "central-live-check", "level": "INFO"})
        assert socket.receive_json()["title"] == "central-live-check"
    with TestClient(app) as scoped:
        login(scoped, "navbatchi")
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.username == "navbatchi"))
            armory_id = user.scope_id
            expected = db.scalar(select(func.count(Cabinet.id)).where(Cabinet.armory_id == armory_id))
        rows = scoped.get("/api/map").json()
        assert sum(r["yacheyka"] for r in rows) == expected
        assert sum(r["qurolxona"] for r in rows) == 1
        assert scoped.get("/api/kpi").json()["yacheykalar"] == expected
        assert scoped.get("/simulyator").status_code == 403
        assert scoped.get("/sozlamalar").status_code == 403
        assert scoped.get("/", follow_redirects=False).headers["location"] == f"/qurolxona/{armory_id}"
        with scoped.websocket_connect("/ws/live") as socket:
            scoped.portal.call(hub.broadcast, {"armory_id": 999999, "title": "foreign", "level": "INFO"})
            scoped.portal.call(hub.broadcast, {"armory_id": armory_id, "title": "own", "level": "INFO"})
            assert socket.receive_json()["title"] == "own"
            with SessionLocal() as db:
                revoke_sessions(db, user.id)
                db.commit()
            socket.send_text("ping")
            try:
                socket.receive_json()
                raise AssertionError("Revoked WebSocket remained authorized")
            except WebSocketDisconnect as error:
                assert error.code == 4401
    print("Scoped map and live messages, anonymous and revoked WebSocket denial passed")

for path in (ROOT / "app").rglob("*.py"):
    ast.parse(path.read_text(encoding="utf-8-sig"))
for name in templates.env.list_templates():
    templates.env.get_template(name)
print("Syntax/template compilation passed")
print("INTEGRATION_DB", SCRATCH / "test.sqlite3")

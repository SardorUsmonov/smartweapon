"""Authentication regression flow; only a temporary backup copy is mutated."""
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_auth_flow_"))
shutil.copy2(ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3", SCRATCH / "test.sqlite3")
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app import config
from app.main import app
from app.db import SessionLocal
from app.models import User, Event
from app.security_models import Credential, LoginSession
from app.services import auth_svc as svc


def post(client, url, **data):
    data["csrf_token"] = client.cookies["aq_csrf"]
    return client.post(url, data=data, follow_redirects=False)


def password(client, username="admin", next_path="/hududlar"):
    client.get("/kirish")
    r = post(client, "/kirish", username=username, password="demo", next=next_path)
    assert r.status_code == 303 and r.headers["location"] == "/kirish/mfa", r.text
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=strict" in r.headers["set-cookie"]
    return client.cookies[svc.COOKIE]


with TestClient(app) as client:
    assert client.get("/kirish", params={"next": "http://["}).status_code == 200
    assert client.get("/til/lat", headers={"referer": "http://["}, follow_redirects=False).headers["location"] == "/"
    r = client.get("/hududlar", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/kirish?next=")
    login = client.get("/kirish?next=/hududlar")
    assert login.status_code == 200 and 'name="csrf_token"' in login.text
    assert 'name="password"' in login.text and "123456" in login.text and "admin2" in login.text
    assert client.post("/kirish", data={"username": "admin", "password": "demo"}).status_code == 403
    client.cookies.set("aq_user", "admin")
    client.cookies.set(svc.COOKIE, "forged-token")
    assert client.get("/profil", follow_redirects=False).status_code == 303
    client.cookies.clear()
    pending = password(client)
    assert client.get("/kirish/mfa").status_code == 200
    assert client.get("/profil", follow_redirects=False).status_code == 303
    bad = post(client, "/kirish/mfa", code="000000")
    assert bad.status_code == 401 and 'name="code"' in bad.text
    result = post(client, "/kirish/mfa", code="123456")
    assert result.status_code == 303 and result.headers["location"] == "/hududlar"
    active = client.cookies[svc.COOKIE]
    assert active != pending
    with SessionLocal() as db:
        assert db.get(LoginSession, svc.token_hash(pending)) is None
        row = db.get(LoginSession, svc.token_hash(active))
        assert row.stage == "active" and row.token_hash != active
    profile = client.get("/profil")
    assert profile.status_code == 200 and "Administrator" in profile.text and 'action="/chiqish"' in profile.text
    assert client.get("/chiqish", follow_redirects=False).headers["location"] == "/profil"
    assert client.get("/profil").status_code == 200
    assert client.get("/hududlar").status_code == 200
    assert post(client, "/chiqish").status_code == 303
    assert not client.cookies.get(svc.COOKIE)
    with SessionLocal() as db:
        assert db.get(LoginSession, svc.token_hash(active)) is None
        assert db.scalar(select(func.count(Event.id)).where(Event.method == "PANEL_MFA")) >= 1
    print("Login, CSRF, MFA, token rotation, profile, POST logout and event audit passed")

    for attempt in range(3):
        result = post(client, "/kirish", username="admin2", password="wrong-password")
        assert result.status_code == 401
    assert post(client, "/kirish", username="admin2", password="demo").status_code == 401
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "admin2"))
        cred = db.get(Credential, user.id)
        assert cred.failures == 3 and cred.locked_until > datetime.now()
        cred.locked_until = datetime.now()-timedelta(seconds=1)
        db.commit()
    password(client, username="admin2")
    for attempt in range(3):
        result = post(client, "/kirish/mfa", code="000000")
        assert result.status_code == 401
    assert not client.cookies.get(svc.COOKIE)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "admin2"))
        cred = db.get(Credential, user.id)
        assert cred.failures == 3 and cred.locked_until > datetime.now()
        assert db.scalar(select(func.count(LoginSession.token_hash)).where(LoginSession.user_id == user.id)) == 0
    print("Password and MFA lockout after three failures passed")

    pending = password(client)
    with SessionLocal() as db:
        row = db.get(LoginSession, svc.token_hash(pending))
        row.expires_at = datetime.now()-timedelta(seconds=1)
        db.commit()
    assert client.get("/kirish/mfa", follow_redirects=False).headers["location"] == "/kirish"
    result = post(client, "/kirish/mfa", code="123456")
    assert result.status_code == 303 and result.headers["location"] == "/kirish"
    password(client, next_path="https://example.com/steal")
    assert post(client, "/kirish/mfa", code="123456").headers["location"] == "/"
    active = client.cookies[svc.COOKIE]
    with SessionLocal() as db:
        row = db.get(LoginSession, svc.token_hash(active))
        row.expires_at = datetime.now()-timedelta(seconds=1)
        db.commit()
    assert client.get("/profil", follow_redirects=False).status_code == 303
    print("Challenge/session expiry, forged cookies and external redirect rejection passed")

    client.cookies.clear()
    client.get("/kirish")
    config.DEMO_MODE = False
    page = client.get("/kirish")
    assert "123456" not in page.text and "demo-users" not in page.text
    result = post(client, "/kirish", username="admin", password="demo")
    assert result.status_code == 401 and not client.cookies.get(svc.COOKIE)
    config.DEMO_MODE = True
    client.cookies.set("aq_lang", "cyr")
    assert 'lang="uz-Cyrl"' in client.get("/kirish").text
    print("Non-demo MFA fails closed; demo hints hidden; Cyrillic login passed")
print("PASS scratch:", SCRATCH)

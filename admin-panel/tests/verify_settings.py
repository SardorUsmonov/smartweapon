"""Settings workflow with two real administrator sessions and an isolated DB."""
import json
import os
import shutil
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_settings_flow_"))
shutil.copy2(ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3", SCRATCH / "test.sqlite3")
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.db import SessionLocal
from app.models import User, Event, Setting, SettingsAudit
from app.security_models import Credential, LoginSession, UserChange
from app.services import auth_svc, settings_svc as svc


def post(client, url, **data):
    data["csrf_token"] = client.cookies["aq_csrf"]
    return client.post(url, data=data, follow_redirects=False)


def login(client, username, password="demo"):
    client.get("/kirish")
    result = post(client, "/kirish", username=username, password=password)
    assert result.status_code == 303, result.text
    if result.headers["location"] == "/kirish/mfa":
        result = post(client, "/kirish/mfa", code="123456")
        assert result.status_code == 303, result.text
    return client.cookies[auth_svc.COOKIE]


def latest_change(user_id=None):
    with SessionLocal() as db:
        query = select(UserChange).order_by(UserChange.id.desc())
        if user_id:
            query = query.where(UserChange.user_id == user_id)
        return db.scalars(query).first()


def update_form(user, **override):
    data = svc.snapshot(user)
    data.update(mfa="1" if data["mfa"] else "", active="1" if data["active"] else "", tasdiq="1", sabab="Sinov o'zgarishini tekshirish")
    data.update(override)
    return data


with ExitStack() as stack:
    admin, reviewer, member = [stack.enter_context(TestClient(app)) for _ in range(3)]
    login(admin, "admin")
    login(reviewer, "admin2")
    for tab in svc.TABS:
        result = admin.get("/sozlamalar", params={"tab": tab})
        assert result.status_code == 200, (tab, result.text[:100])
    assert admin.get("/sozlamalar/foydalanuvchi/yangi").status_code == 200
    secret = "Unique.test-password!42"
    form = dict(username="flow_member", password=secret, full_name="Sinov foydalanuvchi", role="qurolxona_masuli",
                scope_kind="qurolxona", scope_qurolxona="1", scope_hudud="2", scope_id="2", mfa="1", active="1", tasdiq="1", sabab="Yangi hisobni sinov uchun yaratish")
    response = post(admin, "/sozlamalar/foydalanuvchi/yangi", **form)
    assert response.status_code == 303, response.text
    change = latest_change()
    member_id = change.user_id
    with SessionLocal() as db:
        user = db.get(User, member_id)
        cred = db.get(Credential, member_id)
        assert not user.active and user.scope_id == 1
        assert cred.password_hash != secret and auth_svc.check_password(secret, cred.password_hash)
        assert change.status == "pending" and change.proposed["role"] == "qurolxona_masuli"
        for event in db.scalars(select(Event).where(Event.type.in_(["sozlama_ozgardi", "huquq_berish_tasdiqlandi"]))):
            assert secret not in json.dumps(event.payload) and cred.password_hash not in json.dumps(event.payload)
        for audit in db.scalars(select(SettingsAudit)):
            assert secret not in audit.old+audit.new and cred.password_hash not in audit.old+audit.new
    member.get("/kirish")
    assert post(member, "/kirish", username="flow_member", password=secret).status_code == 401
    assert post(admin, f"/sozlamalar/sorov/{change.id}/tasdiqlash", tasdiq="1").status_code == 409
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/tasdiqlash", tasdiq="1").status_code == 303
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/tasdiqlash", tasdiq="1").status_code == 409
    original_token = login(member, "flow_member", secret)
    profile = member.get("/profil")
    assert profile.status_code == 200 and profile.context["ctx"].role == "qurolxona_masuli"
    assert member.get("/sozlamalar").status_code == 403
    assert post(member, "/sozlamalar/autentifikatsiya/saqlash", tasdiq="1").status_code == 403
    print("All settings tabs, pending creation, hash/no-secrets audit, self-approval and activation passed")

    with SessionLocal() as db:
        user = db.get(User, member_id)
        form = update_form(user, role="navbatchi", scope_kind="hudud", scope_hudud="2")
    assert post(admin, f"/sozlamalar/foydalanuvchi/{member_id}", **form).status_code == 303
    change = latest_change(member_id)
    assert post(admin, f"/sozlamalar/foydalanuvchi/{member_id}", **form).status_code == 400
    profile = member.get("/profil")
    assert profile.context["ctx"].role == "qurolxona_masuli" and profile.context["ctx"].scope_id == 1
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/tasdiqlash", tasdiq="1").status_code == 303
    with SessionLocal() as db:
        assert db.get(LoginSession, auth_svc.token_hash(original_token)) is None
        user = db.get(User, member_id)
        assert (user.role, user.scope_kind, user.scope_id) == ("navbatchi", "hudud", 2)
        event = db.scalars(select(Event).where(Event.type == "huquq_berish_tasdiqlandi").order_by(Event.id.desc())).first()
        assert event.approver1 == "admin" and event.approver2 == "admin2"
    assert member.get("/profil", follow_redirects=False).status_code == 303
    login(member, "flow_member", secret)
    assert member.get("/profil").context["ctx"].role == "navbatchi"
    with SessionLocal() as db:
        user = db.get(User, member_id)
        form = update_form(user, full_name="Rad etiladigan taklif")
    assert post(admin, f"/sozlamalar/foydalanuvchi/{member_id}", **form).status_code == 303
    change = latest_change(member_id)
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/rad", tasdiq="1").status_code == 303
    with SessionLocal() as db:
        assert db.get(User, member_id).full_name == "Sinov foydalanuvchi"
        assert db.get(UserChange, change.id).status == "rejected"
    assert post(admin, f"/sozlamalar/foydalanuvchi/{member_id}", **form).status_code == 303
    change = latest_change(member_id)
    with SessionLocal() as db:
        db.get(User, member_id).full_name = "Boshqa tahrir mavjud"
        db.commit()
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/tasdiqlash", tasdiq="1").status_code == 409
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/rad", tasdiq="1").status_code == 303
    print("Pending permission stability, duplicate/stale rejection, approval session revocation and rejection passed")

    with SessionLocal() as db:
        admin2_user = db.scalar(select(User).where(User.username == "admin2"))
        form = update_form(admin2_user, role="tekshiruvchi")
        target_id = admin2_user.id
    assert post(admin, f"/sozlamalar/foydalanuvchi/{target_id}", **form).status_code == 303
    change = latest_change(target_id)
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/tasdiqlash", tasdiq="1").status_code == 409
    assert post(reviewer, f"/sozlamalar/sorov/{change.id}/rad", tasdiq="1").status_code == 303
    invalids = [dict(role="invalid"), dict(scope_kind="invalid"), dict(scope_qurolxona="999999"), dict(scope_qurolxona=""),
                dict(mfa="invalid"), dict(active="invalid"), dict(role="administrator",mfa=""), dict(username="x"),
                dict(password="short"), dict(sabab="x"), dict(tasdiq="")]
    base = dict(username="invalid_member", password=secret, full_name="Sinov hisob", role="qurolxona_masuli",
                scope_kind="qurolxona", scope_qurolxona="1", mfa="1", active="1", tasdiq="1", sabab="Qiymatlarni sinov qilish")
    for override in invalids:
        result = post(admin, "/sozlamalar/foydalanuvchi/yangi", **(base | override))
        assert result.status_code == 400, (override, result.text[:200])
        assert secret not in result.text
    print("Two-administrator safeguard and invalid user/scope/confirmation validation passed")

    def settings_form(group, **override):
        with SessionLocal() as db:
            data = {row["key"]: row["value"] for row in svc.values(db, group)}
        return data | {"tasdiq": "1", "sabab": "Sozlamalarni sinov uchun o'zgartirish"} | override

    for group in ("autentifikatsiya", "chegaralar", "saqlash"):
        assert post(admin, f"/sozlamalar/{group}/saqlash", **settings_form(group)).status_code == 303
    for override in ({"sessiya_daqiqa": "4"}, {"sessiya_daqiqa": "481"}, {"sessiya_daqiqa": "abc"}, {"sessiya_daqiqa": "1.5"}):
        result = post(admin, "/sozlamalar/autentifikatsiya/saqlash", **settings_form("autentifikatsiya", **override))
        assert result.status_code == 303 and "xato" in parse_qs(urlsplit(result.headers["location"]).query)
    for override in ({"urilish_g": "nan"}, {"urilish_g": "inf"}, {"eshik_ochiq_ogohlantirish_s": "180", "eshik_ochiq_signal_s": "60"}):
        result = post(admin, "/sozlamalar/chegaralar/saqlash", **settings_form("chegaralar", **override))
        assert "xato" in parse_qs(urlsplit(result.headers["location"]).query)
    result = post(admin, "/sozlamalar/autentifikatsiya/saqlash", **settings_form("autentifikatsiya", sessiya_daqiqa="90", not_allowed_key="bad"))
    assert result.status_code == 303 and "ok" in parse_qs(urlsplit(result.headers["location"]).query)
    assert post(admin, "/sozlamalar/not_allowed/saqlash", tasdiq="1").status_code == 404
    with SessionLocal() as db:
        assert db.get(Setting, "sessiya_daqiqa").value == "90"
        assert db.get(Setting, "not_allowed_key") is None
        entries = list(db.scalars(select(SettingsAudit).where(SettingsAudit.key == "sessiya_daqiqa")))
        assert entries and entries[-1].username == "admin" and json.loads(entries[-1].new) == "90"
    audit = admin.get("/sozlamalar?tab=audit&page=999999")
    assert audit.status_code == 200 and 1 <= audit.context["page"] <= audit.context["pages"]
    assert admin.get("/sozlamalar?q=no_user_found").context["total"] == 0
    print("Settings whitelist, ranges, cross-validation, persistence, audit and pagination passed")
print("PASS scratch:", SCRATCH)

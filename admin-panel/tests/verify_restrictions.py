"""Verify restriction refusals and persisted staff/device workflows on a DB copy.

Run: python -B -X utf8 tests/verify_restrictions.py
The original database, baseline backup and existing audit rows are preserved.
"""
import copy
import hashlib
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3"
SOURCE_HASH = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_restrictions_"))
shutil.copy2(SOURCE, SCRATCH / "test.sqlite3")
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")
os.environ["AQ_DEMO"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.db import SessionLocal
from app.models import Armory, Cabinet, Custody, Device, Eligibility, Event, Item, Mode, Officer, Unit, User
from app.services.events import verify_chain


def post(client, url, htmx=False, **form):
    return client.post(url, data={**form, "csrf_token": client.cookies["aq_csrf"]},
                       headers={"HX-Request": "true"} if htmx else {}, follow_redirects=False)


def login(client, name):
    assert client.get("/kirish").status_code == 200
    response = post(client, "/kirish", username=name, password="demo")
    assert response.status_code == 303 and response.headers["location"] == "/kirish/mfa", response.text
    assert post(client, "/kirish/mfa", code="123456").status_code == 303


def snapshot(db, cab_id):
    cab = db.get(Cabinet, cab_id)
    off = db.get(Officer, cab.officer_id)
    return {
        "locks_and_sensors": tuple(getattr(cab, key) for key in (
            "door_open", "door_locked", "ak_clamp_locked", "pm_box_locked", "ak_present", "pm_present")),
        "cabinet_status": cab.status,
        "items": list(db.execute(select(Item.id, Item.state, Item.hold).where(Item.cabinet_id == cab.id).order_by(Item.id))),
        "custody": list(db.execute(select(Custody.__table__).where(Custody.cabinet_id == cab.id).order_by(Custody.id))),
        "officer": (off.service_status, off.valid_until, off.permit_ak, off.permit_pm),
        "eligibility": list(db.execute(select(Eligibility.__table__).where(Eligibility.officer_id == off.id).order_by(Eligibility.id))),
    }


with TestClient(app) as admin, TestClient(app) as operator, TestClient(app) as viewer:
    with SessionLocal() as db:
        original_max = db.scalar(select(func.max(Event.id)))
        original_events = copy.deepcopy(list(db.execute(select(Event.__table__).order_by(Event.id))))
        broken_before = verify_chain(db)["broken"]
        now = datetime.now().replace(microsecond=0)
        # Select a healthy existing demo record independently of the new refusal helper.
        original_cab = None
        for candidate in db.scalars(select(Cabinet).where(Cabinet.status == "biriktirilgan", Cabinet.ak_present.is_(True))):
            off = db.get(Officer, candidate.officer_id)
            item = db.scalar(select(Item).where(Item.cabinet_id == candidate.id, Item.category == "avtomat"))
            eligible = off and off.service_status == "faol" and off.permit_ak and (not off.valid_until or off.valid_until >= now)
            if eligible and len({e.kind for e in off.eligibility}) == 5 and all(e.ok and (not e.valid_until or e.valid_until >= now) for e in off.eligibility):
                if item and item.state == "mavjud" and not item.hold and not db.scalar(select(Custody.id).where(Custody.cabinet_id == candidate.id, Custody.returned_at.is_(None))):
                    original_cab = candidate.id
                    break
        assert original_cab, "Baseline should retain a healthy existing demo take/return scenario"
        unit = Unit(region_id=1, name="Cheklov sinovi bo'linmasi")
        db.add(unit); db.flush()
        arm = Armory(unit_id=unit.id, name="Cheklov sinovi qurolxonasi", online=True, last_sync=now)
        db.add(arm); db.flush()
        off = Officer(unit_id=unit.id, armory_id=arm.id, full_name="Cheklov sinovi xodimi", tabel="RESTRICT-001",
                      valid_until=now + timedelta(days=30), service_status="faol", permit_ak=True, permit_pm=True)
        db.add(off); db.flush()
        cab = Cabinet(armory_id=arm.id, officer_id=off.id, label="CH-001", serial="RESTRICT-CAB-001",
                      status="biriktirilgan", ak_present=True, pm_present=True, door_open=False, door_locked=True,
                      ak_clamp_locked=True, pm_box_locked=True, controller_online=True)
        db.add(cab); db.flush()
        kinds = ("qurol_biriktirilgan", "saqlash_vakolati", "maxsus_tayyorgarlik", "yaroqlilik_tekshiruvi", "rahbar_buyrugi")
        for kind in kinds:
            db.add(Eligibility(officer_id=off.id, kind=kind, ok=True, valid_until=now + timedelta(days=30)))
        for category, serial in (("avtomat", "RESTRICT-AK"), ("to'pponcha", "RESTRICT-PM")):
            db.add(Item(kind="qurol", category=category, cabinet_id=cab.id, officer_id=off.id, model=serial,
                        serial=serial, state="mavjud", hold=False))
        server = Device(armory_id=arm.id, kind="server", name="Cheklov sinovi serveri", status="ogohlantirish",
                        metrics={"cpu": 20, "ram": 30, "disk": 40, "ntp_ogish_s": 40}, last_seen=now - timedelta(days=1))
        db.add(server); db.flush()
        arm_id, cab_id, off_id, dev_id = arm.id, cab.id, off.id, server.id
        items = {item.category: item.id for item in db.scalars(select(Item).where(Item.cabinet_id == cab_id))}
        owner = db.scalar(select(User).where(User.username == "masul"))
        owner.scope_kind, owner.scope_id = "qurolxona", arm_id
        owner_name = owner.full_name
        db.commit()

    login(admin, "admin"); login(operator, "masul"); login(viewer, "tekshiruvchi")

    def refuse(reason, action="take", htmx=False):
        with SessionLocal() as db:
            before = snapshot(db, cab_id)
            since = db.scalar(select(func.max(Event.id)))
        response = post(admin, f"/simulyator/yacheyka/{cab_id}/{action}", htmx=htmx)
        assert response.status_code == (200 if htmx else 303), response.text
        if htmx:
            assert "Rad etildi:" in response.text and "ok-flash" not in response.text and "✓" not in response.text
        with SessionLocal() as db:
            assert snapshot(db, cab_id) == before, "Refusal must preserve locks, sensors, restrictions and custody"
            events = list(db.scalars(select(Event).where(Event.id > since).order_by(Event.id)))
            assert [ev.type for ev in events] == ["rad_etildi"], [ev.type for ev in events]
            ev = events[0]
            assert ev.reason == reason and ev.result == "rad", (ev.reason, reason)
            assert ev.officer_id == off_id and ev.payload["cheklov"] == reason
            assert db.get(Cabinet, cab_id).terminal_state == "denied"
        return response

    def take_return(cid, action="take", htmx=False):
        category = "avtomat" if action == "take" else "to'pponcha"
        with SessionLocal() as db:
            before_count = db.scalar(select(func.count(Custody.id)).where(Custody.cabinet_id == cid))
        response = post(admin, f"/simulyator/yacheyka/{cid}/{action}", htmx=htmx)
        assert response.status_code == (200 if htmx else 303)
        if htmx:
            assert "ok-flash" in response.text and "✓" in response.text and "Rad etildi" not in response.text
        with SessionLocal() as db:
            assert db.scalar(select(func.count(Custody.id)).where(Custody.cabinet_id == cid)) == before_count + 1
            item = db.scalar(select(Item).where(Item.cabinet_id == cid, Item.category == category))
            assert item.state == "yo'q"
        assert post(admin, f"/simulyator/yacheyka/{cid}/return").status_code == 303
        with SessionLocal() as db:
            assert not db.scalar(select(Custody.id).where(Custody.cabinet_id == cid, Custody.returned_at.is_(None)))
            assert db.scalar(select(Item.state).where(Item.cabinet_id == cid, Item.category == category)) == "mavjud"

    take_return(original_cab)
    assert post(viewer, f"/simulyator/yacheyka/{cab_id}/take").status_code == 403
    assert post(operator, f"/simulyator/yacheyka/{cab_id}/take").status_code == 403
    assert admin.post(f"/simulyator/yacheyka/{cab_id}/take").status_code == 403

    # Hold is changed through the existing staff UI route; it must stop only the selected item.
    hold_url = f"/jihoz/{items['avtomat']}/hold"
    assert post(operator, hold_url, hold="1", sabab="Tekshiruv tugaguncha ushlab turish").status_code == 303
    with SessionLocal() as db:
        assert db.get(Item, items["avtomat"]).hold
    refuse("item_hold")
    with SessionLocal() as db:
        fixture_unit = db.get(Unit, db.get(Armory, arm_id).unit_id)
        original_unit_name = fixture_unit.name
        fixture_unit.name = '<b data-note="sinov">Hudud & bo‘linma</b>'
        db.commit()
    response = refuse("item_hold", htmx=True)
    assert "tanlangan jihoz ushlab turilgan" in response.text
    assert '<b data-note="sinov">' not in response.text and "&lt;b data-note=&quot;sinov&quot;&gt;" in response.text
    assert "Hudud &amp; bo‘linma&lt;/b&gt;" in response.text
    with SessionLocal() as db:
        db.get(Unit, db.get(Armory, arm_id).unit_id).name = original_unit_name; db.commit()
    take_return(cab_id, "take_pm", htmx=True)
    print("PASS: denied HTMX take shows escaped refusal text without success marker; allowed take retains success feedback")
    assert post(operator, hold_url, hold="0", sabab="Tekshiruv tugadi").status_code == 303

    # Both permit controls persist their audited changes; revocation survives repeated refusals.
    permit_url = f"/xodim/{off_id}/ruxsat"
    for kind, action in (("ak", "take"), ("pm", "take_pm")):
        assert post(operator, permit_url, tur=kind, amal="bekor", sabab="Ruxsatni bekor qilish sinovi").status_code == 303
        with SessionLocal() as db:
            assert not getattr(db.get(Officer, off_id), "permit_" + kind)
            ev = db.scalar(select(Event).where(Event.officer_id == off_id).order_by(Event.id.desc()))
            assert ev.payload["amal"] == "ruxsat" and ev.payload["yangi"] is False and ev.approver1 == owner_name
        refuse("no_permit", action)
        assert post(operator, permit_url, tur=kind, amal="tiklash", sabab="Ruxsat qayta tasdiqlandi").status_code == 303
        with SessionLocal() as db:
            assert getattr(db.get(Officer, off_id), "permit_" + kind)

    status_url = f"/xodim/{off_id}/holat"
    assert post(operator, status_url, holat="kasallik", sabab="Xizmat holati sinovi").status_code == 303
    with SessionLocal() as db:
        assert db.get(Officer, off_id).service_status == "kasallik"
        assert db.get(Cabinet, cab_id).status == "bloklangan"
    refuse("cabinet_blocked")
    assert post(operator, status_url, holat="faol", sabab="Xodim xizmatga qaytdi").status_code == 303
    with SessionLocal() as db:
        assert db.get(Officer, off_id).service_status == "faol"
        assert db.get(Cabinet, cab_id).status == "biriktirilgan"
        # Also protect old inconsistent data with an assigned cabinet but inactive officer.
        db.get(Officer, off_id).service_status = "ta'tilda"; db.commit()
    refuse("service_inactive")
    with SessionLocal() as db:
        db.get(Officer, off_id).service_status = "faol"
        db.get(Officer, off_id).valid_until = now - timedelta(days=1); db.commit()
    refuse("authority_expired")
    with SessionLocal() as db:
        db.get(Officer, off_id).valid_until = now + timedelta(days=30)
        eligibility = db.scalar(select(Eligibility).where(Eligibility.officer_id == off_id, Eligibility.kind == "maxsus_tayyorgarlik"))
        eligibility.ok = False; eligibility_id = eligibility.id; db.commit()
    refuse("eligibility_invalid")
    with SessionLocal() as db:
        eligibility = db.get(Eligibility, eligibility_id)
        eligibility.ok = True; eligibility.valid_until = now - timedelta(days=1); db.commit()
    refuse("eligibility_expired")
    with SessionLocal() as db:
        eligibility = db.get(Eligibility, eligibility_id)
        eligibility.valid_until = now + timedelta(days=30)
        eligibility.kind = "qurol_biriktirilgan"; db.commit()
    refuse("eligibility_missing")  # Five rows but one required kind is missing.
    with SessionLocal() as db:
        db.get(Eligibility, eligibility_id).kind = "maxsus_tayyorgarlik"; db.commit()
    take_return(cab_id)
    print("PASS: existing healthy take/return, authenticated hold/status/AK+PM permit flows, authority/eligibility refusals, unchanged denial locks/custody")

    # A denied mode step must not inflate counts or invent a duration.
    assert post(operator, hold_url, hold="1", sabab="Rejim sinovida cheklov").status_code == 303
    assert post(admin, "/simulyator/rejim/boshlash", armory_id=arm_id, kind="yigilish", started_by="admin", approver2="Sinov", reason="Rejim sinovi").status_code == 303
    with SessionLocal() as db:
        mode = db.scalar(select(Mode).where(Mode.armory_id == arm_id).order_by(Mode.id.desc()))
        mode_id = mode.id; before = snapshot(db, cab_id)
        issued, avg = mode.issued_count, mode.avg_seconds
    assert post(admin, f"/simulyator/rejim/{mode_id}/qadam", n="1").status_code == 303
    with SessionLocal() as db:
        mode = db.get(Mode, mode_id)
        assert mode.issued_count == issued == 0 and mode.queue_count == mode.target_count == 1 and mode.avg_seconds == avg
        assert snapshot(db, cab_id) == before
    assert post(operator, hold_url, hold="0", sabab="Rejim cheklovi tugadi").status_code == 303
    assert post(admin, f"/simulyator/rejim/{mode_id}/qadam", n="1").status_code == 303
    with SessionLocal() as db:
        mode = db.get(Mode, mode_id)
        assert mode.issued_count == 1 and mode.queue_count == 0
    refuse("item_unavailable")  # A repeated take cannot create another open custody record.
    assert post(admin, f"/simulyator/rejim/{mode_id}/qadam", n="1").status_code == 303
    with SessionLocal() as db:
        assert db.get(Mode, mode_id).issued_count == 1
    assert post(admin, f"/simulyator/yacheyka/{cab_id}/return").status_code == 303
    assert post(admin, f"/simulyator/rejim/{mode_id}/tugatish").status_code == 303
    print("PASS: mode denial keeps counters/custody stable; allowed step advances once; duplicate take refuses")

    # Device actions are existing local demo metadata updates, not real device control.
    device_url = f"/qurilma/{dev_id}"
    assert post(admin, device_url + "/self-test").status_code == 303
    with SessionLocal() as db:
        dev = db.get(Device, dev_id)
        assert dev.metrics["self_test"]["ok"] is False and dev.metrics["self_test"]["xato"]
        assert dev.status == "ogohlantirish"
    assert post(admin, device_url + "/vaqt-sinxroni").status_code == 303
    with SessionLocal() as db:
        dev = db.get(Device, dev_id)
        assert dev.metrics["ntp_ogish_s"] == 0 and dev.metrics["vaqt_sinxron"] and dev.last_seen >= now
        ev = db.scalar(select(Event).where(Event.armory_id == arm_id).order_by(Event.id.desc()))
        assert ev.payload["amal"] == "vaqt_sinxroni" and ev.payload["eski_ogish_s"] == 40 and ev.approver1 == "admin"
    assert post(admin, device_url + "/self-test").status_code == 303
    with SessionLocal() as db:
        dev = db.get(Device, dev_id)
        assert dev.metrics["self_test"]["ok"] is True and dev.status == "onlayn"
        assert all(row["ok"] for row in dev.metrics["self_test"]["tekshiruvlar"])
    for prior in ("onlayn", "ogohlantirish", "oflayn"):
        with SessionLocal() as db:
            dev = db.get(Device, dev_id); dev.status = prior; db.commit()
        assert post(admin, device_url + "/xizmat", holat="on", sabab="Rejali tekshiruv").status_code == 303
        with SessionLocal() as db:
            dev = db.get(Device, dev_id)
            assert dev.status == "xizmatda" and dev.metrics["xizmat"]["oldingi_holat"] == prior
            assert dev.metrics["xizmat"]["kim"] == "admin" and dev.metrics["xizmat"]["sabab"] == "Rejali tekshiruv"
        assert post(admin, device_url + "/xizmat", holat="off", sabab="Tekshiruv qayd etildi").status_code == 303
        with SessionLocal() as db:
            dev = db.get(Device, dev_id)
            assert dev.status == prior, f"Service toggle must preserve prior fault: {prior} became {dev.status}"
            assert "xizmat" not in dev.metrics and dev.metrics["ntp_ogish_s"] == 0
            ev = db.scalar(select(Event).where(Event.armory_id == arm_id).order_by(Event.id.desc()))
            assert ev.payload["amal"] == "xizmat_rejimi_tugadi" and ev.payload["boshlagan"] == "admin"
    assert admin.get(device_url).status_code == 200
    with SessionLocal() as db:
        assert list(db.execute(select(Event.__table__).where(Event.id <= original_max).order_by(Event.id))) == original_events
        assert verify_chain(db)["broken"] == broken_before
    print("PASS: persisted self-test failure/success, time sync and service lifecycle; prior faults preserved; existing audit unchanged")

assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_HASH
print("PASS: verification completed in", SCRATCH)

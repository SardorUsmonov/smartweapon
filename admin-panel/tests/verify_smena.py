"""Exercise authenticated shift opening, closing and archived reports on a copy.

Run: python -X utf8 tests/verify_smena.py
The original database and pre-change backup are never modified.
"""
import copy
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_smena_flow_"))
shutil.copy2(ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3", SCRATCH / "test.sqlite3")
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")
os.environ["AQ_DEMO"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.db import SessionLocal
from app.models import Alarm, Armory, ArmoryShift, Cabinet, Custody, Device, Eligibility, Event, Item, Officer, Unit, User
from app.services import smena_svc as svc
from app.services.events import record_event, verify_chain


def post(client, url, **form):
    return client.post(url, data={**form, "csrf_token": client.cookies["aq_csrf"]}, follow_redirects=False)


def login(client, name):
    assert client.get("/kirish").status_code == 200
    response = post(client, "/kirish", username=name, password="demo")
    assert response.status_code == 303 and response.headers["location"] == "/kirish/mfa", response.text
    assert post(client, "/kirish/mfa", code="123456").status_code == 303


def make_armory(db, unit, label):
    now = datetime.now().replace(microsecond=0)
    arm = Armory(unit_id=unit.id, name="Smena sinovi " + label, last_sync=now, online=True, ups_on_battery=False)
    db.add(arm); db.flush()
    officer = Officer(unit_id=unit.id, armory_id=arm.id, full_name="Sinov mas'uli " + label, tabel="SM-" + label,
                      valid_until=now + timedelta(days=365), face_enrolled=True, finger_enrolled=True)
    db.add(officer); db.flush()
    arm.responsible_officer_id = officer.id
    cab = Cabinet(armory_id=arm.id, label="Y-001", serial="SM-CAB-" + label, status="biriktirilgan", officer_id=officer.id,
                  controller_online=True, door_open=False, door_locked=True, ak_present=True, pm_present=True, last_seen=now)
    db.add(cab); db.flush()
    for key in svc.ELIG_LABEL:
        db.add(Eligibility(officer_id=officer.id, kind=key, ok=True, valid_until=now + timedelta(days=365)))
    for category, model, suffix in (("avtomat", "AK-74", "AK"), ("to'pponcha", "PM", "PM")):
        db.add(Item(kind="qurol", category=category, model=model, serial="SM-" + label + "-" + suffix,
                    cabinet_id=cab.id, officer_id=officer.id, state="mavjud"))
    for kind, metrics in (("server", {"cpu": 20, "ram": 35, "disk": 25}), ("kamera", {"oqim": True}),
                          ("terminal", {"kesh": True}), ("ups", {"batareya": 100, "yuklama": 20}), ("nas", {"disk": 30})):
        db.add(Device(armory_id=arm.id, kind=kind, name=f"SM {label} {kind}", status="onlayn", metrics=metrics, last_seen=now))
    db.flush()
    return arm.id, cab.id, officer.id


def shifts_and_events(armory_id):
    with SessionLocal() as db:
        return (db.scalar(select(func.count(ArmoryShift.id)).where(ArmoryShift.armory_id == armory_id)),
                db.scalar(select(func.count(Event.id)).where(Event.armory_id == armory_id)))


with TestClient(app) as client, TestClient(app) as viewer, TestClient(app) as foreign:
    with SessionLocal() as db:
        original_max = db.scalar(select(func.max(Event.id)))
        original_events = list(db.execute(select(Event.__table__).order_by(Event.id)))
        initial_broken = verify_chain(db)["broken"]
        unit = Unit(region_id=1, name="Smena sinovi bo'linmasi")
        db.add(unit); db.flush()
        clean_id, clean_cab, clean_officer = make_armory(db, unit, "CLEAN")
        issue_id, issue_cab, issue_officer = make_armory(db, unit, "ISSUE")
        operator = db.scalar(select(User).where(User.username == "navbatchi"))
        operator.scope_kind, operator.scope_id = "bolinma", unit.id
        operator_name = operator.full_name
        db.commit()

    # Actual password+MFA sessions: no dependency override or route stubs.
    login(client, "navbatchi")
    login(viewer, "tekshiruvchi")
    login(foreign, "masul")
    open_url, close_url = f"/qurolxona/{clean_id}/smena/ochish", f"/qurolxona/{clean_id}/smena/yopish"
    page = client.get(open_url)
    assert page.status_code == 200 and page.context["chk"]["passed"] == 7
    assert page.context["rec"]["nomuvofiq"] == 0 and page.context["perm"]["ok_count"] == 1
    assert not page.context["shift"]
    baseline = shifts_and_events(clean_id)
    for other in (viewer, foreign):
        for url in (open_url, close_url):
            assert post(other, url, permits_confirmed="1", close_confirm="Sinov mas'uli").status_code == 403
    assert foreign.get(open_url).status_code == 403
    assert client.post(open_url, data={"permits_confirmed": "1"}).status_code == 403
    rejected = post(client, open_url, note="Tasdiqsiz sinov")
    assert rejected.status_code == 200 and rejected.context["error"]
    assert rejected.context["form"]["note"] == "Tasdiqsiz sinov"
    assert shifts_and_events(clean_id) == baseline

    opened = post(client, open_url, permits_confirmed="1", opened_by="Forged operator", note="Smena boshlandi")
    assert opened.status_code == 303
    with SessionLocal() as db:
        shift = svc.open_shift(db, clean_id)
        clean_shift = shift.id
        assert shift.opened_by == operator_name, "Opening actor must come from authenticated session"
        assert shift.permits_confirmed and all(shift.selfcheck.values())
        assert shift.reconcile["ruxsat"] == {"jami": 1, "mos": 1, "muammo": 0}
        opened_event = db.scalar(select(Event).where(Event.armory_id == clean_id, Event.type == "smena_ochildi"))
        assert opened_event.payload["smena_id"] == shift.id and opened_event.approver1 == operator_name
    after_open = shifts_and_events(clean_id)
    assert post(client, open_url, permits_confirmed="1").status_code == 303
    assert shifts_and_events(clean_id) == after_open
    assert client.get(f"/qurolxona/{clean_id}").context["shift"].id == clean_shift
    assert client.get(close_url).context["unreturned"] == []
    rejected = post(client, close_url, shift_id=clean_shift)
    assert rejected.status_code == 200 and rejected.context["error"]
    assert shifts_and_events(clean_id) == after_open

    closed = post(client, close_url, shift_id=clean_shift, closed_by="Forged closer", close_confirm="Sinov mas'uli CLEAN", note="Toza topshirildi")
    assert closed.status_code == 303
    report_url = closed.headers["location"]
    report = client.get(report_url)
    assert report.status_code == 200 and report.context["s"].closed_at
    assert report.context["s"].closed_by == operator_name
    assert report.context["yopish"]["qaytarilmagan"] == [] and report.context["yopish"]["ochiq_signallar"] == []
    assert report.context["s"].report_ref.startswith("SM-")
    history = client.get(f"/qurolxona/{clean_id}/smenalar")
    assert history.status_code == 200 and history.context["rows"][0].id == clean_shift
    assert client.get(f"/qurolxona/{clean_id}").context["shift"] is None
    assert foreign.get(report_url).status_code == 403
    assert client.get(f"/qurolxona/{issue_id}/smena/{clean_shift}").status_code == 404
    after_close = shifts_and_events(clean_id)
    assert post(client, close_url, shift_id=clean_shift, close_confirm="Sinov mas'uli CLEAN").status_code == 303
    assert shifts_and_events(clean_id) == after_close

    # A stale browser tab must never close a newly opened shift.
    assert post(client, open_url, permits_confirmed="1").status_code == 303
    with SessionLocal() as db:
        next_shift = svc.open_shift(db, clean_id).id
    stale = post(client, close_url, shift_id=clean_shift, close_confirm="Sinov mas'uli CLEAN")
    assert stale.status_code == 409, "A stale close submission must identify the old shift"
    with SessionLocal() as db:
        assert svc.open_shift(db, clean_id).id == next_shift
    assert post(client, close_url, shift_id=next_shift, close_confirm="Sinov mas'uli CLEAN").status_code == 303
    print("Authenticated clean open→close→history/report, checklist, role/scope/CSRF and duplicate/stale transitions OK")

    # Device trouble and inventory discrepancy remain visible and require acknowledgements.
    with SessionLocal() as db:
        camera = db.scalar(select(Device).where(Device.armory_id == issue_id, Device.kind == "kamera"))
        camera.status = "oflayn"
        cab = db.get(Cabinet, issue_cab)
        cab.ak_present = False  # unconfirmed sensor discrepancy, inventory still lists the item
        # Reserve cabinets with a sensor calibration discrepancy exercise the full
        # opening snapshot beyond the former 50-row truncation.
        for index in range(51):
            reserve = Cabinet(armory_id=issue_id, label=f"Z-{index:03d}", serial=f"SM-RES-{index}",
                              status="zaxira", ak_present=False, pm_present=False, controller_online=True)
            db.add(reserve); db.flush()
            db.add(Item(kind="qurol", category="avtomat", model="AK-74", serial=f"SM-RES-AK-{index}",
                        cabinet_id=reserve.id, state="mavjud"))
        # A busy armory can carry more than 100 unresolved telemetry alarms.
        for index in range(105):
            record_event(db, "aloqa_uzildi", cabinet=cab, title=f"Sinov aloqa signali {index}")
        db.commit()
    open_issue, close_issue = f"/qurolxona/{issue_id}/smena/ochish", f"/qurolxona/{issue_id}/smena/yopish"
    page = client.get(open_issue)
    assert not page.context["chk"]["ok"] and page.context["rec"]["nomuvofiq"] == 52
    baseline = shifts_and_events(issue_id)
    for fields in ({"permits_confirmed": "1"}, {"permits_confirmed": "1", "reconcile_confirmed": "1"}):
        rejected = post(client, open_issue, **fields)
        assert rejected.status_code == 200 and rejected.context["error"]
        assert shifts_and_events(issue_id) == baseline
    reason = "Kamera xizmatda; sensor farqi inventarizatsiyaga topshirildi"
    opened = post(client, open_issue, permits_confirmed="1", reconcile_confirmed="1", reason=reason)
    assert opened.status_code == 303
    with SessionLocal() as db:
        shift = svc.open_shift(db, issue_id)
        issue_shift = shift.id
        assert not shift.selfcheck["kamera"] and shift.reconcile["nomuvofiq"] == 52
        assert len(shift.reconcile["farqlar"]) == 52
        assert shift.reconcile["sabab"] == reason
        failure = db.scalar(select(Event).where(Event.armory_id == issue_id, Event.type == "oz_tekshiruv_xato"))
        assert failure and failure.payload["smena_id"] == issue_shift
        assert db.scalar(select(Alarm.id).where(Alarm.event_id == failure.id))
        # Synthetic device feed during the shift: known item handed over, still outstanding.
        item = db.scalar(select(Item).where(Item.cabinet_id == issue_cab, Item.category == "avtomat"))
        item.state = "yo'q"
        custody = Custody(item_id=item.id, officer_id=issue_officer, cabinet_id=issue_cab,
                          taken_at=datetime.now() - timedelta(minutes=10), due_at=datetime.now() - timedelta(minutes=1))
        db.add(custody); db.flush()
        custody_id = custody.id
        record_event(db, "avtomat_olindi", cabinet=db.get(Cabinet, issue_cab), officer=db.get(Officer, issue_officer), item_id=item.id)
        db.commit()
    close_page = client.get(close_issue)
    assert len(close_page.context["unreturned"]) == 1 and close_page.context["unreturned"][0]["overdue"]
    expected_alarm_ids = {alarm.id for alarm in close_page.context["alarms"]}
    assert len(expected_alarm_ids) == 106
    for fields in ({}, {"ack_unreturned": "1"}):
        rejected = post(client, close_issue, shift_id=issue_shift, close_confirm="Sinov mas'uli ISSUE", **fields)
        assert rejected.status_code == 200 and rejected.context["error"]
        with SessionLocal() as db:
            assert svc.open_shift(db, issue_id).id == issue_shift
    closed = post(client, close_issue, shift_id=issue_shift, close_confirm="Sinov mas'uli ISSUE",
                  ack_unreturned="1", ack_alarms="1", note="Keyingi smenaga topshirildi")
    assert closed.status_code == 303
    report_url = closed.headers["location"]
    report = client.get(report_url)
    snapshot = copy.deepcopy(report.context["yopish"])
    assert len(snapshot["qaytarilmagan"]) == 1 and snapshot["qaytarilmagan"][0]["kechikkan"]
    assert {alarm["id"] for alarm in snapshot["ochiq_signallar"]} == expected_alarm_ids
    assert snapshot["statistika"]["olindi"] == 1
    with SessionLocal() as db:
        shift = db.get(ArmoryShift, issue_shift)
        closed_event = db.scalar(select(Event).where(Event.armory_id == issue_id, Event.type == "smena_yopildi"))
        assert closed_event.payload["qaytarilmagan"] == 1 and closed_event.result == "qaytarilmagan_bor"
        assert db.get(Custody, custody_id).returned_at is None
        assert svc.open_alarms(db, issue_id), "Closing a shift must not resolve its alarms"
        # Later device sync and operational updates cannot rewrite the sealed report.
        db.get(Custody, custody_id).returned_at = datetime.now()
        for alarm in svc.open_alarms(db, issue_id):
            alarm.resolved_at = datetime.now()
        record_event(db, "pm_olindi", armory=db.get(Armory, issue_id), ts=shift.closed_at, offline=True, title="Late device sync fixture")
        db.commit()
    replay = client.get(report_url)
    assert replay.context["yopish"] == snapshot
    assert replay.context["stats"] == snapshot["statistika"], "Closed report statistics must use the closing snapshot"
    for lang in ("lat", "cyr"):
        client.cookies.set("aq_lang", lang)
        assert client.get(report_url).status_code == 200
        assert client.get(f"/qurolxona/{issue_id}/smenalar").status_code == 200
    with SessionLocal() as db:
        assert list(db.execute(select(Event.__table__).where(Event.id <= original_max).order_by(Event.id))) == original_events
        assert verify_chain(db)["broken"] == initial_broken
    print("Device/inventory approvals, 52 discrepancies and 106 alarms fully retained, outstanding custody, sealed report and immutable audit OK")

print("PASS scratch:", SCRATCH)

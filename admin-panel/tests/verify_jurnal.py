"""Jurnal, scoped region views and shift history regression checks.

Run: python -X utf8 tests/verify_jurnal.py
Copies the pre-change backup into a temporary SQLite database. All generated
exports and synthetic fixtures stay in that temporary directory.
"""
import csv
import hashlib
import io
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BACKUP = ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3"
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_jurnal_flow_"))
shutil.copy2(BACKUP, SCRATCH / "test.sqlite3")
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.db import SessionLocal
from app.deps import Ctx, get_ctx
from app.models import Armory, ArmoryShift, Cabinet, Event, ExportLog, Unit, User
from app.routers import jurnal
from app.services import hisobot_svc, kpi
from app.services.events import record_event, verify_chain

jurnal.EXPORT_DIR = SCRATCH / "jurnal"
hisobot_svc.EXPORT_DIR = SCRATCH / "exports"
ctx = Ctx(User(username="tekshiruvchi", full_name="Test inspector", role="tekshiruvchi",
               scope_kind="respublika", active=True), "lat")
app.dependency_overrides[get_ctx] = lambda: ctx


def scope(kind="respublika", sid=None, role="tekshiruvchi"):
    ctx.user = User(username="tekshiruvchi", full_name="Test inspector", role=role,
                    scope_kind=kind, scope_id=sid, active=True)


def csv_rows(data):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig")), delimiter=";"))


with TestClient(app) as client:
    with SessionLocal() as db:
        first = db.scalar(select(Event).where(Event.cabinet_id.is_not(None)).order_by(Event.id))
        first_id, cabinet_id, own_id = first.id, first.cabinet_id, first.armory_id
        own = db.get(Armory, own_id)
        region_id, unit_id = own.unit.region_id, own.unit_id
        foreign = db.scalar(select(Event).where(Event.armory_id != own_id).order_by(Event.id))
        foreign_event, foreign_armory = foreign.id, foreign.armory_id
        original_max = db.scalar(select(func.max(Event.id)))
        original_events = list(db.execute(select(Event.__table__).order_by(Event.id)))
        original_broken = verify_chain(db)["broken"]
        shift = db.scalar(select(ArmoryShift).order_by(ArmoryShift.id))
        report_url = f"/qurolxona/{shift.armory_id}/smena/{shift.id}"
        expected_ids = set(db.scalars(select(Event.id).where(Event.armory_id == own_id,
                                  Event.type.in_(jurnal.TYPE_GROUPS["operatsiya"][1]))))

    pages = ["/jurnal", "/jurnal/partials/jadval?tur=operatsiya", f"/jurnal/{first_id}",
             "/jurnal/favqulodda", "/jurnal/favqulodda?tur=mexanik_kalit", "/jurnal/yaxlitlik",
             f"/jurnal/yaxlitlik?yacheyka={cabinet_id}", "/jurnal/yaxlitlik?yacheyka=missing-cab",
             f"/jurnal/eksport?qurolxona={own_id}&tur=operatsiya", f"/qurolxona/{own_id}/smenalar", report_url]
    for lang in ("lat", "cyr"):
        ctx.lang = lang
        for path in pages:
            response = client.get(path)
            assert response.status_code == 200, (lang, path, response.status_code)
    ctx.lang = "lat"
    assert client.get("/jurnal/yaxlitlik?yacheyka=missing-cab").context["res"] is None
    integrity = client.get("/jurnal/yaxlitlik").context
    assert integrity["res"]["checked"] == len(original_events)
    assert integrity["res"]["broken"] == original_broken
    filtered = client.get(f"/jurnal?tur=operatsiya&qurolxona={own_id}&page=2")
    assert filtered.status_code == 200 and filtered.context["page"] == 2
    assert filtered.context["total"] == len(expected_ids)
    assert all(row["ev"].id in expected_ids for row in filtered.context["rows"])
    query = parse_qs(filtered.context["qlink"](page=3))
    assert query["qurolxona"] == [str(own_id)] and query["tur"] == ["operatsiya"]
    assert client.get("/jurnal?dan=invalid").context["total"] == 0
    print("Jurnal pages, Cyrillic, filters, pagination and full integrity coverage OK")

    client.headers["X-CSRF-Token"] = client.cookies["aq_csrf"]
    with SessionLocal() as db:
        before_exports = db.scalar(select(func.count(ExportLog.id)))
    invalid = [{"maqsad": "x"}, {"maqsad": "Dates test", "dan": "2026-09-12", "gacha": "2020-01-01"},
               {"maqsad": "Empty export", "yacheyka": "nonexistent"}, {"maqsad": "Over limit export"}]
    for form in invalid:
        response = client.post("/jurnal/eksport", data=form)
        assert response.status_code == 200 and response.context["error"], form
        assert response.context["purpose"] == form["maqsad"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ExportLog.id))) == before_exports

    response = client.post("/jurnal/eksport", data={"maqsad": "Smena auditi sinovi", "qurolxona": own_id,
                            "tur": "operatsiya", "muddat": "7"}, follow_redirects=False)
    assert response.status_code == 303
    export_url = response.headers["location"]
    export_id = int(urlsplit(export_url).path.rsplit("/", 1)[-1])
    detail = client.get(export_url)
    assert detail.status_code == 200 and detail.context["file_ok"]
    downloaded = client.get(export_url + "/fayl")
    assert downloaded.status_code == 200
    records = csv_rows(downloaded.content)
    assert {int(row["id"]) for row in records} == expected_ids
    with SessionLocal() as db:
        log = db.get(ExportLog, export_id)
        number, file_path = log.number, jurnal._export_path(log)
        assert log.file_hash == hashlib.sha256(downloaded.content).hexdigest()
        ev = jurnal._export_event(db, log)
        assert ev.payload["rows"] == len(expected_ids) and ev.payload["armory_ids"] == [own_id]
        assert ev.payload["filters"] == {"qurolxona": own_id, "tur": "operatsiya"}
        assert list(db.execute(select(Event.__table__).where(Event.id <= original_max).order_by(Event.id))) == original_events
        assert verify_chain(db)["broken"] == original_broken
    assert client.get(f"/hisobotlar/eksportlar/{export_id}").status_code == 200
    assert client.get(f"/hisobotlar/eksportlar/{export_id}/fayl").content == downloaded.content

    scope("qurolxona", own_id)
    for path in ("/jurnal", "/jurnal/yaxlitlik", "/jurnal/favqulodda", export_url, export_url + "/fayl"):
        assert client.get(path).status_code == 200, path
    assert client.get(f"/jurnal/{foreign_event}").status_code == 403
    scoped_integrity = client.get("/jurnal/yaxlitlik").context
    with SessionLocal() as db:
        assert scoped_integrity["res"]["checked"] == db.scalar(select(func.count(Event.id)).where(Event.armory_id == own_id))
    scope("qurolxona", foreign_armory)
    assert client.get(export_url).status_code == 403
    assert client.get(export_url + "/fayl").status_code == 403
    assert number not in client.get("/jurnal/eksport").text
    scope()
    original_data = file_path.read_bytes()
    file_path.write_bytes(original_data + b"TAMPER")
    assert client.get(export_url + "/fayl").status_code == 409
    assert not client.get(export_url).context["file_ok"]
    file_path.write_bytes(original_data)
    with SessionLocal() as db:
        db.get(ExportLog, export_id).valid_until = datetime.now() - timedelta(days=1)
        db.commit()
    assert client.get(export_url + "/fayl").status_code == 410
    print(f"CSV roundtrip ({len(records)} rows), audit immutability, scopes, shared history, corruption and expiry OK")

    # A text field supplied by an operator must remain literal in spreadsheet exports.
    with SessionLocal() as db:
        formula = record_event(db, "sozlama_ozgardi", armory=db.get(Armory, own_id), title="=1+1", detail="formula fixture")
        formula_id = formula.id
        db.commit()
    response = client.post("/jurnal/eksport", data={"maqsad": "Formula handling test", "qurolxona": own_id,
                           "tur": "sozlama_ozgardi"}, follow_redirects=False)
    assert response.status_code == 303
    result = csv_rows(client.get(response.headers["location"] + "/fayl").content)
    assert next(row for row in result if int(row["id"]) == formula_id)["sarlavha"] == "'=1+1"

    # Same-region/same-unit siblings expose scope bugs hidden by the seed layout.
    with SessionLocal() as db:
        unit = Unit(region_id=region_id, name="OTHER UNIT SCOPE FIXTURE")
        db.add(unit); db.flush()
        sibling = Armory(unit_id=unit_id, name="OTHER ARMORY SAME UNIT")
        neighbor = Armory(unit_id=unit.id, name="OTHER UNIT ARMORY")
        db.add_all([sibling, neighbor]); db.flush()
        sibling_id, neighbor_id = sibling.id, neighbor.id
        db.add_all([Cabinet(armory_id=sibling_id, serial="SCOPE-TEST-A", label="Y-999"),
                    Cabinet(armory_id=neighbor_id, serial="SCOPE-TEST-B", label="Y-999")])
        record_event(db, "rad_etildi", armory=sibling, title="PRIVATE SIBLING EVENT")
        record_event(db, "rad_etildi", armory=neighbor, title="PRIVATE FOREIGN EVENT")
        for n in range(55):
            db.add(ArmoryShift(armory_id=own_id, opened_by="Test", opened_at=datetime.now() - timedelta(days=n),
                               closed_at=datetime.now() - timedelta(days=n, hours=-1)))
        db.commit()
        own_kpis = kpi.kpis(db, "qurolxona", own_id)
        unit_kpis = kpi.kpis(db, "bolinma", unit_id)
        all_arms = list(db.scalars(select(Armory.id)))

    scope("qurolxona", own_id)
    for path in (f"/hudud/{region_id}", f"/hudud/{region_id}/partials/kpi", f"/hudud/{region_id}/partials/lenta",
                 f"/hudud/{region_id}/partials/bolinmalar", "/hududlar/partials/royxat"):
        response = client.get(path)
        assert response.status_code == 200
        assert all(marker not in response.text for marker in ("OTHER ARMORY SAME UNIT", "OTHER UNIT SCOPE FIXTURE",
                                                               "PRIVATE SIBLING EVENT", "PRIVATE FOREIGN EVENT"))
        if "k" in response.context:
            assert response.context["k"] == own_kpis
    own_region = client.get(f"/hudud/{region_id}").context
    assert len(own_region["units"]) == 1 and len(own_region["armories"]) == 1
    exported = client.post(f"/hudud/{region_id}/eksport", data={"maqsad": "Scope export audit"})
    assert exported.status_code == 200
    result = csv_rows(exported.content)
    assert len(result) == 1 and result[0]["Qurolxona"] == "1"
    assert int(result[0]["Yacheyka"]) == own_kpis["yacheykalar"]
    with SessionLocal() as db:
        log = db.scalar(select(ExportLog).where(ExportLog.number == exported.headers["X-Export-Number"]))
        hudud_log_id = log.id
        assert hisobot_svc.file_path(log).read_bytes() == exported.content
        assert log.file_hash == hashlib.sha256(exported.content).hexdigest()
        assert hisobot_svc.export_event(db, log).payload["armory_ids"] == [own_id]
    assert client.get(f"/hisobotlar/eksportlar/{hudud_log_id}").status_code == 200
    assert client.get(f"/hisobotlar/eksportlar/{hudud_log_id}/fayl").content == exported.content
    assert client.get(f"/hisobotlar/hudud_bolinmalar?hudud={region_id}").status_code == 200
    scope("bolinma", unit_id)
    response = client.get(f"/hudud/{region_id}")
    assert response.context["k"] == unit_kpis and len(response.context["units"]) == 1
    assert "OTHER ARMORY SAME UNIT" in response.text and "OTHER UNIT SCOPE FIXTURE" not in response.text
    scope("qurolxona", neighbor_id)
    assert client.get(f"/hisobotlar/eksportlar/{hudud_log_id}/fayl").status_code == 403
    scope("qurolxona", 999999)
    assert client.get("/hududlar").status_code == 403 and client.get(f"/hudud/{region_id}").status_code == 403
    print("Region views/partials/KPI/export preserve armory and unit scopes; CSV persistence and source link OK")

    scope()
    response = client.get(f"/qurolxona/{own_id}/smenalar?page=2")
    assert response.status_code == 200 and response.context["pg"]["page"] == 2 and response.context["rows"]
    assert not client.get(f"/qurolxona/{neighbor_id}/smenalar").context["rows"]
    scope(role="navbatchi")
    for lang in ("lat", "cyr"):
        ctx.lang = lang
        for aid in all_arms:
            for suffix in ("smena/ochish", "smena/yopish"):
                response = client.get(f"/qurolxona/{aid}/{suffix}")
                assert response.status_code == 200, (lang, aid, suffix)
    ctx.lang = "lat"
    print(f"Shift history pagination/empty state and {len(all_arms) * 4} Latin/Cyrillic open/close page requests OK")

print("PASS scratch:", SCRATCH)

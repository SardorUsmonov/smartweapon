"""Leadership snapshot semantics and authenticated scope checks in a fresh DB."""
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_leadership_"))
sys.path.insert(0, str(ROOT))
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")
os.environ["AQ_DEMO"] = "1"

from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, SessionLocal, engine
from app.models import Alarm, Armory, Cabinet, Item, Region, Unit, User
from app.services.executive import LOCAL_TZ, leadership_snapshot, overview
from app.services.kpi import armory_ids_for_scope, kpis, region_rows

NOW = datetime.now(LOCAL_TZ).replace(microsecond=0)
WALL = NOW.replace(tzinfo=None)
Base.metadata.create_all(engine)

with SessionLocal() as db:
    db.add_all([
        Region(id=1, code="UZ-TK", name="Toshkent shahri", short="Toshkent sh.", order=1),
        Region(id=2, code="UZ-FA", name="Farg'ona viloyati", short="Farg'ona", order=2),
        Region(id=3, code="UZ-NG", name="Namangan viloyati", short="Namangan", order=3),
        Region(id=4, code="UZ-AN", name="Andijon viloyati", short="Andijon", order=4),
    ])
    db.flush()
    db.add_all([Unit(id=1, region_id=1, name="Own unit"), Unit(id=2, region_id=2, name="Missing telemetry"),
                Unit(id=4, region_id=4, name="Foreign unit")])
    db.flush()
    db.add_all([
        Armory(id=11, unit_id=1, name="Fresh own", online=True, last_sync=WALL - timedelta(minutes=2)),
        Armory(id=12, unit_id=1, name="Stale own", online=False, last_sync=WALL - timedelta(minutes=30)),
        Armory(id=21, unit_id=2, name="Never synchronized", online=True, last_sync=None),
        Armory(id=41, unit_id=4, name="Foreign", online=False, last_sync=WALL - timedelta(minutes=1)),
    ])
    db.flush()
    for arm_id in [11, 12, 21, 41]:
        db.add(Cabinet(id=arm_id, armory_id=arm_id, serial=f"CAB-{arm_id}", label=str(arm_id)))
    db.flush()
    for item_id, cab_id in enumerate([11, 12, 21, 41, 41, 41, None], start=1):
        db.add(Item(id=item_id, cabinet_id=cab_id, kind="qurol", category="avtomat", serial=f"ITEM-{item_id}"))
    db.add(Item(id=8, cabinet_id=11, kind="jihoz", category="jihoz", serial="NON-WEAPON"))

    def alarm(arm_id, level, opened, resolved=None, region_id=1, **metadata):
        record = Alarm(armory_id=arm_id, region_id=region_id, level=level, type="test",
                       opened_at=opened, resolved_at=resolved, title="Fixture", requires_ack=level != "INFO", **metadata)
        db.add(record)
        return record

    future_resolution = alarm(11, "CRITICAL", WALL - timedelta(days=2), WALL + timedelta(days=1))
    forged_metadata = alarm(12, "SECURITY", WALL - timedelta(hours=1), region_id=4, unit_id=4,
                            acked_at=WALL + timedelta(hours=1))  # mismatched location and future acknowledgement
    resolved_metadata = alarm(11, "WARNING", WALL - timedelta(days=2), WALL - timedelta(hours=1), region_id=4, unit_id=4)
    null_metadata = alarm(11, "WARNING", WALL - timedelta(hours=2), region_id=None)
    alarm(11, "CRITICAL", WALL - timedelta(days=2), WALL - timedelta(days=1))  # exact cutoff closed
    future_opening = alarm(11, "CRITICAL", WALL + timedelta(days=2))  # not yet opened
    for _ in range(3):
        alarm(41, "CRITICAL", WALL - timedelta(days=2), region_id=1)  # cannot leak through region_id
    alarm(None, "SECURITY", WALL - timedelta(days=2), region_id=None)
    alarm(None, "INFO", WALL - timedelta(hours=1), region_id=None)
    db.add_all([
        User(username="admin", full_name="Central", role="administrator", scope_kind="respublika", mfa=True),
        User(username="hudud_tk", full_name="Regional", role="tekshiruvchi", scope_kind="hudud", scope_id=1, mfa=True),
        User(username="tekshiruvchi", full_name="Unit", role="tekshiruvchi", scope_kind="bolinma", scope_id=1, mfa=True),
        User(username="navbatchi", full_name="Local", role="navbatchi", scope_kind="qurolxona", scope_id=11, mfa=True),
    ])
    db.commit()

with SessionLocal() as db:
    snapshot = leadership_snapshot(db, region_rows(db), now=NOW)
    rows = {r["id"]: r for r in snapshot["regions"]}
    tk = rows[1]
    assert tk["critical"] == 1 and tk["warning"] == 1 and tk["offline"] == 1, tk
    assert tk["stock"] == 2 and tk["sites"] == 2 and tk["state"] == "critical"
    assert tk["previous"] == {"critical": 1, "warning": 1, "offline": None}, tk["previous"]
    assert tk["updatedAt"] == (NOW - timedelta(minutes=30)).isoformat(timespec="seconds")
    assert tk["stale"] and tk["staleSites"] == 1 and tk["missingTelemetrySites"] == 0
    missing, absent = rows[2], rows[3]
    assert missing["sites"] == 1 and missing["stock"] == 1 and missing["state"] == "unknown"
    assert missing["critical"] == 0 and missing["offline"] is None and missing["online"] is None
    assert missing["updatedAt"] is None and missing["missingTelemetrySites"] == 1
    assert absent["sites"] == 0 and absent["state"] == "unknown" and absent["critical"] is None
    assert absent["updatedAt"] is None and absent["previous"]["critical"] is None
    assert snapshot["totals"]["critical"] == 5 and snapshot["totals"]["warning"] == 1
    assert snapshot["totals"]["sites"] == 4 and snapshot["totals"]["stock"] == 7
    assert snapshot["totals"]["offline"] is None and snapshot["totals"]["knownOffline"] == 2
    assert snapshot["unassigned"] == {"critical": 1, "warning": 0, "stock": 1}
    assert snapshot["previousTotals"] == {"critical": 5, "warning": 1, "offline": None}
    assert snapshot["asOf"] == NOW.isoformat(timespec="seconds") and snapshot["demo"] is True
    assert snapshot["previousAsOf"] == (NOW - timedelta(days=1)).isoformat(timespec="seconds")
    central_overview = overview(db, kpis(db, now=WALL), region_rows(db), now=NOW)
    summary = central_overview["exec_summary"]
    assert summary["active_critical"] == snapshot["totals"]["critical"]
    assert summary["active_warning"] == snapshot["totals"]["warning"]
    assert summary["total_active"] == 7  # INFO exists but is not an actionable signal in the map.
    assert summary["pending_ack"] == 5  # Workflow ack/resolution remain completed despite a future timestamp.
    assert summary["affected_regions"] == 2  # armory ownership, not the forged metadata
    own_overview = overview(db, kpis(db, "hudud", 1, now=WALL), region_rows(db, armory_ids=[11, 12]), [11, 12], now=NOW)
    forged_attention = next(row for row in own_overview["attention"] if row["id"] == forged_metadata.id)
    assert forged_attention["location"] == "Toshkent sh. · Own unit · Stale own", forged_attention
    assert not forged_attention["needs_ack"] and forged_attention["acked"]
    assert all(row["id"] != future_opening.id for row in central_overview["attention"])
    # Counts and history stay within the same armory scope, even with conflicting
    # Alarm.region_id values; aggregate connection gaps never turn into zero.
    for kind, scope_id, expected_sites, expected_critical in [
        ("hudud", 1, 2, 1), ("bolinma", 1, 2, 1), ("qurolxona", 11, 1, 0),
    ]:
        ids = armory_ids_for_scope(db, kind, scope_id)
        scoped = leadership_snapshot(db, region_rows(db, armory_ids=ids), ids, now=NOW)
        assert [r["id"] for r in scoped["regions"]] == [1]
        assert scoped["totals"]["sites"] == expected_sites and scoped["totals"]["critical"] == expected_critical
        assert scoped["unassigned"] == {"critical": 0, "warning": 0, "stock": 0}
        assert scoped["previousTotals"]["critical"] == 1
        scoped_overview = overview(db, kpis(db, kind, scope_id, now=WALL), region_rows(db, armory_ids=ids), ids, now=NOW)
        assert scoped_overview["exec_summary"]["active_critical"] == scoped["totals"]["critical"]
        assert scoped_overview["exec_summary"]["active_warning"] == scoped["totals"]["warning"]
        assert scoped_overview["exec_summary"]["pending_ack"] == 1
        assert all(row["id"] != future_resolution.id for row in scoped_overview["attention"])
        assert all(row["id"] != future_opening.id and "Foreign" not in row["location"] and "Andijon" not in row["location"]
                   for row in scoped_overview["attention"])
    empty = leadership_snapshot(db, region_rows(db, armory_ids=[]), [], now=NOW)
    assert empty["regions"] == [] and empty["totals"]["sites"] == 0 and empty["totals"]["stock"] == 0
    assert empty["totals"]["offline"] is None and empty["unassigned"]["critical"] == 0
    assert not db.new and not db.dirty and not db.deleted
print("PASS: scoped current/prior counts, SECURITY classification, null vs zero, oldest/stale telemetry and unmapped totals")
print("PASS: overview/snapshot cutoff consistency, pending acknowledgements, INFO distinction and authoritative attention locations")


def login(client, username):
    client.get("/kirish")
    token = client.cookies["aq_csrf"]
    result = client.post("/kirish", data={"username": username, "password": "demo", "csrf_token": token}, follow_redirects=False)
    assert result.status_code == 303
    result = client.post("/kirish/mfa", data={"code": "123456", "csrf_token": token}, follow_redirects=False)
    assert result.status_code == 303


with TestClient(app) as client:
    assert client.get("/api/leadership").status_code == 401
    login(client, "admin")
    response = client.get("/api/leadership")
    assert response.status_code == 200 and len(response.json()["regions"]) == 4
    assert "no-store" in response.headers["cache-control"]
    central_map = response.json()
    for path in ("/signallar?hudud=1", "/signallar/partials/faol?hudud=1"):
        listed = client.get(path)
        assert listed.status_code == 200
        region = next(row for row in central_map["regions"] if row["id"] == 1)
        data = listed.context
        assert data["total"] == region["critical"] + region["warning"] == 2
        assert data["counts"]["by_level"]["SECURITY"] + data["counts"]["by_level"]["CRITICAL"] == region["critical"]
        assert data["counts"]["by_level"]["WARNING"] == region["warning"]
        assert {row["a"].id for row in data["rows"]} == {forged_metadata.id, null_metadata.id}
        for row in data["rows"]:
            assert row["region_id"] == 1 and row["region"] == "Toshkent sh." and row["unit"] == "Own unit"
            card = re.search(r'<article\b[^>]*id="s' + str(row["a"].id) + r'"[^>]*>.*?</article>', listed.text, re.S).group(0)
            assert 'href="/hudud/1"' in card and 'href="/hudud/4"' not in card
        assert any(row["a"].id == resolved_metadata.id and row["region_id"] == 1 for row in data["recent_resolved"])
    for path in ("/signallar?hudud=1&holat=yechilgan", "/signallar/partials/faol?hudud=1&holat=yechilgan"):
        history = client.get(path)
        assert history.status_code == 200
        assert all(row["a"].armory_id in {11, 12} and row["region_id"] == 1 for row in history.context["rows"])
        assert any(row["a"].id == resolved_metadata.id for row in history.context["rows"])
    client.get("/til/cyr", follow_redirects=False)
    translated = client.get("/api/leadership").json()
    assert next(r for r in translated["regions"] if r["id"] == 1)["name"] == "Тошкент шаҳри"
    for name, expected_sites in [("hudud_tk", 2), ("tekshiruvchi", 2), ("navbatchi", 1)]:
        with TestClient(app) as scoped:
            login(scoped, name)
            data = scoped.get("/api/leadership").json()
            assert [r["id"] for r in data["regions"]] == [1], (name, data)
            assert data["totals"]["sites"] == expected_sites
            assert data["unassigned"] == {"critical": 0, "warning": 0, "stock": 0}
            listed = scoped.get("/signallar?hudud=1")
            assert listed.status_code == 200 and listed.context["total"] == data["totals"]["critical"] + data["totals"]["warning"]
            forbidden = scoped.get("/signallar?hudud=4")
            assert forbidden.status_code == 200 and forbidden.context["total"] == 0
print("PASS: anonymous denial, central/region/unit/armory authenticated API scopes, no-store and Cyrillic labels")
print("PASS: map counts match regional signal lists/partials/history; null/stale metadata uses authoritative region labels and links")
print("LEADERSHIP_TEST_DB", SCRATCH / "test.sqlite3")

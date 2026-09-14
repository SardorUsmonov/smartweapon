"""Inventory/custody presentation, source preservation and new-seed regression.

Run: python -B -X utf8 tests/verify_inventory_consistency.py
All writes, including generated demo data, stay in a temporary directory.
"""
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3"
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_inventory_consistency_"))
TARGET = SCRATCH / "test.sqlite3"
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
with sqlite3.connect(SOURCE.as_uri() + "?mode=ro", uri=True) as src, sqlite3.connect(TARGET) as dst:
    src.backup(dst)
os.environ["AQ_DB"] = str(TARGET)
os.environ["AQ_DEMO"] = "1"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal
from app.deps import Ctx, get_ctx
from app.models import Armory, Cabinet, Custody, Item, Unit, User
from app.services import inventar_svc as svc
from app.services.kpi import armory_ids_for_scope, kpis


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.hrefs = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.hrefs.append(attrs["href"])


actor = {"kind": "respublika", "id": None}
app.dependency_overrides[get_ctx] = lambda: Ctx(User(
    id=999, username="consistency_test", full_name="Consistency test", role="administrator",
    scope_kind=actor["kind"], scope_id=actor["id"], active=True), "lat")


def read(client, url, **params):
    response = client.get(url, params=params) if params else client.get(url)
    assert response.status_code == 200, (url, response.status_code, response.text[:200])
    return response


def rows(response):
    return {row[0].id for row in response.context["data"]["rows"]}


def expected(ids, *, overdue=False):
    # Independent SQL: actual item rows on both sides of the visible custody record.
    query = """SELECT DISTINCT i.id FROM item i
        JOIN cabinet current_cab ON current_cab.id=i.cabinet_id
        JOIN custody c ON c.item_id=i.id
        JOIN cabinet custody_cab ON custody_cab.id=c.cabinet_id
        WHERE i.kind='qurol' AND c.returned_at IS NULL"""
    values = []
    if ids is not None:
        marks = ",".join("?" for _ in ids) or "NULL"
        query += f" AND current_cab.armory_id IN ({marks}) AND custody_cab.armory_id IN ({marks})"
        values.extend(ids)
        values.extend(ids)
    if overdue:
        query += " AND c.due_at < ?"
        values.append(datetime.now().isoformat(sep=" "))
    with sqlite3.connect(TARGET.as_uri() + "?mode=ro", uri=True) as db:
        return {r[0] for r in db.execute(query, values)}


with TestClient(app) as client:
    # The exact browser path reported during acceptance: original source rows only.
    unit_page = read(client, "/hudud/1/bolinma/2")
    issued_link = next(link for link in Links(unit_page.text).hrefs
                       if urlsplit(link).path == "/inventar"
                       and parse_qs(urlsplit(link).query).get("berilgan") == ["1"])
    issued_page = read(client, issued_link)
    assert unit_page.context["k"]["berilgan"] == issued_page.context["data"]["total"] == 8, (
        issued_link, unit_page.context["k"], issued_page.context["data"]["total"])
    assert issued_page.context["k"]["xodimda"] == 8
    assert len(rows(issued_page)) == 8
    assert all(row[0].state == "mavjud" for row in issued_page.context["data"]["rows"])
    assert issued_page.text.count('data-inventory-mismatch="') == 8
    original_kpi = read(client, "/inventar/partials/kpi").context["k"]
    assert (original_kpi["xodimda"], original_kpi["ochiq_qaydlar"], original_kpi["takroriy_qaydlar"]) == (182, 183, 1)
    global_page = read(client, "/inventar", berilgan=1)
    next_link = next(link for link in Links(global_page.text).hrefs
                     if urlsplit(link).path == "/inventar" and parse_qs(urlsplit(link).query).get("page") == ["2"])
    assert parse_qs(urlsplit(next_link).query)["berilgan"] == ["1"]
    second_page = read(client, next_link)
    assert second_page.context["data"]["total"] == 182 and second_page.context["p"]["berilgan"]
    assert not (rows(global_page) & rows(second_page))
    assert 'name="berilgan" value="1" checked' in second_page.text
    legacy = read(client, "/inventar", bolinma=2, holat="yo'q")
    assert rows(legacy) == rows(issued_page) and legacy.context["p"]["berilgan"]
    assert not (rows(read(client, "/inventar", bolinma=2, holat="mavjud")) & rows(issued_page))
    for row in issued_page.context["data"]["rows"]:
        detail = read(client, f"/jihoz/{row[0].id}")
        assert detail.context["item"].state == "mavjud" and detail.context["open_count"] == 1
        assert f'data-inventory-mismatch="{row[0].id}"' in detail.text
    print("PASS: actual unit2 Berilgan 8 link opens exactly 8 items; source-state conflicts stay visible")

    with SessionLocal() as db:
        arm = db.get(Armory, 1)
        A, U, R = arm.id, arm.unit_id, arm.unit.region_id
        cab = db.scalar(select(Cabinet).where(Cabinet.armory_id == A, Cabinet.officer_id.is_not(None)))
        foreign = db.scalar(select(Cabinet).join(Armory).join(Unit).where(
            Unit.region_id != R, Cabinet.officer_id.is_not(None)))
        B = foreign.armory_id
        fixtures = {}
        for name, state, current_cab in [
            ("duplicate", "mavjud", cab), ("matched", "yo'q", cab),
            ("no_record", "yo'q", cab), ("available", "mavjud", cab),
            ("foreign_custody", "mavjud", cab), ("foreign_item", "mavjud", foreign),
        ]:
            item = Item(kind="qurol", category="avtomat", model="Consistency fixture", serial="CONSIST-" + name,
                        cabinet_id=current_cab.id, officer_id=current_cab.officer_id, state=state)
            db.add(item)
            db.flush()
            fixtures[name] = item.id
        now = datetime.now()
        for name, record_cab, delta in [("duplicate", cab, -2), ("duplicate", cab, 5),
                                        ("matched", cab, -1), ("foreign_custody", foreign, -3),
                                        ("foreign_item", cab, -3)]:
            db.add(Custody(item_id=fixtures[name], cabinet_id=record_cab.id, officer_id=record_cab.officer_id,
                          taken_at=now - timedelta(hours=8), due_at=now + timedelta(hours=delta)))
        # An open record must not disappear behind the 100 most recent history rows.
        for i in range(105):
            db.add(Custody(item_id=fixtures["duplicate"], cabinet_id=cab.id, officer_id=cab.officer_id,
                          taken_at=now + timedelta(minutes=i), due_at=now + timedelta(hours=2), returned_at=now))
        db.commit()

    for kind, scope in [("respublika", None), ("hudud", R), ("bolinma", U), ("qurolxona", A), ("qurolxona", -999)]:
        actor.update(kind=kind, id=scope)
        with SessionLocal() as db:
            ids = armory_ids_for_scope(db, kind, scope)
            dashboard = kpis(db, kind, scope)
        page = read(client, "/inventar", berilgan=1)
        overdue = read(client, "/inventar", kechikish=1)
        wanted = expected(ids)
        late = expected(ids, overdue=True)
        assert page.context["data"]["total"] == page.context["k"]["xodimda"] == dashboard["berilgan"] == len(wanted)
        assert overdue.context["data"]["total"] == overdue.context["k"]["kechikish"] == dashboard["kechikish"] == len(late)
        assert rows(page) <= wanted and rows(overdue) <= late
        live = read(client, "/inventar/partials/kpi")
        assert live.context["k"] == page.context["k"]
        kpi_link = next(link for link in Links(live.text).hrefs if "berilgan=1" in link)
        assert read(client, kpi_link).context["data"]["total"] == len(wanted)
        if ids is not None and ids:
            scoped = read(client, "/inventar", berilgan=1, q="CONSIST-")
            assert rows(scoped) == {fixtures["duplicate"], fixtures["matched"]}
            assert fixtures["foreign_custody"] not in scoped.context["data"]["open"]
        if ids == []:
            assert not wanted and page.context["k"]["ochiq_qaydlar"] == 0

    actor.update(kind="qurolxona", id=A)
    filtered = read(client, "/inventar", berilgan=1, q="CONSIST-")
    assert filtered.context["data"]["total"] == 2
    assert filtered.context["data"]["open_counts"][fixtures["duplicate"]] == 2
    assert f'data-custody-duplicate="{fixtures["duplicate"]}"' in filtered.text
    assert filtered.context["data"]["open"][fixtures["duplicate"]].due_at < datetime.now()
    detail = read(client, f'/jihoz/{fixtures["duplicate"]}')
    assert detail.context["open_count"] == 2 and detail.context["open"] is not None
    assert len(detail.context["custody"]) == 100 and all(c.returned_at for c in detail.context["custody"])
    assert f'data-custody-duplicate="{fixtures["duplicate"]}"' in detail.text
    missing = read(client, f'/jihoz/{fixtures["no_record"]}')
    assert missing.context["open_count"] == 0 and 'data-inventory-mismatch="' in missing.text
    foreign_detail = read(client, f'/jihoz/{fixtures["foreign_custody"]}')
    assert foreign_detail.context["open_count"] == 0 and not foreign_detail.context["custody"]
    available = read(client, "/inventar", holat="mavjud", q="CONSIST-")
    assert rows(available) == {fixtures["available"]}, "A hidden open record must not imply availability"
    assert client.get(f'/jihoz/{fixtures["foreign_item"]}').status_code == 403
    empty = read(client, "/inventar", berilgan=1, qurolxona=B)
    assert empty.context["data"]["total"] == empty.context["k"]["xodimda"] == 0
    assert read(client, "/inventar", berilgan=1, holat="mavjud", q="CONSIST-").context["data"]["total"] == 0
    print("PASS: distinct counts, duplicate source records, overdue duplicates, 100-row history and scope intersections")

app.dependency_overrides.clear()
preserved = subprocess.run([sys.executable, "-B", "-X", "utf8", "scripts/check_preserved_rows.py", str(SOURCE), str(TARGET)],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
assert preserved.returncode == 0, preserved.stdout + preserved.stderr
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
print("PASS: all original rows across 19 baseline tables survive unchanged; baseline file hash unchanged")

fresh_code = """
from datetime import datetime
from sqlalchemy import func, select
from app.db import Base, engine, SessionLocal
from app.models import Custody, Item
from app.seed import seed
from app.services.events import verify_chain
Base.metadata.create_all(engine)
seed(size='small', days=2, now=datetime(2026, 9, 12, 12, 0))
with SessionLocal() as db:
    issued = set(db.scalars(select(Custody.item_id).where(Custody.returned_at.is_(None))))
    absent = set(db.scalars(select(Item.id).where(Item.state == "yo'q")))
    assert issued and issued == absent, (len(issued), len(absent))
    assert verify_chain(db)['ok']
    print(f'PASS: newly seeded {len(issued)} open-custody items have matching state; audit chain valid')
"""
fresh = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", fresh_code], cwd=ROOT,
                       env={**os.environ, "AQ_DB": str(SCRATCH / "fresh.sqlite3")}, capture_output=True,
                       text=True, encoding="utf-8", timeout=60)
assert fresh.returncode == 0, fresh.stdout + fresh.stderr
print(fresh.stdout.strip())
print("TempDB:", TARGET)

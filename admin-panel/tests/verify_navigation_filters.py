"""Follow rendered navigation/form/pager/live contracts against an isolated database.

Run: python -X utf8 tests/verify_navigation_filters.py
"""
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_navigation_filters_"))
BACKUP = ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3"
with sqlite3.connect(BACKUP.as_uri() + "?mode=ro", uri=True) as src, sqlite3.connect(SCRATCH / "test.sqlite3") as dst:
    src.backup(dst)
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.db import SessionLocal
from app.deps import Ctx, get_ctx
from app.main import app
from app.models import Alarm, Armory, Cabinet, Device, Item, Officer, Unit, User
from app.routers import qurolxonalar, signallar, yacheykalar


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links, self.live, self.forms = [], [], []
        self.form = self.select = self.option = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if "hx-get" in attrs:
            self.live.append(attrs["hx-get"])
        if tag == "form":
            self.form = {"action": attrs.get("action", ""), "method": attrs.get("method", "get"), "values": {}}
            self.forms.append(self.form)
        if self.form and tag == "input" and attrs.get("name"):
            if attrs.get("type") not in ("checkbox", "radio") or "checked" in attrs:
                self.form["values"][attrs["name"]] = attrs.get("value", "")
        if self.form and tag == "select":
            self.select = attrs.get("name")
        if self.form and self.select and tag == "option":
            values = self.form["values"]
            if self.select not in values or "selected" in attrs:
                values[self.select] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "select":
            self.select = None
        if tag == "form":
            self.form = None


with SessionLocal() as db:
    arm = db.scalar(select(Armory).order_by(Armory.id))
    A, U, R = arm.id, arm.unit_id, arm.unit.region_id
    foreign = db.scalar(select(Armory).join(Unit).where(Unit.region_id != R).order_by(Armory.id))
    B, V, S = foreign.id, foreign.unit_id, foreign.unit.region_id
    officer = db.scalar(select(Officer).where(Officer.armory_id == A))
    O = officer.id
    cab = db.scalar(select(Cabinet).where(Cabinet.armory_id == A))
    C = cab.id
    # Ensure genuine filtered pagination even with the small baseline fleet.
    extra_arm = Armory(unit_id=U, name="Navigation fixture", address="Temporary test fixture", online=True)
    db.add(extra_arm)
    db.flush()
    for i in range(3):
        db.add(Alarm(armory_id=A, cabinet_id=C, unit_id=U, region_id=R, level="WARNING", type="batareya",
                     title=f"Navigation fixture {i}", detail="Temporary filter fixture", opened_at=datetime.now()))
    for i in range(55):
        db.add(Item(kind="qurol", category="avtomat", model="Navigation fixture", serial=f"NAV-{i:03d}",
                    cabinet_id=C, officer_id=O, state="mavjud"))
    db.commit()
    arm_map = {a.id: (a.unit_id, a.unit.region_id) for a in db.scalars(select(Armory))}

# Test-only page sizes produce actual rendered next/previous links.
qurolxonalar.PER_PAGE = signallar.PER_PAGE = yacheykalar.PER_PAGE = 1
actor = {"kind": "respublika", "id": None}
app.dependency_overrides[get_ctx] = lambda: Ctx(
    User(id=999, username="navigation_test", full_name="Navigation test", role="qurolxona_masuli",
         scope_kind=actor["kind"], scope_id=actor["id"], active=True), "lat")
ROUTES = ("/inventar", "/signallar", "/yacheykalar", "/qurolxonalar", "/qurilmalar")


def visible_armories(response):
    path, context = response.request.url.path, response.context
    if path == "/inventar":
        return [row[2].id for row in context["data"]["rows"]]
    if path in ("/signallar", "/signallar/partials/faol"):
        return [row["a"].armory_id for row in context["rows"]]
    if path == "/yacheykalar":
        return [row[0].armory_id for row in context["rows"]]
    if path == "/qurolxonalar":
        return [row["id"] for row in context["rows"]]
    return [row["armory_id"] for row in context["pg"]["rows"]]


def allowed_ids(params):
    ids = set(arm_map)
    if actor["kind"] == "hudud":
        ids = {aid for aid in ids if arm_map[aid][1] == actor["id"]}
    elif actor["kind"] == "qurolxona":
        ids &= {actor["id"]}
    for name, index in (("hudud", 1), ("bolinma", 0)):
        if params.get(name):
            ids = {aid for aid in ids if str(arm_map[aid][index]) == str(params[name])}
    if params.get("qurolxona"):
        ids = {aid for aid in ids if str(aid) == str(params["qurolxona"])}
    return ids


def check_page(client, url, require_rows=False):
    response = client.get(url)
    assert response.status_code == 200, (url, response.status_code, response.text[:200])
    params = {k: v[0] for k, v in parse_qs(urlsplit(str(response.request.url)).query, keep_blank_values=True).items()}
    rows = visible_armories(response)
    expected = allowed_ids(params)
    assert set(rows) <= expected, (url, rows, expected, actor)
    if require_rows:
        assert rows, (url, "unexpected empty list")
    parsed = Page(response.text)
    if response.request.url.path in ROUTES:
        form = next(form for form in parsed.forms if form["action"] == response.request.url.path and form["method"] == "get")
        for field in ("hudud", "bolinma", "qurolxona", "xodim"):
            if params.get(field) and int(params[field]) > 0:
                assert form["values"].get(field) == params[field], (url, field, form["values"])
    return response, parsed


with TestClient(app) as client:
    # Fetch actual hyperlinks emitted by the source detail pages, then follow them.
    contracts = []
    for source in (f"/qurolxona/{A}", f"/hudud/{R}/bolinma/{U}", f"/xodim/{O}"):
        response = client.get(source)
        assert response.status_code == 200, source
        for href in Page(response.text).links:
            parts = urlsplit(href)
            if parts.path in ROUTES and any(key in parse_qs(parts.query) for key in ("bolinma", "qurolxona", "xodim")):
                contracts.append(href)
                check_page(client, href)
    assert {urlsplit(href).path for href in contracts} == set(ROUTES), contracts
    print(f"PASS: followed {len(contracts)} actual armory/unit/officer detail links")

    # Exact basic list totals against the database, not just vacuous subset checks.
    for route in ROUTES:
        response, _ = check_page(client, route + "?qurolxona=" + str(A), require_rows=True)
        with SessionLocal() as db:
            if route == "/inventar":
                expected = db.scalar(select(func.count(Item.id)).join(Cabinet).where(Cabinet.armory_id == A, Item.kind == "qurol"))
                actual = response.context["data"]["total"]
            elif route == "/signallar":
                expected = db.scalar(select(func.count(Alarm.id)).where(Alarm.armory_id == A, Alarm.resolved_at.is_(None)))
                actual = response.context["total"]
            elif route == "/yacheykalar":
                expected = db.scalar(select(func.count(Cabinet.id)).where(Cabinet.armory_id == A))
                actual = response.context["total"]
            elif route == "/qurolxonalar":
                expected, actual = 1, response.context["pg"]["total"]
            else:
                expected = db.scalar(select(func.count(Device.id)).where(Device.armory_id == A))
                actual = response.context["pg"]["total"]
        assert actual == expected, (route, actual, expected)

    for kind, scope in (("respublika", None), ("hudud", R), ("qurolxona", A)):
        actor.update(kind=kind, id=scope)
        for route in ROUTES:
            for params in ({"bolinma": U}, {"qurolxona": A}, {"hudud": R, "bolinma": U, "qurolxona": A},
                           {"bolinma": V}, {"qurolxona": B}, {"bolinma": U, "qurolxona": B},
                           {"hudud": S, "bolinma": U}, {"bolinma": 999999}, {"qurolxona": 999999}):
                response, parsed = check_page(client, route + "?" + urlencode(params))
                if not allowed_ids(params):
                    assert not visible_armories(response)
                form = next(form for form in parsed.forms if form["action"] == route and form["method"] == "get")
                # Submitting the actual rendered GET form preserves the current location selection.
                check_page(client, form["action"] + "?" + urlencode(form["values"]))
        for href in contracts:
            check_page(client, href)
    print("PASS: exact per-armory totals and location intersections across central, regional and armory users; real filter forms preserve selections")

    actor.update(kind="respublika", id=None)
    for route in ROUTES:
        for key in ("bolinma", "qurolxona"):
            response = client.get(route, params={key: "invalid"})
            assert response.status_code == 200 and not visible_armories(response), (route, key)
    # Search characters must remain encoded in the rendered pager and tab URLs.
    for route in ROUTES:
        search = "Navigation fixture" if route == "/inventar" else ""
        response, parsed = check_page(client, route + "?" + urlencode({"bolinma": U, "q": search}))
        navigation = [href for href in parsed.links if urlsplit(href).path == route and "page" in parse_qs(urlsplit(href).query)]
        for href in navigation:
            params = parse_qs(urlsplit(href).query, keep_blank_values=True)
            assert params.get("bolinma") == [str(U)], (route, href)
            if search:
                assert params.get("q") == [search]
            check_page(client, href)
        if route in ("/inventar", "/signallar", "/yacheykalar", "/qurolxonalar"):
            assert navigation, (route, "no real pagination link tested")
    response, parsed = check_page(client, f"/inventar?bolinma={U}&xodim={O}")
    assert all(row[0].officer_id == O for row in response.context["data"]["rows"])
    all_tab = next(href for href in parsed.links if urlsplit(href).path == "/inventar"
                   and parse_qs(urlsplit(href).query, keep_blank_values=True).get("tur") == [""])
    assert check_page(client, all_tab)[0].context["tur"] == ""

    # Follow actual HTMX locations and the KPI links they render.
    for route in ("/inventar", "/signallar", "/qurilmalar"):
        response, parsed = check_page(client, f"{route}?bolinma={U}&qurolxona={A}")
        live_url = next(url for url in parsed.live if urlsplit(url).path.startswith(route + "/partials/"))
        params = parse_qs(urlsplit(live_url).query)
        assert params["bolinma"] == [str(U)] and params["qurolxona"] == [str(A)]
        partial = client.get(live_url, headers={"HX-Request": "true"})
        assert partial.status_code == 200
        if route == "/signallar":
            assert set(visible_armories(partial)) <= {A}
            assert partial.context["counts"] == response.context["counts"]
        else:
            key = "k" if route == "/inventar" else "s"
            assert partial.context[key]["jami"] == response.context[key]["jami"]
        for href in Page(partial.text).links:
            if urlsplit(href).path in ROUTES:
                query = parse_qs(urlsplit(href).query)
                assert query.get("bolinma") == [str(U)] and query.get("qurolxona") == [str(A)], href
                check_page(client, href)

    # Existing signal actions return to the full filtered URL embedded in the form.
    response, parsed = check_page(client, f"/signallar?bolinma={U}&qurolxona={A}&q=Navigation+fixture")
    action_form = next(form for form in parsed.forms if form["method"] == "post" and form["action"].endswith("/tasdiqlash"))
    values = action_form["values"]
    values["csrf_token"] = client.cookies["aq_csrf"]
    result = client.post(action_form["action"], data=values, follow_redirects=False)
    assert result.status_code == 303 and result.headers["location"] == values["next"]
    check_page(client, result.headers["location"])
    print("PASS: pagination, all-items tab, employee filter, HTMX/KPI preservation and signal POST return URL")
    print("Temporary DB:", SCRATCH / "test.sqlite3")

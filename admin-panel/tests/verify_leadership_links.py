"""Follow the integrated leadership page's rendered links using an isolated DB."""
import json
import os
import sqlite3
import sys
import tempfile
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_leadership_links_"))
SOURCE = ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3"
with sqlite3.connect(SOURCE.as_uri() + "?mode=ro", uri=True) as source, sqlite3.connect(SCRATCH / "test.sqlite3") as target:
    source.backup(target)
os.environ["AQ_DB"] = str(SCRATCH / "test.sqlite3")
os.environ["AQ_DEMO"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.db import SessionLocal
from app.deps import Ctx, get_ctx
from app.main import app, templates
from app.models import Armory, Region, Unit, User


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.links, self.assets, self.regions, self.nodes, self.data = [], [], {}, [], ""
        self.reading_data = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.nodes.append((tag, attrs))
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
            if attrs.get("data-lm-region"):
                self.regions[attrs["data-lm-region"]] = attrs["href"]
        if tag == "script" and attrs.get("src", "").startswith("/static/"):
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("href", "").startswith("/static/"):
            self.assets.append(attrs["href"])
        if tag == "script" and "data-lm-data" in attrs:
            self.reading_data = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.reading_data = False

    def handle_data(self, value):
        if self.reading_data:
            self.data += value


with SessionLocal() as db:
    site = db.scalar(select(Armory).order_by(Armory.id))
    A, U, R = site.id, site.unit_id, site.unit.region_id
    region_codes = {region.id: region.code for region in db.scalars(select(Region))}
    all_regions = set(region_codes)
    foreign = db.scalar(select(Armory).join(Unit).where(Unit.region_id != R))
    foreign_region = foreign.unit.region_id

actor = {"kind": "respublika", "id": None, "lang": "lat"}
app.dependency_overrides[get_ctx] = lambda: Ctx(
    User(id=999, username="leadership_links_test", full_name="Leadership links test", role="administrator",
         scope_kind=actor["kind"], scope_id=actor["id"], active=True), actor["lang"])

followed = set()
with TestClient(app) as client:
    for kind, scope_id, region_ids in [
        ("respublika", None, all_regions), ("hudud", R, {R}),
        ("bolinma", U, {R}), ("qurolxona", A, {R}),
    ]:
        actor.update(kind=kind, id=scope_id, lang="lat")
        result = client.get("/partials/executive", headers={"HX-Request": "true"})
        assert result.status_code == 200, (kind, result.status_code)
        page = Page(result.text)
        snapshot = json.loads(page.data)
        assert {row["id"] for row in snapshot["regions"]} == region_ids, (kind, snapshot)
        assert page.regions == {region_codes[rid]: f"/hudud/{rid}" for rid in region_ids}
        assert not any(tag == "iframe" or "hx-swap-oob" in attrs for tag, attrs in page.nodes)
        assert "no-store" in result.headers["cache-control"]
        # The actual rendered data and links are scoped together. A caller with a
        # local role must not gain a foreign region by requesting this partial.
        if kind != "respublika":
            assert client.get(f"/hudud/{foreign_region}").status_code == 403
        for href in sorted(set(page.links)):
            path = urlsplit(href)
            if path.scheme or path.netloc:
                continue
            response = client.get(href)
            assert response.status_code == 200, (kind, href, response.status_code)
            followed.add((kind, href))
            if path.path.startswith("/hudud/"):
                assert int(path.path.rsplit("/", 1)[1]) in region_ids
        # New API and HTMX page use the same source model. Time itself can advance
        # between requests, so only compare stable inventory and scope fields.
        api = client.get("/api/leadership")
        assert api.status_code == 200
        assert {row["id"] for row in api.json()["regions"]} == region_ids
        assert api.json()["totals"]["sites"] == snapshot["totals"]["sites"]
        assert api.json()["totals"]["stock"] == snapshot["totals"]["stock"]

    actor.update(kind="respublika", id=None, lang="lat")
    response = client.get("/")
    assert response.status_code == 200
    page = Page(response.text)
    overview = next(attrs for tag, attrs in page.nodes if attrs.get("id") == "executive-overview")
    assert overview.get("hx-get") == "/partials/executive" and overview.get("hx-swap") == "innerHTML"
    for asset in page.assets:
        response = client.get(asset)
        assert response.status_code == 200, (asset, response.status_code)
    assert any("leadership-shell.css" in asset for asset in page.assets)
    assert any("leadership-map.css" in asset for asset in page.assets)
    assert any("leadership-map.js" in asset for asset in page.assets)

    # A national alarm without a mapped armory must never produce an all-clear
    # priority sentence merely because every regional count is zero.
    fallback_context = dict(client.get("/partials/executive").context)
    fallback = deepcopy(fallback_context["leadership"])
    for row in fallback["regions"]:
        row["critical"] = 0
    fallback["totals"]["critical"] = 1
    fallback["unassigned"]["critical"] = 1
    fallback_context.update(leadership=fallback, attention=[])
    rendered = templates.env.get_template("partials/executive.html").render(fallback_context)
    assert "Jiddiy signallar qayd etilmagan" not in rendered
    assert "/signallar" in Page(rendered).links

    actor["lang"] = "cyr"
    response = client.get("/partials/executive")
    assert response.status_code == 200 and "Биринчи навбатда" in response.text
    assert {row["id"] for row in json.loads(Page(response.text).data)["regions"]} == all_regions

print(f"PASS: {len(followed)} rendered leadership links across central/region/unit/armory scopes")
print("PASS: snapshot/API scope agreement, foreign region denial, all local assets, HTMX swap contract and Cyrillic partial")
print("PASS: an unmapped national critical alarm cannot produce a false all-clear priority")
print("LEADERSHIP_LINKS_DB", SCRATCH / "test.sqlite3")

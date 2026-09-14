"""Yacheyka lifecycle and access-scope regression checks; only a temporary database is changed.

Run: python -X utf8 tests/verify_yacheykalar.py
"""
import os,sqlite3,tempfile,sys,html
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
scratch=Path(tempfile.mkdtemp(prefix='aq_yacheykalar_verify_'))
source=ROOT.parent/'.backups/admin-panel-20260912-141835/aq_central.sqlite3'
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(scratch/'test.sqlite3') as dst:src.backup(dst)
os.environ['AQ_DB']=str(scratch/'test.sqlite3')
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app.main import app
from app.deps import Ctx,get_ctx
from app.db import SessionLocal
from app.models import User,Cabinet,Custody,Officer,Device,Backup,Event,Item
from app.services.events import record_event
active={'role':'qurolxona_masuli','kind':'qurolxona','scope':1}
app.dependency_overrides[get_ctx]=lambda:Ctx(User(id=999,username='scope_test',full_name='Scope test',role=active['role'],scope_kind=active['kind'],scope_id=active['scope'],active=True),active.get('lang','lat'))
with TestClient(app,raise_server_exceptions=False) as c:
 def post(url,data={}):return c.post(url,data=data,headers={'X-CSRF-Token':c.cookies.get('aq_csrf')},follow_redirects=False)
 with SessionLocal() as db:
  cab=db.get(Cabinet,1);arm=cab.armory_id;oid=cab.officer_id;rid=cab.armory.unit.region_id
  foreign=db.scalar(select(Cabinet).where(Cabinet.armory_id!=arm,Cabinet.officer_id.is_not(None)))
  fcid=foreign.id;farm=foreign.armory_id;foid=foreign.officer_id
  did=db.scalar(select(Device.id).where(Device.armory_id==arm));fdid=db.scalar(select(Device.id).where(Device.armory_id==farm))
 active['scope']=arm
 c.get('/yacheykalar')
 urls=[f'/xodim/{oid}',f'/xodim/{oid}/partials/holat',f'/qurolxona/{arm}',f'/qurolxona/{arm}/partials/reja',f'/qurolxona/{arm}/partials/qurilmalar',f'/qurolxona/{arm}/partials/hodisalar',f'/qurolxona/{arm}/smena/ochish',f'/qurolxona/{arm}/smena/yopish',f'/qurolxona/{arm}/smenalar',f'/qurilma/{did}',f'/qurilmalar/partials/kontrollerlar/{arm}','/qurilmalar/partials/holat']
 failures=[]
 for url in urls:
  r=c.get(url)
  if r.status_code!=200:failures.append((url,r.status_code))
 for url in [f'/xodim/{foid}',f'/xodim/{foid}/partials/holat',f'/qurolxona/{farm}',f'/qurolxona/{farm}/partials/reja',f'/qurolxona/{farm}/partials/qurilmalar',f'/qurolxona/{farm}/partials/hodisalar',f'/qurolxona/{farm}/smena/ochish',f'/qurolxona/{farm}/smena/yopish',f'/qurolxona/{farm}/smenalar',f'/qurolxona/{farm}/smena/1',f'/qurilma/{fdid}',f'/qurilmalar/partials/kontrollerlar/{farm}']:assert c.get(url).status_code==403,url
 for url,data in [(f'/xodim/{foid}/holat',{'holat':'kasallik','sabab':'Scope denial'}),(f'/xodim/{foid}/ruxsat',{'tur':'ak','sabab':'Scope denial'}),(f'/qurolxona/{farm}/smena/ochish',{}),(f'/qurolxona/{farm}/smena/yopish',{})]:assert post(url,data).status_code==403,url
 for path in ['/xodimlar','/qurolxonalar','/qurilmalar','/qidiruv?q=Y-']:assert c.get(path).status_code==200,path
 assert all(row[0].armory_id==arm for row in c.get('/xodimlar').context['rows'])
 assert all(row['id']==arm for row in c.get('/qurolxonalar').context['rows'])
 assert all(r.id==rid for r in c.get('/qurolxonalar').context['regions_all'])
 assert all(row['armory_id']==arm for row in c.get('/qurilmalar').context['pg']['rows'])
 active['role']='administrator'
 for url in [f'/qurilma/{fdid}/self-test',f'/qurilma/{fdid}/vaqt-sinxroni',f'/qurilma/{fdid}/xizmat','/qurilmalar/zaxira/nusxa','/qurilmalar/zaxira/tiklash-sinovi']:assert post(url,{'sabab':'Scope denial'}).status_code==403,url
 assert c.get('/qurilmalar/zaxira').status_code==403
 assert post(f'/qurilma/{did}/self-test').status_code==303
 active['role']='tekshiruvchi'
 for url,data in [(f'/xodim/{oid}/holat',{'holat':'kasallik','sabab':'Role denial'}),(f'/xodim/{oid}/ruxsat',{'tur':'ak','sabab':'Role denial'}),(f'/qurolxona/{arm}/smena/ochish',{}),(f'/qurolxona/{arm}/smena/yopish',{}),(f'/qurilma/{did}/self-test',{}),(f'/qurilma/{did}/vaqt-sinxroni',{}),(f'/qurilma/{did}/xizmat',{'sabab':'Role denial'})]:assert post(url,data).status_code==403,url
 print('PASS: scope+role direct/partial/POST restrictions, all 4 lists scoped, regional filter scoped, permitted local admin action; GET failures:',failures)
 with SessionLocal() as db:
  foreign=db.get(Cabinet,fcid);off=db.get(Officer,oid);item=db.scalar(select(Item).where(Item.cabinet_id==fcid))
  ev=record_event(db,'rad_etildi',cabinet=foreign,officer=off,title='FOREIGN_HISTORY_SENTINEL',detail='Foreign scope history',simulated=True);eid=ev.id
  hist=Custody(item_id=item.id,officer_id=oid,cabinet_id=fcid,taken_at=datetime.now()-timedelta(days=1),due_at=datetime.now()-timedelta(hours=1),returned_at=None,match_ok=False);db.add(hist);db.commit();hid=hist.id
 for suffix in ['', '/partials/holat']:
  r=c.get(f'/xodim/{oid}'+suffix);assert r.status_code==200,(suffix,r.text[:100])
  assert 'FOREIGN_HISTORY_SENTINEL' not in r.text
  assert all(row['c'].id!=hid for row in r.context['open_rows'])
  if suffix=='':assert all(row['c'].id!=hid for row in r.context['custody']) and all(e.id!=eid for e in r.context['denials'])
  assert not r.context['last_ev'] or r.context['last_ev'].id!=eid
 active.update(kind='respublika',scope=None)
 r=c.get(f'/xodim/{oid}');assert 'FOREIGN_HISTORY_SENTINEL' in r.text and any(row['c'].id==hid for row in r.context['custody'])
 assert c.get('/qurilmalar/zaxira').status_code==200
 active['role']='administrator';assert post('/qurilmalar/zaxira/nusxa').status_code==303
 print('PASS: foreign officer history hidden from scoped detail+partial and present centrally; central backup GET+admin POST.')
 print('Test DB:',scratch/'test.sqlite3')
 assert not failures,failures

# Administrative lifecycle, telemetry invariants and all rendering states.
with TestClient(app) as c:
    active.update(role="qurolxona_masuli", kind="respublika", scope=None, lang="lat")
    c.get("/yacheykalar")

    def post(url, data=None):
        return c.post(url, data=data or {}, headers={"X-CSRF-Token": c.cookies["aq_csrf"]}, follow_redirects=False)

    from app.routers.yacheykalar import HOLAT_FILTERS
    for status in HOLAT_FILTERS:
        assert c.get("/yacheykalar", params={"holat": status}).status_code == 200
    for params in ({"page": -1}, {"page": 999999}, {"q": "no-such-cabinet"}, {"hudud": "invalid"}):
        r = c.get("/yacheykalar", params=params)
        assert r.status_code == 200 and 1 <= r.context["page"] <= r.context["pages"]
    assert c.get("/yacheyka/999999").status_code == 404
    with SessionLocal() as db:
        open_ids = select(Custody.cabinet_id).where(Custody.returned_at.is_(None))
        cab = db.scalar(select(Cabinet).where(Cabinet.status == "biriktirilgan", Cabinet.id.not_in(open_ids)))
        cid, assigned_id = cab.id, cab.officer_id
        lock_snapshot = (cab.door_open, cab.door_locked, cab.ak_clamp_locked, cab.pm_box_locked)
        event_count = db.scalar(select(func.count(Event.id)))
        officer = db.get(Officer, assigned_id)
        officer.service_status = "faol"
        for eligibility in officer.eligibility:
            eligibility.ok = True
            eligibility.valid_until = datetime.now() + timedelta(days=30)
        db.commit()
    for data, error in (({"sabab": "a", "tasdiq": "1"}, "sabab"), ({"sabab": "Valid reason"}, "tasdiq")):
        r = post(f"/yacheyka/{cid}/bloklash", data)
        assert r.status_code == 303 and f"xato={error}" in r.headers["location"]
    for action, data, status in (
        ("bloklash", {"sabab": "Lifecycle block", "tasdiq": "1"}, "bloklangan"),
        ("blokdan-chiqarish", {"sabab": "Lifecycle restore", "tasdiq": "1"}, "biriktirilgan"),
        ("xizmat", {"sabab": "Lifecycle service", "rejim": "on"}, "xizmatda"),
        ("xizmat", {"sabab": "Lifecycle completion", "rejim": "off"}, "biriktirilgan"),
        ("ajratish", {"sabab": "Assignment test", "tasdiq": "1"}, "zaxira"),
        ("biriktirish", {"sabab": "Assignment restore", "officer_id": assigned_id}, "biriktirilgan"),
    ):
        r = post(f"/yacheyka/{cid}/{action}", data)
        assert r.status_code == 303 and "ok=" in r.headers["location"], (action, r.headers)
        assert c.get(r.headers["location"]).status_code == 200
        with SessionLocal() as db:
            cab = db.get(Cabinet, cid)
            assert cab.status == status
            assert lock_snapshot == (cab.door_open, cab.door_locked, cab.ak_clamp_locked, cab.pm_box_locked)
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Event.id))) == event_count + 6
        db.get(Cabinet, cid).status = "nosoz"
        db.commit()
    for action, mode, status in (
        ("bloklash", "", "bloklangan"), ("blokdan-chiqarish", "", "nosoz"),
        ("xizmat", "on", "xizmatda"), ("bloklash", "", "bloklangan"),
        ("blokdan-chiqarish", "", "xizmatda"), ("xizmat", "off", "nosoz"),
    ):
        r = post(f"/yacheyka/{cid}/{action}", {"sabab": "Preserve prior restriction", "tasdiq": "1", "rejim": mode})
        assert r.status_code == 303 and "ok=" in r.headers["location"]
        with SessionLocal() as db:
            cab = db.get(Cabinet, cid)
            assert cab.status == status and cab.terminal_state == "blocked"
            assert lock_snapshot == (cab.door_open, cab.door_locked, cab.ak_clamp_locked, cab.pm_box_locked)
    for status in ("biriktirilgan", "zaxira", "bloklangan", "nosoz", "xizmatda"):
        with SessionLocal() as db:
            cab = db.get(Cabinet, cid)
            cab.status, cab.controller_online, cab.battery_pct = status, False, 12
            cab.mains_ok, cab.last_seen, cab.terminal_state = False, None, "unknown"
            db.commit()
        for suffix in ("", "/partials/holat", "/partials/hodisalar"):
            r = c.get(f"/yacheyka/{cid}{suffix}")
            assert r.status_code == 200
            if suffix != "/partials/hodisalar":
                body = html.unescape(r.text)
                assert 'data-zone="texnik"' in body and "Kontroller oflayn." in body and "12 %" in body
    r = post(f"/yacheyka/{cid}/xizmat", {"sabab": "Invalid enum test", "rejim": "anything"})
    assert "xato=holat" in r.headers["location"]
    with SessionLocal() as db:
        assert db.get(Cabinet, cid).status == "xizmatda"
        held_cab = db.scalar(select(Custody.cabinet_id).where(Custody.returned_at.is_(None)))
        event_count = db.scalar(select(func.count(Event.id)))
    r = post(f"/yacheyka/{held_cab}/ajratish", {"sabab": "Custody blocks unassignment", "tasdiq": "1"})
    assert "xato=custody" in r.headers["location"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Event.id))) == event_count
    active["lang"] = "cyr"
    assert "Қурол катаклари" in c.get("/yacheykalar").text
    assert "ҳаракатлар" in c.get(f"/yacheyka/{cid}").text
    active.update(role="tekshiruvchi", lang="lat")
    assert '/bloklash"' not in c.get(f"/yacheyka/{cid}").text
    assert post(f"/yacheyka/{cid}/bloklash", {"sabab": "Role denial", "tasdiq": "1"}).status_code == 403
    print("PASS: yacheyka lifecycle, 6 audit records, fault/service restriction restoration, unchanged physical lock telemetry, all 11 filters, 15 status/partial views, Cyrillic and rejected invalid actions")

# Existing inventory, signal and mode workflows: access boundaries and rendering.
from app.models import Alarm, Armory, Mode
with TestClient(app) as c:
    active.update(role="qurolxona_masuli", kind="qurolxona", scope=arm, lang="lat")
    c.get("/inventar")

    def post(url, data=None):
        return c.post(url, data=data or {}, headers={"X-CSRF-Token": c.cookies["aq_csrf"]}, follow_redirects=False)

    with SessionLocal() as db:
        local_item = db.scalar(select(Item).join(Cabinet).where(Cabinet.armory_id == arm))
        foreign_item = db.scalar(select(Item).join(Cabinet).where(Cabinet.armory_id == farm))
        iid, fiid = local_item.id, foreign_item.id
        local_item.hold = False
        db.get(Armory, arm).online = True
        for arm_id, cabinet_id in ((arm, 1), (farm, fcid)):
            location = db.get(Armory, arm_id)
            alarm = Alarm(armory_id=arm_id, cabinet_id=cabinet_id, unit_id=location.unit_id,
                          region_id=location.unit.region_id, level="WARNING", type="batareya",
                          title="Workflow alarm", detail="Isolated regression fixture", opened_at=datetime.now(), requires_ack=True)
            db.add(alarm)
            db.flush()
            if arm_id == arm:
                aid = alarm.id
            else:
                faid = alarm.id
        db.commit()
    for url in ("/inventar", "/inventar?tur=jihoz", "/inventar?kechikish=1", "/inventar?farq=1",
                "/inventar/partials/kpi", "/inventarizatsiya", f"/jihoz/{iid}", "/signallar",
                "/signallar/partials/faol", f"/signal/{aid}", f"/signal/{aid}/partials/holat",
                "/rejimlar", "/rejimlar/partials/faol", "/rejimlar/tarix"):
        assert c.get(url).status_code == 200, url
    assert c.get(f"/jihoz/{fiid}").status_code == 403
    assert c.get(f"/inventarizatsiya/{farm}").status_code == 403
    assert c.get(f"/signal/{faid}").status_code == 404
    for url, data in ((f"/jihoz/{fiid}/hold", {"hold": "1", "sabab": "Foreign item"}),
                      (f"/jihoz/{fiid}/korik", {"inspection_state": "yaroqli"}),
                      (f"/jihoz/{fiid}/holat", {"holat": "nosoz", "sabab": "Foreign item"}),
                      ("/inventarizatsiya/boshlash", {"armory_id": farm}),
                      (f"/inventarizatsiya/{farm}/skan", {}),
                      (f"/inventarizatsiya/{farm}/yakunlash", {}),
                      (f"/inventarizatsiya/{farm}/bekor", {}),
                      (f"/signal/{faid}/tasdiqlash", {}),
                      (f"/signal/{faid}/yechish", {"sabab": "tekshirildi"}),
                      (f"/signal/{faid}/yonaltirish", {})):
        assert post(url, data).status_code == 403, url
    assert post(f"/jihoz/{iid}/hold", {"hold": "invalid"}).status_code == 400
    for value in ("1", "0"):
        assert post(f"/jihoz/{iid}/hold", {"hold": value, "sabab": "Existing inventory demo"}).status_code == 303
    r = post(f"/signal/{aid}/tasdiqlash", {"next": "/\\external.example"})
    assert r.status_code == 303 and r.headers["location"] == f"/signal/{aid}"
    assert post(f"/signal/{aid}/yonaltirish").status_code == 303
    assert "xato=sabab" in post(f"/signal/{aid}/yechish", {"sabab": "boshqa"}).headers["location"]
    assert post(f"/signal/{aid}/yechish", {"sabab": "tekshirildi"}).status_code == 303
    with SessionLocal() as db:
        alarm = db.get(Alarm, aid)
        assert alarm.acked_at and alarm.resolved_at and alarm.forwarded
    assert post("/inventarizatsiya/boshlash", {"armory_id": arm}).status_code == 303
    assert c.get(f"/inventarizatsiya/{arm}").status_code == 200
    assert post(f"/inventarizatsiya/{arm}/skan").status_code == 303
    assert c.get(f"/inventarizatsiya/{arm}").status_code == 200
    r = post(f"/inventarizatsiya/{arm}/yakunlash", {"tasdiq": "1", "tasdiqlovchi": "Test reviewer", "izoh": "Fixture inventory"})
    assert r.status_code == 303
    act_url = r.headers["location"]
    assert c.get(act_url).status_code == 200
    pdf = c.get(act_url + "/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    active["scope"] = farm
    assert c.get(act_url).status_code == 403 and c.get(act_url + "/pdf").status_code == 403
    active.update(role="navbatchi", scope=arm)
    assert c.get("/rejimlar/boshlash").status_code == 200
    with SessionLocal() as db:
        for mode in db.scalars(select(Mode).where(Mode.armory_id == arm, Mode.ended_at.is_(None))):
            mode.ended_at = datetime.now()
        db.commit()
    mode_data = {"armory_id": arm, "kind": "yigilish", "started_by": "Scope test", "approver2": "Test reviewer", "reason": "Existing demo flow", "confirm": "1"}
    assert post("/rejimlar/boshlash", {**mode_data, "armory_id": farm}).status_code == 400
    r = post("/rejimlar/boshlash", mode_data)
    assert r.status_code == 303, r.text[:200]
    mode_url = r.headers["location"]
    assert c.get(mode_url).status_code == 200 and c.get(mode_url + "/partials/holat").status_code == 200
    assert "xato=tasdiq" in post(mode_url + "/tugatish").headers["location"]
    active["scope"] = farm
    assert c.get(mode_url).status_code == 403 and c.get(mode_url + "/partials/holat").status_code == 403
    assert post(mode_url + "/tugatish", {"confirm": "1"}).status_code == 403
    active["scope"] = arm
    assert post(mode_url + "/tugatish", {"confirm": "1", "note": "Verified demo end"}).status_code == 303
    with SessionLocal() as db:
        foreign_cab = db.get(Cabinet, fcid)
        ev = record_event(db, "texnik_xizmat", cabinet=foreign_cab, item_id=iid,
                          title="FOREIGN_ITEM_SENTINEL", simulated=True, make_alarm=False)
        db.add(Custody(item_id=iid, cabinet_id=fcid, officer_id=foid, taken_at=datetime.now(),
                       due_at=datetime.now() - timedelta(hours=1), match_ok=False))
        db.commit()
    scoped_item = c.get(f"/jihoz/{iid}")
    assert scoped_item.status_code == 200 and "FOREIGN_ITEM_SENTINEL" not in scoped_item.text
    assert all(scoped_item.context["cabs"][cu.cabinet_id].armory_id == arm for cu in scoped_item.context["custody"])
    active.update(kind="respublika", scope=None)
    assert "FOREIGN_ITEM_SENTINEL" in c.get(f"/jihoz/{iid}").text
    active.update(role="tekshiruvchi", kind="qurolxona", scope=arm)
    for url, data in ((f"/jihoz/{iid}/hold", {"hold": "1", "sabab": "Denied"}),
                      ("/inventarizatsiya/boshlash", {"armory_id": arm}),
                      (f"/signal/{aid}/tasdiqlash", {}), ("/rejimlar/boshlash", mode_data)):
        assert post(url, data).status_code == 403, url
    print("PASS: inventory hold/scan/act/PDF, signal acknowledge/forward/resolve and safe return URL, existing mode start/stop, foreign and role denials, scoped historical item records")

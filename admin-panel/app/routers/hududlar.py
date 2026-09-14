"""Hududlar bo'limi: 14 hudud ro'yxati (KPI, saralash, filtr), hudud sahifasi (KPI, bo'linmalar jadvali, signal lentasi,
qurolxonalar ro'yxati), bo'linma sahifasi, bo'linma qo'shish/tahrirlash (administrator, jurnal + sozlamalar auditi),
hudud jadvalini CSV eksport (ExportLog + `eksport_qilindi`). Panel hech qachon qulf ochmaydi."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Alarm, Armory, Cabinet, Custody, Event, ExportLog, Mode, Officer, Region, SettingsAudit, Unit
from ..services import kpi as kpisvc
from ..services import hisobot_svc
from ..services.events import ALARM_BADGE, LEVEL_LABEL, record_event
from ..services.live import hub
from ..services.mapsvg import region_paths
from .dashboard import alerts_feed

router = APIRouter()

PER_PAGE = 50
UNIT_KINDS = {"tuman_iib": "Tuman IIB", "shahar_iib": "Shahar IIB", "funksional": "Funksional bo'linma"}
SORT_OPTIONS = [("yacheyka", "Yacheyka soni"), ("berilgan", "Berilgan qurollar"), ("kechikish", "Kechikish"), ("rad", "Rad etilgan (bugun)"),
                ("signal", "Faol signallar"), ("oflayn", "Oflayn qurolxonalar"), ("qurolxona", "Qurolxona soni"), ("bolinma", "Bo'linma soni"), ("nom", "Nomi")]
OPS_TYPES = ["avtomat_olindi", "avtomat_qaytarildi", "pm_olindi", "pm_qaytarildi"]
DENY_TYPES = ["rad_etildi", "rad_etildi_takror"]
OFFICER_STATUS = {"faol": "Faol", "ta'tilda": "Ta'tilda", "kasallik": "Kasallik", "vaqtincha_chetlashtirilgan": "Vaqtincha chetlashtirilgan",
                  "ishdan_boshagan": "Ishdan bo'shagan"}
CAB_STATUS = ["biriktirilgan", "zaxira", "bloklangan", "nosoz", "xizmatda"]


# ---------------- yordamchilar ----------------
def _username(ctx: Ctx) -> str:
    return ctx.user.username if ctx and ctx.user else "mehmon"


def _notify(ev: Event, armory: Armory | None = None) -> None:
    hub.broadcast_threadsafe({"type": "event", "event_type": ev.type, "level": ev.level, "cabinet_id": None,
                              "armory_id": armory.id if armory else None, "title": ev.title, "ts": ev.ts_server.isoformat()})


def _user_region_id(db: Session, ctx: Ctx) -> int | None:
    """Foydalanuvchi vakolat doirasi qaysi hududga tegishli (respublika bo'lsa None)."""
    sk, sid = ctx.scope_kind, ctx.scope_id
    if not sid:
        return None
    if sk == "hudud":
        return sid
    if sk == "bolinma":
        u = db.get(Unit, sid)
        return u.region_id if u else None
    if sk == "qurolxona":
        a = db.get(Armory, sid)
        return a.unit.region_id if a else None
    return None


def _region_or_403(db: Session, ctx: Ctx, region_id: int) -> Region:
    reg = db.get(Region, region_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Hudud topilmadi")
    own = _user_region_id(db, ctx)
    if ctx.scope_kind != "respublika" and own != region_id:
        raise HTTPException(status_code=403, detail="Bu hudud vakolat doirangizdan tashqarida")
    return reg


def _region_scope(ctx: Ctx, region_id: int) -> tuple[str, int | None]:
    if ctx.scope_kind in ("qurolxona", "bolinma"):
        return ctx.scope_kind, ctx.scope_id
    return "hudud", region_id


def _visible_unit_ids(db: Session, ctx: Ctx) -> list[int] | None:
    if ctx.scope_kind == "bolinma":
        return [ctx.scope_id] if ctx.scope_id else []
    if ctx.scope_kind == "qurolxona":
        return list(db.scalars(select(Armory.unit_id).where(Armory.id == ctx.scope_id)))
    return None


def _unit_or_404(db: Session, region: Region, unit_id: int, ctx: Ctx) -> Unit:
    u = db.get(Unit, unit_id)
    if u is None or u.region_id != region.id:
        raise HTTPException(status_code=404, detail="Bo'linma topilmadi")
    if ctx.scope_kind == "bolinma" and ctx.scope_id != unit_id:
        raise HTTPException(status_code=403, detail="Bu bo'linma vakolat doirangizdan tashqarida")
    if ctx.scope_kind == "qurolxona":
        own_unit = db.scalar(select(Armory.unit_id).where(Armory.id == ctx.scope_id))
        if own_unit != unit_id:
            raise HTTPException(status_code=403, detail="Bu bo'linma vakolat doirangizdan tashqarida")
    return u


def _require(ctx: Ctx, action: str, msg: str) -> None:
    if not ctx.can(action):
        raise HTTPException(status_code=403, detail=msg)


def _require_structure(ctx: Ctx, *, create: bool = False) -> None:
    _require(ctx, "sozlamalar", "Tuzilmani o'zgartirish uchun administrator huquqi talab qilinadi")
    if ctx.scope_kind == "qurolxona" or (create and ctx.scope_kind == "bolinma"):
        raise HTTPException(403, "Bo'linma tuzilmasini o'zgartirish vakolat doirangizdan tashqarida")


def _paginate(items: list, page: int, per_page: int = PER_PAGE):
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, page), pages)
    return items[(page - 1) * per_page: page * per_page], page, pages, total


def _armory_stats(db: Session, armory_ids: list[int], now: datetime) -> dict[int, dict]:
    """Har qurolxona bo'yicha: yacheyka, biriktirilgan, berilgan, kechikish, signal (CRITICAL/SECURITY), signal_all."""
    st = {i: {"yacheyka": 0, "biriktirilgan": 0, "berilgan": 0, "kechikish": 0, "signal": 0, "signal_all": 0} for i in armory_ids}
    if not armory_ids:
        return st
    for arm_id, cnt, assigned in db.execute(select(Cabinet.armory_id, func.count(Cabinet.id), func.count(Cabinet.officer_id))
                                            .where(Cabinet.armory_id.in_(armory_ids)).group_by(Cabinet.armory_id)):
        st[arm_id]["yacheyka"] = cnt; st[arm_id]["biriktirilgan"] = assigned
    for arm_id, counts in kpisvc.armory_weapon_custody_counts(db, armory_ids, now).items():
        st[arm_id].update(counts)
    for arm_id, lvl, cnt in db.execute(select(Alarm.armory_id, Alarm.level, func.count(Alarm.id))
                                       .where(Alarm.resolved_at.is_(None), Alarm.armory_id.in_(armory_ids)).group_by(Alarm.armory_id, Alarm.level)):
        st[arm_id]["signal_all"] += cnt
        if lvl in ("CRITICAL", "SECURITY"):
            st[arm_id]["signal"] += cnt
    return st


def _row_status(r: dict) -> str:
    if r["signal"] or r["oflayn"]:
        return "critical"
    if r["kechikish"]:
        return "warning"
    if not r["qurolxona"]:
        return "nodata"
    return "good"


def unit_rows(db: Session, region_id: int, now: datetime | None = None,
              allowed_armory_ids: list[int] | None = None, allowed_unit_ids: list[int] | None = None):
    """Hudud bo'linmalari jadvali + qurolxonalar va ularning statistikasi."""
    now = now or datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    units_q = select(Unit).where(Unit.region_id == region_id)
    if allowed_unit_ids is not None:
        units_q = units_q.where(Unit.id.in_(allowed_unit_ids))
    units = db.execute(units_q.order_by(Unit.name)).scalars().all()
    unit_ids = [u.id for u in units]
    arm_q = select(Armory).where(Armory.unit_id.in_(unit_ids))
    if allowed_armory_ids is not None:
        arm_q = arm_q.where(Armory.id.in_(allowed_armory_ids))
    arms = db.execute(arm_q.order_by(Armory.name)).scalars().all() if unit_ids else []
    stats = _armory_stats(db, [a.id for a in arms], now)
    event_scope = [] if allowed_armory_ids is None else [Event.armory_id.in_(allowed_armory_ids)]
    rad = dict(db.execute(select(Event.unit_id, func.count(Event.id)).where(*event_scope, Event.region_id == region_id, Event.ts_server >= day_start,
                                                                             Event.type.in_(DENY_TYPES)).group_by(Event.unit_id)).all())
    ops = dict(db.execute(select(Event.unit_id, func.count(Event.id)).where(*event_scope, Event.region_id == region_id, Event.ts_server >= day_start,
                                                                             Event.type.in_(OPS_TYPES)).group_by(Event.unit_id)).all())
    rows = []
    for u in units:
        r = {"id": u.id, "name": u.name, "kind": u.kind, "kind_label": UNIT_KINDS.get(u.kind, u.kind), "qurolxona": 0, "oflayn": 0,
             "yacheyka": 0, "biriktirilgan": 0, "berilgan": 0, "kechikish": 0, "signal": 0, "signal_all": 0,
             "rad": rad.get(u.id, 0), "sutkalik": ops.get(u.id, 0), "armory_id": None}
        for a in arms:
            if a.unit_id != u.id:
                continue
            r["qurolxona"] += 1
            r["oflayn"] += 0 if a.online else 1
            r["armory_id"] = r["armory_id"] or a.id
            for k in ("yacheyka", "biriktirilgan", "berilgan", "kechikish", "signal", "signal_all"):
                r[k] += stats[a.id][k]
        r.update(kpisvc.weapon_custody_counts(db, [a.id for a in arms if a.unit_id == u.id], now))
        r["status"] = _row_status(r)
        rows.append(r)
    return rows, arms, stats


def _armory_rows(db: Session, arms: list[Armory], stats: dict[int, dict]) -> list[dict]:
    resp_ids = [a.responsible_officer_id for a in arms if a.responsible_officer_id]
    resp = {o.id: o for o in db.execute(select(Officer).where(Officer.id.in_(resp_ids))).scalars()} if resp_ids else {}
    out = []
    for a in arms:
        s = stats.get(a.id, {})
        out.append({"a": a, "s": s, "unit": a.unit, "masul": resp.get(a.responsible_officer_id),
                    "status": "critical" if (not a.online or s.get("signal")) else ("warning" if s.get("kechikish") else "good")})
    return out


def region_list(db: Session, saralash: str, tartib: str, holat: str, q: str):
    rows = kpisvc.region_rows(db)
    units_by_region = dict(db.execute(select(Unit.region_id, func.count(Unit.id)).group_by(Unit.region_id)).all())
    for r in rows:
        r["bolinma"] = units_by_region.get(r["id"], 0)
    totals = {k: sum(r[k] for r in rows) for k in ("yacheyka", "berilgan", "kechikish", "rad", "signal", "oflayn", "qurolxona", "bolinma")}
    if q:
        ql = q.strip().lower()
        rows = [r for r in rows if ql in r["name"].lower() or ql in r["short"].lower() or ql in r["code"].lower()]
    if holat == "muammo":
        rows = [r for r in rows if r["status"] == "critical"]
    elif holat == "kechikish":
        rows = [r for r in rows if r["kechikish"]]
    elif holat == "meyorda":
        rows = [r for r in rows if r["status"] == "good"]
    keys = {k for k, _ in SORT_OPTIONS}
    if saralash not in keys:
        saralash = "yacheyka"
    if tartib not in ("asc", "desc"):
        tartib = "asc" if saralash == "nom" else "desc"
    if saralash == "nom":
        rows.sort(key=lambda r: r["short"].lower(), reverse=(tartib == "desc"))
    else:
        rows.sort(key=lambda r: (r[saralash], r["yacheyka"]), reverse=(tartib == "desc"))
    return rows, totals, saralash, tartib


def _region_modes(db: Session, armory_ids: list[int]) -> list[dict]:
    if not armory_ids:
        return []
    out = []
    for m in db.execute(select(Mode).where(Mode.ended_at.is_(None), Mode.armory_id.in_(armory_ids)).order_by(Mode.started_at.desc())).scalars():
        a = db.get(Armory, m.armory_id)
        out.append({"m": m, "where": a.unit.name if a else ""})
    return out


# ---------------- /hududlar ----------------
@router.get("/hududlar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), saralash: str = "yacheyka", tartib: str = "",
              holat: str = "", q: str = "", korinish: str = "kartochka", page: int = 1):
    from ..main import render
    own = _user_region_id(db, ctx)
    if own:
        return RedirectResponse(f"/hudud/{own}", status_code=303)
    if ctx.scope_kind != "respublika":
        raise HTTPException(403, "Vakolat doirasi topilmadi")
    rows, totals, saralash, tartib = region_list(db, saralash, tartib, holat, q)
    rows, page, pages, total = _paginate(rows, page)
    korinish = "jadval" if korinish == "jadval" else "kartochka"
    return render(request, "hududlar/list.html", ctx, active="hududlar", breadcrumb=[("Hududlar", "")], title="Hududlar",
                  rows=rows, totals=totals, page=page, pages=pages, total=total, saralash=saralash, tartib=tartib, holat=holat, q=q,
                  korinish=korinish, sort_options=SORT_OPTIONS, map_svg=region_paths(rows))


@router.get("/hududlar/partials/royxat")
def p_list(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), saralash: str = "yacheyka", tartib: str = "",
           holat: str = "", q: str = "", korinish: str = "kartochka", page: int = 1):
    from ..main import render
    own = _user_region_id(db, ctx)
    if own:
        return RedirectResponse(f"/hudud/{own}/partials/bolinmalar", status_code=303)
    if ctx.scope_kind != "respublika":
        raise HTTPException(403, "Vakolat doirasi topilmadi")
    rows, totals, saralash, tartib = region_list(db, saralash, tartib, holat, q)
    rows, page, pages, total = _paginate(rows, page)
    return render(request, "hududlar/_royxat.html", ctx, rows=rows, totals=totals, page=page, pages=pages, total=total,
                  saralash=saralash, tartib=tartib, korinish="jadval" if korinish == "jadval" else "kartochka")


# ---------------- /hudud/{id} ----------------
def _region_context(db: Session, region: Region, now: datetime, ctx: Ctx) -> dict:
    scope_kind, scope_id = _region_scope(ctx, region.id)
    ids = kpisvc.armory_ids_for_scope(db, scope_kind, scope_id) or []
    visible_units = _visible_unit_ids(db, ctx)
    rows, arms, stats = unit_rows(db, region.id, now, ids if visible_units is not None else None, visible_units)
    officer_q = select(Officer.service_status, func.count(Officer.id)).join(Unit, Unit.id == Officer.unit_id).where(Unit.region_id == region.id)
    if visible_units is not None:
        officer_q = officer_q.where(Officer.unit_id.in_(visible_units))
    if ctx.scope_kind == "qurolxona":
        officer_q = officer_q.where(Officer.id.in_(select(Cabinet.officer_id).where(Cabinet.armory_id.in_(ids))))
    officers = dict(db.execute(officer_q.group_by(Officer.service_status)).all())
    return {"region": region, "k": kpisvc.kpis(db, scope_kind, scope_id, now), "units": rows, "armories": _armory_rows(db, arms, stats),
            "feed": alerts_feed(db, 8, ids), "days": kpisvc.daily_ops(db, 7, ids, now), "modes": _region_modes(db, ids),
            "officers_total": sum(officers.values()), "officers_active": officers.get("faol", 0), "armory_ids": ids}


@router.get("/hudud/{region_id}")
def region_page(region_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), page: int = 1, xato: str = ""):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    now = datetime.now()
    c = _region_context(db, region, now, ctx)
    units, upage, upages, utotal = _paginate(c["units"], page)
    return render(request, "hududlar/detail.html", ctx, active="hududlar", breadcrumb=[("Hududlar", "/hududlar"), (region.name, "")],
                  title=region.name, unit_kinds=UNIT_KINDS, page=upage, pages=upages, total=utotal, xato=xato, **{**c, "units": units})


@router.get("/hudud/{region_id}/partials/kpi")
def p_kpi(region_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    return render(request, "hududlar/_kpi.html", ctx, region=region, k=kpisvc.kpis(db, *_region_scope(ctx, region.id)))


@router.get("/hudud/{region_id}/partials/lenta")
def p_feed(region_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    ids = kpisvc.armory_ids_for_scope(db, *_region_scope(ctx, region.id)) or []
    return render(request, "hududlar/_lenta.html", ctx, region=region, feed=alerts_feed(db, 8, ids))


@router.get("/hudud/{region_id}/partials/bolinmalar")
def p_units(region_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), page: int = 1):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    ids = kpisvc.armory_ids_for_scope(db, *_region_scope(ctx, region.id)) or []
    visible_units = _visible_unit_ids(db, ctx)
    rows, _arms, _stats = unit_rows(db, region.id, allowed_armory_ids=ids if visible_units is not None else None,
                                  allowed_unit_ids=visible_units)
    units, page, pages, total = _paginate(rows, page)
    return render(request, "hududlar/_bolinmalar.html", ctx, region=region, units=units, page=page, pages=pages, total=total)


# ---------------- eksport (CSV) ----------------
def _units_csv(region: Region, rows: list[dict]) -> bytes:
    from .jurnal import _csv_safe
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(["Hudud", "Bo'linma", "Turi", "Qurolxona", "Oflayn", "Yacheyka", "Biriktirilgan", "Berilgan", "Kechikish", "Rad (bugun)",
                "Signal (CRITICAL/SECURITY)", "Barcha faol signallar"])
    for r in rows:
        w.writerow([_csv_safe(region.name), _csv_safe(r["name"]), _csv_safe(r["kind_label"]), r["qurolxona"], r["oflayn"], r["yacheyka"], r["biriktirilgan"], r["berilgan"],
                    r["kechikish"], r["rad"], r["signal"], r["signal_all"]])
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM: Excel uchun


@router.post("/hudud/{region_id}/eksport")
def export_units(region_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), maqsad: str = Form("")):
    region = _region_or_403(db, ctx, region_id)
    _require(ctx, "eksport", "Eksport uchun ruxsat yo'q")
    maqsad = maqsad.strip()
    if len(maqsad) < 3:
        return RedirectResponse(f"/hudud/{region.id}?xato=maqsad", status_code=303)
    now = datetime.now().replace(microsecond=0)
    ids = kpisvc.armory_ids_for_scope(db, *_region_scope(ctx, region.id)) or []
    visible_units = _visible_unit_ids(db, ctx)
    rows, _arms, _stats = unit_rows(db, region.id, now, ids if visible_units is not None else None, visible_units)
    data = _units_csv(region, rows)
    digest = hashlib.sha256(data).hexdigest()
    number = hisobot_svc.next_number(db, now)
    log = ExportLog(number=number, username=_username(ctx), report="hudud_bolinmalar", fmt="csv", purpose=maqsad[:200],
                    valid_until=now + timedelta(days=30), ts=now, file_hash=digest)
    db.add(log); db.flush()
    path = hisobot_svc.file_path(log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    armory = db.get(Armory, ids[0]) if len(ids) == 1 else None
    ev = record_event(db, "eksport_qilindi", armory=armory, title="Hudud jadvali eksport qilindi", detail=f"{number} · {region.short} · bo'linmalar · CSV"[:300],
                      reason=maqsad[:60], approver1=_username(ctx), simulated=False,
                      payload={"number": number, "report": "hudud_bolinmalar", "fmt": "csv", "filters": {"hudud": region.id},
                               "rows": len(rows), "total": len(rows), "file_hash": digest, "armory_ids": ids,
                               "scope": f"{region.name} · {len(rows)} bo'linma · {len(ids)} qurolxona",
                               "valid_until": log.valid_until.isoformat(), "purpose": maqsad[:200]})
    db.commit()
    _notify(ev, armory)
    fname = f"hudud_{region.code}_{now.strftime('%Y%m%d_%H%M')}.csv"
    return Response(content=data, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"', "X-Export-Number": number})


@router.get("/hisobotlar/hudud_bolinmalar")
def region_report_source(hudud: int = 0, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    region_id = hudud or _user_region_id(db, ctx)
    if region_id:
        _region_or_403(db, ctx, region_id)
        return RedirectResponse(f"/hudud/{region_id}", status_code=303)
    return RedirectResponse("/hududlar", status_code=303)


# ---------------- bo'linma sahifasi ----------------
@router.get("/hudud/{region_id}/bolinma/yangi")
def unit_new_form(region_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    _require_structure(ctx, create=True)
    return render(request, "hududlar/bolinma_form.html", ctx, active="hududlar", title="Yangi bo'linma",
                  breadcrumb=[("Hududlar", "/hududlar"), (region.name, f"/hudud/{region.id}"), ("Yangi bo'linma", "")],
                  region=region, unit=None, unit_kinds=UNIT_KINDS, form={"nom": "", "turi": "tuman_iib", "asos": "", "qurolxona_yaratish": True,
                                                                          "qurolxona_nomi": "", "manzil": ""}, error="")


@router.post("/hudud/{region_id}/bolinma/yangi")
def unit_create(region_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), nom: str = Form(""),
                turi: str = Form("tuman_iib"), asos: str = Form(""), qurolxona_yaratish: str = Form(""), qurolxona_nomi: str = Form(""),
                manzil: str = Form("")):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    _require_structure(ctx, create=True)
    nom, asos, qurolxona_nomi, manzil = nom.strip(), asos.strip(), qurolxona_nomi.strip(), manzil.strip()
    form = {"nom": nom, "turi": turi, "asos": asos, "qurolxona_yaratish": bool(qurolxona_yaratish), "qurolxona_nomi": qurolxona_nomi, "manzil": manzil}
    error = _validate_unit(db, region, nom, turi, asos)
    if error:
        return render(request, "hududlar/bolinma_form.html", ctx, active="hududlar", title="Yangi bo'linma",
                      breadcrumb=[("Hududlar", "/hududlar"), (region.name, f"/hudud/{region.id}"), ("Yangi bo'linma", "")],
                      region=region, unit=None, unit_kinds=UNIT_KINDS, form=form, error=error)
    now = datetime.now().replace(microsecond=0)
    unit = Unit(region_id=region.id, name=nom, kind=turi)
    db.add(unit); db.flush()
    armory = None
    if qurolxona_yaratish:
        armory = Armory(unit_id=unit.id, name=qurolxona_nomi or f"{nom} qurolxonasi", address=manzil or f"{region.short}, {nom}",
                        online=False, wan_ok=False, last_sync=None, pending_events=0)
        db.add(armory); db.flush()
    new = {"nom": nom, "turi": turi, "hudud": region.code, "qurolxona": armory.name if armory else None}
    db.add(SettingsAudit(username=_username(ctx), key=f"tuzilma.bolinma.{unit.id}", old="", new=json.dumps(new, ensure_ascii=False), ts=now))
    ev = record_event(db, "sozlama_ozgardi", armory=armory, title="Bo'linma qo'shildi",
                      detail=f"{region.short} · {nom} ({UNIT_KINDS[turi]})" + (f" · {armory.name}" if armory else ""), reason=asos[:60],
                      approver1=_username(ctx), simulated=False,
                      payload={"amal": "bolinma_qoshildi", "hudud_id": region.id, "bolinma_id": unit.id, "yangi": new, "asos": asos})
    db.commit()
    _notify(ev, armory)
    return RedirectResponse(f"/hudud/{region.id}/bolinma/{unit.id}", status_code=303)


def _validate_unit(db: Session, region: Region, nom: str, turi: str, asos: str, unit_id: int | None = None) -> str:
    if len(nom) < 3 or len(nom) > 120:
        return "Bo'linma nomi 3–120 belgidan iborat bo'lishi kerak"
    if turi not in UNIT_KINDS:
        return "Bo'linma turi noto'g'ri"
    if len(asos) < 3:
        return "Asos (buyruq yoki xat raqami) ko'rsatilishi shart"
    dup = db.execute(select(Unit.id).where(Unit.region_id == region.id, func.lower(Unit.name) == nom.lower())).first()
    if dup and dup[0] != unit_id:
        return "Bu hududda shunday nomli bo'linma allaqachon mavjud"
    return ""


@router.get("/hudud/{region_id}/bolinma/{unit_id}")
def unit_page(region_id: int, unit_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), page: int = 1):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    unit = _unit_or_404(db, region, unit_id, ctx)
    now = datetime.now()
    arm_query = select(Armory).where(Armory.unit_id == unit.id)
    if ctx.scope_kind == "qurolxona":
        arm_query = arm_query.where(Armory.id == ctx.scope_id)
    arms = db.execute(arm_query.order_by(Armory.name)).scalars().all()
    ids = [a.id for a in arms]
    stats = _armory_stats(db, ids, now)
    officer_query = select(Officer).where(Officer.unit_id == unit.id)
    if ctx.scope_kind == "qurolxona":
        officer_query = officer_query.where(Officer.id.in_(select(Cabinet.officer_id).where(Cabinet.armory_id.in_(ids))))
    scoped_officers = list(db.scalars(officer_query))
    officers = {}
    for officer in scoped_officers:
        officers[officer.service_status] = officers.get(officer.service_status, 0) + 1
    cab_status = dict(db.execute(select(Cabinet.status, func.count(Cabinet.id)).where(Cabinet.armory_id.in_(ids)).group_by(Cabinet.status)).all()) if ids else {}
    alarm_scope = [Alarm.unit_id == unit.id]
    event_scope = [Event.unit_id == unit.id]
    if ctx.scope_kind == "qurolxona":
        alarm_scope.append(Alarm.armory_id.in_(ids))
        event_scope.append(Event.armory_id.in_(ids))
    alarms = db.execute(select(Alarm).where(*alarm_scope, Alarm.resolved_at.is_(None)).order_by(Alarm.opened_at.desc()).limit(20)).scalars().all()
    total_ev = db.scalar(select(func.count(Event.id)).where(*event_scope)) or 0
    pages = max(1, (total_ev + PER_PAGE - 1) // PER_PAGE)
    page = min(max(1, page), pages)
    events = db.execute(select(Event).where(*event_scope).order_by(Event.ts_server.desc(), Event.id.desc())
                        .offset((page - 1) * PER_PAGE).limit(PER_PAGE)).scalars().all()
    cab_labels = dict(db.execute(select(Cabinet.id, Cabinet.label).where(Cabinet.armory_id.in_(ids))).all()) if ids else {}
    off_names = {officer.id: officer.full_name for officer in scoped_officers}
    officer_rows = [(OFFICER_STATUS.get(k, k), v) for k, v in sorted(officers.items(), key=lambda kv: -kv[1])]
    return render(request, "hududlar/bolinma.html", ctx, active="hududlar", title=unit.name,
                  breadcrumb=[("Hududlar", "/hududlar"), (region.name, f"/hudud/{region.id}"), (unit.name, "")],
                  region=region, unit=unit, kind_label=UNIT_KINDS.get(unit.kind, unit.kind),
                  k=kpisvc.kpis(db, "qurolxona" if ctx.scope_kind == "qurolxona" else "bolinma", ctx.scope_id if ctx.scope_kind == "qurolxona" else unit.id, now),
                  armories=_armory_rows(db, arms, stats), officers=officer_rows, officers_total=sum(officers.values()),
                  cabinet_status_rows=[(s, cab_status.get(s, 0)) for s in CAB_STATUS], cab_total=sum(cab_status.values()), alarms=alarms,
                  events=events, cab_labels=cab_labels, off_names=off_names, page=page, pages=pages, total=total_ev,
                  level_label=LEVEL_LABEL, alarm_badge=ALARM_BADGE)


@router.get("/hudud/{region_id}/bolinma/{unit_id}/tahrir")
def unit_edit_form(region_id: int, unit_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    unit = _unit_or_404(db, region, unit_id, ctx)
    _require_structure(ctx)
    return render(request, "hududlar/bolinma_form.html", ctx, active="hududlar", title="Bo'linmani tahrirlash",
                  breadcrumb=[("Hududlar", "/hududlar"), (region.name, f"/hudud/{region.id}"), (unit.name, f"/hudud/{region.id}/bolinma/{unit.id}"), ("Tahrirlash", "")],
                  region=region, unit=unit, unit_kinds=UNIT_KINDS, form={"nom": unit.name, "turi": unit.kind, "asos": ""}, error="")


@router.post("/hudud/{region_id}/bolinma/{unit_id}/tahrir")
def unit_update(region_id: int, unit_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db),
                nom: str = Form(""), turi: str = Form(""), asos: str = Form("")):
    from ..main import render
    region = _region_or_403(db, ctx, region_id)
    unit = _unit_or_404(db, region, unit_id, ctx)
    _require_structure(ctx)
    nom, asos = nom.strip(), asos.strip()
    error = _validate_unit(db, region, nom, turi, asos, unit_id=unit.id)
    if error:
        return render(request, "hududlar/bolinma_form.html", ctx, active="hududlar", title="Bo'linmani tahrirlash",
                      breadcrumb=[("Hududlar", "/hududlar"), (region.name, f"/hudud/{region.id}"), (unit.name, f"/hudud/{region.id}/bolinma/{unit.id}"), ("Tahrirlash", "")],
                      region=region, unit=unit, unit_kinds=UNIT_KINDS, form={"nom": nom, "turi": turi, "asos": asos}, error=error)
    old = {"nom": unit.name, "turi": unit.kind}
    new = {"nom": nom, "turi": turi}
    if old == new:
        return RedirectResponse(f"/hudud/{region.id}/bolinma/{unit.id}", status_code=303)
    now = datetime.now().replace(microsecond=0)
    unit.name = nom; unit.kind = turi
    armory = db.execute(select(Armory).where(Armory.unit_id == unit.id).order_by(Armory.id)).scalars().first()
    db.add(SettingsAudit(username=_username(ctx), key=f"tuzilma.bolinma.{unit.id}", old=json.dumps(old, ensure_ascii=False),
                         new=json.dumps(new, ensure_ascii=False), ts=now))
    ev = record_event(db, "sozlama_ozgardi", armory=armory, title="Bo'linma ma'lumotlari o'zgartirildi",
                      detail=f"{region.short} · {old['nom']} → {nom} ({UNIT_KINDS[turi]})"[:300], reason=asos[:60], approver1=_username(ctx),
                      simulated=False, payload={"amal": "bolinma_tahrirlandi", "hudud_id": region.id, "bolinma_id": unit.id, "eski": old, "yangi": new, "asos": asos})
    db.commit()
    _notify(ev, armory)
    return RedirectResponse(f"/hudud/{region.id}/bolinma/{unit.id}", status_code=303)

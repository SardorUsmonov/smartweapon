"""Rejimlar: yig'ilish va trevoga rejimlari (faol rejimlar jonli, boshlash, tugatish, tarix).

Panel hech qachon qulf ochmaydi: rejim faqat qurolxona kontrollerlariga "navbatsiz berish" holatini
e'lon qiladi, har xodim o'z yacheykasida biometrik autentifikatsiyadan o'tadi.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Armory, Cabinet, Custody, Event, Item, Mode, Officer, Region, Unit
from ..services import kpi as kpisvc
from ..services import sim as simsvc

router = APIRouter()

PER_PAGE = 50
KINDS = ("trevoga", "yigilish")
KIND_LABEL = {"trevoga": "TREVOGA", "yigilish": "YIG'ILISH"}
KIND_TITLE = {"trevoga": "Trevoga", "yigilish": "Yig'ilish"}
KIND_DESC = {
    "trevoga": "Jangovar shay holat: barcha biriktirilgan yacheykalar navbatsiz berish holatiga o'tadi, "
               "kechikish nazorati vaqtincha to'xtatiladi, har berish SECURITY darajasida jurnalga yoziladi.",
    "yigilish": "Rejalashtirilgan yig'ilish yoki mashg'ulot: berish ruxsatlar ro'yxati bo'yicha, "
                "muddat va qaytarish nazorati saqlanadi.",
}
# rejim davomida ko'rsatiladigan hodisa turlari (jurnal vaqt chizig'i)
MODE_EVENT_TYPES = ["rejim_boshlandi", "rejim_tugadi", "avtomat_olindi", "pm_olindi", "avtomat_qaytarildi", "pm_qaytarildi",
                    "rad_etildi", "rad_etildi_takror", "favqulodda_ochish", "mexanik_kalit", "shkaf_bloklandi",
                    "aloqa_uzildi", "aloqa_tiklandi", "qaytarish_nomuvofiq", "buzish_urinishi"]
STATE_LABEL = {"olindi": "Olindi", "xodimda": "Xodimda (rejimdan oldin)", "kutmoqda": "Kutmoqda", "bloklangan": "Berilmaydi"}
BLOCKED = ("bloklangan", "nosoz", "xizmatda")


# ---------------- yordamchilar ----------------
def _require(ctx: Ctx) -> None:
    if not ctx.can("rejim"):
        raise HTTPException(status_code=403, detail="Rejimni boshqarish faqat navbatchi/operator roli uchun")


def _scope_ids(db: Session, ctx: Ctx) -> list[int] | None:
    return kpisvc.armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)


def _in_scope(ids: list[int] | None, armory_id: int | None) -> bool:
    return ids is None or armory_id in ids


def _who(ctx: Ctx) -> str:
    return ctx.user.full_name if ctx and ctx.user else "Navbatchi"


def _dur(start: datetime, end: datetime | None = None) -> str:
    s = max(int(((end or datetime.now()) - start).total_seconds()), 0)
    h, r = divmod(s, 3600)
    mnt, sec = divmod(r, 60)
    if h:
        return f"{h} soat {mnt} daq"
    if mnt:
        return f"{mnt} daq {sec} s"
    return f"{sec} s"


def _arm_info(db: Session, armory_ids) -> dict[int, dict]:
    """Qurolxona -> hudud/bo'linma nomlari (bir so'rovda)."""
    ids = sorted({i for i in armory_ids if i})
    if not ids:
        return {}
    q = (select(Armory.id, Armory.name, Armory.online, Unit.id, Unit.name, Region.id, Region.short)
         .join(Unit, Unit.id == Armory.unit_id).join(Region, Region.id == Unit.region_id).where(Armory.id.in_(ids)))
    return {r[0]: {"id": r[0], "name": r[1], "online": r[2], "unit_id": r[3], "unit": r[4], "region_id": r[5], "region": r[6],
                   "where": f"{r[6]} · {r[4]}"} for r in db.execute(q)}


def _mode_row(m: Mode, info: dict[int, dict]) -> dict:
    a = info.get(m.armory_id) if m.armory_id else None
    pct = min(round(100 * m.issued_count / m.target_count), 100) if m.target_count else 0
    eta_min = round(m.queue_count * m.avg_seconds / 60) if (m.ended_at is None and m.avg_seconds and m.queue_count) else 0
    return {"m": m, "kind": KIND_LABEL.get(m.kind, m.kind.upper()), "kind_title": KIND_TITLE.get(m.kind, m.kind),
            "arm": a, "where": a["where"] if a else "Respublika", "pct": pct, "active": m.ended_at is None,
            "duration": _dur(m.started_at, m.ended_at), "eta_min": eta_min}


def _cabinet_rows(db: Session, m: Mode) -> tuple[list[dict], dict]:
    """Rejim qamrovidagi har yacheyka holati: olindi / xodimda / kutmoqda / berilmaydi."""
    counts = {"olindi": 0, "xodimda": 0, "kutmoqda": 0, "bloklangan": 0, "jami": 0}
    if not m.armory_id:
        return [], counts
    start = m.started_at - timedelta(seconds=5)
    end = m.ended_at or datetime.now()
    cabs = db.execute(select(Cabinet, Officer).join(Officer, Officer.id == Cabinet.officer_id, isouter=True)
                      .where(Cabinet.armory_id == m.armory_id).order_by(Cabinet.wall, Cabinet.position)).all()
    cab_ids = [c.id for c, _ in cabs]
    first: dict[int, Custody] = {}
    if cab_ids:
        for cu in db.execute(select(Custody).where(Custody.cabinet_id.in_(cab_ids), Custody.taken_at >= start, Custody.taken_at <= end)
                             .order_by(Custody.taken_at)).scalars():
            first.setdefault(cu.cabinet_id, cu)
    items = {}
    if first:
        items = {i.id: i for i in db.execute(select(Item).where(Item.id.in_([cu.item_id for cu in first.values()]))).scalars()}
    rows = []
    for cab, off in cabs:
        if not cab.officer_id:
            continue  # qamrov: biriktirilgan yacheykalar (mode_start target_count bilan bir xil)
        cu = first.get(cab.id)
        if cu is not None:
            state = "olindi"
        elif cab.status in BLOCKED:
            state = "bloklangan"
        elif m.ended_at is None and not cab.ak_present:
            state = "xodimda"
        else:
            state = "kutmoqda"
        it = items.get(cu.item_id) if cu else None
        rows.append({"cab": cab, "officer": off, "state": state, "label": STATE_LABEL[state] if not (state == "kutmoqda" and m.ended_at) else "Berilmadi",
                     "ts": cu.taken_at if cu else None, "weapon": f"{it.model} {it.serial}" if it else "",
                     "returned": bool(cu and cu.returned_at)})
        counts[state] += 1
        counts["jami"] += 1
    return rows, counts


def _view(db: Session, m: Mode, info: dict[int, dict] | None = None) -> dict:
    info = info if info is not None else _arm_info(db, [m.armory_id])
    v = _mode_row(m, info)
    v["rows"], v["counts"] = _cabinet_rows(db, m)
    return v


def _active_views(db: Session, ids: list[int] | None) -> list[dict]:
    q = select(Mode).where(Mode.ended_at.is_(None)).order_by(Mode.started_at.desc())
    if ids is not None:
        q = q.where(Mode.armory_id.in_(ids))
    modes = db.execute(q).scalars().all()
    info = _arm_info(db, [m.armory_id for m in modes])
    return [_view(db, m, info) for m in modes]


def _stats(db: Session, ids: list[int] | None) -> dict:
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = now - timedelta(days=30)

    def cnt(*where):
        q = select(func.count(Mode.id)).where(*where)
        if ids is not None:
            q = q.where(Mode.armory_id.in_(ids))
        return db.scalar(q) or 0

    avg_q = select(func.avg(Mode.avg_seconds)).where(Mode.started_at >= month, Mode.avg_seconds > 0)
    if ids is not None:
        avg_q = avg_q.where(Mode.armory_id.in_(ids))
    return {"faol": cnt(Mode.ended_at.is_(None)), "bugun": cnt(Mode.started_at >= day_start), "oy": cnt(Mode.started_at >= month),
            "oy_tugagan": cnt(Mode.started_at >= month, Mode.ended_at.is_not(None)), "avg": int(db.scalar(avg_q) or 0),
            "today": day_start.date().isoformat()}


def _armory_groups(db: Session, ids: list[int] | None) -> list[tuple[str, list[dict]]]:
    """Boshlash formasi uchun qurolxonalar, hudud bo'yicha guruhlangan."""
    q = (select(Armory, Unit, Region).join(Unit, Unit.id == Armory.unit_id).join(Region, Region.id == Unit.region_id)
         .order_by(Region.order, Unit.name, Armory.name))
    if ids is not None:
        q = q.where(Armory.id.in_(ids))
    active = {m.armory_id for m in db.execute(select(Mode).where(Mode.ended_at.is_(None))).scalars()}
    groups: dict[str, list[dict]] = {}
    for a, u, r in db.execute(q):
        n_cab = db.scalar(select(func.count(Cabinet.id)).where(Cabinet.armory_id == a.id, Cabinet.officer_id.is_not(None))) or 0
        groups.setdefault(r.short, []).append({"id": a.id, "name": a.name, "unit": u.name, "online": a.online, "active": a.id in active, "cabs": n_cab})
    return list(groups.items())


def _parse_date(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


# ---------------- sahifalar ----------------
@router.get("/rejimlar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    ids = _scope_ids(db, ctx)
    views = _active_views(db, ids)
    q = select(Mode).where(Mode.ended_at.is_not(None)).order_by(Mode.ended_at.desc()).limit(8)
    if ids is not None:
        q = q.where(Mode.armory_id.in_(ids))
    recent_modes = db.execute(q).scalars().all()
    recent = [_mode_row(m, _arm_info(db, [m.armory_id for m in recent_modes])) for m in recent_modes]
    return render(request, "rejimlar/list.html", ctx, active="rejimlar", breadcrumb=[("Rejimlar", "/rejimlar")], title="Rejimlar",
                  views=views, recent=recent, stats=_stats(db, ids), kind_desc=KIND_DESC)


@router.get("/rejimlar/partials/faol")
def p_faol(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "rejimlar/_faol.html", ctx, views=_active_views(db, _scope_ids(db, ctx)))


@router.get("/rejimlar/tarix")
def history(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), tur: str = "", hudud: int | None = None,
            holat: str = "", dan: str = "", gacha: str = "", q: str = "", page: int = 1):
    from ..main import render
    ids = _scope_ids(db, ctx)
    base = select(Mode).join(Armory, Armory.id == Mode.armory_id, isouter=True).join(Unit, Unit.id == Armory.unit_id, isouter=True)
    if ids is not None:
        base = base.where(Mode.armory_id.in_(ids))
    if tur in KINDS:
        base = base.where(Mode.kind == tur)
    if hudud:
        base = base.where(Unit.region_id == hudud)
    if holat == "faol":
        base = base.where(Mode.ended_at.is_(None))
    elif holat == "tugagan":
        base = base.where(Mode.ended_at.is_not(None))
    d0, d1 = _parse_date(dan), _parse_date(gacha)
    if d0:
        base = base.where(Mode.started_at >= d0)
    if d1:
        base = base.where(Mode.started_at < d1 + timedelta(days=1))
    if q.strip():
        like = f"%{q.strip()}%"
        base = base.where(or_(Mode.started_by.ilike(like), Mode.approver2.ilike(like), Mode.reason.ilike(like), Armory.name.ilike(like), Unit.name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    page = min(max(page, 1), pages)
    modes = db.execute(base.order_by(Mode.started_at.desc()).offset((page - 1) * PER_PAGE).limit(PER_PAGE)).scalars().all()
    info = _arm_info(db, [m.armory_id for m in modes])
    rows = [_mode_row(m, info) for m in modes]
    filters = {"tur": tur, "hudud": hudud or "", "holat": holat, "dan": dan, "gacha": gacha, "q": q}
    qs = urlencode({k: v for k, v in filters.items() if v})
    return render(request, "rejimlar/tarix.html", ctx, active="rejimlar", breadcrumb=[("Rejimlar", "/rejimlar"), ("Tarix", "")],
                  title="Rejimlar tarixi", rows=rows, total=total, page=page, pages=pages, per_page=PER_PAGE, f=filters,
                  base_qs="?" + qs + ("&" if qs else ""), kinds=KIND_TITLE)


@router.get("/rejimlar/boshlash")
def start_form(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), armory_id: int | None = None):
    from ..main import render
    _require(ctx)
    ids = _scope_ids(db, ctx)
    groups = _armory_groups(db, ids)
    form = {"armory_id": armory_id or (groups[0][1][0]["id"] if groups and groups[0][1] else ""), "kind": "trevoga",
            "started_by": _who(ctx), "approver2": "", "reason": ""}
    return render(request, "rejimlar/boshlash.html", ctx, active="rejimlar", breadcrumb=[("Rejimlar", "/rejimlar"), ("Rejim boshlash", "")],
                  title="Rejim boshlash", groups=groups, form=form, error="", kind_desc=KIND_DESC)


@router.post("/rejimlar/boshlash")
def start_post(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), armory_id: int = Form(0),
               kind: str = Form("trevoga"), started_by: str = Form(""), approver2: str = Form(""), reason: str = Form(""),
               confirm: str = Form("")):
    from ..main import render
    _require(ctx)
    ids = _scope_ids(db, ctx)
    form = {"armory_id": armory_id, "kind": kind, "started_by": started_by.strip(), "approver2": approver2.strip(), "reason": reason.strip()}
    a = db.get(Armory, armory_id) if armory_id else None
    error = ""
    if a is None or not _in_scope(ids, a.id):
        error = "Qurolxona tanlanmagan yoki vakolat doirangizdan tashqarida"
    elif kind not in KINDS:
        error = "Rejim turi noto'g'ri"
    elif not form["started_by"]:
        error = "Boshlovchi ko'rsatilishi shart"
    elif not form["approver2"]:
        error = "Ikkinchi tasdiqlovchi (komandir yoki navbatchi rahbar) ko'rsatilishi shart"
    elif len(form["reason"]) < 5:
        error = "Sabab (buyruq raqami yoki asos) kamida 5 belgidan iborat bo'lsin"
    elif not confirm:
        error = "Rejimni boshlashni tasdiqlang"
    elif db.scalar(select(func.count(Mode.id)).where(Mode.armory_id == a.id, Mode.ended_at.is_(None))):
        error = "Bu qurolxonada faol rejim allaqachon bor: avval uni tugating"
    if error:
        resp = render(request, "rejimlar/boshlash.html", ctx, active="rejimlar", breadcrumb=[("Rejimlar", "/rejimlar"), ("Rejim boshlash", "")],
                      title="Rejim boshlash", groups=_armory_groups(db, ids), form=form, error=error, kind_desc=KIND_DESC)
        resp.status_code = 400
        return resp
    # sim.mode_start: Mode yozuvi + `rejim_boshlandi` (SECURITY) hodisasi, jonli xabar. Qulf ochilmaydi.
    m = simsvc.mode_start(db, a, kind, form["started_by"], form["approver2"], form["reason"][:200])
    db.commit()
    return RedirectResponse(f"/rejim/{m.id}", status_code=303)


@router.get("/rejim/{mode_id}")
def detail(mode_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    m = db.get(Mode, mode_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Rejim topilmadi")
    if not _in_scope(_scope_ids(db, ctx), m.armory_id):
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    v = _view(db, m)
    start = m.started_at - timedelta(seconds=5)
    end = m.ended_at + timedelta(seconds=5) if m.ended_at else datetime.now()
    eq = select(Event).where(Event.ts_server >= start, Event.ts_server <= end).order_by(Event.ts_server.desc(), Event.id.desc()).limit(50)
    if m.armory_id:
        eq = eq.where(Event.armory_id == m.armory_id, Event.type.in_(MODE_EVENT_TYPES))
    else:
        eq = eq.where(Event.armory_id.is_(None), Event.type.in_(["rejim_boshlandi", "rejim_tugadi"]))
    events = db.execute(eq).scalars().all()
    crumb = f"{v['kind']} · {v['arm']['unit'] if v['arm'] else 'Respublika'}"
    return render(request, "rejimlar/detail.html", ctx, active="rejimlar", breadcrumb=[("Rejimlar", "/rejimlar"), (crumb, "")],
                  title=f"{v['kind_title']} · {v['where']}", v=v, events=events, state_label=STATE_LABEL, who=_who(ctx))


@router.get("/rejim/{mode_id}/partials/holat")
def p_holat(mode_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    m = db.get(Mode, mode_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Rejim topilmadi")
    if not _in_scope(_scope_ids(db, ctx), m.armory_id):
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    return render(request, "rejimlar/_holat.html", ctx, v=_view(db, m), state_label=STATE_LABEL)


@router.post("/rejim/{mode_id}/tugatish")
def stop_post(mode_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), note: str = Form(""), confirm: str = Form("")):
    _require(ctx)
    m = db.get(Mode, mode_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Rejim topilmadi")
    if not _in_scope(_scope_ids(db, ctx), m.armory_id):
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    if m.ended_at is not None:
        return RedirectResponse(f"/rejim/{m.id}", status_code=303)
    if not confirm:
        return RedirectResponse(f"/rejim/{m.id}?xato=tasdiq#tugatish", status_code=303)
    note = note.strip()
    if note:
        m.reason = (m.reason + " | Yakun: " + note)[:200] if m.reason else ("Yakun: " + note)[:200]
    # sim.mode_stop: ended_at + `rejim_tugadi` hodisasi (approver1 = tugatgan shaxs), jonli xabar
    simsvc.mode_stop(db, m, _who(ctx))
    db.commit()
    return RedirectResponse(f"/rejim/{m.id}", status_code=303)

"""Yacheykalar: ro'yxat (filtr, sahifalash), yacheyka kartasi (2D raqamli egizak, terminal ko'zgusi, telemetriya,
jihozlar, hodisalar vaqt chizig'i), harakatlar (bloklash, blokdan chiqarish, xizmat rejimi, biriktirish, ajratish).

Panel HECH QACHON qulf ochmaydi: ochish faqat terminalda (karta + maxsus PIN, ikki shaxs qoidasi).
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import ROLE_LABEL, Ctx, get_ctx
from ..models import Alarm, Armory, Cabinet, Custody, Event, Item, Officer, Region, Unit
from ..services import sim as simsvc
from ..services import twin_svc
from ..services.events import record_event
from ..services.kpi import armory_ids_for_scope
from ..services.list_scope import location_context

router = APIRouter()
PER_PAGE = 50

HOLAT_FILTERS = {
    "": "Barcha holatlar", "biriktirilgan": "Biriktirilgan", "zaxira": "Zaxira", "bloklangan": "Bloklangan", "nosoz": "Nosoz",
    "xizmatda": "Xizmatda", "muammo": "Muammo (bloklangan, nosoz, xizmatda)", "xodimda": "Qurol xodimda",
    "eshik_ochiq": "Eshik ochiq", "oflayn": "Kontroller oflayn", "batareya": "Batareya past (< 30 %)",
}
PILLS = [("", "Barchasi", "jami"), ("biriktirilgan", "Biriktirilgan", "biriktirilgan"), ("zaxira", "Zaxira", "zaxira"),
         ("xodimda", "Qurol xodimda", "xodimda"), ("muammo", "Muammo", "muammo"), ("eshik_ochiq", "Eshik ochiq", "eshik_ochiq"),
         ("oflayn", "Oflayn", "oflayn")]

MSG_OK = {
    "bloklandi": "Yacheyka bloklandi: terminal kirishni rad etadi. Hodisa jurnalga yozildi (XAVFSIZLIK).",
    "blokdan_chiqdi": "Yacheyka blokdan chiqarildi, oldingi holat tiklandi. Hodisa jurnalga yozildi.",
    "xizmat_on": "Xizmat rejimi yoqildi: yacheyka berish-qaytarishdan chiqarildi.",
    "xizmat_off": "Xizmat rejimi tugatildi, yacheyka ishga qaytdi.",
    "biriktirildi": "Xodim yacheykaga biriktirildi, jihozlar xodimga o'tkazildi.",
    "ajratildi": "Xodim yacheykadan ajratildi, yacheyka zaxiraga o'tdi.",
}
MSG_XATO = {
    "sabab": "Sabab ko'rsatilishi shart (kamida 5 belgi).",
    "tasdiq": "Tasdiq belgisi qo'yilmagan, harakat bajarilmadi.",
    "holat": "Bu harakat yacheykaning joriy holatida mumkin emas.",
    "xodim": "Xodim topilmadi. Ro'yxatdan tanlang yoki tabel raqamini tekshiring.",
    "faol": "Xodim xizmat holati 'faol' emas, biriktirib bo'lmaydi.",
    "bolinma": "Xodim boshqa bo'linmaga tegishli. Yacheyka faqat o'z bo'linmasi xodimiga biriktiriladi.",
    "band": "Bu xodimga boshqa yacheyka biriktirilgan (bir xodim - bir yacheyka).",
    "yaroqlilik": "Xodimning 5 ta yaroqlilik sharti to'liq emas yoki muddati o'tgan.",
    "custody": "Qurol hozir xodimda: ajratishdan oldin qurol qaytarilishi shart.",
}


# ---------------- yordamchilar ----------------
def _int(v: str | None) -> int | None:
    try:
        return int(v) if v not in ("", None) else None
    except (TypeError, ValueError):
        return None


def _who(ctx: Ctx) -> str:
    return ctx.user.full_name if ctx and ctx.user else "Mehmon"


def _scope_ids(db: Session, ctx: Ctx) -> list[int] | None:
    return armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)


def _in_scope(db: Session, ctx: Ctx, cab: Cabinet) -> bool:
    ids = _scope_ids(db, ctx)
    return ids is None or cab.armory_id in ids


def _err(request: Request, ctx: Ctx, code: int, title: str, message: str):
    from ..main import render
    resp = render(request, "yacheykalar/xato.html", ctx, active="yacheykalar", breadcrumb=[("Yacheykalar", "/yacheykalar")],
                  title=title, message=message)
    resp.status_code = code
    return resp


def _guard(request: Request, ctx: Ctx, db: Session, cab_id: int, perm: str | None = None):
    """Yacheykani yuklaydi; vakolat doirasi va rolni tekshiradi. (cab, None) yoki (None, xato javobi)."""
    cab = db.get(Cabinet, cab_id)
    if cab is None:
        return None, _err(request, ctx, 404, "Yacheyka topilmadi", "Bunday identifikatorli yacheyka bazada yo'q.")
    if not _in_scope(db, ctx, cab):
        return None, _err(request, ctx, 403, "Ruxsat yo'q", "Bu yacheyka sizning vakolat doirangizdan tashqarida.")
    if perm and not ctx.can(perm):
        return None, _err(request, ctx, 403, "Ruxsat yo'q", "Bu harakat uchun rolingiz yetarli emas: qurolxona mas'uli talab qilinadi.")
    return cab, None


def _back(cab: Cabinet, ok: str = "", xato: str = "") -> RedirectResponse:
    qs = urlencode({k: v for k, v in (("ok", ok), ("xato", xato)) if v})
    return RedirectResponse(f"/yacheyka/{cab.id}" + (f"?{qs}" if qs else ""), status_code=303)


def _crumbs(cab: Cabinet) -> list:
    a = cab.armory
    return [(a.unit.region.short, f"/hudud/{a.unit.region_id}"), (a.unit.name, f"/qurolxona/{a.id}"), (f"Yacheyka {cab.label}", None)]


def _joined(sel):
    return (sel.select_from(Cabinet).join(Armory, Armory.id == Cabinet.armory_id).join(Unit, Unit.id == Armory.unit_id)
            .join(Region, Region.id == Unit.region_id).outerjoin(Officer, Officer.id == Cabinet.officer_id))


def _holat_cond(h: str):
    if h in ("biriktirilgan", "zaxira", "bloklangan", "nosoz", "xizmatda"):
        return Cabinet.status == h
    if h == "muammo":
        return Cabinet.status.in_(["bloklangan", "nosoz", "xizmatda"])
    if h == "xodimda":
        return or_(Cabinet.ak_present.is_(False), Cabinet.pm_present.is_(False))
    if h == "eshik_ochiq":
        return Cabinet.door_open.is_(True)
    if h == "oflayn":
        return Cabinet.controller_online.is_(False)
    if h == "batareya":
        return Cabinet.battery_pct < 30
    return None


def _counts(db: Session, ids: list[int] | None) -> dict:
    def cnt(*c):
        s = select(func.count(Cabinet.id))
        if ids is not None:
            s = s.where(Cabinet.armory_id.in_(ids))
        return db.scalar(s.where(*c) if c else s) or 0
    return {"jami": cnt(), "biriktirilgan": cnt(Cabinet.status == "biriktirilgan"), "zaxira": cnt(Cabinet.status == "zaxira"),
            "muammo": cnt(Cabinet.status.in_(["bloklangan", "nosoz", "xizmatda"])),
            "xodimda": cnt(or_(Cabinet.ak_present.is_(False), Cabinet.pm_present.is_(False))),
            "eshik_ochiq": cnt(Cabinet.door_open.is_(True)), "oflayn": cnt(Cabinet.controller_online.is_(False))}


# ---------------- ro'yxat ----------------
@router.get("/yacheykalar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), holat: str = "", hudud: str = "",
              qurolxona: str = "", q: str = "", page: int = 1, bolinma: str = ""):
    from ..main import render
    location = location_context(db, ctx, hudud, bolinma, qurolxona)
    ids = location["ids"]
    hudud_id, unit_id, arm_id = (location["selected"][key] for key in ("hudud", "bolinma", "qurolxona"))
    q = (q or "").strip()
    holat = holat if holat in HOLAT_FILTERS else ""
    conds = []
    if ids is not None:
        conds.append(Cabinet.armory_id.in_(ids))
    if hudud_id:
        conds.append(Unit.region_id == hudud_id)
    if arm_id:
        conds.append(Cabinet.armory_id == arm_id)
    if q:
        like = f"%{q}%"
        conds.append(or_(Cabinet.label.ilike(like), Cabinet.serial.ilike(like), Officer.full_name.ilike(like), Officer.tabel.ilike(like)))
    hc = _holat_cond(holat)
    if hc is not None:
        conds.append(hc)
    total = db.scalar(_joined(select(func.count(Cabinet.id))).where(*conds)) or 0
    pages = max(1, -(-total // PER_PAGE))
    page = min(max(1, page), pages)
    rows = db.execute(_joined(select(Cabinet, Armory, Unit, Region, Officer)).where(*conds)
                      .order_by(Region.order, Unit.name, Armory.id, Cabinet.position)
                      .offset((page - 1) * PER_PAGE).limit(PER_PAGE)).all()
    aq = select(Armory, Unit, Region).join(Unit, Unit.id == Armory.unit_id).join(Region, Region.id == Unit.region_id).order_by(Region.order, Unit.name)
    if ids is not None:
        aq = aq.where(Armory.id.in_(ids))
    if hudud_id:
        aq = aq.where(Unit.region_id == hudud_id)
    armories = db.execute(aq).all()
    params = {k: v for k, v in {"holat": holat, **location["selected"], "q": q}.items() if v}
    base_qs = urlencode(params)
    pill_qs = urlencode({k: v for k, v in params.items() if k != "holat"})
    return render(request, "yacheykalar/list.html", ctx, active="yacheykalar", breadcrumb=[("Yacheykalar", None)], title="Yacheykalar",
                  rows=rows, total=total, page=page, pages=pages, per_page=PER_PAGE, holat=holat, hudud=hudud_id, bolinma=unit_id, qurolxona=arm_id, q=q,
                  location_fields=location["fields"],
                  counts=_counts(db, ids), armories=armories, holat_filters=HOLAT_FILTERS, pills=PILLS, base_qs=base_qs, pill_qs=pill_qs,
                  scope_label=None if location["scope_ids"] is None else len(location["scope_ids"]))


# ---------------- yacheyka kartasi ----------------
def _detail_data(db: Session, cab: Cabinet) -> dict:
    now = datetime.now()
    items = db.execute(select(Item).where(Item.cabinet_id == cab.id).order_by(Item.kind, Item.category, Item.id)).scalars().all()
    events = db.execute(select(Event).where(Event.cabinet_id == cab.id).order_by(Event.ts_server.desc(), Event.id.desc()).limit(50)).scalars().all()
    open_custody = db.execute(select(Custody, Item).join(Item, Item.id == Custody.item_id)
                              .where(Custody.cabinet_id == cab.id, Custody.returned_at.is_(None)).order_by(Custody.taken_at)).all()
    custody_hist = db.execute(select(Custody, Item).join(Item, Item.id == Custody.item_id)
                              .where(Custody.cabinet_id == cab.id, Custody.returned_at.is_not(None)).order_by(Custody.returned_at.desc()).limit(6)).all()
    alarms = db.execute(select(Alarm).where(Alarm.cabinet_id == cab.id, Alarm.resolved_at.is_(None)).order_by(Alarm.opened_at.desc())).scalars().all()
    off_ids = {e.officer_id for e in events if e.officer_id} | {c.officer_id for c, _ in open_custody} | {c.officer_id for c, _ in custody_hist}
    officer_names = {}
    if off_ids:
        officer_names = {o.id: o.full_name for o in db.execute(select(Officer).where(Officer.id.in_(off_ids))).scalars()}
    item_names = {it.id: f"{it.model} {it.serial}".strip() for it in items}
    missing = {e.item_id for e in events if e.item_id and e.item_id not in item_names}
    if missing:
        for it in db.execute(select(Item).where(Item.id.in_(missing))).scalars():
            item_names[it.id] = f"{it.model} {it.serial}".strip()
    elig = list(cab.officer.eligibility) if cab.officer else []
    elig_ok = sum(1 for e in elig if e.ok and (e.valid_until is None or e.valid_until >= now))
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    ops_today = db.scalar(select(func.count(Event.id)).where(Event.cabinet_id == cab.id, Event.ts_server >= today0,
                                                             Event.type.in_(["avtomat_olindi", "avtomat_qaytarildi", "pm_olindi", "pm_qaytarildi"]))) or 0
    denied_7d = db.scalar(select(func.count(Event.id)).where(Event.cabinet_id == cab.id, Event.type.in_(["rad_etildi", "rad_etildi_takror"]),
                                                             Event.ts_server >= today0.replace(day=today0.day) - __import__("datetime").timedelta(days=7))) or 0
    return {"items": items, "events": events, "open_custody": open_custody, "custody_hist": custody_hist, "alarms": alarms,
            "officer_names": officer_names, "item_names": item_names, "twin": twin_svc.build(cab, items), "terminal": twin_svc.terminal(cab),
            "elig_ok": elig_ok, "elig_total": len(elig), "ops_today": ops_today, "denied_7d": denied_7d, "now": now}


def _free_officers(db: Session, cab: Cabinet) -> list[Officer]:
    assigned = select(Cabinet.officer_id).where(Cabinet.officer_id.is_not(None))
    return db.execute(select(Officer).where(Officer.unit_id == cab.armory.unit_id, Officer.service_status == "faol", Officer.id.not_in(assigned))
                      .order_by(Officer.full_name).limit(300)).scalars().all()


@router.get("/yacheyka/{cab_id}")
def detail(cab_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), ok: str = "", xato: str = ""):
    from ..main import render
    cab, err = _guard(request, ctx, db, cab_id)
    if err:
        return err
    data = _detail_data(db, cab)
    free = _free_officers(db, cab) if ctx.can("biriktirish") and not cab.officer_id else []
    return render(request, "yacheykalar/detail.html", ctx, active="yacheykalar", breadcrumb=_crumbs(cab), title=f"Yacheyka {cab.label}",
                  cab=cab, ok=ok, xato=xato, msg_ok=MSG_OK, msg_xato=MSG_XATO, free_officers=free,
                  role_label=ROLE_LABEL.get(ctx.role, ctx.role), **data)


@router.get("/yacheyka/{cab_id}/partials/holat")
def p_holat(cab_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    cab, err = _guard(request, ctx, db, cab_id)
    if err:
        return err
    return render(request, "yacheykalar/_holat.html", ctx, cab=cab, **_detail_data(db, cab))


@router.get("/yacheyka/{cab_id}/partials/hodisalar")
def p_hodisalar(cab_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    cab, err = _guard(request, ctx, db, cab_id)
    if err:
        return err
    return render(request, "yacheykalar/_hodisalar.html", ctx, cab=cab, **_detail_data(db, cab))


# ---------------- harakatlar (POST + 303) ----------------
def _restore_status(db: Session, cab: Cabinet) -> str:
    """Keep a pre-existing fault/service restriction after a temporary admin state."""
    event_type = "shkaf_bloklandi" if cab.status == "bloklangan" else "texnik_xizmat"
    previous = select(Event).where(Event.cabinet_id == cab.id, Event.type == event_type)
    if event_type == "texnik_xizmat":
        previous = previous.where(Event.payload["rejim"].as_string() == "boshlandi")
    event = db.scalar(previous.order_by(Event.id.desc()).limit(1))
    old_status = (event.payload or {}).get("oldingi_holat") if event else None
    if old_status in ("nosoz", "xizmatda"):
        return old_status
    return "biriktirilgan" if cab.officer_id else "zaxira"


@router.post("/yacheyka/{cab_id}/bloklash")
def bloklash(cab_id: int, request: Request, sabab: str = Form(""), tasdiq: str = Form(""),
             ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    cab, err = _guard(request, ctx, db, cab_id, "bloklash")
    if err:
        return err
    sabab = sabab.strip()
    if len(sabab) < 5:
        return _back(cab, xato="sabab")
    if not tasdiq:
        return _back(cab, xato="tasdiq")
    if cab.status == "bloklangan":
        return _back(cab, xato="holat")
    prev = cab.status
    cab.status = "bloklangan"; cab.terminal_state = "blocked"
    ev = record_event(db, "shkaf_bloklandi", cabinet=cab, officer=cab.officer, method="PANEL", reason=sabab[:60], approver1=_who(ctx),
                      title="Yacheyka bloklandi", detail=(simsvc._label(cab) + " · " + sabab)[:300],
                      payload={"oldingi_holat": prev, "sabab": sabab, "foydalanuvchi": ctx.user.username if ctx.user else ""}, simulated=False)
    db.commit(); simsvc._notify(ev, cab)
    return _back(cab, ok="bloklandi")


@router.post("/yacheyka/{cab_id}/blokdan-chiqarish")
def blokdan_chiqarish(cab_id: int, request: Request, sabab: str = Form(""), tasdiq: str = Form(""),
                      ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    cab, err = _guard(request, ctx, db, cab_id, "bloklash")
    if err:
        return err
    sabab = sabab.strip()
    if len(sabab) < 5:
        return _back(cab, xato="sabab")
    if not tasdiq:
        return _back(cab, xato="tasdiq")
    if cab.status != "bloklangan":
        return _back(cab, xato="holat")
    cab.status = _restore_status(db, cab)
    cab.terminal_state = "blocked" if cab.status in ("nosoz", "xizmatda") else "idle"
    ev = record_event(db, "shkaf_blokdan_chiqdi", cabinet=cab, officer=cab.officer, method="PANEL", reason=sabab[:60], approver1=_who(ctx),
                      title="Yacheyka blokdan chiqarildi", detail=(simsvc._label(cab) + " · " + sabab)[:300],
                      payload={"yangi_holat": cab.status, "sabab": sabab, "foydalanuvchi": ctx.user.username if ctx.user else ""}, simulated=False)
    db.commit(); simsvc._notify(ev, cab)
    return _back(cab, ok="blokdan_chiqdi")


@router.post("/yacheyka/{cab_id}/xizmat")
def xizmat(cab_id: int, request: Request, rejim: str = Form("on"), sabab: str = Form(""),
           ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    cab, err = _guard(request, ctx, db, cab_id, "bloklash")
    if err:
        return err
    sabab = sabab.strip()
    if len(sabab) < 5:
        return _back(cab, xato="sabab")
    if rejim not in ("on", "off"):
        return _back(cab, xato="holat")
    if rejim == "on":
        if cab.status in ("xizmatda", "bloklangan"):
            return _back(cab, xato="holat")
        prev = cab.status
        cab.status = "xizmatda"; cab.terminal_state = "blocked"
        ev = record_event(db, "texnik_xizmat", cabinet=cab, officer=cab.officer, method="PANEL", reason=sabab[:60], approver1=_who(ctx),
                          title="Xizmat rejimi yoqildi", detail=(simsvc._label(cab) + " · " + sabab)[:300],
                          payload={"rejim": "boshlandi", "oldingi_holat": prev, "sabab": sabab}, simulated=False)
        db.commit(); simsvc._notify(ev, cab)
        return _back(cab, ok="xizmat_on")
    if cab.status != "xizmatda":
        return _back(cab, xato="holat")
    cab.status = _restore_status(db, cab)
    cab.terminal_state = "blocked" if cab.status in ("nosoz", "xizmatda") else "idle"
    ev = record_event(db, "texnik_xizmat", cabinet=cab, officer=cab.officer, method="PANEL", reason=sabab[:60], approver1=_who(ctx),
                      title="Xizmat rejimi tugatildi", detail=(simsvc._label(cab) + " · " + sabab)[:300],
                      payload={"rejim": "tugadi", "yangi_holat": cab.status, "sabab": sabab}, simulated=False)
    db.commit(); simsvc._notify(ev, cab)
    return _back(cab, ok="xizmat_off")


@router.post("/yacheyka/{cab_id}/biriktirish")
def biriktirish(cab_id: int, request: Request, officer_id: str = Form(""), tabel: str = Form(""), sabab: str = Form(""),
                ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    cab, err = _guard(request, ctx, db, cab_id, "biriktirish")
    if err:
        return err
    if cab.officer_id or cab.status != "zaxira":
        return _back(cab, xato="holat")
    off = None
    oid = _int(officer_id)
    if oid:
        off = db.get(Officer, oid)
    elif tabel.strip():
        off = db.execute(select(Officer).where(Officer.tabel == tabel.strip())).scalar_one_or_none()
    if off is None:
        return _back(cab, xato="xodim")
    if off.service_status != "faol":
        return _back(cab, xato="faol")
    if off.unit_id != cab.armory.unit_id:
        return _back(cab, xato="bolinma")
    if db.scalar(select(func.count(Cabinet.id)).where(Cabinet.officer_id == off.id)):
        return _back(cab, xato="band")
    now = datetime.now()
    elig = list(off.eligibility)
    if len(elig) < 5 or any((not e.ok) or (e.valid_until is not None and e.valid_until < now) for e in elig):
        return _back(cab, xato="yaroqlilik")
    cab.officer_id = off.id; cab.status = "biriktirilgan"; cab.terminal_state = "idle"
    off.armory_id = cab.armory_id
    for it in db.execute(select(Item).where(Item.cabinet_id == cab.id)).scalars():
        it.officer_id = off.id
    ev = record_event(db, "biriktirildi", cabinet=cab, officer=off, method="PANEL", reason=sabab.strip()[:60], approver1=_who(ctx),
                      title="Xodim biriktirildi", detail=f"{simsvc._label(cab)} · {off.full_name} ({off.tabel})"[:300],
                      payload={"xodim_id": off.id, "tabel": off.tabel, "sabab": sabab.strip()}, simulated=False)
    db.commit(); simsvc._notify(ev, cab)
    return _back(cab, ok="biriktirildi")


@router.post("/yacheyka/{cab_id}/ajratish")
def ajratish(cab_id: int, request: Request, sabab: str = Form(""), tasdiq: str = Form(""),
             ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    cab, err = _guard(request, ctx, db, cab_id, "biriktirish")
    if err:
        return err
    sabab = sabab.strip()
    if len(sabab) < 5:
        return _back(cab, xato="sabab")
    if not tasdiq:
        return _back(cab, xato="tasdiq")
    if not cab.officer_id:
        return _back(cab, xato="holat")
    if db.scalar(select(func.count(Custody.id)).where(Custody.cabinet_id == cab.id, Custody.returned_at.is_(None))):
        return _back(cab, xato="custody")
    off = db.get(Officer, cab.officer_id)
    cab.officer_id = None
    if cab.status == "biriktirilgan":
        cab.status = "zaxira"
    for it in db.execute(select(Item).where(Item.cabinet_id == cab.id)).scalars():
        it.officer_id = None
    ev = record_event(db, "ajratildi", cabinet=cab, officer=off, method="PANEL", reason=sabab[:60], approver1=_who(ctx),
                      title="Xodim ajratildi", detail=(f"{simsvc._label(cab)} · {off.full_name} ({off.tabel})" if off else simsvc._label(cab))[:300] + " · " + sabab,
                      payload={"xodim_id": off.id if off else None, "sabab": sabab}, simulated=False)
    db.commit(); simsvc._notify(ev, cab)
    return _back(cab, ok="ajratildi")

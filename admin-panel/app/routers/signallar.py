"""Signal markazi: faol signallar (4 daraja), tasdiqlash/yechish, batafsil sahifa, yechilganlar tarixi.

Panel HECH QACHON qulf ochmaydi: bu yerda faqat signal holati (tasdiq, yechish, yo'naltirish) o'zgaradi
va har o'zgarish `record_event` orqali jurnalga yoziladi.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Alarm, Armory, Cabinet, Event, Region, Unit
from ..services import sim as simsvc
from ..services.events import ALARM_BADGE, LEVEL_LABEL, record_event
from ..services.executive import LOCAL_TZ, _active_at
from ..services.kpi import armory_ids_for_scope
from ..services.list_scope import location_context

router = APIRouter()

PER_PAGE = 50
LEVELS = ["SECURITY", "CRITICAL", "WARNING", "INFO"]
LEVEL_NAME = {"INFO": "Axborot", "WARNING": "Ogohlantirish", "CRITICAL": "Kritik signal", "SECURITY": "Xavfsizlik"}
LEVEL_TONE = {"INFO": "blue", "WARNING": "yellow", "CRITICAL": "red", "SECURITY": "violet"}
LEVEL_ICON = {"INFO": "info", "WARNING": "clock", "CRITICAL": "alert", "SECURITY": "shield"}
# Alarm.type -> o'zbekcha nom
TYPE_LABEL = {
    "takroriy_rad": "Takroriy rad etish", "nomuvofiqlik": "Qaytarish nomuvofiqligi", "kechikish": "Qaytarish kechikishi",
    "eshik_ochiq": "Eshik ochiq qoldi", "urilish": "Urilish", "tamper": "Buzishga urinish", "lyuk": "Xizmat lyuki ochildi",
    "quvvat": "Quvvat uzilishi", "batareya": "Batareya past", "oflayn": "Aloqa uzildi", "mexanik_kalit": "Mexanik kalit",
    "favqulodda": "Favqulodda ochish", "oz_tekshiruv": "O'z-tekshiruv xatosi", "qulf_xatosi": "Qulf xatosi",
    "datchik_xatosi": "Datchik xatosi", "disk": "Disk to'ldi", "kamera": "Kamera oqimi uzildi", "ntp": "Vaqt sinxroni buzildi",
    "server_yoq": "Server yo'q rejimi", "zaxira": "Zaxira nusxa xatosi",
}
HOLAT_LABEL = {"faol": "Faol", "kutmoqda": "Tasdiq kutmoqda", "tasdiqlangan": "Tasdiqlangan", "yechilgan": "Yechilgan"}
# Yechish sabablari (tanlov); "boshqa" izoh talab qiladi
RESOLVE_REASONS = [
    ("tekshirildi", "Tekshirildi, muammo yo'q"), ("xodim", "Xodim bilan bog'lanildi, qurol qaytarildi"),
    ("texnik", "Texnik nosozlik bartaraf etildi"), ("aloqa", "Aloqa tiklandi"), ("soxta", "Soxta ishga tushish (datchik)"),
    ("qorovul", "Qorovul posti tekshirdi"), ("boshqa", "Boshqa (izohda)"),
]
REASON_LABEL = dict(RESOLVE_REASONS)
XATO = {"sabab": "Yechish uchun sabab tanlang; «Boshqa» bo'lsa izoh yozing.", "yechilgan": "Signal allaqachon yechilgan.",
        "tasdiqlangan": "Signal allaqachon tasdiqlangan."}
# Terminal holati -> LED rangi
LED = {"idle": "var(--accent)", "face": "var(--yellow)", "finger": "var(--yellow)", "ok": "var(--green)", "open": "var(--green)",
       "lock": "var(--accent)", "denied": "var(--red)", "blocked": "var(--red)"}

_LEVEL_ORDER = case((Alarm.level == "SECURITY", 0), (Alarm.level == "CRITICAL", 1), (Alarm.level == "WARNING", 2), else_=3)
_ACK_ORDER = case((Alarm.acked_at.is_(None), 0), else_=1)


# ---------------- yordamchilar ----------------
def _qs(**params) -> str:
    return urlencode({k: v for k, v in params.items() if v not in ("", None, 0, False)})


def _scope_ids(ctx: Ctx, db: Session) -> list[int] | None:
    return armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)


def _who(ctx: Ctx) -> str:
    return (ctx.user.full_name if ctx and ctx.user else "Navbatchi")[:80]


def _base_q(ids: list[int] | None):
    # Existing metadata may be incomplete; an assigned alarm always belongs to
    # its armory's actual unit/region, matching the dashboard and scope filter.
    region_id = case((Alarm.armory_id.is_not(None), Unit.region_id), else_=Alarm.region_id)
    q = (select(Alarm, Region.short, Unit.name, Armory.name, Armory.online, Cabinet.label, Cabinet.status, Region.id)
         .outerjoin(Armory, Armory.id == Alarm.armory_id)
         .outerjoin(Unit, Unit.id == func.coalesce(Armory.unit_id, Alarm.unit_id))
         .outerjoin(Region, Region.id == region_id).outerjoin(Cabinet, Cabinet.id == Alarm.cabinet_id))
    if ids is not None:
        q = q.where(Alarm.armory_id.in_(ids))
    return q


def _apply_filters(q, holat: str, daraja: str, text: str, now: datetime):
    if holat == "yechilgan":
        q = q.where(Alarm.resolved_at.is_not(None))
    elif holat == "tasdiqlangan":
        q = q.where(*_active_at(now), Alarm.acked_at.is_not(None))
    elif holat == "kutmoqda":
        q = q.where(*_active_at(now), Alarm.acked_at.is_(None), Alarm.requires_ack.is_(True))
    else:
        q = q.where(*_active_at(now))
    if daraja in LEVELS:
        q = q.where(Alarm.level == daraja)
    # location_context already narrowed the armory ids to the selected region.
    if text:
        like = f"%{text}%"
        q = q.where(or_(Alarm.title.ilike(like), Alarm.detail.ilike(like), Cabinet.label.ilike(like),
                        Armory.name.ilike(like), Unit.name.ilike(like), Region.short.ilike(like)))
    return q


def _shape(row, now: datetime) -> dict:
    a, reg, unit, arm, online, cab_label, cab_status, region_id = row
    end = a.resolved_at or now
    return {
        "a": a, "region": reg or "", "region_id": region_id, "unit": unit or "", "armory": arm or "", "armory_online": online,
        "cab_label": cab_label or "", "cab_status": cab_status or "",
        "type_label": TYPE_LABEL.get(a.type, a.type), "badge": ALARM_BADGE.get(a.type, LEVEL_LABEL.get(a.level, a.level)),
        "needs_ack": bool(a.requires_ack and a.acked_at is None and a.resolved_at is None),
        "status": "yechilgan" if a.resolved_at else ("tasdiqlangan" if a.acked_at else "faol"),
        "duration_min": max(int((end - a.opened_at).total_seconds() // 60), 0),
    }


def _where(r: dict) -> str:
    parts = [p for p in (r["region"], r["unit"], r["cab_label"]) if p]
    return " · ".join(parts)


def _counts(db: Session, ids: list[int] | None, now: datetime) -> dict:
    def base(*extra):
        q = select(func.count(Alarm.id)).where(*extra)
        if ids is not None:
            q = q.where(Alarm.armory_id.in_(ids))
        return q
    active = _active_at(now)
    lvl_q = select(Alarm.level, func.count(Alarm.id)).where(*active).group_by(Alarm.level)
    if ids is not None:
        lvl_q = lvl_q.where(Alarm.armory_id.in_(ids))
    by_level = {lv: 0 for lv in LEVELS}
    for lv, n in db.execute(lvl_q):
        by_level[lv] = n
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "by_level": by_level, "faol": sum(by_level.values()),
        "kutmoqda": db.scalar(base(*active, Alarm.requires_ack.is_(True), Alarm.acked_at.is_(None))) or 0,
        "tasdiqlangan": db.scalar(base(*active, Alarm.acked_at.is_not(None))) or 0,
        "yonaltirilgan": db.scalar(base(*active, Alarm.forwarded.is_(True))) or 0,
        "bugun_yechildi": db.scalar(base(Alarm.resolved_at >= day_start)) or 0,
    }


def _list_ctx(ctx: Ctx, db: Session, holat: str, daraja: str, hudud: str, q: str, page: int,
              bolinma: str = "", qurolxona: str = "") -> dict:
    """Ro'yxat sahifasi va jonli partial uchun umumiy kontekst."""
    now = datetime.now(LOCAL_TZ).replace(tzinfo=None)
    holat = holat if holat in HOLAT_LABEL else "faol"
    daraja = daraja if daraja in LEVELS else ""
    q = (q or "").strip()[:80]
    location = location_context(db, ctx, hudud, bolinma, qurolxona)
    ids = location["ids"]
    hudud = location["selected"]["hudud"]
    base = _apply_filters(_base_q(ids), holat, daraja, q, now)
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    page = min(max(page, 1), pages)
    if holat == "yechilgan":
        order = (Alarm.resolved_at.desc(),)
    else:
        order = (_LEVEL_ORDER, _ACK_ORDER, Alarm.opened_at.desc())
    rows = [_shape(r, now) for r in db.execute(base.order_by(*order).offset((page - 1) * PER_PAGE).limit(PER_PAGE))]
    recent_resolved = []
    if holat != "yechilgan":
        rq = _apply_filters(_base_q(ids), "yechilgan", daraja, q, now).order_by(Alarm.resolved_at.desc()).limit(8)
        recent_resolved = [_shape(r, now) for r in db.execute(rq)]
    params = {"holat": holat if holat != "faol" else "", "daraja": daraja, **location["selected"], "q": q}

    def link(**kw) -> str:
        p = {**params, **kw}
        if p.get("holat") == "faol":
            p["holat"] = ""
        return "/signallar?" + _qs(**p)

    def page_url(n: int) -> str:
        return link(page=n if n > 1 else 0)

    qs = _qs(**params, page=page if page > 1 else 0)
    return {
        "holat": holat, "daraja": daraja, "hudud": hudud, "q": q, "page": page, "pages": pages, "total": total, "rows": rows,
        "recent_resolved": recent_resolved, "counts": _counts(db, ids, now), "qs": qs, "link": link, "page_url": page_url,
        "next_url": "/signallar" + ("?" + qs if qs else ""), "can_ack": ctx.can("signal_ack"), "reasons": RESOLVE_REASONS,
        "levels": LEVELS, "level_name": LEVEL_NAME, "level_tone": LEVEL_TONE, "level_icon": LEVEL_ICON, "holat_label": HOLAT_LABEL,
        "type_label": TYPE_LABEL, "now": now,
        "location_fields": location["fields"], "location_selected": location["selected"],
    }


# ---------------- sahifalar ----------------
@router.get("/signallar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), holat: str = "faol", daraja: str = "",
              hudud: str = "", q: str = "", page: int = 1, xato: str = "", bolinma: str = "", qurolxona: str = ""):
    from ..main import render
    data = _list_ctx(ctx, db, holat, daraja, hudud, q, page, bolinma, qurolxona)
    return render(request, "signallar/list.html", ctx, active="signallar", breadcrumb=[("Signallar", "/signallar")],
                  title="Signal markazi", xato=XATO.get(xato, ""), **data)


@router.get("/signallar/partials/faol")
def p_faol(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), holat: str = "faol", daraja: str = "",
           hudud: str = "", q: str = "", page: int = 1, bolinma: str = "", qurolxona: str = ""):
    from ..main import render
    data = _list_ctx(ctx, db, holat, daraja, hudud, q, page, bolinma, qurolxona)
    return render(request, "signallar/_faol.html", ctx, **data)


def _detail_ctx(ctx: Ctx, db: Session, alarm_id: int) -> dict:
    now = datetime.now()
    ids = _scope_ids(ctx, db)
    row = db.execute(_base_q(ids).where(Alarm.id == alarm_id)).first()
    if row is None:
        raise HTTPException(404, "Signal topilmadi")
    r = _shape(row, now)
    a: Alarm = r["a"]
    cab = db.get(Cabinet, a.cabinet_id) if a.cabinet_id else None
    arm = db.get(Armory, a.armory_id) if a.armory_id else None
    src = db.get(Event, a.event_id) if a.event_id else None
    if ids is not None and src and src.armory_id not in ids:
        src = None
    # panel harakatlari (tasdiq / yechish / yo'naltirish) shu signal bo'yicha
    event_scope = [Event.armory_id.in_(ids)] if ids is not None else []
    actions = list(db.execute(select(Event).where(Event.type == "texnik_xizmat", Event.method == "PANEL",
                                                  Event.payload["alarm_id"].as_integer() == a.id, *event_scope)
                              .order_by(Event.ts_server.asc())).scalars())
    by_action = {}
    for e in actions:
        by_action.setdefault((e.payload or {}).get("action"), e)
    # bog'liq hodisalar: shu yacheyka (yoki qurolxona) bo'yicha signal oynasida
    t0 = a.opened_at - timedelta(minutes=30)
    t1 = (a.resolved_at or now) + timedelta(minutes=5)
    eq = select(Event).where(Event.ts_server >= t0, Event.ts_server <= t1, *event_scope)
    if cab is not None:
        eq = eq.where(Event.cabinet_id == cab.id)
    elif arm is not None:
        eq = eq.where(Event.armory_id == arm.id)
    else:
        eq = eq.where(Event.armory_id.is_(None))
    related = list(db.execute(eq.order_by(Event.ts_server.desc()).limit(30)).scalars())
    # shu obyekt bo'yicha boshqa signallar (tarix)
    hq = _base_q(ids).where(Alarm.id != a.id)
    if cab is not None:
        hq = hq.where(Alarm.cabinet_id == cab.id)
    elif arm is not None:
        hq = hq.where(Alarm.armory_id == arm.id)
    else:
        hq = hq.where(Alarm.armory_id.is_(None))
    history = [_shape(x, now) for x in db.execute(hq.order_by(Alarm.opened_at.desc()).limit(10))]
    officer = cab.officer if cab is not None else None
    return {
        "r": r, "a": a, "cab": cab, "arm": arm, "officer": officer, "src": src, "actions": actions, "by_action": by_action,
        "related": related, "history": history, "can_ack": ctx.can("signal_ack"), "reasons": RESOLVE_REASONS, "now": now,
        "terminal_text": simsvc.TERMINAL_TEXT, "led": LED, "level_name": LEVEL_NAME, "type_label": TYPE_LABEL, "where": _where(r),
        "next_url": f"/signal/{a.id}",
    }


@router.get("/signal/{alarm_id}")
def detail(alarm_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), xato: str = ""):
    from ..main import render
    data = _detail_ctx(ctx, db, alarm_id)
    a = data["a"]
    return render(request, "signallar/detail.html", ctx, active="signallar",
                  breadcrumb=[("Signallar", "/signallar"), (f"Signal #{a.id}", "")], title=f"Signal #{a.id} · {data['r']['type_label']}",
                  xato=XATO.get(xato, ""), **data)


@router.get("/signal/{alarm_id}/partials/holat")
def p_holat(alarm_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "signallar/_holat.html", ctx, **_detail_ctx(ctx, db, alarm_id))


# ---------------- harakatlar (POST) ----------------
def _checked_alarm(ctx: Ctx, db: Session, alarm_id: int) -> Alarm:
    if not ctx.can("signal_ack"):
        raise HTTPException(403, "Signalni tasdiqlash/yechish huquqi yo'q (navbatchi yoki qurolxona mas'uli kerak)")
    a = db.get(Alarm, alarm_id)
    if a is None:
        raise HTTPException(404, "Signal topilmadi")
    ids = _scope_ids(ctx, db)
    if ids is not None and a.armory_id not in ids:
        raise HTTPException(403, "Signal vakolat doirasidan tashqarida")
    return a


def _next(next_: str, alarm_id: int, xato: str = "") -> str:
    from ..services.auth_svc import safe_next
    url = next_ if next_ and safe_next(next_) == next_ else f"/signal/{alarm_id}"
    if xato:
        url += ("&" if "?" in url else "?") + "xato=" + xato
    return url


def _log(db: Session, ctx: Ctx, a: Alarm, action: str, title: str, reason: str = "", note: str = "") -> None:
    """Signal holati o'zgarishini jurnalga yozadi (EVENT_RULES: texnik_xizmat, INFO, signal yaratmaydi) va jonli xabar beradi."""
    cab = db.get(Cabinet, a.cabinet_id) if a.cabinet_id else None
    arm = db.get(Armory, a.armory_id) if a.armory_id else None
    who = _who(ctx)
    where = a.detail or a.title
    detail = f"{TYPE_LABEL.get(a.type, a.type)} · {where} · {who}" + (f" · {note}" if note else "")
    ev = record_event(db, "texnik_xizmat", cabinet=cab, armory=arm, method="PANEL", result=action, reason=reason[:60],
                      title=title, detail=detail[:300], simulated=False, make_alarm=False,
                      payload={"alarm_id": a.id, "action": action, "alarm_type": a.type, "alarm_level": a.level, "by": who,
                               "reason": reason, "note": note})
    db.commit()
    simsvc._notify(ev, cab, arm)


@router.post("/signal/{alarm_id}/tasdiqlash")
def ack(alarm_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), next: str = Form("")):
    a = _checked_alarm(ctx, db, alarm_id)
    if a.resolved_at is not None:
        return RedirectResponse(_next(next, a.id, "yechilgan"), status_code=303)
    if a.acked_at is not None:
        return RedirectResponse(_next(next, a.id, "tasdiqlangan"), status_code=303)
    a.acked_by = _who(ctx)
    a.acked_at = datetime.now().replace(microsecond=0)
    _log(db, ctx, a, "tasdiqlandi", "Signal tasdiqlandi")
    return RedirectResponse(_next(next, a.id), status_code=303)


@router.post("/signal/{alarm_id}/yechish")
def resolve(alarm_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), sabab: str = Form(""), izoh: str = Form(""),
            next: str = Form("")):
    a = _checked_alarm(ctx, db, alarm_id)
    sabab = sabab.strip()
    izoh = " ".join(izoh.split())[:200]
    if sabab not in REASON_LABEL or (sabab == "boshqa" and not izoh):
        return RedirectResponse(_next(next, a.id, "sabab"), status_code=303)
    if a.resolved_at is not None:
        return RedirectResponse(_next(next, a.id, "yechilgan"), status_code=303)
    now = datetime.now().replace(microsecond=0)
    who = _who(ctx)
    if a.acked_at is None:          # yechish tasdiqni ham o'z ichiga oladi
        a.acked_by = who
        a.acked_at = now
    a.resolved_by = who
    a.resolved_at = now
    _log(db, ctx, a, "yechildi", "Signal yechildi", reason=REASON_LABEL[sabab], note=izoh)
    return RedirectResponse(_next(next, a.id), status_code=303)


@router.post("/signal/{alarm_id}/yonaltirish")
def forward(alarm_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), next: str = Form("")):
    a = _checked_alarm(ctx, db, alarm_id)
    if a.resolved_at is not None:
        return RedirectResponse(_next(next, a.id, "yechilgan"), status_code=303)
    if not a.forwarded:
        a.forwarded = True
        _log(db, ctx, a, "yonaltirildi", "Qorovul postiga yo'naltirildi")
    return RedirectResponse(_next(next, a.id), status_code=303)

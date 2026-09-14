"""Xodimlar bo'limi: ro'yxat, xodim kartasi (yaroqlilik, kredensiallar, ruxsatlar, navbat, custody, rad etishlar),
harakatlar (xizmat holati, ruxsatni bekor qilish) va umumiy qidiruv (/qidiruv)."""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Armory, Cabinet, Custody, Eligibility, Event, Item, Officer, Region, Shift, Unit
from ..services import sim as simsvc
from ..services.events import record_event
from ..services.kpi import armory_ids_for_scope

router = APIRouter()
PER_PAGE = 50

# xizmat holati: kod -> (yorliq, chip rangi)
STATUS = {
    "faol": ("Faol", "green"),
    "ta'tilda": ("Ta'tilda", "yellow"),
    "kasallik": ("Kasallik varaqasi", "yellow"),
    "vaqtincha_chetlashtirilgan": ("Vaqtincha chetlashtirilgan", "red"),
    "ishdan_boshagan": ("Ishdan bo'shagan", "gray"),
}
# 5 yaroqlilik sharti [01 §2.2] tartibi va yorliqlari
ELIG = [
    ("qurol_biriktirilgan", "Qurol biriktirilgan (buyruq)"),
    ("saqlash_vakolati", "Saqlash va olib yurish vakolati"),
    ("maxsus_tayyorgarlik", "Maxsus tayyorgarlik kursi"),
    ("yaroqlilik_tekshiruvi", "Yaroqlilik tekshiruvi (tibbiy/psixologik)"),
    ("rahbar_buyrugi", "Rahbar buyrug'i (berishga ruxsat)"),
]
ELIG_LABEL = dict(ELIG)
DENY_REASON = {
    "outside_shift": "Navbat oynasidan tashqarida", "no_permit": "Ruxsat yo'q", "biometric_mismatch": "Biometrik mos kelmadi",
    "wrong_pin": "Noto'g'ri PIN", "lockout": "Blokirovka (3 urinish)", "cabinet_blocked": "Yacheyka bloklangan",
}
PERMIT = {"ak": ("AVTOMAT", "AK-74"), "pm": ("TO'PPONCHA", "PM")}
DENY_TYPES = ("rad_etildi", "rad_etildi_takror")
TAKE_TYPES = ("avtomat_olindi", "pm_olindi")
MSG = {
    "holat": "Xizmat holati o'zgartirildi va jurnalga yozildi.",
    "holat_blok": "Xizmat holati o'zgartirildi, yacheyka bloklandi va jurnalga yozildi.",
    "holat_ochildi": "Xizmat holati «Faol» qilindi, yacheyka blokdan chiqarildi.",
    "ruxsat_bekor": "Ruxsat bekor qilindi va jurnalga (XAVFSIZLIK) yozildi.",
    "ruxsat_tiklandi": "Ruxsat tiklandi va jurnalga (XAVFSIZLIK) yozildi.",
    "sabab_kerak": "Sabab maydoni majburiy. Harakat bajarilmadi.",
    "ozgarish_yoq": "O'zgarish yo'q: tanlangan qiymat joriy qiymat bilan bir xil.",
}


# ---------------- yordamchilar ----------------
def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like(s: str) -> str:
    return f"%{_esc(s)}%"


def _who(ctx: Ctx) -> str:
    return ctx.user.full_name if ctx and ctx.user else "Operator"


def _officer_query(ids: list[int] | None = None):
    """Xodim + bo'linma + hudud + qurolxona + yacheyka + ochiq custody soni (qurollangan)."""
    armed_query = select(func.count(Custody.id)).where(Custody.officer_id == Officer.id, Custody.returned_at.is_(None))
    cabinet_join = Cabinet.officer_id == Officer.id
    if ids is not None:
        armed_query = armed_query.where(Custody.cabinet_id.in_(
            select(Cabinet.id).where(Cabinet.armory_id.in_(ids)).correlate(None)))
        cabinet_join = cabinet_join & Cabinet.armory_id.in_(ids)
    armed = armed_query.correlate(Officer).scalar_subquery()
    q = (select(Officer, Unit, Region, Armory, Cabinet, armed.label("armed"))
         .join(Unit, Unit.id == Officer.unit_id).join(Region, Region.id == Unit.region_id)
         .outerjoin(Armory, Armory.id == Officer.armory_id).outerjoin(Cabinet, cabinet_join))
    return q, armed


def _get_officer(db: Session, ctx: Ctx, oid: int) -> Officer:
    off = db.get(Officer, oid)
    if off is None:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    if ids is not None and off.armory_id not in ids:
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    return off


def _cabinet_of(db: Session, off: Officer, ids: list[int] | None = None) -> Cabinet | None:
    query = select(Cabinet).where(Cabinet.officer_id == off.id)
    if ids is not None:
        query = query.where(Cabinet.armory_id.in_(ids))
    return db.execute(query.order_by(Cabinet.id)).scalars().first()


def _live(db: Session, off: Officer, now: datetime | None = None, ids: list[int] | None = None) -> dict:
    """Jonli blok uchun: yacheyka, ochiq custody (qurollangan), so'nggi hodisa."""
    now = now or datetime.now()
    cab = _cabinet_of(db, off, ids)
    open_query = select(Custody, Item).join(Item, Item.id == Custody.item_id).where(Custody.officer_id == off.id, Custody.returned_at.is_(None))
    event_query = select(Event).where(Event.officer_id == off.id)
    if ids is not None:
        open_query = open_query.where(Custody.cabinet_id.in_(select(Cabinet.id).where(Cabinet.armory_id.in_(ids))))
        event_query = event_query.where(Event.armory_id.in_(ids))
    open_c = db.execute(open_query.order_by(Custody.taken_at.desc())).all()
    open_rows = [{"c": c, "item": it, "overdue": c.due_at < now, "cab": db.get(Cabinet, c.cabinet_id)} for c, it in open_c]
    last_ev = db.execute(event_query.order_by(Event.ts_server.desc()).limit(1)).scalars().first()
    return {"cab": cab, "open_rows": open_rows, "armed": len(open_rows), "last_ev": last_ev, "now": now}


# ---------------- ro'yxat ----------------
@router.get("/xodimlar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db),
              hudud: int | None = None, bolinma: int | None = None, holat: str = "", q: str = "", page: int = 1):
    from ..main import render
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    base, armed = _officer_query(ids)
    if ids is not None:
        base = base.where(Officer.armory_id.in_(ids))
    if hudud:
        base = base.where(Region.id == hudud)
    if bolinma:
        base = base.where(Unit.id == bolinma)
    if holat == "qurollangan":
        base = base.where(armed > 0)
    elif holat in STATUS:
        base = base.where(Officer.service_status == holat)
    qs = q.strip()
    if qs:
        like = _like(qs)
        base = base.where(or_(Officer.full_name.ilike(like, escape="\\"), Officer.tabel.like(like, escape="\\"),
                              Officer.card_uid.ilike(like, escape="\\")))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    armed_total = db.scalar(select(func.count()).select_from(base.where(armed > 0).subquery())) or 0
    pages = max(1, -(-total // PER_PAGE))
    page = min(max(1, page), pages)
    rows = db.execute(base.order_by(Region.order, Unit.name, Officer.tabel).offset((page - 1) * PER_PAGE).limit(PER_PAGE)).all()

    # filtr ro'yxatlari (vakolat doirasiga mos)
    reg_q = select(Region).order_by(Region.order)
    unit_q = select(Unit).join(Region, Region.id == Unit.region_id).order_by(Region.order, Unit.name)
    if ids is not None:
        unit_ids = select(Armory.unit_id).where(Armory.id.in_(ids))
        unit_q = unit_q.where(Unit.id.in_(unit_ids))
        reg_q = reg_q.where(Region.id.in_(select(Unit.region_id).where(Unit.id.in_(unit_ids))))
    if hudud:
        unit_q = unit_q.where(Unit.region_id == hudud)
    region_opts = db.execute(reg_q).scalars().all()
    unit_opts = db.execute(unit_q).scalars().all()

    filters = {k: v for k, v in (("hudud", hudud), ("bolinma", bolinma), ("holat", holat), ("q", qs)) if v}
    base_qs = urlencode(filters)
    holat_qs = urlencode({k: v for k, v in filters.items() if k != "holat"})
    return render(request, "xodimlar/list.html", ctx, active="xodimlar", breadcrumb=[("Xodimlar", "/xodimlar")], title="Xodimlar",
                  rows=rows, total=total, armed_total=armed_total, page=page, pages=pages, per_page=PER_PAGE,
                  hudud=hudud, bolinma=bolinma, holat=holat, q=qs, region_opts=region_opts, unit_opts=unit_opts,
                  base_qs=base_qs, holat_qs=holat_qs, statuses=STATUS)


# ---------------- xodim kartasi ----------------
@router.get("/xodim/{oid}")
def detail(oid: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), xabar: str = ""):
    from ..main import render
    off = _get_officer(db, ctx, oid)
    now = datetime.now()
    unit = db.get(Unit, off.unit_id)
    region = unit.region if unit else None
    armory = db.get(Armory, off.armory_id) if off.armory_id else None
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    live = _live(db, off, now, ids)
    event_scope = [Event.armory_id.in_(ids)] if ids is not None else []
    custody_scope = [Custody.cabinet_id.in_(select(Cabinet.id).where(Cabinet.armory_id.in_(ids)))] if ids is not None else []
    shift_scope = [Shift.unit_id.in_(select(Armory.unit_id).where(Armory.id.in_(ids)))] if ids is not None else []

    elig_by_kind = {e.kind: e for e in db.execute(select(Eligibility).where(Eligibility.officer_id == off.id)).scalars()}
    elig = []
    for kind, label in ELIG:
        e = elig_by_kind.get(kind)
        days = (e.valid_until - now).days if e and e.valid_until else None
        tone = "green"
        if e is None or not e.ok or (days is not None and days < 0):
            tone = "red"
        elif days is not None and days < 30:
            tone = "yellow"
        elig.append({"kind": kind, "label": label, "e": e, "days": days, "tone": tone})
    elig_ok = all(x["tone"] != "red" for x in elig)
    for kind, e in elig_by_kind.items():          # seedda bo'lmagan qo'shimcha turlar ham ko'rinsin
        if kind not in ELIG_LABEL:
            elig.append({"kind": kind, "label": kind, "e": e, "days": None, "tone": "green" if e.ok else "red"})

    shifts = db.execute(select(Shift).where(Shift.officer_id == off.id, *shift_scope).order_by(Shift.start.desc()).limit(8)).scalars().all()
    current_shift = next((s for s in shifts if s.start <= now <= s.end), None)
    next_shift = min((s for s in shifts if s.start > now), key=lambda s: s.start, default=None)

    cust = db.execute(select(Custody, Item, Cabinet).join(Item, Item.id == Custody.item_id).join(Cabinet, Cabinet.id == Custody.cabinet_id)
                      .where(Custody.officer_id == off.id, *custody_scope).order_by(Custody.taken_at.desc()).limit(30)).all()
    custody = [{"c": c, "item": it, "cab": cb, "overdue": (c.returned_at or now) > c.due_at} for c, it, cb in cust]

    denials = db.execute(select(Event).where(Event.officer_id == off.id, Event.type.in_(DENY_TYPES), *event_scope)
                         .order_by(Event.ts_server.desc()).limit(20)).scalars().all()
    d30 = now - timedelta(days=30)
    stats = {
        "olish_30": db.scalar(select(func.count(Event.id)).where(Event.officer_id == off.id, Event.type.in_(TAKE_TYPES), Event.ts_server >= d30, *event_scope)) or 0,
        "rad_30": db.scalar(select(func.count(Event.id)).where(Event.officer_id == off.id, Event.type.in_(DENY_TYPES), Event.ts_server >= d30, *event_scope)) or 0,
        "kechikish_30": db.scalar(select(func.count(Custody.id)).where(Custody.officer_id == off.id, Custody.taken_at >= d30, *custody_scope,
                                                                       or_(Custody.returned_at > Custody.due_at,
                                                                           (Custody.returned_at.is_(None)) & (Custody.due_at < now)))) or 0,
        "farq_30": db.scalar(select(func.count(Custody.id)).where(Custody.officer_id == off.id, Custody.match_ok.is_(False), Custody.taken_at >= d30, *custody_scope)) or 0,
    }
    initials = "".join(p[0] for p in off.full_name.split()[:2]).upper()
    return render(request, "xodimlar/detail.html", ctx, active="xodimlar", title=off.full_name,
                  breadcrumb=[("Xodimlar", "/xodimlar"), (off.full_name, None)],
                  off=off, unit=unit, region=region, armory=armory, elig=elig, elig_ok=elig_ok, shifts=shifts,
                  current_shift=current_shift, next_shift=next_shift, custody=custody, denials=denials, stats=stats,
                  initials=initials, statuses=STATUS, permits=PERMIT, deny_reason=DENY_REASON,
                  xabar=MSG.get(xabar, ""), xabar_tone="yellow" if xabar in ("sabab_kerak", "ozgarish_yoq") else "green", **live)


@router.get("/xodim/{oid}/partials/holat")
def p_holat(oid: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    off = _get_officer(db, ctx, oid)
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    return render(request, "xodimlar/holat_partial.html", ctx, off=off, statuses=STATUS, **_live(db, off, ids=ids))


# ---------------- harakatlar ----------------
@router.post("/xodim/{oid}/holat")
def set_status(oid: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db),
               holat: str = Form(...), sabab: str = Form("")):
    """Xizmat holatini o'zgartirish: faol bo'lmagan holat -> yacheyka bloklanadi; faol -> shu sabab bilan bloklangan yacheyka ochiladi."""
    if not ctx.can("bloklash"):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q: faqat qurolxona mas'uli")
    off = _get_officer(db, ctx, oid)
    if holat not in STATUS:
        raise HTTPException(status_code=400, detail="Noma'lum holat")
    sabab = sabab.strip()
    if not sabab:
        return RedirectResponse(f"/xodim/{oid}?xabar=sabab_kerak", status_code=303)
    old = off.service_status
    if old == holat:
        return RedirectResponse(f"/xodim/{oid}?xabar=ozgarish_yoq", status_code=303)
    who = _who(ctx)
    cab = _cabinet_of(db, off, armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id))
    armory = cab.armory if cab else (db.get(Armory, off.armory_id) if off.armory_id else None)
    old_l = STATUS[old][0] if old in STATUS else old
    new_l = STATUS[holat][0]
    off.service_status = holat
    ev = record_event(db, "huquq_berish_tasdiqlandi", cabinet=cab, armory=armory, officer=off, method="PANEL",
                      title=f"Xizmat holati o'zgartirildi: {old_l} → {new_l}",
                      detail=f"{off.full_name} · tabel {off.tabel} · {sabab}", reason=sabab[:60], approver1=who,
                      payload={"amal": "xizmat_holati", "eski": old, "yangi": holat, "sabab": sabab, "kim": who})
    msg = "holat"
    if cab is not None:
        label = simsvc._label(cab)
        if holat != "faol" and cab.status == "biriktirilgan":
            cab.status = "bloklangan"
            cab.terminal_state = "blocked"
            ev = record_event(db, "shkaf_bloklandi", cabinet=cab, officer=off, method="PANEL",
                              title=f"Yacheyka bloklandi: xodim {new_l.lower()}", detail=f"{label} · {sabab}", reason=sabab[:60], approver1=who,
                              payload={"manba": "xodim_holati", "holat": holat, "sabab": sabab, "kim": who})
            msg = "holat_blok"
        elif holat == "faol" and cab.status == "bloklangan" and _blocked_by_status(db, cab):
            cab.status = "biriktirilgan"
            cab.terminal_state = "idle"
            ev = record_event(db, "shkaf_blokdan_chiqdi", cabinet=cab, officer=off, method="PANEL",
                              title="Yacheyka blokdan chiqarildi: xodim faol", detail=f"{label} · {sabab}", reason=sabab[:60], approver1=who,
                              payload={"manba": "xodim_holati", "holat": holat, "sabab": sabab, "kim": who})
            msg = "holat_ochildi"
    db.commit()
    simsvc._notify(ev, cab, armory)
    return RedirectResponse(f"/xodim/{oid}?xabar={msg}", status_code=303)


def _blocked_by_status(db: Session, cab: Cabinet) -> bool:
    """Yacheykaning oxirgi blok hodisasi xodim holati sababli bo'lganmi (boshqa sababli blokni bu forma ochmaydi)."""
    last = db.execute(select(Event).where(Event.cabinet_id == cab.id, Event.type.in_(("shkaf_bloklandi", "shkaf_blokdan_chiqdi")))
                      .order_by(Event.id.desc()).limit(1)).scalars().first()
    return bool(last and last.type == "shkaf_bloklandi" and (last.payload or {}).get("manba") == "xodim_holati")


@router.post("/xodim/{oid}/ruxsat")
def set_permit(oid: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db),
               tur: str = Form(...), amal: str = Form("bekor"), sabab: str = Form("")):
    """Ruxsatni bekor qilish / tiklash (AVTOMAT yoki TO'PPONCHA). XAVFSIZLIK darajasida jurnalga yoziladi."""
    if not ctx.can("biriktirish"):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q: faqat qurolxona mas'uli")
    off = _get_officer(db, ctx, oid)
    if tur not in PERMIT or amal not in ("bekor", "tiklash"):
        raise HTTPException(status_code=400, detail="Noto'g'ri so'rov")
    sabab = sabab.strip()
    if not sabab:
        return RedirectResponse(f"/xodim/{oid}?xabar=sabab_kerak", status_code=303)
    attr = "permit_ak" if tur == "ak" else "permit_pm"
    old = bool(getattr(off, attr))
    new = amal == "tiklash"
    if old == new:
        return RedirectResponse(f"/xodim/{oid}?xabar=ozgarish_yoq", status_code=303)
    setattr(off, attr, new)
    who = _who(ctx)
    cab = _cabinet_of(db, off, armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id))
    armory = cab.armory if cab else (db.get(Armory, off.armory_id) if off.armory_id else None)
    name, model = PERMIT[tur]
    ev = record_event(db, "huquq_berish_tasdiqlandi", cabinet=cab, armory=armory, officer=off, method="PANEL",
                      result="tiklandi" if new else "bekor",
                      title=f"Ruxsat {'tiklandi' if new else 'bekor qilindi'}: {name} ({model})",
                      detail=f"{off.full_name} · tabel {off.tabel} · {sabab}", reason=sabab[:60], approver1=who,
                      payload={"amal": "ruxsat", "ruxsat": tur, "eski": old, "yangi": new, "sabab": sabab, "kim": who})
    db.commit()
    simsvc._notify(ev, cab, armory)
    return RedirectResponse(f"/xodim/{oid}?xabar={'ruxsat_tiklandi' if new else 'ruxsat_bekor'}", status_code=303)


# ---------------- umumiy qidiruv ----------------
@router.get("/qidiruv")
def search(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), q: str = ""):
    """Xodim (F.I.Sh., tabel, karta), yacheyka (label/seriya), jihoz (seriya/RFID/model) bo'yicha qidiruv."""
    from ..main import render
    qs = q.strip()
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    officers, cabinets, items = [], [], []
    counts = {"xodim": 0, "yacheyka": 0, "jihoz": 0}
    if qs:
        like = _like(qs)
        oq, _armed = _officer_query(ids)
        oq = oq.where(or_(Officer.full_name.ilike(like, escape="\\"), Officer.tabel.like(like, escape="\\"),
                          Officer.card_uid.ilike(like, escape="\\")))
        cq = (select(Cabinet, Armory, Unit, Region, Officer).join(Armory, Armory.id == Cabinet.armory_id)
              .join(Unit, Unit.id == Armory.unit_id).join(Region, Region.id == Unit.region_id)
              .outerjoin(Officer, Officer.id == Cabinet.officer_id)
              .where(or_(Cabinet.label.ilike(like, escape="\\"), Cabinet.serial.ilike(like, escape="\\"))))
        iq = (select(Item, Cabinet, Armory, Unit, Region, Officer).outerjoin(Cabinet, Cabinet.id == Item.cabinet_id)
              .outerjoin(Armory, Armory.id == Cabinet.armory_id).outerjoin(Unit, Unit.id == Armory.unit_id)
              .outerjoin(Region, Region.id == Unit.region_id).outerjoin(Officer, Officer.id == Item.officer_id)
              .where(or_(Item.serial.ilike(like, escape="\\"), Item.rfid.ilike(like, escape="\\"), Item.model.ilike(like, escape="\\"))))
        if ids is not None:
            oq = oq.where(Officer.armory_id.in_(ids))
            cq = cq.where(Cabinet.armory_id.in_(ids))
            iq = iq.where(Cabinet.armory_id.in_(ids))
        counts["xodim"] = db.scalar(select(func.count()).select_from(oq.subquery())) or 0
        counts["yacheyka"] = db.scalar(select(func.count()).select_from(cq.subquery())) or 0
        counts["jihoz"] = db.scalar(select(func.count()).select_from(iq.subquery())) or 0
        officers = db.execute(oq.order_by(Officer.full_name).limit(50)).all()
        cabinets = db.execute(cq.order_by(Region.order, Unit.name, Cabinet.position).limit(50)).all()
        items = db.execute(iq.order_by(Item.kind, Item.serial).limit(50)).all()
    return render(request, "xodimlar/qidiruv.html", ctx, active="", title="Qidiruv", breadcrumb=[("Qidiruv", None)],
                  q=qs, officers=officers, cabinets=cabinets, items=items, counts=counts, total=sum(counts.values()), statuses=STATUS)

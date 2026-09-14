"""Inventar xizmati: jihozlar ro'yxati va filtrlar, ko'rik/ta'mir/hold harakatlari,
inventarizatsiya sessiyalari (RFID skan simulyatsiyasi) va akt (PDF, reportlab)."""
from __future__ import annotations

import io
import random
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..models import Armory, Cabinet, Custody, Event, Item, Officer, Region, Unit
from .events import record_event
from .live import hub

PER_PAGE = 50
KINDS = ["qurol", "magazin", "oq_dori", "jihoz"]
KIND_LABEL = {"qurol": "Qurol", "magazin": "Magazin", "oq_dori": "O'q-dori", "jihoz": "Jihoz"}
# Item.state -> (chip class, matn)
STATE_LABEL = {"mavjud": ("chip-green", "Uyada"), "yo'q": ("chip-yellow", "Xodimda"),
               "nosoz": ("chip-red", "Nosoz"), "xizmatda": ("chip-yellow", "Xizmatda")}
# Item.inspection_state -> (chip class, matn)
INSP_LABEL = {"yaroqli": ("chip-green", "Yaroqli"), "ko'rik_kutilmoqda": ("chip-yellow", "Ko'rik kutilmoqda"),
              "ko'rikda": ("chip-yellow", "Ko'rikda"), "ta'mirda": ("chip-red", "Ta'mirda")}
# paneldan o'rnatish mumkin bo'lgan holatlar ("yo'q" faqat apparat/custody orqali)
PANEL_STATES = ["mavjud", "nosoz", "xizmatda"]
# inventarizatsiya skan natijasi -> (chip class, matn)
SCAN_LABEL = {"topildi": ("chip-green", "Uyada · mos"), "xodimda": ("chip-gray", "Xodimda (kutilgan)"),
              "topilmadi": ("chip-red", "Topilmadi"), "kutilmagan": ("chip-red", "Kutilmagan · uyada"),
              "rfid_mos_emas": ("chip-red", "RFID mos emas"), "miqdor_farqi": ("chip-yellow", "Miqdor farqi")}
DISCREPANCY_CODES = {"topilmadi", "kutilmagan", "rfid_mos_emas", "miqdor_farqi"}
KIND_ORDER = {"qurol": 0, "magazin": 1, "oq_dori": 2, "jihoz": 3}


def _joined(stmt):
    """Item -> Cabinet -> Armory -> Unit -> Region, Officer (barchasi outer join)."""
    return (stmt.outerjoin(Cabinet, Cabinet.id == Item.cabinet_id)
            .outerjoin(Armory, Armory.id == Cabinet.armory_id)
            .outerjoin(Unit, Unit.id == Armory.unit_id)
            .outerjoin(Region, Region.id == Unit.region_id)
            .outerjoin(Officer, Officer.id == Item.officer_id))


def where_label(arm: Armory | None, cab: Cabinet | None = None) -> str:
    if arm is None:
        return ""
    s = f"{arm.unit.region.short} · {arm.unit.name}"
    return s + f" · {cab.label}" if cab is not None else s


def _notify(ev: Event, cab: Cabinet | None, arm: Armory | None):
    hub.broadcast_threadsafe({"type": "event", "event_type": ev.type, "level": ev.level, "cabinet_id": cab.id if cab else None,
                              "armory_id": arm.id if arm else None, "title": ev.title, "ts": ev.ts_server.isoformat()})


# ---------------- Ro'yxat ----------------
def _custody_scope(armory_ids: list[int] | None) -> list:
    return [] if armory_ids is None else [Custody.cabinet_id.in_(
        select(Cabinet.id).where(Cabinet.armory_id.in_(armory_ids)).correlate(None))]


def _open_items(armory_ids: list[int] | None, *extra):
    return select(Custody.item_id).where(Custody.returned_at.is_(None), *_custody_scope(armory_ids), *extra)


def _conds(f: dict, now: datetime) -> list:
    conds = []
    if f.get("kind"):
        conds.append(Item.kind == f["kind"])
    if f.get("berilgan") or f.get("holat") == "yo'q":
        conds.append(Item.id.in_(_open_items(f.get("armory_ids"))))
    if f.get("holat") == "mavjud":
        # A record outside the viewer's scope must not make an item look available.
        # Exclude it conservatively without exposing that record's private details.
        conds.extend([Item.state == "mavjud", ~Item.id.in_(_open_items(None))])
    elif f.get("holat") and f["holat"] != "yo'q":
        conds.append(Item.state == f["holat"])
    if f.get("korik"):
        conds.append(Item.inspection_state == f["korik"])
    if f.get("region_id"):
        conds.append(Region.id == f["region_id"])
    if f.get("armory_ids") is not None:
        conds.append(Armory.id.in_(f["armory_ids"]))
    if f.get("officer_id") is not None:
        conds.append(Item.officer_id == f["officer_id"])
    if f.get("hold"):
        conds.append(Item.hold.is_(True))
    if f.get("q"):
        like = f"%{f['q'].strip()}%"
        conds.append(or_(Item.serial.ilike(like), Item.rfid.ilike(like), Item.model.ilike(like), Item.category.ilike(like)))
    if f.get("kechikish"):
        conds.append(Item.id.in_(_open_items(f.get("armory_ids"), Custody.due_at < now)))
    if f.get("farq"):
        conds.append(Item.id.in_(select(Custody.item_id).where(Custody.match_ok.is_(False))))
    return conds


def list_items(db: Session, f: dict, page: int = 1, per_page: int = PER_PAGE, now: datetime | None = None) -> dict:
    """Filtrlangan jihozlar sahifasi: qatorlar (item, cab, arm, unit, region, officer), jami, ochiq custody va farq xaritalari."""
    now = now or datetime.now()
    conds = _conds(f, now)
    total = db.scalar(_joined(select(func.count(Item.id)).select_from(Item)).where(*conds)) or 0
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(max(page, 1), pages)
    stmt = (_joined(select(Item, Cabinet, Armory, Unit, Region, Officer)).where(*conds)
            .order_by(Region.order, Armory.id, Cabinet.position, Item.id).offset((page - 1) * per_page).limit(per_page))
    rows = db.execute(stmt).all()
    ids = [r[0].id for r in rows]
    open_c: dict[int, Custody] = {}
    open_counts: dict[int, int] = {}
    farq_c: dict[int, Custody] = {}
    if ids:
        for c in db.execute(select(Custody).where(Custody.item_id.in_(ids), Custody.returned_at.is_(None),
                           *_custody_scope(f.get("armory_ids"))).order_by(Custody.due_at, Custody.id)).scalars():
            open_c.setdefault(c.item_id, c)
            open_counts[c.item_id] = open_counts.get(c.item_id, 0) + 1
        for c in db.execute(select(Custody).where(Custody.item_id.in_(ids), Custody.match_ok.is_(False),
                           *_custody_scope(f.get("armory_ids"))).order_by(Custody.returned_at)).scalars():
            farq_c[c.item_id] = c
    return {"rows": rows, "total": total, "page": page, "pages": pages, "open": open_c,
            "open_counts": open_counts, "farq": farq_c, "now": now}


def kind_counts(db: Session, armory_ids: list[int] | None, *, officer_id: int | None = None) -> dict[str, int]:
    q = select(Item.kind, func.count(Item.id)).select_from(Item)
    if armory_ids is not None:
        q = q.join(Cabinet, Cabinet.id == Item.cabinet_id).where(Cabinet.armory_id.in_(armory_ids))
    if officer_id is not None:
        q = q.where(Item.officer_id == officer_id)
    out = {k: 0 for k in KINDS}
    for k, n in db.execute(q.group_by(Item.kind)):
        out[k] = n
    return out


def summary(db: Session, armory_ids: list[int] | None, now: datetime | None = None, *, officer_id: int | None = None) -> dict:
    """Inventar KPI: jami, uyada, xodimda, kechikish, farqlar (30 kun), ko'rik/ta'mir, ushlab turilgan."""
    now = now or datetime.now()

    def item_q(*extra):
        q = select(func.count(Item.id)).select_from(Item)
        if armory_ids is not None:
            q = q.join(Cabinet, Cabinet.id == Item.cabinet_id).where(Cabinet.armory_id.in_(armory_ids))
        if officer_id is not None:
            q = q.where(Item.officer_id == officer_id)
        return q.where(*extra) if extra else q

    def cust_q(*extra):
        q = select(func.count(Custody.id))
        if armory_ids is not None:
            q = q.join(Cabinet, Cabinet.id == Custody.cabinet_id).where(Cabinet.armory_id.in_(armory_ids))
        if officer_id is not None:
            q = q.where(Custody.officer_id == officer_id)
        return q.where(*extra)

    issued = Item.id.in_(_open_items(armory_ids))
    issued_weapons = item_q(Item.kind == "qurol", issued)
    issued_count = db.scalar(issued_weapons) or 0
    # Count items for navigation; retain the number of source records separately.
    visible_items = issued_weapons.with_only_columns(Item.id).correlate(None)
    open_records = db.scalar(select(func.count(Custody.id)).where(
        Custody.item_id.in_(visible_items), Custody.returned_at.is_(None), *_custody_scope(armory_ids))) or 0
    return {
        "jami": db.scalar(item_q()) or 0,
        "qurollar": db.scalar(item_q(Item.kind == "qurol")) or 0,
        "uyada": db.scalar(item_q(Item.kind == "qurol", Item.state == "mavjud", ~Item.id.in_(_open_items(None)))) or 0,
        "xodimda": issued_count,
        "ochiq_qaydlar": open_records,
        "takroriy_qaydlar": open_records - issued_count,
        "kechikish": db.scalar(item_q(Item.kind == "qurol", Item.id.in_(_open_items(armory_ids, Custody.due_at < now)))) or 0,
        "farq": db.scalar(cust_q(Custody.match_ok.is_(False), Custody.returned_at >= now - timedelta(days=30))) or 0,
        "korik": db.scalar(item_q(Item.inspection_state != "yaroqli")) or 0,
        "hold": db.scalar(item_q(Item.hold.is_(True))) or 0,
        "nosoz": db.scalar(item_q(Item.state.in_(["nosoz", "xizmatda"]))) or 0,
    }


# ---------------- Jihoz kartasi ----------------
def item_detail(db: Session, item_id: int, now: datetime | None = None, *, armory_ids: list[int] | None = None) -> dict | None:
    now = now or datetime.now()
    row = db.execute(_joined(select(Item, Cabinet, Armory, Unit, Region, Officer)).where(Item.id == item_id)).first()
    if row is None:
        return None
    item, cab, arm, unit, reg, off = row
    custody_scope = _custody_scope(armory_ids)
    event_scope = [] if armory_ids is None else [Event.armory_id.in_(armory_ids)]
    custody = db.execute(select(Custody).where(Custody.item_id == item_id, *custody_scope).order_by(Custody.taken_at.desc()).limit(100)).scalars().all()
    # Current custody must remain visible even beyond the 100-row history window.
    open_rows = db.scalars(select(Custody).where(Custody.item_id == item_id, Custody.returned_at.is_(None),
                           *custody_scope).order_by(Custody.due_at, Custody.id)).all()
    off_ids = {c.officer_id for c in [*custody, *open_rows]}
    cab_ids = {c.cabinet_id for c in [*custody, *open_rows]}
    officers = {o.id: o for o in db.execute(select(Officer).where(Officer.id.in_(off_ids))).scalars()} if off_ids else {}
    cabs = {c.id: c for c in db.execute(select(Cabinet).where(Cabinet.id.in_(cab_ids))).scalars()} if cab_ids else {}
    events = db.execute(select(Event).where(Event.item_id == item_id, *event_scope).order_by(Event.ts_server.desc()).limit(30)).scalars().all()
    open_c = open_rows[0] if open_rows else None
    stats = {
        "custody": db.scalar(select(func.count(Custody.id)).where(Custody.item_id == item_id, *custody_scope)) or 0,
        "farq": db.scalar(select(func.count(Custody.id)).where(Custody.item_id == item_id, Custody.match_ok.is_(False), *custody_scope)) or 0,
        "kechikish": db.scalar(select(func.count(Custody.id)).where(Custody.item_id == item_id, Custody.returned_at.is_(None), Custody.due_at < now, *custody_scope)) or 0,
    }
    return {"item": item, "cab": cab, "arm": arm, "unit": unit, "reg": reg, "off": off, "custody": custody,
            "officers": officers, "cabs": cabs, "events": events, "open": open_c,
            "open_count": len(open_rows), "stats": stats, "now": now}


def set_inspection(db: Session, item: Item, cab: Cabinet | None, arm: Armory | None, new_state: str,
                   next_inspection: datetime | None, reason: str, by: str) -> Event:
    """Ko'rik/ta'mir holati. ta'mirda/ko'rikda -> jihoz xizmatda; yaroqli -> uyada (agar xodimda bo'lmasa)."""
    if new_state not in INSP_LABEL:
        raise ValueError("Noma'lum ko'rik holati")
    old, old_state = item.inspection_state, item.state
    item.inspection_state = new_state
    if next_inspection is not None:
        item.next_inspection = next_inspection
    if new_state in ("ta'mirda", "ko'rikda") and item.state == "mavjud":
        item.state = "xizmatda"
    elif new_state == "yaroqli" and item.state in ("xizmatda", "nosoz"):
        item.state = "mavjud"
    ev = record_event(db, "texnik_xizmat", cabinet=cab, armory=arm, item_id=item.id, reason=reason[:60], approver1=by,
                      title=f"Ko'rik holati: {INSP_LABEL[new_state][1]}",
                      detail=f"{where_label(arm, cab)} · {item.model} {item.serial}", simulated=False,
                      level="WARNING" if new_state == "ta'mirda" else "INFO",
                      payload={"harakat": "korik", "item_id": item.id, "eski": old, "yangi": new_state,
                               "holat_eski": old_state, "holat_yangi": item.state, "kim": by,
                               "keyingi_korik": next_inspection.isoformat() if next_inspection else None})
    _notify(ev, cab, arm)
    return ev


def set_state(db: Session, item: Item, cab: Cabinet | None, arm: Armory | None, new_state: str, reason: str, by: str) -> Event:
    if new_state not in PANEL_STATES:
        raise ValueError("Bu holatni paneldan o'rnatib bo'lmaydi")
    if item.state == "yo'q":
        raise ValueError("Jihoz xodimda: holat faqat qaytarishda (apparat) o'zgaradi")
    old = item.state
    item.state = new_state
    ev = record_event(db, "texnik_xizmat", cabinet=cab, armory=arm, item_id=item.id, reason=reason[:60], approver1=by,
                      title=f"Jihoz holati: {STATE_LABEL[new_state][1]}",
                      detail=f"{where_label(arm, cab)} · {item.model} {item.serial}", simulated=False,
                      level="WARNING" if new_state == "nosoz" else "INFO",
                      payload={"harakat": "holat", "item_id": item.id, "eski": old, "yangi": new_state, "kim": by})
    _notify(ev, cab, arm)
    return ev


def set_hold(db: Session, item: Item, cab: Cabinet | None, arm: Armory | None, hold: bool, reason: str, by: str) -> Event:
    """Ushlab turish: berish bloklanadi (qulf paneldan ochilmaydi, faqat belgi)."""
    item.hold = hold
    ev = record_event(db, "texnik_xizmat", cabinet=cab, armory=arm, item_id=item.id, reason=reason[:60], approver1=by,
                      title="Jihoz ushlab turildi · berish bloklandi" if hold else "Ushlab turish bekor qilindi",
                      detail=f"{where_label(arm, cab)} · {item.model} {item.serial}", simulated=False,
                      level="WARNING" if hold else "INFO",
                      payload={"harakat": "hold", "item_id": item.id, "hold": hold, "kim": by})
    _notify(ev, cab, arm)
    return ev


# ---------------- Inventarizatsiya sessiyalari (xotirada) ----------------
_SESSIONS: dict[int, dict] = {}


def session_get(armory_id: int) -> dict | None:
    return _SESSIONS.get(armory_id)


def sessions_all() -> list[dict]:
    return sorted(_SESSIONS.values(), key=lambda s: s["started_at"], reverse=True)


def session_start(armory: Armory, by: str) -> dict:
    s = _SESSIONS.get(armory.id)
    if s:
        return s
    s = {"armory_id": armory.id, "started_by": by, "started_at": datetime.now().replace(microsecond=0), "scanned": False,
         "scanned_at": None, "results": {}, "discrepancies": [], "counts": {}}
    _SESSIONS[armory.id] = s
    return s


def session_cancel(armory_id: int) -> None:
    _SESSIONS.pop(armory_id, None)


def session_items(db: Session, armory_id: int) -> list[tuple]:
    """Qurolxonadagi barcha jihozlar: (item, cab, officer), yacheyka tartibi bo'yicha."""
    rows = db.execute(select(Item, Cabinet, Officer).join(Cabinet, Cabinet.id == Item.cabinet_id)
                      .outerjoin(Officer, Officer.id == Item.officer_id).where(Cabinet.armory_id == armory_id)).all()
    return sorted(rows, key=lambda r: (r[1].position, KIND_ORDER.get(r[0].kind, 9), r[0].id))


def session_scan(db: Session, s: dict) -> dict:
    """RFID skan simulyatsiyasi: Item.state bilan solishtirish. Natija sessiyada saqlanadi (deterministik)."""
    rnd = random.Random(f"{s['armory_id']}|{s['started_at'].isoformat()}")
    rows = session_items(db, s["armory_id"])
    # oxirgi custody nomuvofiq bo'lgan (qaytarilgan) qurollar: uyada RFID mos emas
    mismatch: set[int] = set()
    latest: dict[int, Custody] = {}
    ids = [r[0].id for r in rows]
    if ids:
        for c in db.execute(select(Custody).where(Custody.item_id.in_(ids), Custody.returned_at.is_not(None)).order_by(Custody.returned_at)).scalars():
            latest[c.item_id] = c
        mismatch = {i for i, c in latest.items() if not c.match_ok}
    results: dict[int, dict] = {}
    disc: list[dict] = []
    counts = {"jami": 0, "rfid": 0, "topildi": 0, "xodimda": 0, "topilmadi": 0, "kutilmagan": 0, "rfid_mos_emas": 0, "miqdor_farqi": 0}
    for item, cab, off in rows:
        counts["jami"] += 1
        found_qty = item.qty
        if item.rfid:
            counts["rfid"] += 1
            if item.state == "mavjud":
                if item.id in mismatch:
                    code, note = "rfid_mos_emas", "Uyadagi RFID biriktirilgan jihozga mos emas"
                elif rnd.random() < 0.015:
                    code, note = "topilmadi", "RFID o'qilmadi, uyada yo'q"
                else:
                    code, note = "topildi", ""
            elif item.state == "yo'q":
                if rnd.random() < 0.04:
                    code, note = "kutilmagan", "Uyada topildi, tizimda: xodimda"
                else:
                    code, note = "xodimda", ""
            else:
                code, note = "topildi", ""
        else:
            if item.state == "yo'q":
                code, note = "xodimda", ""
            elif item.qty > 1 and rnd.random() < 0.012:
                found_qty = max(item.qty - rnd.randint(1, max(1, item.qty // 4)), 0)
                code, note = "miqdor_farqi", f"Kutilgan {item.qty}, topildi {found_qty}"
            else:
                code, note = "topildi", ""
        counts[code] += 1
        results[item.id] = {"code": code, "note": note, "qty": found_qty}
        if code in DISCREPANCY_CODES:
            disc.append({"item_id": item.id, "kind": item.kind, "model": item.model, "serial": item.serial, "rfid": item.rfid or "",
                         "cabinet_id": cab.id, "cabinet": cab.label, "officer": off.full_name if off else "", "officer_id": off.id if off else None,
                         "tizimda": item.state, "code": code, "note": note})
    s.update(scanned=True, scanned_at=datetime.now().replace(microsecond=0), results=results, discrepancies=disc, counts=counts)
    return s


def session_finish(db: Session, s: dict, armory: Armory, by: str, confirm: str, note: str, hold_disc: bool) -> Event:
    """Aktni yakunlash: event `inventarizatsiya` (payload: natijalar), farqli jihozlar ixtiyoriy hold."""
    held: list[int] = []
    if hold_disc and s["discrepancies"]:
        for d in s["discrepancies"]:
            it = db.get(Item, d["item_id"])
            if it is not None and not it.hold:
                it.hold = True
                held.append(it.id)
    c = s["counts"]
    n_disc = len(s["discrepancies"])
    payload = {"armory_id": armory.id, "started_by": s["started_by"], "started_at": s["started_at"].isoformat(),
               "scanned_at": s["scanned_at"].isoformat() if s["scanned_at"] else None,
               "finished_at": datetime.now().replace(microsecond=0).isoformat(), "counts": c, "discrepancies": s["discrepancies"],
               "izoh": note, "hold_qoyildi": held, "tasdiqlovchi": confirm, "kim": by}
    ev = record_event(db, "inventarizatsiya", armory=armory, approver1=by, approver2=confirm, reason=note[:60],
                      title="Inventarizatsiya yakunlandi", simulated=False, level="WARNING" if n_disc else "INFO",
                      detail=f"{where_label(armory)} · {c.get('jami', 0)} jihoz, {n_disc} farq", payload=payload)
    _SESSIONS.pop(armory.id, None)
    _notify(ev, None, armory)
    return ev


def history(db: Session, armory_ids: list[int] | None, limit: int = 30) -> list[tuple[Event, Armory | None]]:
    q = select(Event).where(Event.type == "inventarizatsiya").order_by(Event.ts_server.desc()).limit(limit)
    if armory_ids is not None:
        q = q.where(Event.armory_id.in_(armory_ids))
    evs = db.execute(q).scalars().all()
    arm_ids = {e.armory_id for e in evs if e.armory_id}
    arms = {a.id: a for a in db.execute(select(Armory).where(Armory.id.in_(arm_ids))).scalars()} if arm_ids else {}
    return [(e, arms.get(e.armory_id)) for e in evs]


# ---------------- Akt PDF (reportlab) ----------------
_FONT: str | None = None


def _pdf_font() -> str:
    global _FONT
    if _FONT:
        return _FONT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for p in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            try:
                pdfmetrics.registerFont(TTFont("AqFont", p))
                _FONT = "AqFont"
                return _FONT
            except Exception:  # noqa: BLE001
                continue
    _FONT = "Helvetica"
    return _FONT


def act_pdf(ev: Event, armory: Armory | None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font = _pdf_font()
    p = ev.payload or {}
    c = p.get("counts", {})
    disc = p.get("discrepancies", [])
    st_h = ParagraphStyle("h", fontName=font, fontSize=14, leading=18, spaceAfter=4)
    st_b = ParagraphStyle("b", fontName=font, fontSize=9.5, leading=13)
    st_s = ParagraphStyle("s", fontName=font, fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Inventarizatsiya akti N{ev.id}")
    where = where_label(armory) if armory else "-"
    body = [
        Paragraph("O'zbekiston Respublikasi Ichki ishlar vazirligi · Aqlli qurolxona · Nazorat markazi", st_s),
        Paragraph(f"INVENTARIZATSIYA AKTI № {ev.id}", st_h),
        Paragraph(f"Qurolxona: {where}{(' · ' + armory.name) if armory else ''}", st_b),
        Paragraph(f"Boshlangan: {_fmt(p.get('started_at'))} · Skan: {_fmt(p.get('scanned_at'))} · Yakunlangan: {_fmt(p.get('finished_at'))}", st_b),
        Paragraph(f"O'tkazdi: {p.get('kim') or ev.approver1 or '-'} · Tasdiqladi: {p.get('tasdiqlovchi') or ev.approver2 or '-'}", st_b),
        Spacer(1, 6),
        Paragraph("Natijalar", ParagraphStyle("h2", parent=st_h, fontSize=11)),
    ]
    stats = [["Ko'rsatkich", "Soni"], ["Jami jihozlar", c.get("jami", 0)], ["RFID bilan skanlandi", c.get("rfid", 0)],
             ["Uyada, mos", c.get("topildi", 0)], ["Xodimda (kutilgan)", c.get("xodimda", 0)], ["Topilmadi", c.get("topilmadi", 0)],
             ["Kutilmagan (uyada)", c.get("kutilmagan", 0)], ["RFID mos emas", c.get("rfid_mos_emas", 0)],
             ["Miqdor farqi", c.get("miqdor_farqi", 0)], ["Farqlar jami", len(disc)], ["Hold qo'yildi", len(p.get("hold_qoyildi", []))]]
    t = Table(stats, colWidths=[90 * mm, 30 * mm])
    t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf5")), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                           ("ALIGN", (1, 0), (1, -1), "RIGHT")]))
    body += [t, Spacer(1, 8), Paragraph("Farqlar ro'yxati", ParagraphStyle("h3", parent=st_h, fontSize=11))]
    if disc:
        data = [["#", "Yacheyka", "Tur", "Model", "Seriya", "Tizimda", "Natija", "Izoh"]]
        for i, d in enumerate(disc, 1):
            data.append([i, d.get("cabinet", ""), KIND_LABEL.get(d.get("kind", ""), d.get("kind", "")), d.get("model", ""), d.get("serial", ""),
                         STATE_LABEL.get(d.get("tizimda", ""), ("", d.get("tizimda", "")))[1], SCAN_LABEL.get(d.get("code", ""), ("", d.get("code", "")))[1],
                         Paragraph(d.get("note", ""), st_s)])
        t2 = Table(data, colWidths=[8 * mm, 16 * mm, 16 * mm, 26 * mm, 26 * mm, 18 * mm, 26 * mm, 42 * mm], repeatRows=1)
        t2.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 8),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf5")), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                                ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        body.append(t2)
    else:
        body.append(Paragraph("Farqlar aniqlanmadi. Inventar tizim hisobiga mos.", st_b))
    if p.get("izoh"):
        body += [Spacer(1, 8), Paragraph(f"Izoh: {p['izoh']}", st_b)]
    body += [Spacer(1, 14), Paragraph(f"Jurnal yozuvi #{ev.id} · hash {ev.hash[:16]}... · prev {ev.prev_hash[:16] if ev.prev_hash else '-'}...", st_s),
             Spacer(1, 18), Paragraph("O'tkazdi: ______________________          Tasdiqladi: ______________________", st_b),
             Paragraph("NAMUNAVIY MA'LUMOT · simulyator (prototip)", st_s)]
    doc.build(body)
    return buf.getvalue()


def _fmt(iso: str | None) -> str:
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return iso

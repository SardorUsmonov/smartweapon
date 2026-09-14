"""Jurnal: append-only hodisalar (Event) ro'yxati, batafsil sahifa, hash zanjiri yaxlitligi, CSV eksport,
favqulodda ochilishlar va mexanik kalit tabi. Panel hech qanday yozuvni tahrirlamaydi va o'chirmaydi."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Alarm, Armory, Cabinet, Event, ExportLog, Item, Officer, Region, Unit
from ..services.events import EVENT_RULES, LEVEL_LABEL, _chain_hash, record_event, verify_chain
from ..services.kpi import armory_ids_for_scope
from ..services.sim import _notify

router = APIRouter()

PER_PAGE = 100
EXPORT_LIMIT = 20000
LEVELS = ["INFO", "WARNING", "CRITICAL", "SECURITY"]
EXPORT_DIR = config.DATA_DIR / "eksport"

# ---- lug'atlar (o'zbek lotin) ----
TYPE_LABEL: dict[str, str] = {
    "auth_ok": "Kirish tasdiqlandi", "rad_etildi": "Kirish rad etildi", "rad_etildi_takror": "Takroriy rad etish (blokirovka)",
    "qulf_ochildi": "Qulf ochildi", "eshik_ochildi": "Eshik ochildi", "eshik_yopildi": "Eshik yopildi",
    "avtomatik_qulflandi": "Avtomatik qulflandi", "avtomat_olindi": "Avtomat olindi", "avtomat_qaytarildi": "Avtomat qaytarildi",
    "pm_olindi": "To'pponcha olindi", "pm_qaytarildi": "To'pponcha qaytarildi", "qaytarish_nomuvofiq": "Qaytarish nomuvofiq",
    "kechikish": "Qaytarish kechikdi", "eshik_ochiq_qoldi": "Eshik ochiq qoldi", "urilish": "Urilish aniqlandi",
    "buzish_urinishi": "Buzishga urinish (tamper)", "lyuk_ochildi": "Xizmat lyuki ochildi", "quvvat_uzildi": "Quvvat uzildi",
    "quvvat_tiklandi": "Quvvat tiklandi", "batareya_past": "Batareya past", "aloqa_uzildi": "Aloqa uzildi (oflayn)",
    "aloqa_tiklandi": "Aloqa tiklandi", "sinxronlandi": "Sinxronlandi", "mexanik_kalit": "Mexanik kalit bilan ochildi",
    "favqulodda_ochish": "Favqulodda ochish", "rejim_boshlandi": "Rejim boshlandi", "rejim_tugadi": "Rejim tugadi",
    "shkaf_bloklandi": "Yacheyka bloklandi", "shkaf_blokdan_chiqdi": "Yacheyka blokdan chiqarildi",
    "biriktirildi": "Xodim biriktirildi", "ajratildi": "Xodim ajratildi", "smena_ochildi": "Smena ochildi",
    "smena_yopildi": "Smena yopildi", "oz_tekshiruv_xato": "O'z-tekshiruv xatosi", "qulf_xatosi": "Qulf xatosi",
    "datchik_xatosi": "Datchik xatosi", "disk_toldi": "Disk to'ldi", "kamera_oqimi_uzildi": "Kamera oqimi uzildi",
    "kamera_oqimi_tiklandi": "Kamera oqimi tiklandi", "vaqt_sinxroni_buzildi": "Vaqt sinxroni buzildi",
    "server_yoq_rejimi": "Serversiz rejim", "huquq_berish_tasdiqlandi": "Huquq berish tasdiqlandi",
    "eksport_qilindi": "Eksport qilindi", "zaxira_nusxa": "Zaxira nusxa", "zaxira_nusxa_xato": "Zaxira nusxa xatosi",
    "texnik_xizmat": "Texnik xizmat", "inventarizatsiya": "Inventarizatsiya", "sozlama_ozgardi": "Sozlama o'zgardi",
}
TYPE_GROUPS: dict[str, tuple[str, list[str]]] = {
    "operatsiya": ("Olish-qaytarish", ["avtomat_olindi", "avtomat_qaytarildi", "pm_olindi", "pm_qaytarildi"]),
    "kirish": ("Kirish va qulf", ["auth_ok", "qulf_ochildi", "eshik_ochildi", "eshik_yopildi", "avtomatik_qulflandi"]),
    "rad_etildi": ("Rad etilgan urinishlar", ["rad_etildi", "rad_etildi_takror"]),
    "favqulodda": ("Favqulodda va mexanik kalit", ["favqulodda_ochish", "mexanik_kalit"]),
    "kechikish": ("Kechikishlar", ["kechikish"]),
    "signal": ("Signal beruvchi hodisalar", [k for k, r in EVENT_RULES.items() if r[1]]),
    "texnik": ("Texnik holat", ["quvvat_uzildi", "quvvat_tiklandi", "batareya_past", "aloqa_uzildi", "aloqa_tiklandi", "sinxronlandi",
                               "oz_tekshiruv_xato", "qulf_xatosi", "datchik_xatosi", "disk_toldi", "kamera_oqimi_uzildi",
                               "kamera_oqimi_tiklandi", "vaqt_sinxroni_buzildi", "server_yoq_rejimi", "zaxira_nusxa",
                               "zaxira_nusxa_xato", "texnik_xizmat", "lyuk_ochildi"]),
    "boshqaruv": ("Boshqaruv va audit", ["shkaf_bloklandi", "shkaf_blokdan_chiqdi", "biriktirildi", "ajratildi", "smena_ochildi",
                                        "smena_yopildi", "rejim_boshlandi", "rejim_tugadi", "huquq_berish_tasdiqlandi",
                                        "eksport_qilindi", "sozlama_ozgardi", "inventarizatsiya"]),
}
REASON_LABEL = {
    "outside_shift": "Navbat oynasidan tashqarida", "no_permit": "Ruxsat yo'q", "biometric_mismatch": "Biometriya mos kelmadi",
    "wrong_pin": "Noto'g'ri PIN", "cabinet_blocked": "Yacheyka bloklangan", "lockout": "Vaqtincha blokirovka",
}
RESULT_LABEL = {"ok": "OK", "rad": "Rad etildi", "nomuvofiq": "Nomuvofiq", "kutilmoqda": "Kutilmoqda"}
METHOD_LABEL = {"YUZ+BARMOQ": "Yuz + barmoq", "KARTA+BARMOQ": "Karta + barmoq", "PIN": "PIN", "FAVQULODDA": "Favqulodda",
                "MEXANIK": "Mexanik kalit", "PANEL": "Nazorat paneli"}
EXPORT_DAYS = {"7": "7 kun", "30": "30 kun", "90": "90 kun", "365": "1 yil"}


# ---------------- yordamchilar ----------------
def _int(s: str | int | None) -> int:
    try:
        return int(s) if s not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def _date(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def _filters(dan="", gacha="", hudud="", qurolxona="", bolinma="", tur="", daraja="", xodim="", yacheyka="", oflayn="", page="1") -> dict:
    return {"dan": dan.strip()[:10], "gacha": gacha.strip()[:10], "hudud": _int(hudud), "qurolxona": _int(qurolxona),
            "bolinma": _int(bolinma), "tur": tur.strip(), "daraja": daraja.strip().upper(), "xodim": xodim.strip()[:60],
            "yacheyka": yacheyka.strip()[:40], "oflayn": "1" if oflayn in ("1", "on", "true") else "", "page": max(1, _int(page) or 1)}


def _linker(f: dict):
    def qlink(**over):
        d = dict(f); d.update(over)
        return urlencode({k: v for k, v in d.items() if v not in ("", None, 0, False) and not (k == "page" and v == 1)})
    return qlink


def _filter_error(f: dict) -> str:
    if any(f[key] and _date(f[key]) is None for key in ("dan", "gacha")):
        return "Sana noto'g'ri. Sanani YYYY-MM-DD shaklida kiriting."
    if f["dan"] and f["gacha"] and f["dan"] > f["gacha"]:
        return "Boshlanish sanasi tugash sanasidan keyin bo'lishi mumkin emas."
    return ""


def _conditions(db: Session, ctx: Ctx, f: dict) -> list:
    conds = []
    if _filter_error(f):
        conds.append(false())
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    if ids is not None:
        conds.append(Event.armory_id.in_(ids))
    d0, d1 = _date(f["dan"]), _date(f["gacha"])
    if d0:
        conds.append(Event.ts_server >= d0)
    if d1:
        conds.append(Event.ts_server < d1 + timedelta(days=1))
    if f["hudud"]:
        conds.append(Event.region_id == f["hudud"])
    if f["bolinma"]:
        conds.append(Event.unit_id == f["bolinma"])
    if f["qurolxona"]:
        conds.append(Event.armory_id == f["qurolxona"])
    tur = f["tur"]
    if tur in TYPE_GROUPS:
        conds.append(Event.type.in_(TYPE_GROUPS[tur][1]))
    elif tur:
        conds.append(Event.type == tur)
    if f["daraja"] in LEVELS:
        conds.append(Event.level == f["daraja"])
    x = f["xodim"]
    if x:
        sub = select(Officer.id).where(or_(Officer.full_name.ilike(f"%{x}%"), Officer.tabel == x))
        if x.isdigit() and len(x) < 10:
            sub = select(Officer.id).where(or_(Officer.id == int(x), Officer.tabel == x))
        conds.append(Event.officer_id.in_(sub))
    y = f["yacheyka"]
    if y:
        sub = select(Cabinet.id).where(or_(Cabinet.label.ilike(f"%{y}%"), Cabinet.serial.ilike(f"%{y}%")))
        if y.isdigit() and len(y) < 10:
            sub = select(Cabinet.id).where(Cabinet.id == int(y))
        conds.append(Event.cabinet_id.in_(sub))
    if f["oflayn"]:
        conds.append(Event.offline.is_(True))
    return conds


def _map(db: Session, model, ids: set) -> dict:
    """id -> obyekt; SQLite parametr chegarasi uchun 900 tadan bo'lib so'raydi."""
    out = {}
    ids = sorted(i for i in ids if i)
    for i in range(0, len(ids), 900):
        for o in db.execute(select(model).where(model.id.in_(ids[i:i + 900]))).scalars():
            out[o.id] = o
    return out


def _enrich(db: Session, events: list[Event]) -> list[dict]:
    regions = _map(db, Region, {e.region_id for e in events})
    units = _map(db, Unit, {e.unit_id for e in events})
    armories = _map(db, Armory, {e.armory_id for e in events})
    cabinets = _map(db, Cabinet, {e.cabinet_id for e in events})
    officers = _map(db, Officer, {e.officer_id for e in events})
    items = _map(db, Item, {e.item_id for e in events})
    alarms: dict[int, int] = {}
    ev_ids = [e.id for e in events]
    for i in range(0, len(ev_ids), 900):
        for eid, aid in db.execute(select(Alarm.event_id, Alarm.id).where(Alarm.event_id.in_(ev_ids[i:i + 900]))):
            alarms[eid] = aid
    rows = []
    for e in events:
        rows.append({
            "ev": e, "region": regions.get(e.region_id), "unit": units.get(e.unit_id), "armory": armories.get(e.armory_id),
            "cabinet": cabinets.get(e.cabinet_id), "officer": officers.get(e.officer_id), "item": items.get(e.item_id),
            "alarm_id": alarms.get(e.id), "type_label": TYPE_LABEL.get(e.type, e.type), "level_label": LEVEL_LABEL.get(e.level, e.level),
            "reason_label": REASON_LABEL.get(e.reason, e.reason), "result_label": RESULT_LABEL.get(e.result, e.result),
            "method_label": METHOD_LABEL.get(e.method, e.method),
        })
    return rows


def _page(db: Session, conds: list, page: int, per_page: int = PER_PAGE) -> tuple[list[Event], int, int, int]:
    total = db.scalar(select(func.count(Event.id)).where(*conds)) or 0
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    q = select(Event).where(*conds).order_by(Event.ts_server.desc(), Event.id.desc()).offset((page - 1) * per_page).limit(per_page)
    return db.execute(q).scalars().all(), total, pages, page


def _level_counts(db: Session, conds: list) -> dict[str, int]:
    out = {lv: 0 for lv in LEVELS}
    for lv, n in db.execute(select(Event.level, func.count(Event.id)).where(*conds).group_by(Event.level)):
        out[lv] = n
    return out


def _armory_options(db: Session, ctx: Ctx, region_id: int) -> list[Armory]:
    if not region_id:
        return []
    q = select(Armory).join(Unit, Unit.id == Armory.unit_id).where(Unit.region_id == region_id).order_by(Unit.name)
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    if ids is not None:
        q = q.where(Armory.id.in_(ids))
    return db.execute(q).scalars().all()


def _type_options() -> list[tuple[str, str]]:
    return sorted(((k, v) for k, v in TYPE_LABEL.items()), key=lambda kv: kv[1])


def _armory_in_scope(db: Session, ctx: Ctx, armory_id: int | None) -> bool:
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    return ids is None or armory_id in ids


def _filter_summary(db: Session, f: dict) -> list[tuple[str, str]]:
    """Faol filtrlar ro'yxati (eksport sahifasi va yozuvi uchun)."""
    out = []
    if f["dan"] or f["gacha"]:
        out.append(("Sana oralig'i", f"{f['dan'] or '…'} — {f['gacha'] or '…'}"))
    if f["hudud"]:
        r = db.get(Region, f["hudud"]); out.append(("Hudud", r.name if r else str(f["hudud"])))
    if f["bolinma"]:
        u = db.get(Unit, f["bolinma"]); out.append(("Bo'linma", u.name if u else str(f["bolinma"])))
    if f["qurolxona"]:
        a = db.get(Armory, f["qurolxona"]); out.append(("Qurolxona", a.name if a else str(f["qurolxona"])))
    if f["tur"]:
        out.append(("Tur", TYPE_GROUPS[f["tur"]][0] if f["tur"] in TYPE_GROUPS else TYPE_LABEL.get(f["tur"], f["tur"])))
    if f["daraja"]:
        out.append(("Daraja", LEVEL_LABEL.get(f["daraja"], f["daraja"])))
    if f["xodim"]:
        out.append(("Xodim", f["xodim"]))
    if f["yacheyka"]:
        out.append(("Yacheyka", f["yacheyka"]))
    if f["oflayn"]:
        out.append(("Oflayn", "faqat oflayn yozilgan hodisalar"))
    return out


def _list_context(db: Session, ctx: Ctx, f: dict) -> dict:
    conds = _conditions(db, ctx, f)
    events, total, pages, page = _page(db, conds, f["page"])
    f["page"] = page
    return {"rows": _enrich(db, events), "total": total, "pages": pages, "page": page, "f": f, "qlink": _linker(f),
            "counts": _level_counts(db, conds), "per_page": PER_PAGE, "base": "/jurnal", "error": _filter_error(f)}


# ---------------- ro'yxat ----------------
@router.get("/jurnal")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), dan: str = "", gacha: str = "",
              hudud: str = "", qurolxona: str = "", bolinma: str = "", tur: str = "", daraja: str = "", xodim: str = "",
              yacheyka: str = "", oflayn: str = "", page: str = "1"):
    from ..main import render
    f = _filters(dan, gacha, hudud, qurolxona, bolinma, tur, daraja, xodim, yacheyka, oflayn, page)
    c = _list_context(db, ctx, f)
    return render(request, "jurnal/list.html", ctx, active="jurnal", breadcrumb=[("Jurnal", "/jurnal")], title="Hodisalar jurnali",
                  groups=TYPE_GROUPS, type_options=_type_options(), levels=LEVELS, level_label=LEVEL_LABEL,
                  armory_options=_armory_options(db, ctx, f["hudud"]), can_export=ctx.can("eksport"), tab="jurnal", **c)


@router.get("/jurnal/partials/jadval")
def p_table(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), dan: str = "", gacha: str = "",
            hudud: str = "", qurolxona: str = "", bolinma: str = "", tur: str = "", daraja: str = "", xodim: str = "",
            yacheyka: str = "", oflayn: str = "", page: str = "1"):
    from ..main import render
    f = _filters(dan, gacha, hudud, qurolxona, bolinma, tur, daraja, xodim, yacheyka, oflayn, page)
    return render(request, "jurnal/_table.html", ctx, level_label=LEVEL_LABEL, **_list_context(db, ctx, f))


# ---------------- favqulodda tab ----------------
@router.get("/jurnal/favqulodda")
def emergency_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), dan: str = "", gacha: str = "",
                   hudud: str = "", tur: str = "", page: str = "1"):
    from ..main import render
    tur = tur if tur in ("favqulodda_ochish", "mexanik_kalit") else "favqulodda"
    f = _filters(dan=dan, gacha=gacha, hudud=hudud, tur=tur, page=page)
    conds = _conditions(db, ctx, f)
    events, total, pages, page_n = _page(db, conds, f["page"])
    f["page"] = page_n
    now = datetime.now()
    scope_conds = _conditions(db, ctx, _filters())
    scope_ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    alarm_conds = [] if scope_ids is None else [Alarm.armory_id.in_(scope_ids)]
    base_q = select(func.count(Event.id)).where(*scope_conds)
    stats = {
        "favqulodda_30": db.scalar(base_q.where(Event.type == "favqulodda_ochish", Event.ts_server >= now - timedelta(days=30))) or 0,
        "mexanik_30": db.scalar(base_q.where(Event.type == "mexanik_kalit", Event.ts_server >= now - timedelta(days=30))) or 0,
        "jami": db.scalar(base_q.where(Event.type.in_(TYPE_GROUPS["favqulodda"][1]))) or 0,
        "tasdiq_kutmoqda": db.scalar(select(func.count(Alarm.id)).where(*alarm_conds, Alarm.type.in_(["favqulodda", "mexanik_kalit"]),
                                                                        Alarm.resolved_at.is_(None), Alarm.acked_at.is_(None))) or 0,
    }
    return render(request, "jurnal/favqulodda.html", ctx, active="jurnal", breadcrumb=[("Jurnal", "/jurnal"), ("Favqulodda", "")],
                  title="Favqulodda ochilishlar", rows=_enrich(db, events), total=total, pages=pages, page=page_n, f=f,
                  qlink=_linker(f), base="/jurnal/favqulodda", stats=stats, tab="favqulodda", level_label=LEVEL_LABEL,
                  can_export=ctx.can("eksport"), error=_filter_error(f))


# ---------------- yaxlitlik ----------------
@router.get("/jurnal/yaxlitlik")
def integrity_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), yacheyka: str = ""):
    from ..main import render
    cab: Cabinet | None = None
    y = yacheyka.strip()
    error = ""
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    if y:
        if y.isdigit() and len(y) < 10:
            cab = db.get(Cabinet, int(y))
        if cab is None:
            candidates = select(Cabinet).where(or_(Cabinet.label == y, Cabinet.serial == y))
            if ids is not None:
                candidates = candidates.where(Cabinet.armory_id.in_(ids))
            matches = db.execute(candidates.order_by(Cabinet.id).limit(2)).scalars().all()
            if len(matches) == 1:
                cab = matches[0]
            elif matches:
                error = "Bu yorliq bir nechta yacheykada bor. Aniq ID yoki seriya raqamini kiriting."
        if cab is None and not error:
            error = "Yacheyka topilmadi. ID, to'liq yorliq yoki seriya raqamini tekshiring."
        if cab is not None and not _armory_in_scope(db, ctx, cab.armory_id):
            raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    conds = [Event.cabinet_id == cab.id] if cab else ([] if ids is None else [Event.armory_id.in_(ids)])
    total_events = db.scalar(select(func.count(Event.id)).where(*conds)) or 0
    t0 = time.perf_counter()
    res = None
    if not error:
        if cab or ids is None:
            res = verify_chain(db, cab.id if cab else None, limit=max(total_events, 1))
        else:
            # The shared cabinet-less stream spans armories. Verify each visible record
            # against its actual predecessor without disclosing adjacent records.
            visible = db.execute(select(Event).where(*conds).order_by(Event.id)).scalars().all()
            visible_ids = {ev.id for ev in visible}
            predecessors, previous = {}, {}
            for eid, stream, stored_hash in db.execute(select(Event.id, Event.cabinet_id, Event.hash).order_by(Event.id)):
                if eid in visible_ids:
                    predecessors[eid] = previous.get(stream, "")
                previous[stream] = stored_hash
            broken = []
            for ev in visible:
                body = {"type": ev.type, "ts": ev.ts_device.isoformat(), "cab": ev.cabinet_id, "arm": ev.armory_id,
                        "off": ev.officer_id, "item": ev.item_id, "method": ev.method, "result": ev.result,
                        "reason": ev.reason, "payload": ev.payload or {}}
                expected = predecessors[ev.id]
                if ev.prev_hash != expected or ev.hash != _chain_hash(expected, body):
                    broken.append(ev.id)
            res = {"checked": len(visible), "broken": len(broken), "first_broken": broken[0] if broken else None, "ok": not broken}
        res["ms"] = int((time.perf_counter() - t0) * 1000)
    first = db.get(Event, res["first_broken"]) if res and res.get("first_broken") else None
    streams = len(db.execute(select(Event.cabinet_id).where(*conds).distinct()).all())
    last_ev = db.execute(select(Event).where(*conds).order_by(Event.id.desc()).limit(1)).scalars().first()
    return render(request, "jurnal/yaxlitlik.html", ctx, active="jurnal", breadcrumb=[("Jurnal", "/jurnal"), ("Yaxlitlik", "")],
                  title="Jurnal yaxlitligi", res=res, cab=cab, first=first, streams=streams, total_events=total_events,
                  last_ev=last_ev, yacheyka=y, tab="yaxlitlik", checked_at=datetime.now(), can_export=ctx.can("eksport"),
                  error=error, scoped=ids is not None)


# ---------------- eksport ----------------
def _export_path(log: ExportLog):
    return EXPORT_DIR / f"{log.number}.csv"


def _csv_safe(value):
    """Keep spreadsheet programs from executing user-provided cells as formulas."""
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))):
        return "'" + value
    return value


def _export_event(db: Session, log: ExportLog) -> Event | None:
    return db.execute(select(Event).where(Event.type == "eksport_qilindi", Event.detail.like(f"{log.number} ·%"))
                      .order_by(Event.id.desc()).limit(1)).scalars().first()


def _export_visible(db: Session, ctx: Ctx, log: ExportLog, ev: Event | None) -> bool:
    if not ctx.can("eksport"):
        return False
    ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    if ids is None:
        return True
    arms = (ev.payload or {}).get("armory_ids") if ev else None
    if isinstance(arms, list):
        return bool(arms) and set(arms).issubset(set(ids))
    # Historical exports predate scope snapshots; only their creator can view them.
    return bool(ctx.user and log.username == ctx.user.username)


def _export_context(db: Session, ctx: Ctx, f: dict) -> dict:
    recent = []
    for log in db.execute(select(ExportLog).where(ExportLog.report == "jurnal").order_by(ExportLog.id.desc())).scalars():
        if _export_visible(db, ctx, log, _export_event(db, log)):
            recent.append(log)
        if len(recent) == 10:
            break
    return {"f": f, "qlink": _linker(f), "total": db.scalar(select(func.count(Event.id)).where(*_conditions(db, ctx, f))) or 0,
            "limit": EXPORT_LIMIT, "summary": _filter_summary(db, f), "days": EXPORT_DAYS, "recent": recent,
            "tab": "eksport", "now": datetime.now(), "can_export": True}


def _csv_rows(db: Session, conds: list):
    q = select(Event).where(*conds).order_by(Event.ts_server.desc(), Event.id.desc()).limit(EXPORT_LIMIT)
    events = db.execute(q).scalars().all()
    rows = _enrich(db, events)
    head = ["id", "seq", "ts_device", "ts_server", "daraja", "tur", "tur_nomi", "hudud", "bolinma", "qurolxona", "yacheyka",
            "yacheyka_serial", "xodim", "tabel", "jihoz", "usul", "natija", "sabab", "urinishlar", "tasdiqlovchi1", "tasdiqlovchi2",
            "oflayn", "simulyatsiya", "sarlavha", "tafsilot", "payload", "prev_hash", "hash"]
    yield head
    for r in rows:
        e = r["ev"]
        yield [e.id, e.seq, e.ts_device.isoformat(sep=" "), e.ts_server.isoformat(sep=" "), e.level, e.type, r["type_label"],
               r["region"].name if r["region"] else "", r["unit"].name if r["unit"] else "", r["armory"].name if r["armory"] else "",
               r["cabinet"].label if r["cabinet"] else "", r["cabinet"].serial if r["cabinet"] else "",
               r["officer"].full_name if r["officer"] else "", r["officer"].tabel if r["officer"] else "",
               f"{r['item'].model} {r['item'].serial}".strip() if r["item"] else "", e.method, e.result, e.reason, e.attempts,
               e.approver1, e.approver2, "1" if e.offline else "0", "1" if e.simulated else "0", e.title, e.detail,
               json.dumps(e.payload or {}, ensure_ascii=False, sort_keys=True), e.prev_hash, e.hash]


@router.get("/jurnal/eksport")
def export_form(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), dan: str = "", gacha: str = "",
                hudud: str = "", qurolxona: str = "", bolinma: str = "", tur: str = "", daraja: str = "", xodim: str = "",
                yacheyka: str = "", oflayn: str = ""):
    from ..main import render
    if not ctx.can("eksport"):
        raise HTTPException(status_code=403, detail="Eksport huquqi yo'q")
    f = _filters(dan, gacha, hudud, qurolxona, bolinma, tur, daraja, xodim, yacheyka, oflayn)
    return render(request, "jurnal/eksport.html", ctx, active="jurnal", breadcrumb=[("Jurnal", "/jurnal"), ("Eksport", "")],
                  title="Jurnal eksporti", error=_filter_error(f), purpose="", valid_days="30", **_export_context(db, ctx, f))


@router.post("/jurnal/eksport")
def export_post(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), maqsad: str = Form(""),
                muddat: str = Form("30"), dan: str = Form(""), gacha: str = Form(""), hudud: str = Form(""), qurolxona: str = Form(""),
                bolinma: str = Form(""), tur: str = Form(""), daraja: str = Form(""), xodim: str = Form(""), yacheyka: str = Form(""),
                oflayn: str = Form("")):
    if not ctx.can("eksport"):
        raise HTTPException(status_code=403, detail="Eksport huquqi yo'q")
    f = _filters(dan, gacha, hudud, qurolxona, bolinma, tur, daraja, xodim, yacheyka, oflayn)
    purpose = maqsad.strip()[:200]
    error = _filter_error(f)
    if len(purpose) < 5:
        error = "Eksport maqsadini kamida 5 belgi bilan kiriting."
    days = int(muddat) if muddat in EXPORT_DAYS else 30
    conds = _conditions(db, ctx, f)
    total = db.scalar(select(func.count(Event.id)).where(*conds)) or 0
    if not error and not total:
        error = "Eksport uchun hodisa topilmadi. Filtrlarni o'zgartiring."
    if not error and total > EXPORT_LIMIT:
        error = f"Eksport chegarasi {EXPORT_LIMIT} ta hodisa. Filtrlar bilan ro'yxatni qisqartiring."
    if error:
        from ..main import render
        return render(request, "jurnal/eksport.html", ctx, active="jurnal", breadcrumb=[("Jurnal", "/jurnal"), ("Eksport", "")],
                      title="Jurnal eksporti", error=error, purpose=purpose, valid_days=str(days), **_export_context(db, ctx, f))
    now = datetime.now().replace(microsecond=0)
    username = ctx.user.username if ctx.user else "mehmon"
    # fayl
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    n = -1
    for row in _csv_rows(db, conds):
        w.writerow([_csv_safe(value) for value in row]); n += 1
    data = ("﻿" + buf.getvalue()).encode("utf-8")  # BOM: Excel UTF-8 ni to'g'ri ochishi uchun
    file_hash = hashlib.sha256(data).hexdigest()
    # ExportLog yozuvi (raqam id asosida)
    log = ExportLog(number="", username=username, report="jurnal", fmt="csv", purpose=purpose, valid_until=now + timedelta(days=days),
                    ts=now, file_hash=file_hash)
    db.add(log); db.flush()
    log.number = f"E-{now.year}-{log.id:06d}"
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    _export_path(log).write_bytes(data)
    ev = record_event(db, "eksport_qilindi", approver1=username, method="PANEL", title="Jurnal eksport qilindi (CSV)",
                      detail=f"{log.number} · {n} qator · {username} · {purpose[:80]}", simulated=False,
                      payload={"number": log.number, "rows": n, "fmt": "csv", "purpose": purpose, "valid_until": log.valid_until.isoformat(),
                               "file_hash": file_hash, "filters": {k: v for k, v in f.items() if v and k != "page"}, "user": username,
                               "armory_ids": list(db.scalars(select(Event.armory_id).where(*conds).distinct()))})
    db.commit()
    _notify(ev)
    return RedirectResponse(f"/jurnal/eksport/{log.id}", status_code=303)


@router.get("/jurnal/eksport/{export_id}")
def export_detail(export_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    log = db.get(ExportLog, export_id)
    if log is None or log.report != "jurnal":
        raise HTTPException(status_code=404, detail="Eksport yozuvi topilmadi")
    ev = _export_event(db, log)
    if not _export_visible(db, ctx, log, ev):
        raise HTTPException(status_code=403, detail="Eksport vakolat doirasidan tashqarida")
    path = _export_path(log)
    file_ok = path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == log.file_hash
    now = datetime.now()
    expired = bool(log.valid_until and log.valid_until < now)
    return render(request, "jurnal/eksport_detail.html", ctx, active="jurnal",
                  breadcrumb=[("Jurnal", "/jurnal"), ("Eksport", "/jurnal/eksport"), (log.number, "")], title="Eksport " + log.number,
                  log=log, ev=ev, exists=path.exists(), size_kb=(path.stat().st_size // 1024 + 1) if path.exists() else 0,
                  expired=expired, tab="eksport", now=now, can_export=ctx.can("eksport"), file_ok=file_ok,
                  summary=_filter_summary(db, _filters(**{k: v for k, v in ((ev.payload or {}).get("filters", {}) if ev else {}).items()
                                                          if k in _filters()})),
                  event_visible=bool(ev and _armory_in_scope(db, ctx, ev.armory_id)))


@router.get("/jurnal/eksport/{export_id}/fayl")
def export_file(export_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    if not ctx.can("eksport"):
        raise HTTPException(status_code=403, detail="Eksport huquqi yo'q")
    log = db.get(ExportLog, export_id)
    if log is None or log.report != "jurnal":
        raise HTTPException(status_code=404, detail="Eksport yozuvi topilmadi")
    if not _export_visible(db, ctx, log, _export_event(db, log)):
        raise HTTPException(status_code=403, detail="Eksport vakolat doirasidan tashqarida")
    if log.valid_until and log.valid_until < datetime.now():
        raise HTTPException(status_code=410, detail="Eksport amal qilish muddati tugagan")
    path = _export_path(log)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    if hashlib.sha256(path.read_bytes()).hexdigest() != log.file_hash:
        raise HTTPException(status_code=409, detail="Eksport fayli hash qiymati mos emas")
    return FileResponse(str(path), media_type="text/csv; charset=utf-8", filename=f"jurnal_{log.number}.csv")


# ---------------- batafsil ----------------
@router.get("/jurnal/{event_id}")
def detail_page(event_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    ev = db.get(Event, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Hodisa topilmadi")
    if not _armory_in_scope(db, ctx, ev.armory_id):
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    body = {"type": ev.type, "ts": ev.ts_device.isoformat(), "cab": ev.cabinet_id, "arm": ev.armory_id, "off": ev.officer_id,
            "item": ev.item_id, "method": ev.method, "result": ev.result, "reason": ev.reason, "payload": ev.payload or {}}
    hash_ok = ev.hash == _chain_hash(ev.prev_hash, body)
    stream = Event.cabinet_id == ev.cabinet_id if ev.cabinet_id is not None else Event.cabinet_id.is_(None)
    prev_ev = db.execute(select(Event).where(stream, Event.id < ev.id).order_by(Event.id.desc()).limit(1)).scalars().first()
    next_ev = db.execute(select(Event).where(stream, Event.id > ev.id).order_by(Event.id.asc()).limit(1)).scalars().first()
    link_ok = (prev_ev.hash == ev.prev_hash) if prev_ev else (ev.prev_hash == "")
    before = db.execute(select(Event).where(stream, Event.id < ev.id).order_by(Event.id.desc()).limit(5)).scalars().all()
    after = db.execute(select(Event).where(stream, Event.id > ev.id).order_by(Event.id.asc()).limit(5)).scalars().all()
    scope_ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    neighbors = list(reversed(before)) + [ev] + after
    around = _enrich(db, [item for item in neighbors if scope_ids is None or item.armory_id in scope_ids])
    row = _enrich(db, [ev])[0]
    rule = EVENT_RULES.get(ev.type)
    return render(request, "jurnal/detail.html", ctx, active="jurnal",
                  breadcrumb=[("Jurnal", "/jurnal"), (f"Hodisa #{ev.id}", "")], title=f"Hodisa #{ev.id}", r=row, ev=ev,
                  hash_ok=hash_ok, link_ok=link_ok, prev_ev=prev_ev, next_ev=next_ev, around=around,
                  payload_json=json.dumps(ev.payload or {}, ensure_ascii=False, indent=2, sort_keys=True), rule=rule,
                  level_label=LEVEL_LABEL, type_label=TYPE_LABEL, tab="jurnal", can_export=ctx.can("eksport"))

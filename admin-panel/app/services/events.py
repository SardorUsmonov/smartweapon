"""Hodisalar: append-only jurnal, hash zanjiri, signal yaratish qoidalari."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alarm, Armory, Cabinet, Event, Officer, Unit

# hodisa turi -> (daraja, signal yaratadimi, signal turi, tasdiq talab qiladimi)
EVENT_RULES: dict[str, tuple[str, bool, str, bool]] = {
    "auth_ok": ("INFO", False, "", False),
    "rad_etildi": ("WARNING", False, "", False),
    "rad_etildi_takror": ("CRITICAL", True, "takroriy_rad", True),
    "qulf_ochildi": ("INFO", False, "", False),
    "eshik_ochildi": ("INFO", False, "", False),
    "eshik_yopildi": ("INFO", False, "", False),
    "avtomatik_qulflandi": ("INFO", False, "", False),
    "avtomat_olindi": ("INFO", False, "", False),
    "avtomat_qaytarildi": ("INFO", False, "", False),
    "pm_olindi": ("INFO", False, "", False),
    "pm_qaytarildi": ("INFO", False, "", False),
    "qaytarish_nomuvofiq": ("CRITICAL", True, "nomuvofiqlik", True),
    "kechikish": ("WARNING", True, "kechikish", False),
    "eshik_ochiq_qoldi": ("WARNING", True, "eshik_ochiq", False),
    "urilish": ("CRITICAL", True, "urilish", True),
    "buzish_urinishi": ("CRITICAL", True, "tamper", True),
    "lyuk_ochildi": ("WARNING", True, "lyuk", False),
    "quvvat_uzildi": ("WARNING", True, "quvvat", False),
    "quvvat_tiklandi": ("INFO", False, "", False),
    "batareya_past": ("WARNING", True, "batareya", False),
    "aloqa_uzildi": ("CRITICAL", True, "oflayn", False),
    "aloqa_tiklandi": ("INFO", False, "", False),
    "sinxronlandi": ("INFO", False, "", False),
    "mexanik_kalit": ("SECURITY", True, "mexanik_kalit", True),
    "favqulodda_ochish": ("SECURITY", True, "favqulodda", True),
    "rejim_boshlandi": ("SECURITY", False, "", False),
    "rejim_tugadi": ("INFO", False, "", False),
    "shkaf_bloklandi": ("SECURITY", False, "", False),
    "shkaf_blokdan_chiqdi": ("INFO", False, "", False),
    "biriktirildi": ("INFO", False, "", False),
    "ajratildi": ("INFO", False, "", False),
    "smena_ochildi": ("INFO", False, "", False),
    "smena_yopildi": ("INFO", False, "", False),
    "oz_tekshiruv_xato": ("CRITICAL", True, "oz_tekshiruv", True),
    "qulf_xatosi": ("CRITICAL", True, "qulf_xatosi", True),
    "datchik_xatosi": ("CRITICAL", True, "datchik_xatosi", False),
    "disk_toldi": ("WARNING", True, "disk", False),
    "kamera_oqimi_uzildi": ("CRITICAL", True, "kamera", False),
    "kamera_oqimi_tiklandi": ("INFO", False, "", False),
    "vaqt_sinxroni_buzildi": ("CRITICAL", True, "ntp", False),
    "server_yoq_rejimi": ("WARNING", True, "server_yoq", False),
    "huquq_berish_tasdiqlandi": ("SECURITY", False, "", False),
    "eksport_qilindi": ("SECURITY", False, "", False),
    "zaxira_nusxa": ("INFO", False, "", False),
    "zaxira_nusxa_xato": ("WARNING", True, "zaxira", False),
    "texnik_xizmat": ("INFO", False, "", False),
    "inventarizatsiya": ("INFO", False, "", False),
    "sozlama_ozgardi": ("SECURITY", False, "", False),
}

LEVEL_LABEL = {"INFO": "AXBOROT", "WARNING": "OGOHLANTIRISH", "CRITICAL": "SIGNAL", "SECURITY": "XAVFSIZLIK"}
ALARM_BADGE = {"tamper": "TREVOGA", "urilish": "TREVOGA", "oflayn": "OFLAYN", "favqulodda": "FAVQULODDA",
               "mexanik_kalit": "MEXANIK", "kechikish": "KECHIKISH"}


def _chain_hash(prev_hash: str, payload: dict) -> str:
    raw = prev_hash + "|" + json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def last_hash(db: Session, cabinet_id: int | None) -> tuple[str, int]:
    """Yacheyka oqimi bo'yicha oxirgi hash va tartib raqami."""
    q = select(Event.hash, Event.seq).order_by(Event.id.desc()).limit(1)
    if cabinet_id is not None:
        q = q.where(Event.cabinet_id == cabinet_id)
    else:
        q = q.where(Event.cabinet_id.is_(None))
    row = db.execute(q).first()
    return (row[0], row[1]) if row else ("", 0)


def record_event(db: Session, type_: str, *, cabinet: Cabinet | None = None, armory: Armory | None = None,
                 officer: Officer | None = None, item_id: int | None = None, ts: datetime | None = None,
                 method: str = "", result: str = "ok", reason: str = "", attempts: int = 0,
                 approver1: str = "", approver2: str = "", offline: bool = False, title: str = "",
                 detail: str = "", payload: dict | None = None, simulated: bool = True,
                 make_alarm: bool | None = None, level: str | None = None) -> Event:
    rule = EVENT_RULES.get(type_, ("INFO", False, "", False))
    lvl = level or rule[0]
    now = datetime.now().replace(microsecond=0)
    ts_device = ts or now
    if armory is None and cabinet is not None:
        armory = cabinet.armory
    unit: Unit | None = armory.unit if armory is not None else None
    region_id = unit.region_id if unit is not None else None
    prev, seq = last_hash(db, cabinet.id if cabinet else None)
    body = {
        "type": type_, "ts": ts_device.isoformat(), "cab": cabinet.id if cabinet else None,
        "arm": armory.id if armory else None, "off": officer.id if officer else None, "item": item_id,
        "method": method, "result": result, "reason": reason, "payload": payload or {},
    }
    ev = Event(
        seq=seq + 1, ts_device=ts_device, ts_server=ts_device if ts else now, type=type_, level=lvl,
        region_id=region_id, unit_id=unit.id if unit else None, armory_id=armory.id if armory else None,
        cabinet_id=cabinet.id if cabinet else None, officer_id=officer.id if officer else None, item_id=item_id,
        method=method, result=result, reason=reason, attempts=attempts, approver1=approver1, approver2=approver2,
        offline=offline, simulated=simulated, title=title or type_, detail=detail, payload=payload or {},
        prev_hash=prev, hash=_chain_hash(prev, body),
    )
    db.add(ev)
    db.flush()
    want_alarm = rule[1] if make_alarm is None else make_alarm
    if want_alarm:
        db.add(Alarm(event_id=ev.id, level=lvl, type=rule[2] or type_, region_id=region_id,
                     unit_id=unit.id if unit else None, armory_id=armory.id if armory else None,
                     cabinet_id=cabinet.id if cabinet else None, title=ev.title, detail=detail,
                     opened_at=ev.ts_server, requires_ack=rule[3], forwarded=lvl in ("CRITICAL", "SECURITY")))
    return ev


def verify_chain(db: Session, cabinet_id: int | None = None, limit: int = 100000) -> dict:
    """Hash zanjirini qayta hisoblab tekshiradi."""
    q = select(Event).order_by(Event.id.asc()).limit(limit)
    if cabinet_id is not None:
        q = q.where(Event.cabinet_id == cabinet_id)
    prev_by_stream: dict[int | None, str] = {}
    checked = broken = 0
    first_broken = None
    for ev in db.execute(q).scalars():
        key = ev.cabinet_id
        expected_prev = prev_by_stream.get(key, "")
        body = {"type": ev.type, "ts": ev.ts_device.isoformat(), "cab": ev.cabinet_id, "arm": ev.armory_id,
                "off": ev.officer_id, "item": ev.item_id, "method": ev.method, "result": ev.result,
                "reason": ev.reason, "payload": ev.payload or {}}
        ok = ev.prev_hash == expected_prev and ev.hash == _chain_hash(expected_prev, body)
        checked += 1
        if not ok:
            broken += 1
            first_broken = first_broken or ev.id
        prev_by_stream[key] = ev.hash
    return {"checked": checked, "broken": broken, "first_broken": first_broken, "ok": broken == 0}


def overdue_threshold(now: datetime) -> datetime:
    return now


def default_due(taken_at: datetime) -> datetime:
    """Qaytarish muddati: navbat oxiri + 30 daqiqa (taxmin №4); demo: 12 soat."""
    return taken_at + timedelta(hours=12, minutes=30)

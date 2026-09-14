"""Simulyator: apparat o'rnida yacheyka va qurolxona hodisalarini hosil qiladi (01 §2.5 ssenariysi)."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alarm, Armory, Cabinet, Custody, Eligibility, Item, Mode, Officer
from .events import record_event
from .live import hub

R = random.Random()

TERMINAL_TEXT = {
    "idle": ("Yuzingizni kameraga", "qarating"), "face": ("Yuz tanilmoqda…", ""), "finger": ("Barmoq izini", "beshikka qo'ying"),
    "ok": ("Ruxsat", "Chapga qadam qo'ying, eshikni oching"), "open": ("Eshik ochiq", "Yopilganda avtomatik qulflanadi"),
    "lock": ("Qulflandi", ""), "denied": ("Rad etildi", "Navbatchiga murojaat qiling"), "blocked": ("Yacheyka bloklangan", ""),
}


def _notify(ev, cab: Cabinet | None = None, armory: Armory | None = None):
    hub.broadcast_threadsafe({"type": "event", "event_type": ev.type, "level": ev.level, "cabinet_id": cab.id if cab else None,
                              "armory_id": armory.id if armory else (cab.armory_id if cab else None), "title": ev.title, "ts": ev.ts_server.isoformat()})


def _label(cab: Cabinet) -> str:
    a = cab.armory
    return f"{a.unit.region.short} · {a.unit.name} · {cab.label}"


def _take_restriction(db: Session, cab: Cabinet, off: Officer | None, item: Item | None,
                      weapon: str, now: datetime) -> tuple[str, str] | None:
    """Reject restricted demo issuance before changing any lock or custody state."""
    from .smena_svc import ELIG_LABEL

    if cab.status != "biriktirilgan" or off is None:
        return ("cabinet_blocked" if cab.status == "bloklangan" else "no_permit",
                "yacheyka biriktirilmagan yoki bloklangan")
    if off.service_status != "faol":
        return "service_inactive", "xodimning xizmat holati faol emas"
    if off.valid_until and off.valid_until < now:
        return "authority_expired", "xodim vakolatining muddati o'tgan"
    if weapon not in ("avtomat", "to'pponcha") or not (off.permit_ak if weapon == "avtomat" else off.permit_pm):
        return "no_permit", "tanlangan qurol uchun ruxsat yo'q"
    if item is None or item.state != "mavjud":
        return "item_unavailable", "tanlangan jihoz uyada mavjud emas"
    if item.hold:
        return "item_hold", "tanlangan jihoz ushlab turilgan"
    eligibility = db.scalars(select(Eligibility).where(Eligibility.officer_id == off.id)).all()
    if not set(ELIG_LABEL).issubset({row.kind for row in eligibility}):
        return "eligibility_missing", "yaroqlilik yozuvlari to'liq emas"
    if any(not row.ok for row in eligibility):
        return "eligibility_invalid", "yaroqlilik sharti tasdiqlanmagan"
    if any(row.valid_until and row.valid_until < now for row in eligibility):
        return "eligibility_expired", "yaroqlilik shartining muddati o'tgan"
    return None


def cabinet_take(db: Session, cab: Cabinet, method: str = "YUZ+BARMOQ", weapon: str = "avtomat") -> list:
    """To'liq olish ssenariysi: auth, qulf, eshik, olish, eshik yopish, avtomatik qulf."""
    off = db.get(Officer, cab.officer_id) if cab.officer_id else None
    out = []
    now = datetime.now().replace(microsecond=0)
    item = db.execute(select(Item).where(Item.cabinet_id == cab.id, Item.category == weapon).order_by(Item.id)).scalars().first()
    restriction = _take_restriction(db, cab, off, item, weapon, now)
    if restriction:
        reason, detail = restriction
        ev = record_event(db, "rad_etildi", cabinet=cab, officer=off, item_id=item.id if item else None,
                          method=method, result="rad", reason=reason, title="Kirish rad etildi",
                          detail=_label(cab) + " · " + detail, level="WARNING", make_alarm=False,
                          payload={"manba": "simulyator", "qurol": weapon, "cheklov": reason})
        cab.terminal_state = "denied"; out.append(ev); _notify(ev, cab); return out
    ev = record_event(db, "auth_ok", cabinet=cab, officer=off, method=method, title="Kirish tasdiqlandi", detail=_label(cab) + " · " + method); out.append(ev)
    out.append(record_event(db, "qulf_ochildi", cabinet=cab, officer=off, title="Qulf ochildi", detail=_label(cab)))
    cab.door_locked = False; cab.door_open = True; cab.terminal_state = "open"
    out.append(record_event(db, "eshik_ochildi", cabinet=cab, officer=off, title="Eshik ochildi", detail=_label(cab)))
    if item and item.state == "mavjud":
        typ = "avtomat_olindi" if weapon == "avtomat" else "pm_olindi"
        ev = record_event(db, typ, cabinet=cab, officer=off, item_id=item.id, title=("Avtomat olindi" if weapon == "avtomat" else "To'pponcha olindi"),
                          detail=_label(cab) + f" · {item.model} {item.serial}"); out.append(ev)
        item.state = "yo'q"
        if weapon == "avtomat":
            cab.ak_present = False; cab.ak_clamp_locked = False
        else:
            cab.pm_present = False; cab.pm_box_locked = False
        db.add(Custody(item_id=item.id, officer_id=off.id, cabinet_id=cab.id, taken_at=now, due_at=now + timedelta(hours=12, minutes=30)))
    cab.door_open = False; cab.door_locked = True; cab.terminal_state = "lock"
    out.append(record_event(db, "eshik_yopildi", cabinet=cab, officer=off, title="Eshik yopildi", detail=_label(cab)))
    ev = record_event(db, "avtomatik_qulflandi", cabinet=cab, officer=off, title="Avtomatik qulflandi", detail=_label(cab)); out.append(ev)
    _notify(ev, cab)
    return out


def cabinet_return(db: Session, cab: Cabinet, method: str = "YUZ+BARMOQ", mismatch: bool = False) -> list:
    off = db.get(Officer, cab.officer_id) if cab.officer_id else None
    out = []
    if off is None:
        return out
    now = datetime.now().replace(microsecond=0)
    out.append(record_event(db, "auth_ok", cabinet=cab, officer=off, method=method, title="Kirish tasdiqlandi", detail=_label(cab) + " · qaytarish"))
    cab.door_locked = False; cab.door_open = True; cab.terminal_state = "open"
    out.append(record_event(db, "eshik_ochildi", cabinet=cab, officer=off, title="Eshik ochildi", detail=_label(cab)))
    open_c = db.execute(select(Custody).where(Custody.cabinet_id == cab.id, Custody.returned_at.is_(None)).order_by(Custody.taken_at)).scalars().all()
    for c in open_c:
        item = db.get(Item, c.item_id)
        c.returned_at = now; c.match_ok = not mismatch
        if item:
            item.state = "mavjud"
            typ = "avtomat_qaytarildi" if item.category == "avtomat" else "pm_qaytarildi"
            out.append(record_event(db, typ, cabinet=cab, officer=off, item_id=item.id, title=("Avtomat qaytarildi" if item.category == "avtomat" else "To'pponcha qaytarildi"),
                                    detail=_label(cab) + f" · {item.model} {item.serial}", result="ok" if not mismatch else "nomuvofiq"))
            if item.category == "avtomat":
                cab.ak_present = True; cab.ak_clamp_locked = True
            else:
                cab.pm_present = True; cab.pm_box_locked = True
    if mismatch:
        out.append(record_event(db, "qaytarish_nomuvofiq", cabinet=cab, officer=off, title="Qaytarish nomuvofiq", detail=_label(cab) + " · RFID biriktirilgan qurolga mos emas"))
    cab.door_open = False; cab.door_locked = True; cab.terminal_state = "lock"
    out.append(record_event(db, "eshik_yopildi", cabinet=cab, officer=off, title="Eshik yopildi", detail=_label(cab)))
    ev = record_event(db, "avtomatik_qulflandi", cabinet=cab, officer=off, title="Avtomatik qulflandi", detail=_label(cab)); out.append(ev)
    _notify(ev, cab)
    return out


SIMPLE = {
    "denied": ("rad_etildi", "Kirish rad etildi", "biometric_mismatch", "rad", "WARNING"),
    "denied_repeat": ("rad_etildi_takror", "3 marta rad etildi, blokirovka 15 daqiqa", "lockout", "rad", "CRITICAL"),
    "door_left": ("eshik_ochiq_qoldi", "Eshik ochiq qoldi", "", "ok", "WARNING"),
    "impact": ("urilish", "Urilish aniqlandi", "", "ok", "CRITICAL"),
    "tamper": ("buzish_urinishi", "Buzishga urinish (tamper)", "", "ok", "CRITICAL"),
    "hatch": ("lyuk_ochildi", "Xizmat lyuki ochildi", "", "ok", "WARNING"),
    "power_loss": ("quvvat_uzildi", "Quvvat uzildi, batareyada", "", "ok", "WARNING"),
    "power_restore": ("quvvat_tiklandi", "Quvvat tiklandi", "", "ok", "INFO"),
    "battery_low": ("batareya_past", "Batareya 18 %", "", "ok", "WARNING"),
    "lock_fault": ("qulf_xatosi", "Qulf qaytar aloqasi yo'q", "", "ok", "CRITICAL"),
    "sensor_fault": ("datchik_xatosi", "Qisqich datchigi javob bermayapti", "", "ok", "CRITICAL"),
    "mech_key": ("mexanik_kalit", "Mexanik kalit bilan ochildi", "", "ok", "SECURITY"),
    "late": ("kechikish", "Qaytarish muddati o'tdi", "", "ok", "WARNING"),
}


def cabinet_simple(db: Session, cab: Cabinet, action: str):
    typ, title, reason, result, level = SIMPLE[action]
    off = db.get(Officer, cab.officer_id) if cab.officer_id else None
    if action == "power_loss":
        cab.mains_ok = False; cab.battery_pct = 96
    if action == "power_restore":
        cab.mains_ok = True
    if action == "battery_low":
        cab.battery_pct = 18
    if action in ("lock_fault", "sensor_fault"):
        cab.status = "nosoz"
    if action == "late":
        c = db.execute(select(Custody).where(Custody.cabinet_id == cab.id, Custody.returned_at.is_(None))).scalars().first()
        if c:
            c.due_at = datetime.now() - timedelta(minutes=1)
        else:
            cabinet_take(db, cab)
            c = db.execute(select(Custody).where(Custody.cabinet_id == cab.id, Custody.returned_at.is_(None))).scalars().first()
            if c:
                c.due_at = datetime.now() - timedelta(minutes=1)
    ev = record_event(db, typ, cabinet=cab, officer=off, title=title, detail=_label(cab), reason=reason, result=result, attempts=3 if action == "denied_repeat" else 0)
    if action == "denied":
        cab.terminal_state = "denied"
    _notify(ev, cab)
    return ev


ARMORY_ACTIONS = {
    "offline": ("aloqa_uzildi", "Qurolxona oflayn", "CRITICAL"), "online": ("aloqa_tiklandi", "Aloqa tiklandi, hodisalar sinxronlandi", "INFO"),
    "camera_down": ("kamera_oqimi_uzildi", "Kamera oqimi yo'q", "CRITICAL"), "camera_up": ("kamera_oqimi_tiklandi", "Kamera oqimi tiklandi", "INFO"),
    "ups_low": ("batareya_past", "UPS batareyasi 15 %", "WARNING"), "disk_full": ("disk_toldi", "Disk 82 % to'lgan", "WARNING"),
    "ntp_drift": ("vaqt_sinxroni_buzildi", "NTP og'ishi 40 s", "CRITICAL"), "server_down": ("server_yoq_rejimi", "Server javob bermayapti, kesh bilan ishlash", "WARNING"),
    "shift_open": ("smena_ochildi", "Smena ochildi, o'z-tekshiruv o'tdi", "INFO"), "shift_close": ("smena_yopildi", "Smena yopildi, hisobot shakllandi", "INFO"),
    "selfcheck_fail": ("oz_tekshiruv_xato", "O'z-tekshiruv: kamera javob bermadi", "CRITICAL"), "backup_fail": ("zaxira_nusxa_xato", "Kunlik zaxira nusxa bajarilmadi", "WARNING"),
}


def armory_action(db: Session, armory: Armory, action: str):
    typ, title, level = ARMORY_ACTIONS[action]
    where = f"{armory.unit.region.short} · {armory.unit.name}"
    if action == "offline":
        armory.online = False; armory.wan_ok = False; armory.pending_events = 0
        for c in armory.cabinets:
            c.controller_online = False
    if action == "online":
        armory.online = True; armory.wan_ok = True; armory.last_sync = datetime.now(); armory.pending_events = 0
        for c in armory.cabinets:
            c.controller_online = True
        # oflayn signalini yechamiz
        for al in db.execute(select(Alarm).where(Alarm.armory_id == armory.id, Alarm.type == "oflayn", Alarm.resolved_at.is_(None))).scalars():
            al.resolved_at = datetime.now(); al.resolved_by = "tizim"
    if action == "ups_low":
        armory.ups_on_battery = True; armory.ups_battery_pct = 15
    ev = record_event(db, typ, armory=armory, title=title, detail=where)
    _notify(ev, None, armory)
    return ev


def mode_start(db: Session, armory: Armory, kind: str, started_by: str, approver2: str = "", reason: str = "") -> Mode:
    m = Mode(kind=kind, unit_id=armory.unit_id, armory_id=armory.id, started_by=started_by, approver2=approver2,
             started_at=datetime.now().replace(microsecond=0), target_count=len([c for c in armory.cabinets if c.officer_id]),
             issued_count=0, queue_count=0, reason=reason)
    db.add(m); db.flush()
    ev = record_event(db, "rejim_boshlandi", armory=armory, title=("Trevoga" if kind == "trevoga" else "Yig'ilish") + " rejimi boshlandi",
                      detail=f"{armory.unit.region.short} · {armory.unit.name}", approver1=started_by, approver2=approver2)
    _notify(ev, None, armory)
    return m


def mode_stop(db: Session, m: Mode, by: str):
    m.ended_at = datetime.now().replace(microsecond=0)
    armory = db.get(Armory, m.armory_id) if m.armory_id else None
    ev = record_event(db, "rejim_tugadi", armory=armory, title="Rejim tugatildi", detail=f"{m.issued_count}/{m.target_count} berildi", approver1=by)
    _notify(ev, None, armory)


def mode_progress(db: Session, m: Mode, n: int = 1):
    """Rejim davomida n ta yacheykadan qurol olinadi."""
    armory = db.get(Armory, m.armory_id)
    cabs = [c for c in armory.cabinets if c.officer_id and c.ak_present and c.status == "biriktirilgan"]
    R.shuffle(cabs)
    done = 0
    for c in cabs[:n]:
        events = cabinet_take(db, c)
        if any(ev.type == "avtomat_olindi" for ev in events):
            done += 1
    m.issued_count = min(m.issued_count + done, m.target_count)
    m.queue_count = max(m.target_count - m.issued_count, 0)
    if done:
        m.avg_seconds = R.randint(30, 45)


def random_step(db: Session):
    """Avto-rejim: tasodifiy jonli hodisa."""
    cabs = db.execute(select(Cabinet).where(Cabinet.status == "biriktirilgan").order_by(Cabinet.id)).scalars().all()
    if not cabs:
        return None
    cab = R.choice(cabs)
    r = R.random()
    if r < 0.45:
        return cabinet_take(db, cab) if cab.ak_present else cabinet_return(db, cab)
    if r < 0.6:
        return cabinet_return(db, cab) if not cab.ak_present else cabinet_take(db, cab)
    if r < 0.8:
        return cabinet_simple(db, cab, "denied")
    if r < 0.88:
        return cabinet_simple(db, cab, "door_left")
    if r < 0.93:
        return cabinet_simple(db, cab, "impact")
    if r < 0.97:
        return cabinet_simple(db, cab, "late")
    return cabinet_simple(db, cab, "tamper")

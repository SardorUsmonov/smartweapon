"""Qurolxona smenasi (TZ §7.1, §7.4): o'z-tekshiruv, yacheyka/inventar solishtiruvi, ruxsat ro'yxati,
smena ochish/yopish va qurolxona sahifasi uchun agregatlar. Panel HECH QACHON qulf ochmaydi."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (Alarm, Armory, ArmoryShift, Cabinet, Custody, Device, Eligibility, Event, Item, Officer,
                      Region, Unit)
from .events import record_event
from .live import hub

# o'z-tekshiruv tarkibi (TZ §7.1): kalit, nom
SELFCHECK_ITEMS = [
    ("server", "Lokal server"), ("baza", "Ma'lumotlar bazasi"), ("kamera", "Kameralar"), ("terminal", "Terminal"),
    ("kontroller", "Yacheyka kontrollerlari"), ("ups", "UPS / quvvat"), ("disk", "Disk hajmi"),
]
SELFCHECK_LABEL = dict(SELFCHECK_ITEMS)
DEVICE_KIND_LABEL = {"server": "Server", "kommutator": "Kommutator", "ups": "UPS", "nas": "NAS", "kamera": "Kamera",
                     "terminal": "Terminal", "kontroller": "Kontroller"}
ELIG_LABEL = {"qurol_biriktirilgan": "qurol biriktirilgan", "saqlash_vakolati": "saqlash vakolati",
              "maxsus_tayyorgarlik": "maxsus tayyorgarlik", "yaroqlilik_tekshiruvi": "yaroqlilik tekshiruvi",
              "rahbar_buyrugi": "rahbar buyrug'i"}
OPS_TYPES = ("avtomat_olindi", "avtomat_qaytarildi", "pm_olindi", "pm_qaytarildi")
DENY_TYPES = ("rad_etildi", "rad_etildi_takror")


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def where_label(armory: Armory) -> str:
    return f"{armory.unit.region.short} · {armory.unit.name}"


def _live(ev: Event, armory: Armory) -> None:
    hub.broadcast_threadsafe({"type": "event", "event_type": ev.type, "level": ev.level, "cabinet_id": None,
                              "armory_id": armory.id, "title": ev.title, "ts": ev.ts_server.isoformat()})


# ---------------- smena holati ----------------
def open_shift(db: Session, armory_id: int) -> ArmoryShift | None:
    return db.execute(select(ArmoryShift).where(ArmoryShift.armory_id == armory_id, ArmoryShift.closed_at.is_(None))
                      .order_by(ArmoryShift.opened_at.desc())).scalars().first()


def shift_history(db: Session, armory_id: int, limit: int = 50, offset: int = 0) -> list[ArmoryShift]:
    return list(db.execute(select(ArmoryShift).where(ArmoryShift.armory_id == armory_id)
                           .order_by(ArmoryShift.opened_at.desc()).offset(offset).limit(limit)).scalars())


def shift_count(db: Session, armory_id: int) -> int:
    return db.scalar(select(func.count(ArmoryShift.id)).where(ArmoryShift.armory_id == armory_id)) or 0


# ---------------- qurilmalar ----------------
def devices(db: Session, armory_id: int) -> list[Device]:
    order = {"server": 0, "kommutator": 1, "ups": 2, "nas": 3, "kamera": 4, "terminal": 5}
    rows = list(db.execute(select(Device).where(Device.armory_id == armory_id)).scalars())
    rows.sort(key=lambda d: (order.get(d.kind, 9), d.name))
    return rows


def metrics_text(dev: Device) -> str:
    m = dev.metrics or {}
    parts = []
    names = {"cpu": "CPU", "ram": "RAM", "disk": "Disk", "portlar": "portlar", "band": "band", "batareya": "batareya",
             "yuklama": "yuklama", "oqim": "oqim", "kesh": "kesh"}
    pct = {"cpu", "ram", "disk", "batareya", "yuklama"}
    for k, v in m.items():
        label = names.get(k, k)
        if isinstance(v, bool):
            parts.append(f"{label}: {'bor' if v else 'yo‘q'}")
        elif k in pct:
            parts.append(f"{label} {v} %")
        else:
            parts.append(f"{label} {v}")
    return " · ".join(parts)


def device_tone(dev: Device) -> str:
    if dev.status == "oflayn":
        return "red"
    if dev.status == "ogohlantirish":
        return "yellow"
    m = dev.metrics or {}
    if dev.kind in ("server", "nas") and int(m.get("disk", 0)) >= 85:
        return "yellow"
    if dev.kind == "ups" and int(m.get("batareya", 100)) < 30:
        return "yellow"
    return "green"


# ---------------- o'z-tekshiruv (TZ §7.1) ----------------
def selfcheck(db: Session, armory: Armory) -> dict:
    """Server, baza, kamera, terminal, kontroller, UPS, disk — Device jadvali va yacheyka telemetriyasidan."""
    devs = devices(db, armory.id)
    by_kind: dict[str, list[Device]] = {}
    for d in devs:
        by_kind.setdefault(d.kind, []).append(d)
    server = by_kind.get("server", [None])[0]
    ups = by_kind.get("ups", [None])[0]
    nas = by_kind.get("nas", [None])[0]
    terminal = by_kind.get("terminal", [None])[0]
    cams = by_kind.get("kamera", [])
    cabs = list(armory.cabinets)
    ctrl_on = sum(1 for c in cabs if c.controller_online)
    items: list[dict] = []

    def add(key: str, ok: bool, detail: str):
        items.append({"key": key, "label": SELFCHECK_LABEL[key], "ok": bool(ok), "detail": detail})

    if server is not None:
        m = server.metrics or {}
        add("server", server.status == "onlayn", f"{server.name} · CPU {m.get('cpu', '—')} % · RAM {m.get('ram', '—')} %")
    else:
        add("server", False, "server qurilmasi ro'yxatda yo'q")
    add("baza", server is not None and server.status == "onlayn",
        f"lokal baza (SQLite, WAL) · sinxron {armory.last_sync.strftime('%d.%m %H:%M') if armory.last_sync else '—'} · kutilayotgan hodisalar {armory.pending_events}")
    cams_on = sum(1 for c in cams if c.status == "onlayn")
    add("kamera", bool(cams) and cams_on == len(cams), f"{cams_on}/{len(cams)} kamera oqimi faol")
    if terminal is not None:
        add("terminal", terminal.status == "onlayn", f"{terminal.name} · kesh: {'bor' if (terminal.metrics or {}).get('kesh') else 'yo‘q'}")
    else:
        add("terminal", False, "terminal ro'yxatda yo'q")
    add("kontroller", bool(cabs) and ctrl_on == len(cabs), f"{ctrl_on}/{len(cabs)} kontroller onlayn")
    if ups is not None:
        m = ups.metrics or {}
        batt = int(m.get("batareya", armory.ups_battery_pct))
        add("ups", ups.status == "onlayn" and not armory.ups_on_battery and batt >= 30,
            f"batareya {batt} % · yuklama {m.get('yuklama', '—')} %" + (" · batareyada ishlamoqda" if armory.ups_on_battery else " · tarmoqda"))
    else:
        add("ups", False, "UPS ro'yxatda yo'q")
    sd = int((server.metrics or {}).get("disk", 0)) if server is not None else 0
    nd = int((nas.metrics or {}).get("disk", 0)) if nas is not None else 0
    add("disk", sd < 85 and nd < 85, f"server {sd} % · NAS {nd} % (chegara 85 %)")
    failed = [i for i in items if not i["ok"]]
    return {"items": items, "ok": not failed, "failed": failed, "passed": len(items) - len(failed), "total": len(items),
            "flags": {i["key"]: i["ok"] for i in items}}


# ---------------- yacheyka va inventar solishtiruvi ----------------
def reconcile(db: Session, armory: Armory) -> dict:
    """Har yacheyka bo'yicha: Item holati (mavjud/yo'q) bilan yacheyka datchiklari (ak_present/pm_present) mos keladimi."""
    cabs = sorted(armory.cabinets, key=lambda c: (c.wall, c.position))
    cab_ids = [c.id for c in cabs]
    items = list(db.execute(select(Item).where(Item.cabinet_id.in_(cab_ids), Item.kind == "qurol")).scalars()) if cab_ids else []
    by_cab: dict[int, dict[str, Item]] = {}
    for it in items:
        by_cab.setdefault(it.cabinet_id, {})[it.category] = it
    open_c = dict(db.execute(select(Custody.cabinet_id, func.count(Custody.id))
                             .where(Custody.cabinet_id.in_(cab_ids), Custody.returned_at.is_(None)).group_by(Custody.cabinet_id)).all()) if cab_ids else {}
    farqlar: list[dict] = []
    mos = 0
    for c in cabs:
        probs = []
        ak = by_cab.get(c.id, {}).get("avtomat")
        pm = by_cab.get(c.id, {}).get("to'pponcha")
        if ak is not None and (ak.state == "mavjud") != bool(c.ak_present):
            probs.append("AK: inventar «%s», datchik «%s»" % (ak.state, "uyada" if c.ak_present else "yo'q"))
        if pm is not None and (pm.state == "mavjud") != bool(c.pm_present):
            probs.append("PM: inventar «%s», datchik «%s»" % (pm.state, "uyada" if c.pm_present else "yo'q"))
        if c.status == "biriktirilgan" and c.officer_id is None:
            probs.append("biriktirilgan, lekin xodim yo'q")
        if c.status == "biriktirilgan" and ak is None and pm is None:
            probs.append("biriktirilgan yacheykada qurol ro'yxati yo'q")
        if c.door_open:
            probs.append("eshik ochiq")
        if probs:
            farqlar.append({"cabinet_id": c.id, "label": c.label, "wall": c.wall, "detail": "; ".join(probs),
                            "officer": c.officer.full_name if c.officer else ""})
        else:
            mos += 1
    return {"yacheyka": len(cabs), "mos": mos, "nomuvofiq": len(farqlar), "berilgan": sum(open_c.values()),
            "qurollar": len(items), "farqlar": farqlar}


# ---------------- ruxsat ro'yxati ----------------
def permits(db: Session, armory: Armory, now: datetime | None = None) -> dict:
    now = now or _now()
    cabs = sorted([c for c in armory.cabinets if c.officer_id], key=lambda c: (c.wall, c.position))
    off_ids = [c.officer_id for c in cabs]
    offs = {o.id: o for o in db.execute(select(Officer).where(Officer.id.in_(off_ids))).scalars()} if off_ids else {}
    elig: dict[int, list[Eligibility]] = {}
    if off_ids:
        for e in db.execute(select(Eligibility).where(Eligibility.officer_id.in_(off_ids))).scalars():
            elig.setdefault(e.officer_id, []).append(e)
    rows: list[dict] = []
    for c in cabs:
        o = offs.get(c.officer_id)
        if o is None:
            continue
        issues: list[str] = []
        if o.service_status != "faol":
            issues.append("xizmat holati: " + o.service_status.replace("_", " "))
        if o.valid_until and o.valid_until < now:
            issues.append("vakolat muddati o'tgan")
        if o.card_status != "faol":
            issues.append("karta: " + o.card_status)
        if not (o.face_enrolled or o.finger_enrolled):
            issues.append("biometriya ro'yxatdan o'tmagan")
        if not o.permit_ak and not o.permit_pm:
            issues.append("qurol ruxsati yo'q")
        bad = [e for e in elig.get(o.id, []) if not e.ok or (e.valid_until and e.valid_until < now)]
        for e in bad:
            issues.append(ELIG_LABEL.get(e.kind, e.kind) + (" muddati o'tgan" if e.ok else " tasdiqlanmagan"))
        if len(elig.get(o.id, [])) < 5:
            issues.append("yaroqlilik yozuvlari to'liq emas (%d/5)" % len(elig.get(o.id, [])))
        rows.append({"officer": o, "cabinet": c, "issues": issues, "ok": not issues,
                     "elig_ok": len(elig.get(o.id, [])) - len(bad), "elig_total": len(elig.get(o.id, []))})
    rows.sort(key=lambda r: (r["ok"], r["cabinet"].wall, r["cabinet"].position))
    issues_n = sum(1 for r in rows if not r["ok"])
    return {"rows": rows, "total": len(rows), "ok_count": len(rows) - issues_n, "issue_count": issues_n}


# ---------------- smena statistikasi ----------------
def shift_stats(db: Session, armory_id: int, since: datetime, until: datetime | None = None) -> dict:
    def cnt(*extra):
        q = select(func.count(Event.id)).where(Event.armory_id == armory_id, Event.ts_server >= since, *extra)
        if until is not None:
            q = q.where(Event.ts_server <= until)
        return db.scalar(q) or 0

    taken = cnt(Event.type.in_(("avtomat_olindi", "pm_olindi")))
    returned = cnt(Event.type.in_(("avtomat_qaytarildi", "pm_qaytarildi")))
    aq = select(func.count(Alarm.id)).where(Alarm.armory_id == armory_id, Alarm.opened_at >= since)
    if until is not None:
        aq = aq.where(Alarm.opened_at <= until)
    return {"olindi": taken, "qaytarildi": returned, "operatsiya": taken + returned, "rad": cnt(Event.type.in_(DENY_TYPES)),
            "favqulodda": cnt(Event.type.in_(("favqulodda_ochish", "mexanik_kalit"))),
            "signal": db.scalar(aq) or 0, "hodisa": cnt()}


def unreturned(db: Session, armory_id: int, now: datetime | None = None) -> list[dict]:
    """Qaytarilmagan qurollar: ochiq Custody yozuvlari (Item, Officer, Cabinet bilan)."""
    now = now or _now()
    q = (select(Custody, Item, Officer, Cabinet).join(Item, Item.id == Custody.item_id).join(Officer, Officer.id == Custody.officer_id)
         .join(Cabinet, Cabinet.id == Custody.cabinet_id).where(Cabinet.armory_id == armory_id, Custody.returned_at.is_(None))
         .order_by(Custody.due_at.asc()))
    out = []
    for cu, it, of, cab in db.execute(q):
        out.append({"custody": cu, "item": it, "officer": of, "cabinet": cab, "overdue": cu.due_at < now,
                    "late_min": int((now - cu.due_at).total_seconds() // 60) if cu.due_at < now else 0})
    return out


def open_alarms(db: Session, armory_id: int) -> list[Alarm]:
    return list(db.execute(select(Alarm).where(Alarm.armory_id == armory_id, Alarm.resolved_at.is_(None))
                           .order_by(Alarm.opened_at.desc())).scalars())


def recent_events(db: Session, armory_id: int, limit: int = 30, since: datetime | None = None,
                  until: datetime | None = None) -> list[Event]:
    q = select(Event).where(Event.armory_id == armory_id)
    if since is not None:
        q = q.where(Event.ts_server >= since)
    if until is not None:
        q = q.where(Event.ts_server <= until)
    return list(db.execute(q.order_by(Event.ts_server.desc(), Event.id.desc()).limit(limit)).scalars())


# ---------------- yacheykalar rejasi ----------------
def cabinet_plan(db: Session, armory: Armory, now: datetime | None = None) -> dict:
    """A/B devor bo'yicha yacheyka kataklari: holat rangi va belgilar."""
    now = now or _now()
    cabs = sorted(armory.cabinets, key=lambda c: (c.wall, c.position))
    cab_ids = [c.id for c in cabs]
    overdue_ids = set()
    if cab_ids:
        overdue_ids = {r[0] for r in db.execute(select(Custody.cabinet_id).where(Custody.cabinet_id.in_(cab_ids), Custody.returned_at.is_(None), Custody.due_at < now))}
    walls: dict[str, list[dict]] = {}
    counts = {"ok": 0, "out": 0, "free": 0, "bad": 0, "svc": 0, "off": 0}
    for c in cabs:
        if not c.controller_online:
            cls, state = "off", "kontroller oflayn"
        elif c.status in ("bloklangan", "nosoz"):
            cls, state = "bad", ("bloklangan" if c.status == "bloklangan" else "nosoz")
        elif c.status == "xizmatda":
            cls, state = "svc", "xizmat rejimi"
        elif c.status == "zaxira":
            cls, state = "free", "zaxira (biriktirilmagan)"
        elif not c.ak_present or not c.pm_present:
            cls, state = "out", "qurol xodimda"
        else:
            cls, state = "ok", "qurol uyada"
        counts[cls] += 1
        flags = []
        if c.door_open:
            flags.append(("door", "eshik ochiq"))
        if c.id in overdue_ids:
            flags.append(("clock", "qaytarish kechikkan"))
        if not c.mains_ok:
            flags.append(("power", "tarmoq quvvati yo'q"))
        if c.battery_pct < 30:
            flags.append(("battery", "batareya %d %%" % c.battery_pct))
        walls.setdefault(c.wall, []).append({
            "id": c.id, "label": c.label, "cls": cls, "state": state, "flags": flags, "officer": c.officer.full_name if c.officer else "",
            "ak": c.ak_present, "pm": c.pm_present, "door_open": c.door_open, "battery": c.battery_pct,
            "title": f"{c.label} · {state}" + (f" · {c.officer.full_name}" if c.officer else "") + (" · " + ", ".join(f[1] for f in flags) if flags else ""),
        })
    return {"walls": [(w, walls[w]) for w in sorted(walls)], "counts": counts, "total": len(cabs)}


# ---------------- qurolxonalar ro'yxati ----------------
def armory_rows(db: Session, armory_ids: list[int] | None, region_id: int | None = None, holat: str = "", q: str = "",
                sort: str = "", now: datetime | None = None) -> list[dict]:
    now = now or _now()
    sel = (select(Armory, Unit, Region).join(Unit, Unit.id == Armory.unit_id).join(Region, Region.id == Unit.region_id)
           .order_by(Region.order, Unit.name))
    if armory_ids is not None:
        sel = sel.where(Armory.id.in_(armory_ids))
    if region_id:
        sel = sel.where(Unit.region_id == region_id)
    if holat == "onlayn":
        sel = sel.where(Armory.online.is_(True))
    elif holat == "oflayn":
        sel = sel.where(Armory.online.is_(False))
    if q:
        like = f"%{q.strip()}%"
        sel = sel.where((Armory.name.ilike(like)) | (Unit.name.ilike(like)) | (Region.name.ilike(like)) | (Armory.address.ilike(like)))
    base = list(db.execute(sel))
    ids = [a.id for a, _, _ in base]
    if not ids:
        return []
    cab_total = dict(db.execute(select(Cabinet.armory_id, func.count(Cabinet.id)).where(Cabinet.armory_id.in_(ids)).group_by(Cabinet.armory_id)).all())
    cab_assigned = dict(db.execute(select(Cabinet.armory_id, func.count(Cabinet.id)).where(Cabinet.armory_id.in_(ids), Cabinet.status == "biriktirilgan").group_by(Cabinet.armory_id)).all())
    cab_bad = dict(db.execute(select(Cabinet.armory_id, func.count(Cabinet.id)).where(Cabinet.armory_id.in_(ids), Cabinet.status.in_(["bloklangan", "nosoz", "xizmatda"])).group_by(Cabinet.armory_id)).all())
    from .kpi import armory_weapon_custody_counts
    custody_counts = armory_weapon_custody_counts(db, ids, now)
    issued = {arm_id: counts["berilgan"] for arm_id, counts in custody_counts.items()}
    overdue = {arm_id: counts["kechikish"] for arm_id, counts in custody_counts.items()}
    alarms = dict(db.execute(select(Alarm.armory_id, func.count(Alarm.id)).where(Alarm.armory_id.in_(ids), Alarm.resolved_at.is_(None)).group_by(Alarm.armory_id)).all())
    crit = dict(db.execute(select(Alarm.armory_id, func.count(Alarm.id)).where(Alarm.armory_id.in_(ids), Alarm.resolved_at.is_(None), Alarm.level.in_(["CRITICAL", "SECURITY"])).group_by(Alarm.armory_id)).all())
    shifts = {s.armory_id: s for s in db.execute(select(ArmoryShift).where(ArmoryShift.armory_id.in_(ids), ArmoryShift.closed_at.is_(None))).scalars()}
    dev_off = dict(db.execute(select(Device.armory_id, func.count(Device.id)).where(Device.armory_id.in_(ids), Device.status != "onlayn").group_by(Device.armory_id)).all())
    rows = []
    for a, u, r in base:
        n_al, n_ov, n_bad = alarms.get(a.id, 0), overdue.get(a.id, 0), cab_bad.get(a.id, 0)
        if not a.online or crit.get(a.id, 0):
            status = "critical"
        elif n_ov or n_al or n_bad or a.ups_on_battery:
            status = "warning"
        else:
            status = "good"
        rows.append({"id": a.id, "name": a.name, "address": a.address, "online": a.online, "last_sync": a.last_sync,
                     "wan_ok": a.wan_ok, "ups_on_battery": a.ups_on_battery, "ups_pct": a.ups_battery_pct, "pending": a.pending_events,
                     "region_id": r.id, "region": r.short, "unit": u.name, "unit_id": u.id,
                     "yacheyka": cab_total.get(a.id, 0), "biriktirilgan": cab_assigned.get(a.id, 0), "muammo": n_bad,
                     "berilgan": issued.get(a.id, 0), "kechikish": n_ov, "signal": n_al, "kritik": crit.get(a.id, 0),
                     "qurilma_muammo": dev_off.get(a.id, 0), "smena": shifts.get(a.id), "status": status})
    if holat == "smena":
        rows = [x for x in rows if x["smena"] is not None]
    elif holat == "muammo":
        rows = [x for x in rows if x["status"] != "good"]
    keys = {"kechikish": lambda x: -x["kechikish"], "signal": lambda x: -x["signal"], "yacheyka": lambda x: -x["yacheyka"],
            "berilgan": lambda x: -x["berilgan"], "holat": lambda x: (x["online"], {"critical": 0, "warning": 1, "good": 2}[x["status"]])}
    if sort in keys:
        rows.sort(key=keys[sort])
    return rows


# ---------------- smena ochish / yopish ----------------
def open_new_shift(db: Session, armory: Armory, opened_by: str, chk: dict, rec: dict, perm: dict, note: str = "",
                   reason: str = "") -> ArmoryShift:
    """ArmoryShift yaratadi, `smena_ochildi` (va kerak bo'lsa `oz_tekshiruv_xato`) hodisasini yozadi."""
    now = _now()
    s = ArmoryShift(armory_id=armory.id, opened_by=opened_by, opened_at=now, selfcheck=dict(chk["flags"]),
                    reconcile={"yacheyka": rec["yacheyka"], "mos": rec["mos"], "nomuvofiq": rec["nomuvofiq"], "berilgan": rec["berilgan"],
                               "farqlar": [{"label": f["label"], "detail": f["detail"]} for f in rec["farqlar"]],
                               "ruxsat": {"jami": perm["total"], "mos": perm["ok_count"], "muammo": perm["issue_count"]},
                               "izoh": note, "sabab": reason},
                    permits_confirmed=True)
    db.add(s); db.flush()
    where = where_label(armory)
    if not chk["ok"]:
        ev = record_event(db, "oz_tekshiruv_xato", armory=armory, simulated=False, result="xato",
                          title="O'z-tekshiruv xatosi", reason=(reason or "")[:60],
                          detail=where + " · " + ", ".join(i["label"] for i in chk["failed"]) + " · smena sabab bilan ochildi",
                          payload={"smena_id": s.id, "xatolar": [i["key"] for i in chk["failed"]], "sabab": reason})
        _live(ev, armory)
    ev = record_event(db, "smena_ochildi", armory=armory, simulated=False, approver1=opened_by, title="Smena ochildi",
                      detail=f"{where} · o'z-tekshiruv {chk['passed']}/{chk['total']} · yacheyka {rec['mos']}/{rec['yacheyka']} mos · ruxsat {perm['ok_count']}/{perm['total']}",
                      payload={"smena_id": s.id, "oz_tekshiruv": chk["flags"], "solishtiruv": {"mos": rec["mos"], "nomuvofiq": rec["nomuvofiq"], "berilgan": rec["berilgan"]},
                               "ruxsat": {"jami": perm["total"], "muammo": perm["issue_count"]}, "izoh": note, "sabab": reason})
    _live(ev, armory)
    return s


def close_shift(db: Session, armory: Armory, s: ArmoryShift, closed_by: str, close_confirm: str, note: str = "") -> ArmoryShift:
    """Smenani yopadi: qaytarilmagan qurollar va ochiq signallar hisobotga muhrlanadi, `smena_yopildi` yoziladi."""
    now = _now()
    unret = unreturned(db, armory.id, now)
    alarms = open_alarms(db, armory.id)
    st = shift_stats(db, armory.id, s.opened_at, now)
    s.closed_by = closed_by; s.closed_at = now; s.close_confirm = close_confirm
    s.report_ref = "SM-%s-%s-%06d" % (now.strftime("%Y%m%d"), armory.id, s.id)
    rec = dict(s.reconcile or {})
    rec["yopish"] = {
        "qaytarilmagan": [{"label": u["cabinet"].label, "xodim": u["officer"].full_name, "tabel": u["officer"].tabel, "qurol": f"{u['item'].model} {u['item'].serial}",
                           "muddat": u["custody"].due_at.isoformat(), "kechikkan": u["overdue"]} for u in unret],
        "ochiq_signallar": [{"id": a.id, "daraja": a.level, "sarlavha": a.title, "tasdiqlangan": bool(a.acked_at)} for a in alarms],
        "statistika": st, "izoh": note,
    }
    s.reconcile = rec
    where = where_label(armory)
    ev = record_event(db, "smena_yopildi", armory=armory, simulated=False, approver1=closed_by, approver2=close_confirm,
                      title="Smena yopildi", result="ok" if not unret else "qaytarilmagan_bor",
                      detail=f"{where} · qaytarilmagan {len(unret)} · ochiq signallar {len(alarms)} · operatsiyalar {st['operatsiya']} · hisobot {s.report_ref}",
                      payload={"smena_id": s.id, "hisobot": s.report_ref, "qaytarilmagan": len(unret), "kechikkan": sum(1 for u in unret if u["overdue"]),
                               "ochiq_signallar": len(alarms), "statistika": st, "izoh": note})
    _live(ev, armory)
    return s

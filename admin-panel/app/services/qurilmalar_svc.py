"""Qurilmalar bo'limi xizmatlari: 5 darajali daraxt, samarali holat, ko'rsatkichlar, self-test, hodisalar."""
from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import Armory, Backup, Cabinet, Device, Event, Region, Unit
from .live import hub

KIND_LABEL = {"server": "Server", "kommutator": "Kommutator", "ups": "UPS", "nas": "NAS", "kamera": "Kamera",
              "terminal": "Terminal", "kontroller": "Kontroller"}
KIND_ICON = {"server": "cpu", "kommutator": "swap", "ups": "battery", "nas": "box", "kamera": "camera",
             "terminal": "eye", "kontroller": "lock"}
KIND_ORDER = ["server", "terminal", "kommutator", "ups", "nas", "kamera"]
STATUS_LABEL = {"onlayn": "Onlayn", "oflayn": "Oflayn", "ogohlantirish": "Ogohlantirish", "xizmatda": "Xizmatda"}
STATUS_CHIP = {"onlayn": "chip-green", "oflayn": "chip-red", "ogohlantirish": "chip-yellow", "xizmatda": "chip-yellow"}
STATUSES = ["onlayn", "oflayn", "ogohlantirish", "xizmatda"]

METRIC_LABEL = {"cpu": "CPU", "ram": "RAM", "disk": "Disk", "batareya": "Batareya", "yuklama": "Yuklama",
                "portlar": "Portlar", "band": "Band portlar", "oqim": "Video oqim", "kesh": "Lokal kesh",
                "ntp_ogish_s": "NTP og'ishi, s"}
# foiz ko'rsatkichlar: (sariq chegara, qizil chegara, teskari — past qiymat yomon)
PCT_METRICS = {"cpu": (75, 90, False), "ram": (75, 90, False), "disk": (70, 85, False),
               "batareya": (50, 20, True), "yuklama": (70, 85, False)}
# qurilma turi -> unga tegishli qurolxona darajasidagi hodisa turlari
KIND_EVENTS = {
    "kamera": ["kamera_oqimi_uzildi", "kamera_oqimi_tiklandi"],
    "ups": ["quvvat_uzildi", "quvvat_tiklandi", "batareya_past"],
    "server": ["server_yoq_rejimi", "disk_toldi", "vaqt_sinxroni_buzildi", "aloqa_uzildi", "aloqa_tiklandi", "sinxronlandi", "zaxira_nusxa_xato"],
    "nas": ["disk_toldi", "zaxira_nusxa", "zaxira_nusxa_xato"],
    "kommutator": ["aloqa_uzildi", "aloqa_tiklandi"],
    "terminal": ["oz_tekshiruv_xato", "vaqt_sinxroni_buzildi", "smena_ochildi", "smena_yopildi"],
}
BACKUP_KIND_LABEL = {"kunlik": "Kunlik nusxa", "haftalik": "Haftalik nusxa", "tiklash_sinovi": "Tiklash sinovi"}
# rejalashtirish (prototip: statik jadval)
BACKUP_SCHEDULE = {"kunlik": "Har kuni 02:00", "haftalik": "Har dushanba 03:00", "tiklash_sinovi": "Har 30 kunda"}


# ---------------- holat ----------------
def eff_status(dev: Device, armory_online: bool) -> str:
    """Samarali holat: xizmat rejimi > qurolxona oflayn > qurilma holati."""
    if dev.status == "xizmatda":
        return "xizmatda"
    if not armory_online:
        return "oflayn"
    return dev.status if dev.status in STATUS_LABEL else "onlayn"


def metric_tone(key: str, val) -> str:
    spec = PCT_METRICS.get(key)
    if not spec or not isinstance(val, (int, float)):
        return ""
    y, r, inv = spec
    if inv:
        return "red" if val <= r else "yellow" if val <= y else "green"
    return "red" if val >= r else "yellow" if val >= y else "green"


def metric_rows(dev: Device) -> list[dict]:
    """Ko'rsatkichlar ro'yxati: foiz (progress), mantiqiy (chip), son."""
    out = []
    m = dev.metrics or {}
    for key in ["cpu", "ram", "disk", "batareya", "yuklama", "portlar", "band", "oqim", "kesh", "ntp_ogish_s"]:
        if key not in m:
            continue
        val = m[key]
        row = {"key": key, "label": METRIC_LABEL.get(key, key), "value": val}
        if key in PCT_METRICS:
            row.update(kind="pct", pct=max(0, min(100, int(val))), tone=metric_tone(key, val), text=f"{int(val)} %")
        elif isinstance(val, bool):
            row.update(kind="bool", tone="green" if val else "red", text="bor" if val else "yo'q")
        elif key == "band" and "portlar" in m:
            row.update(kind="num", text=f"{val} / {m['portlar']}", tone="")
        else:
            row.update(kind="num", text=str(val), tone="")
        out.append(row)
    return out


def metric_short(dev: Device) -> str:
    m = dev.metrics or {}
    parts = []
    for key in ["cpu", "ram", "disk", "batareya", "yuklama"]:
        if key in m:
            parts.append(f"{METRIC_LABEL[key]} {int(m[key])} %")
    if "band" in m and "portlar" in m:
        parts.append(f"{m['band']}/{m['portlar']} port")
    if "oqim" in m:
        parts.append("oqim bor" if m["oqim"] else "oqim yo'q")
    if "kesh" in m:
        parts.append("kesh bor" if m["kesh"] else "kesh yo'q")
    if "ntp_ogish_s" in m:
        parts.append(f"NTP {m['ntp_ogish_s']} s")
    return " · ".join(parts)


def dev_dict(dev: Device, arm: Armory) -> dict:
    st = eff_status(dev, arm.online)
    return {"id": dev.id, "kind": dev.kind, "kind_label": KIND_LABEL.get(dev.kind, dev.kind), "icon": KIND_ICON.get(dev.kind, "cpu"),
            "name": dev.name, "status": st, "status_label": STATUS_LABEL[st], "chip": STATUS_CHIP[st], "last_seen": dev.last_seen,
            "metrics": metric_short(dev), "armory": arm, "armory_id": arm.id, "unit": arm.unit, "region": arm.unit.region,
            "xizmat": (dev.metrics or {}).get("xizmat")}


def controller_counts(db: Session) -> dict[int, dict]:
    q = select(Cabinet.armory_id, func.count(Cabinet.id),
               func.sum(case((Cabinet.controller_online.is_(False), 1), else_=0))).group_by(Cabinet.armory_id)
    return {a: {"jami": n or 0, "oflayn": int(off or 0)} for a, n, off in db.execute(q)}


def _cnt() -> dict:
    return {"jami": 0, "onlayn": 0, "oflayn": 0, "ogohlantirish": 0, "xizmatda": 0, "ctrl": 0, "ctrl_oflayn": 0}


def _add(dst: dict, src: dict):
    for k in dst:
        dst[k] += src.get(k, 0)


def load_devices(db: Session, armory_ids: list[int] | None = None) -> list[dict]:
    """Vakolat doirasidagi barcha qurilmalar (qurolxona bilan)."""
    q = select(Device, Armory).join(Armory, Armory.id == Device.armory_id)
    if armory_ids is not None:
        q = q.where(Armory.id.in_(armory_ids))
    q = q.join(Unit, Unit.id == Armory.unit_id).join(Region, Region.id == Unit.region_id).order_by(Region.order, Unit.name, Armory.name, Device.id)
    return [dev_dict(d, a) for d, a in db.execute(q)]


def filter_devices(devs: list[dict], holat: str = "", tur: str = "", q: str = "", hudud: int | None = None) -> list[dict]:
    ql = q.strip().lower()
    out = []
    for d in devs:
        if holat and d["status"] != holat:
            continue
        if tur and d["kind"] != tur:
            continue
        if hudud and d["region"].id != hudud:
            continue
        if ql and ql not in (d["name"] + " " + d["armory"].name + " " + d["unit"].name + " " + d["region"].name + " " + d["kind_label"]).lower():
            continue
        out.append(d)
    return out


def build_tree(db: Session, devs: list[dict], filtered: bool) -> tuple[list[dict], dict]:
    """Respublika › hudud › bo'linma › qurolxona › qurilma/kontroller daraxti. `devs` — allaqachon filtrlangan ro'yxat."""
    ctrl = controller_counts(db)
    regions: dict[int, dict] = {}
    for d in devs:
        r, u, a = d["region"], d["unit"], d["armory"]
        rn = regions.setdefault(r.id, {"id": r.id, "name": r.name, "short": r.short, "order": r.order, "units": {}, "cnt": _cnt()})
        un = rn["units"].setdefault(u.id, {"id": u.id, "name": u.name, "kind": u.kind, "armories": {}, "cnt": _cnt()})
        an = un["armories"].setdefault(a.id, {"id": a.id, "name": a.name, "online": a.online, "last_sync": a.last_sync,
                                              "ups_on_battery": a.ups_on_battery, "devices": [], "cnt": _cnt()})
        if not an["devices"]:
            c = ctrl.get(a.id, {"jami": 0, "oflayn": 0})
            an["cnt"]["ctrl"] = c["jami"]; an["cnt"]["ctrl_oflayn"] = c["oflayn"]
        an["devices"].append(d)
        an["cnt"]["jami"] += 1; an["cnt"][d["status"]] += 1
    total = _cnt()
    tree = []
    for rn in sorted(regions.values(), key=lambda x: x["order"]):
        units = []
        for un in sorted(rn["units"].values(), key=lambda x: x["name"]):
            arms = sorted(un["armories"].values(), key=lambda x: x["name"])
            for an in arms:
                an["devices"].sort(key=lambda d: (KIND_ORDER.index(d["kind"]) if d["kind"] in KIND_ORDER else 99, d["id"]))
                _add(un["cnt"], an["cnt"])
            un["armories"] = arms
            un["open"] = filtered
            units.append(un)
            _add(rn["cnt"], un["cnt"])
        rn["units"] = units
        rn["open"] = filtered
        tree.append(rn)
        _add(total, rn["cnt"])
    return tree, total


def summary(db: Session, armory_ids: list[int] | None = None) -> dict:
    devs = load_devices(db, armory_ids)
    s = _cnt()
    for d in devs:
        s["jami"] += 1; s[d["status"]] += 1
    ctrl = controller_counts(db)
    for a_id, c in ctrl.items():
        if armory_ids is None or a_id in armory_ids:
            s["ctrl"] += c["jami"]; s["ctrl_oflayn"] += c["oflayn"]
    aq = select(func.count(Armory.id)).where(Armory.online.is_(False))
    if armory_ids is not None:
        aq = aq.where(Armory.id.in_(armory_ids))
    s["qurolxona_oflayn"] = db.scalar(aq) or 0
    s["now"] = datetime.now()
    return s


def paginate(items: list, page: int, per_page: int = 50) -> dict:
    total = len(items)
    pages = max(1, ceil(total / per_page))
    page = min(max(1, page), pages)
    return {"rows": items[(page - 1) * per_page: page * per_page], "page": page, "pages": pages, "total": total, "per_page": per_page}


# ---------------- self-test ----------------
def self_test(dev: Device, arm: Armory) -> tuple[bool, list[dict]]:
    """Qurilma o'z-tekshiruvi (simulyatsiya): ko'rsatkichlar chegaralar bilan solishtiriladi."""
    m = dev.metrics or {}
    checks: list[dict] = []

    def add(label, ok, value):
        checks.append({"label": label, "ok": bool(ok), "value": value})

    add("Qurolxona aloqasi", arm.online, "onlayn" if arm.online else "oflayn")
    add("Qurilma javobi", dev.status != "oflayn" and arm.online, "javob bor" if (dev.status != "oflayn" and arm.online) else "javob yo'q")
    if dev.kind == "server":
        add("CPU yuklamasi", m.get("cpu", 0) < 90, f"{m.get('cpu', 0)} %")
        add("RAM band", m.get("ram", 0) < 90, f"{m.get('ram', 0)} %")
        add("Disk to'lganligi", m.get("disk", 0) < 85, f"{m.get('disk', 0)} %")
        add("Vaqt sinxroni (NTP)", m.get("ntp_ogish_s", 0) < 5, f"{m.get('ntp_ogish_s', 0)} s")
        add("Baza yaxlitligi", True, "ok")
    elif dev.kind == "kommutator":
        add("Portlar", m.get("band", 0) <= m.get("portlar", 24), f"{m.get('band', 0)}/{m.get('portlar', 24)}")
        add("PoE quvvati", True, "me'yorda")
    elif dev.kind == "ups":
        add("Batareya zaryadi", m.get("batareya", 0) >= 20, f"{m.get('batareya', 0)} %")
        add("Yuklama", m.get("yuklama", 0) <= 85, f"{m.get('yuklama', 0)} %")
        add("Tarmoq quvvati", not arm.ups_on_battery, "batareyada" if arm.ups_on_battery else "tarmoqda")
    elif dev.kind == "nas":
        add("Disk to'lganligi", m.get("disk", 0) < 85, f"{m.get('disk', 0)} %")
        add("RAID holati", True, "ok")
    elif dev.kind == "kamera":
        add("Video oqim", m.get("oqim", False), "bor" if m.get("oqim") else "yo'q")
        add("Yozuv arxivi", True, "ok")
    elif dev.kind == "terminal":
        add("Lokal kesh", m.get("kesh", False), "bor" if m.get("kesh") else "yo'q")
        add("Kamera moduli", True, "ok")
        add("Barmoq izi skaneri", True, "ok")
        add("Vaqt sinxroni (NTP)", m.get("ntp_ogish_s", 0) < 5, f"{m.get('ntp_ogish_s', 0)} s")
    return all(c["ok"] for c in checks), checks


# ---------------- hodisalar ----------------
def device_events(db: Session, dev: Device, limit: int = 30) -> list[Event]:
    types = list(KIND_EVENTS.get(dev.kind, [])) + ["texnik_xizmat"]
    q = select(Event).where(Event.armory_id == dev.armory_id, Event.cabinet_id.is_(None), Event.type.in_(types))\
        .order_by(Event.ts_server.desc(), Event.id.desc()).limit(400)
    out = []
    for e in db.execute(q).scalars():
        if e.type == "texnik_xizmat" and (e.payload or {}).get("device_id") != dev.id:
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out


def notify(ev: Event, armory_id: int | None = None):
    hub.broadcast_threadsafe({"type": "event", "event_type": ev.type, "level": ev.level, "cabinet_id": None,
                              "armory_id": armory_id, "title": ev.title, "ts": ev.ts_server.isoformat()})


# ---------------- zaxira nusxalash ----------------
def backup_overview(db: Session, now: datetime | None = None) -> dict:
    from ..backup_models import BackupArtifact
    now = now or datetime.now()
    last, artifacts = {}, {}
    for kind in ("kunlik", "haftalik", "tiklash_sinovi"):
        row = db.execute(select(Backup, BackupArtifact).join(BackupArtifact, Backup.id == BackupArtifact.backup_id)
                         .where(Backup.kind == kind).order_by(Backup.ts.desc(), Backup.id.desc())).first()
        last[kind] = row[0] if row else None
        artifacts[kind] = row[1] if row else None
    since = now - timedelta(days=30)
    stat = {}
    for row, artifact in db.execute(select(Backup, BackupArtifact).join(BackupArtifact, Backup.id == BackupArtifact.backup_id).where(Backup.ts >= since)):
        st = stat.setdefault(row.kind, {"ok": 0, "warning": 0})
        st["warning" if artifact.manifest["audit"]["broken"] else "ok"] += 1
    legacy = db.scalar(select(func.count(Backup.id)).where(~select(BackupArtifact.backup_id).where(BackupArtifact.backup_id == Backup.id).exists()))
    return {"last": last, "artifacts": artifacts, "stat30": stat, "legacy_count": legacy}

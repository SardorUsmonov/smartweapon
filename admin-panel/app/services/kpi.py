"""KPI va agregatlar: respublika, hudud, bo'linma, qurolxona darajasida."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from ..models import Alarm, Armory, Cabinet, Custody, Event, Item, Mode, Region, Unit


def scope_filters(scope_kind: str, scope_id: int | None):
    """Qaytaradi: (armory filter, cabinet-join kerakmi). Barcha so'rovlar armory orqali ierarxiyaga bog'lanadi."""
    if scope_kind == "hudud":
        return lambda q: q.join(Unit, Unit.id == Armory.unit_id).where(Unit.region_id == scope_id)
    if scope_kind == "bolinma":
        return lambda q: q.where(Armory.unit_id == scope_id)
    if scope_kind == "qurolxona":
        return lambda q: q.where(Armory.id == scope_id)
    return lambda q: q


def armory_ids_for_scope(db: Session, scope_kind: str, scope_id: int | None) -> list[int] | None:
    if scope_kind == "respublika":
        return None
    if scope_kind not in {"hudud", "bolinma", "qurolxona"} or scope_id is None:
        return []
    f = scope_filters(scope_kind, scope_id)
    q = f(select(Armory.id))
    return [r[0] for r in db.execute(q)]


def weapon_custody_counts(db: Session, armory_ids: list[int] | None = None, now: datetime | None = None) -> dict:
    """Item-list KPI: distinct weapons with visible open custody, regardless of stale Item.state."""
    now = now or datetime.now()
    scope_cabinets = select(Cabinet.id).where(Cabinet.armory_id.in_(armory_ids)) if armory_ids is not None else None

    def count(*conditions):
        custody = select(Custody.item_id).where(Custody.returned_at.is_(None), *conditions)
        items = select(func.count(func.distinct(Item.id))).where(Item.kind == "qurol")
        if scope_cabinets is not None:
            custody = custody.where(Custody.cabinet_id.in_(scope_cabinets))
            items = items.where(Item.cabinet_id.in_(scope_cabinets))
        return db.scalar(items.where(Item.id.in_(custody))) or 0

    return {"berilgan": count(), "kechikish": count(Custody.due_at < now)}


def armory_weapon_custody_counts(db: Session, armory_ids: list[int], now: datetime | None = None) -> dict[int, dict]:
    """Each armory row matches that armory's item-list filter on both cabinet references."""
    now = now or datetime.now()
    counts = {arm_id: {"berilgan": 0, "kechikish": 0} for arm_id in armory_ids}
    if not armory_ids:
        return counts
    current_cab, custody_cab = aliased(Cabinet), aliased(Cabinet)
    query = (select(current_cab.armory_id, func.count(func.distinct(Item.id))).select_from(Item)
             .join(current_cab, current_cab.id == Item.cabinet_id)
             .join(Custody, Custody.item_id == Item.id).join(custody_cab, custody_cab.id == Custody.cabinet_id)
             .where(Item.kind == "qurol", Custody.returned_at.is_(None), current_cab.armory_id.in_(armory_ids),
                    custody_cab.armory_id == current_cab.armory_id).group_by(current_cab.armory_id))
    for arm_id, total in db.execute(query):
        counts[arm_id]["berilgan"] = total
    for arm_id, total in db.execute(query.where(Custody.due_at < now)):
        counts[arm_id]["kechikish"] = total
    return counts


def kpis(db: Session, scope_kind: str = "respublika", scope_id: int | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    ids = armory_ids_for_scope(db, scope_kind, scope_id)

    def cab_q(*extra):
        q = select(func.count(Cabinet.id))
        if ids is not None:
            q = q.where(Cabinet.armory_id.in_(ids))
        return q.where(*extra) if extra else q

    def ev_q(*extra):
        q = select(func.count(Event.id))
        if ids is not None:
            q = q.where(Event.armory_id.in_(ids))
        return q.where(*extra)

    total_cab = db.scalar(cab_q()) or 0
    armories_total = db.scalar(select(func.count(Armory.id)).where(Armory.id.in_(ids)) if ids is not None else select(func.count(Armory.id))) or 0
    armories_offline = db.scalar((select(func.count(Armory.id)).where(Armory.online.is_(False), Armory.id.in_(ids))) if ids is not None else select(func.count(Armory.id)).where(Armory.online.is_(False))) or 0

    custody_counts = weapon_custody_counts(db, ids, now)
    issued, overdue = custody_counts["berilgan"], custody_counts["kechikish"]

    blocked = db.scalar(cab_q(Cabinet.status.in_(["bloklangan", "nosoz", "xizmatda"]))) or 0
    ops_today = db.scalar(ev_q(Event.ts_server >= day_start, Event.type.in_(["avtomat_olindi", "avtomat_qaytarildi", "pm_olindi", "pm_qaytarildi"]))) or 0
    denied_today = db.scalar(ev_q(Event.ts_server >= day_start, Event.type.in_(["rad_etildi", "rad_etildi_takror"]))) or 0
    emergency_30d = db.scalar(ev_q(Event.ts_server >= now - timedelta(days=30), Event.type == "favqulodda_ochish")) or 0

    disc_q = select(func.count(Custody.id)).where(Custody.match_ok.is_(False), Custody.returned_at >= now - timedelta(days=30))
    if ids is not None:
        disc_q = disc_q.join(Cabinet, Cabinet.id == Custody.cabinet_id).where(Cabinet.armory_id.in_(ids))
    discrepancies = db.scalar(disc_q) or 0

    alarms_q = select(func.count(Alarm.id)).where(Alarm.resolved_at.is_(None))
    if ids is not None:
        alarms_q = alarms_q.where(Alarm.armory_id.in_(ids))
    active_alarms = db.scalar(alarms_q) or 0
    ack_q = select(func.count(Alarm.id)).where(Alarm.resolved_at.is_(None), Alarm.requires_ack.is_(True), Alarm.acked_at.is_(None))
    if ids is not None:
        ack_q = ack_q.where(Alarm.armory_id.in_(ids))
    pending_ack = db.scalar(ack_q) or 0

    weapons_total_q = select(func.count(Item.id)).where(Item.kind == "qurol")
    if ids is not None:
        weapons_total_q = weapons_total_q.join(Cabinet, Cabinet.id == Item.cabinet_id).where(Cabinet.armory_id.in_(ids))
    weapons_total = db.scalar(weapons_total_q) or 0

    return {
        "yacheykalar": total_cab, "qurolxonalar": armories_total, "qurolxona_onlayn": armories_total - armories_offline,
        "qurolxona_oflayn": armories_offline, "berilgan": issued, "kechikish": overdue, "bloklangan": blocked,
        "sutkalik": ops_today, "rad_etilgan": denied_today, "favqulodda": emergency_30d, "inventar_farqlari": discrepancies,
        "faol_signallar": active_alarms, "tasdiq_kutmoqda": pending_ack, "qurollar_jami": weapons_total,
        "qurollar_mavjud": max(weapons_total - issued, 0),
    }


def region_rows(db: Session, now: datetime | None = None, armory_ids: list[int] | None = None) -> list[dict]:
    """Hududlar jadvali: har hudud bo'yicha yacheyka, berilgan, kechikish, rad etish, signal, oflayn va holat."""
    now = now or datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows: dict[int, dict] = {}
    arms = select(Armory.id, Unit.region_id).join(Unit, Unit.id == Armory.unit_id)
    if armory_ids is not None:
        arms = arms.where(Armory.id.in_(armory_ids))
    arm_reg = dict(db.execute(arms).all())
    region_query = select(Region).order_by(Region.order)
    if armory_ids is not None:
        region_query = region_query.where(Region.id.in_(set(arm_reg.values())))
    for r in db.execute(region_query).scalars():
        rows[r.id] = {"id": r.id, "code": r.code, "name": r.name, "short": r.short, "yacheyka": 0, "berilgan": 0,
                      "kechikish": 0, "rad": 0, "signal": 0, "oflayn": 0, "qurolxona": 0, "status": "good"}
    for arm_id, cnt in db.execute(select(Cabinet.armory_id, func.count(Cabinet.id)).group_by(Cabinet.armory_id)):
        if arm_id in arm_reg:
            rows[arm_reg[arm_id]]["yacheyka"] += cnt
    for arm_id, online in db.execute(select(Armory.id, Armory.online)):
        if arm_id not in arm_reg:
            continue
        rows[arm_reg[arm_id]]["qurolxona"] += 1
        if not online:
            rows[arm_reg[arm_id]]["oflayn"] += 1
    for region_id, row in rows.items():
        visible_ids = [arm_id for arm_id, reg_id in arm_reg.items() if reg_id == region_id]
        row.update(weapon_custody_counts(db, visible_ids, now))
    events_query = select(Event.region_id, func.count(Event.id)).where(Event.ts_server >= day_start, Event.type.in_(["rad_etildi", "rad_etildi_takror"]))
    alarms_query = select(Alarm.region_id, func.count(Alarm.id)).where(Alarm.resolved_at.is_(None), Alarm.level.in_(["CRITICAL", "SECURITY"]))
    if armory_ids is not None:
        events_query = events_query.where(Event.armory_id.in_(armory_ids))
        alarms_query = alarms_query.where(Alarm.armory_id.in_(armory_ids))
    for reg_id, cnt in db.execute(events_query.group_by(Event.region_id)):
        if reg_id in rows:
            rows[reg_id]["rad"] += cnt
    for reg_id, cnt in db.execute(alarms_query.group_by(Alarm.region_id)):
        if reg_id in rows:
            rows[reg_id]["signal"] += cnt
    for r in rows.values():
        if r["signal"] or r["oflayn"]:
            r["status"] = "critical"
        elif r["kechikish"]:
            r["status"] = "warning"
        r["badge"] = r["kechikish"] + r["signal"] + r["oflayn"]
    return sorted(rows.values(), key=lambda x: -x["yacheyka"])


def daily_ops(db: Session, days: int = 7, armory_ids: list[int] | None = None, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    out = []
    names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    for i in range(days - 1, -1, -1):
        d0 = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        d1 = d0 + timedelta(days=1)
        q = select(func.count(Event.id)).where(Event.ts_server >= d0, Event.ts_server < d1,
                                              Event.type.in_(["avtomat_olindi", "avtomat_qaytarildi", "pm_olindi", "pm_qaytarildi"]))
        if armory_ids is not None:
            q = q.where(Event.armory_id.in_(armory_ids))
        out.append({"date": d0.date().isoformat(), "label": names[d0.weekday()], "value": db.scalar(q) or 0, "today": i == 0})
    return out


def active_modes(db: Session) -> list[Mode]:
    return list(db.execute(select(Mode).where(Mode.ended_at.is_(None)).order_by(Mode.started_at.desc())).scalars())

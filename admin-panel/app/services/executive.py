"""Scoped, source-backed summaries for the leadership situation center."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..config import DEMO_MODE, TZ_OFFSET_HOURS
from ..models import Alarm, Armory, Cabinet, Item, Region, Unit
from .events import LEVEL_LABEL


LOCAL_TZ = timezone(timedelta(hours=TZ_OFFSET_HOURS))


def _active_at(instant: datetime, *, historical: bool = False) -> tuple:
    """Current state follows workflow completion; history follows stored times.

    A non-null resolution means the application completed the workflow even if
    a faulty clock wrote a future timestamp. Prior comparisons reconstruct the
    saved lifecycle and cannot correct such clock discrepancies.
    """
    resolved = or_(Alarm.resolved_at.is_(None), Alarm.resolved_at > instant) if historical else Alarm.resolved_at.is_(None)
    return Alarm.opened_at <= instant, resolved


def leadership_snapshot(
    db: Session, regions: list[dict], armory_ids: list[int] | None = None,
    now: datetime | None = None,
) -> dict:
    """Read the visible inventory and alarm lifecycle; never synthesize telemetry.

    Existing DateTime columns contain local Uzbekistan wall time. ``asOf`` is the
    time of this database snapshot, not the devices' last synchronization. A
    region's timestamp is its oldest site update so a fresh site cannot conceal
    a stale one. Missing updates keep connection totals unknown.
    """
    instant = now or datetime.now(LOCAL_TZ)
    instant = instant.replace(tzinfo=LOCAL_TZ) if instant.tzinfo is None else instant.astimezone(LOCAL_TZ)
    local_now = instant.replace(tzinfo=None)
    cutoff = local_now - timedelta(days=1)
    stale_minutes = 15

    def iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value.replace(tzinfo=LOCAL_TZ) if value.tzinfo is None else value.astimezone(LOCAL_TZ)
        return aware.isoformat(timespec="seconds")

    region_ids = {row["id"] for row in regions}
    query = (select(Armory.id, Unit.region_id, Armory.online, Armory.last_sync)
             .join(Unit, Unit.id == Armory.unit_id).where(Unit.region_id.in_(region_ids)))
    if armory_ids is not None:
        query = query.where(Armory.id.in_(armory_ids))
    sites = db.execute(query).all()
    visible_ids = [site.id for site in sites]
    by_region = {region_id: [] for region_id in region_ids}
    for site in sites:
        by_region[site.region_id].append(site)

    weapons = dict(db.execute(
        select(Unit.region_id, func.count(Item.id)).select_from(Item)
        .join(Cabinet, Cabinet.id == Item.cabinet_id).join(Armory, Armory.id == Cabinet.armory_id)
        .join(Unit, Unit.id == Armory.unit_id)
        .where(Item.kind == "qurol", Armory.id.in_(visible_ids)).group_by(Unit.region_id)
    ).all())

    def alarm_counts(at: datetime, *, historical: bool = False) -> tuple[dict[int, dict], dict]:
        # Use the owning armory's region, not a possibly incomplete historical
        # Alarm.region_id. The same visible armories define both periods.
        active = _active_at(at, historical=historical)
        result = {region_id: {"critical": 0, "warning": 0} for region_id in region_ids}
        q = (select(Unit.region_id, Alarm.level, func.count(Alarm.id)).select_from(Alarm)
             .join(Armory, Armory.id == Alarm.armory_id).join(Unit, Unit.id == Armory.unit_id)
             .where(*active, Armory.id.in_(visible_ids), Alarm.level.in_(["CRITICAL", "SECURITY", "WARNING"]))
             .group_by(Unit.region_id, Alarm.level))
        for region_id, level, count in db.execute(q):
            result[region_id]["warning" if level == "WARNING" else "critical"] += count
        # Centrally registered records without a site remain visible in the
        # national total, explicitly identified as unmapped. Scoped users must
        # never receive them.
        unassigned = {"critical": 0, "warning": 0}
        if armory_ids is None:
            q = (select(Alarm.level, func.count(Alarm.id)).where(*active, Alarm.armory_id.is_(None),
                 Alarm.level.in_(["CRITICAL", "SECURITY", "WARNING"])).group_by(Alarm.level))
            for level, count in db.execute(q):
                unassigned["warning" if level == "WARNING" else "critical"] += count
        return result, unassigned

    current, unmapped_current = alarm_counts(local_now)
    previous, unmapped_previous = alarm_counts(cutoff, historical=True)
    rows = []
    for region in regions:
        owned = by_region[region["id"]]
        updates = [site.last_sync for site in owned if site.last_sync is not None]
        missing = len(owned) - len(updates)
        stale = sum((local_now - update).total_seconds() >= stale_minutes * 60 for update in updates)
        online = sum(bool(site.online) for site in owned if site.last_sync is not None)
        offline = sum(not site.online for site in owned if site.last_sync is not None)
        critical, warning = current[region["id"]]["critical"], current[region["id"]]["warning"]
        state = ("critical" if critical else "warning" if warning or offline
                 else "unknown" if not owned or missing else "stable")
        rows.append({
            "id": region["id"], "code": region["code"], "name": region["name"], "short": region["short"],
            "sites": len(owned), "stock": weapons.get(region["id"], 0),
            "critical": critical if owned else None, "warning": warning if owned else None,
            "online": online if owned and not missing else None,
            "offline": offline if owned and not missing else None,
            "knownOnline": online, "knownOffline": offline, "missingTelemetrySites": missing,
            "telemetrySites": len(updates), "staleSites": stale,
            "updatedAt": iso(min(updates)) if updates and not missing else None,
            "stale": bool(stale), "state": state, "href": f"/hudud/{region['id']}",
            "previous": {**previous[region["id"]], "offline": None} if owned else
                        {"critical": None, "warning": None, "offline": None},
        })

    unassigned_stock = 0
    if armory_ids is None:
        unassigned_stock = db.scalar(select(func.count(Item.id)).where(Item.kind == "qurol", Item.cabinet_id.is_(None))) or 0
    total_missing = sum(row["missingTelemetrySites"] for row in rows)
    total_online = sum(row["knownOnline"] for row in rows)
    total_offline = sum(row["knownOffline"] for row in rows)
    return {
        "asOf": iso(instant), "demo": DEMO_MODE, "staleMinutes": stale_minutes, "regions": rows,
        "previousAsOf": iso(cutoff),
        "totals": {
            "sites": len(sites), "stock": sum(weapons.values()) + unassigned_stock,
            "critical": sum(value["critical"] for value in current.values()) + unmapped_current["critical"],
            "warning": sum(value["warning"] for value in current.values()) + unmapped_current["warning"],
            "online": total_online if sites and not total_missing else None,
            "offline": total_offline if sites and not total_missing else None,
            "knownOnline": total_online, "knownOffline": total_offline,
            "missingTelemetrySites": total_missing, "telemetrySites": len(sites) - total_missing,
            "staleSites": sum(row["staleSites"] for row in rows),
        },
        "previousTotals": {
            "critical": sum(value["critical"] for value in previous.values()) + unmapped_previous["critical"],
            "warning": sum(value["warning"] for value in previous.values()) + unmapped_previous["warning"],
            "offline": None,
        },
        "unassigned": {**unmapped_current, "stock": unassigned_stock},
        "sourceNote": "Hisoblar bazadagi yozuvlardan. Hudud vaqti — obyektlar orasidagi eng eski sinxronlash vaqti.",
        "comparisonNote": "24 soat oldingi signallar saqlangan ochilish va yopilish yozuvlaridan, hozirgi vakolatdagi obyektlar bo'yicha tiklandi. Aloqa holati tarixi mavjud emas.",
    }


def overview(
    db: Session, k: dict, regions: list[dict], armory_ids: list[int] | None = None,
    now: datetime | None = None,
) -> dict:
    """Return active conditions only; dates come from stored armory telemetry."""
    instant = now or datetime.now(LOCAL_TZ)
    local_now = instant.astimezone(LOCAL_TZ).replace(tzinfo=None) if instant.tzinfo else instant
    conditions = _active_at(local_now)
    unacknowledged = Alarm.acked_at.is_(None)
    active = select(Alarm).where(*conditions)
    level_counts = select(Alarm.level, func.count(Alarm.id)).where(*conditions).group_by(Alarm.level)
    pending_ack = select(func.count(Alarm.id)).where(*conditions, Alarm.requires_ack.is_(True), unacknowledged)
    alarm_regions = (select(func.coalesce(Unit.region_id, Alarm.region_id)).select_from(Alarm)
                     .outerjoin(Armory, Armory.id == Alarm.armory_id).outerjoin(Unit, Unit.id == Armory.unit_id)
                     .where(*conditions))
    offline_regions = select(Unit.region_id).join(Armory, Armory.unit_id == Unit.id).where(Armory.online.is_(False))
    last_sync = select(func.max(Armory.last_sync))
    if armory_ids is not None:
        active = active.where(Alarm.armory_id.in_(armory_ids))
        level_counts = level_counts.where(Alarm.armory_id.in_(armory_ids))
        pending_ack = pending_ack.where(Alarm.armory_id.in_(armory_ids))
        alarm_regions = alarm_regions.where(Alarm.armory_id.in_(armory_ids))
        offline_regions = offline_regions.where(Armory.id.in_(armory_ids))
        last_sync = last_sync.where(Armory.id.in_(armory_ids))

    counts = dict(db.execute(level_counts).all())
    affected = set(db.scalars(alarm_regions)) | set(db.scalars(offline_regions))
    visible_regions = {r["id"] for r in regions}
    total_armories = k["qurolxonalar"]
    summary = {
        "active_critical": counts.get("CRITICAL", 0) + counts.get("SECURITY", 0),
        "active_warning": counts.get("WARNING", 0),
        "pending_ack": db.scalar(pending_ack) or 0,
        "total_active": sum(counts.values()),
        "latest_sync": db.scalar(last_sync),
        "affected_regions": len(affected & visible_regions),
        "region_total": len(regions),
        "online_percent": round(k["qurolxona_onlayn"] / total_armories * 100, 1) if total_armories else None,
    }

    urgency = case((Alarm.level.in_(["CRITICAL", "SECURITY"]), 0), (Alarm.level == "WARNING", 1), else_=2)
    acknowledgement = case((unacknowledged, 0), else_=1)
    attention = []
    for alarm in db.scalars(active.order_by(urgency, acknowledgement, Alarm.opened_at.desc(), Alarm.id.desc()).limit(4)):
        armory = db.get(Armory, alarm.armory_id) if alarm.armory_id else None
        unit = db.get(Unit, armory.unit_id) if armory else db.get(Unit, alarm.unit_id) if alarm.unit_id else None
        region_id = unit.region_id if armory and unit else alarm.region_id
        region = db.get(Region, region_id) if region_id else None
        acked = alarm.acked_at is not None
        location = " · ".join(part for part in (region.short if region else "", unit.name if unit else "", armory.name if armory else "") if part)
        attention.append({
            "id": alarm.id,
            "title": alarm.title,
            "detail": alarm.detail,
            "location": location or "Respublika",
            "ts": alarm.opened_at,
            "level": alarm.level,
            "level_label": LEVEL_LABEL.get(alarm.level, alarm.level),
            "acked": acked,
            "needs_ack": bool(alarm.requires_ack and not acked),
            "href": f"/signal/{alarm.id}",
        })
    return {"exec_summary": summary, "attention": attention}

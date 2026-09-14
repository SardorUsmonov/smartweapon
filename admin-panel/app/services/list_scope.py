"""Location filters shared by list pages; requested locations only narrow user scope."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import Ctx
from ..models import Armory, Region, Unit
from .kpi import armory_ids_for_scope


def filter_id(value: str | int | None) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return -1  # An invalid selection must not silently expand to every location.


def location_context(db: Session, ctx: Ctx, hudud="", bolinma="", qurolxona="") -> dict:
    selected = {"hudud": filter_id(hudud), "bolinma": filter_id(bolinma), "qurolxona": filter_id(qurolxona)}
    scope_ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)
    query = (select(Armory, Unit, Region).join(Unit, Unit.id == Armory.unit_id)
             .join(Region, Region.id == Unit.region_id).order_by(Region.order, Unit.name, Armory.name, Armory.id))
    if scope_ids is not None:
        query = query.where(Armory.id.in_(scope_ids))
    available = db.execute(query).all()
    filtered = [a.id for a, u, r in available
                if (not selected["hudud"] or r.id == selected["hudud"])
                and (not selected["bolinma"] or u.id == selected["bolinma"])
                and (not selected["qurolxona"] or a.id == selected["qurolxona"])]
    ids = filtered if any(selected.values()) else scope_ids
    options = {"hudud": {}, "bolinma": {}, "qurolxona": {}}
    for a, u, r in available:
        options["hudud"][r.id] = r.short
        options["bolinma"][u.id] = f"{r.short} · {u.name}"
        options["qurolxona"][a.id] = f"{r.short} · {u.name} · {a.name}"
    labels = {"hudud": ("Hudud", "Barcha hududlar"), "bolinma": ("Bo'linma", "Barcha bo'linmalar"),
              "qurolxona": ("Qurolxona", "Barcha qurolxonalar")}
    fields = [{"name": key, "label": labels[key][0], "all_label": labels[key][1], "value": selected[key],
               "options": list(options[key].items()), "known": selected[key] in options[key]}
              for key in selected]
    return {"selected": selected, "ids": ids, "scope_ids": scope_ids, "fields": fields}

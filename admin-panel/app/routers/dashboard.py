"""Respublika dashboardi (kirish ekrani) va uning jonli qismlari."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..i18n import t as translate
from ..models import Alarm, Armory, Cabinet, Event, Region, Unit
from ..services import kpi as kpisvc
from ..services.executive import LOCAL_TZ, leadership_snapshot, overview
from ..services.events import ALARM_BADGE, LEVEL_LABEL
from ..services.mapsvg import region_paths

router = APIRouter()


def _scope(ctx: Ctx):
    return ctx.scope_kind, ctx.scope_id


def _ids(db: Session, ctx: Ctx):
    return kpisvc.armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)


def _executive_context(db: Session, ctx: Ctx) -> dict:
    snapshot_at = datetime.now(LOCAL_TZ)
    local_now = snapshot_at.replace(tzinfo=None)
    ids = _ids(db, ctx)
    k = kpisvc.kpis(db, *_scope(ctx), now=local_now)
    rows = kpisvc.region_rows(db, now=local_now, armory_ids=ids)
    return {
        "k": k, "rows": rows, "map_svg": region_paths(rows, executive=True),
        "leadership": _leadership_context(db, ctx, rows, ids, now=snapshot_at),
        **overview(db, k, rows, armory_ids=ids, now=snapshot_at),
    }


def _leadership_context(
    db: Session, ctx: Ctx, rows: list[dict], ids: list[int] | None, now: datetime | None = None,
) -> dict:
    snapshot = leadership_snapshot(db, rows, armory_ids=ids, now=now)
    for row in snapshot["regions"]:
        row["name"] = translate(row["name"], ctx.lang)
        row["short"] = translate(row["short"], ctx.lang)
    for key in ("sourceNote", "comparisonNote"):
        snapshot[key] = translate(snapshot[key], ctx.lang)
    return snapshot


def alerts_feed(db: Session, limit: int = 6, armory_ids: list[int] | None = None) -> list[dict]:
    """Signal lentasi: faol signallar + so'nggi SECURITY/INFO hodisalar aralashmasi, vaqt bo'yicha."""
    q = select(Alarm).where(Alarm.resolved_at.is_(None)).order_by(Alarm.opened_at.desc()).limit(limit)
    if armory_ids is not None:
        q = q.where(Alarm.armory_id.in_(armory_ids))
    rows = []
    for a in db.execute(q).scalars():
        badge = ALARM_BADGE.get(a.type, "OGOHLANTIRISH" if a.level == "WARNING" else "SIGNAL")
        rows.append({"kind": "alarm", "id": a.id, "level": a.level, "badge": badge, "ts": a.opened_at, "title": a.detail or a.title,
                     "detail": a.title, "cabinet_id": a.cabinet_id, "armory_id": a.armory_id, "acked": bool(a.acked_at), "requires_ack": a.requires_ack})
    eq = select(Event).where(Event.level.in_(["SECURITY", "INFO"]), Event.type.in_(["huquq_berish_tasdiqlandi", "smena_ochildi", "texnik_xizmat", "rejim_boshlandi", "favqulodda_ochish", "mexanik_kalit"]))\
        .order_by(Event.ts_server.desc()).limit(limit)
    if armory_ids is not None:
        eq = eq.where(Event.armory_id.in_(armory_ids))
    for e in db.execute(eq).scalars():
        where = _where(db, e.armory_id) or "Respublika · Sozlamalar"
        rows.append({"kind": "event", "id": e.id, "level": e.level, "badge": "XAVFSIZLIK" if e.level == "SECURITY" else "AXBOROT",
                     "ts": e.ts_server, "title": where, "detail": e.title + (" · " + e.detail if e.detail else ""), "cabinet_id": e.cabinet_id,
                     "armory_id": e.armory_id, "acked": True, "requires_ack": False})
    rows.sort(key=lambda r: r["ts"], reverse=True)
    return rows[:limit]


def _where(db: Session, armory_id: int | None) -> str:
    if not armory_id:
        return ""
    a = db.get(Armory, armory_id)
    return f"{a.unit.region.short} · {a.unit.name}" if a else ""


@router.get("/")
def dashboard(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    sk, sid = _scope(ctx)
    if sk == "hudud" and sid:
        return _region_redirect(sid)
    if sk == "bolinma":
        unit = db.get(Unit, sid)
        if not unit:
            raise HTTPException(403, "Vakolat doirasi topilmadi.")
        return RedirectResponse(f"/hudud/{unit.region_id}/bolinma/{unit.id}", status_code=303)
    if sk == "qurolxona":
        return RedirectResponse(f"/qurolxona/{sid}", status_code=303)
    return render(request, "dashboard.html", ctx, active="respublika", **_executive_context(db, ctx),
                  feed=alerts_feed(db, armory_ids=_ids(db, ctx)), days=kpisvc.daily_ops(db, armory_ids=_ids(db, ctx)),
                  title="Respublika bo'yicha holat")


def _region_redirect(region_id: int):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"/hudud/{region_id}", status_code=303)


# ---- jonli qismlar (HTMX) ----
@router.get("/partials/executive")
def p_executive(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "partials/executive.html", ctx, **_executive_context(db, ctx))


@router.get("/partials/kpi")
def p_kpi(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "partials/kpi.html", ctx, k=kpisvc.kpis(db, *_scope(ctx)))


@router.get("/partials/map")
def p_map(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    rows = kpisvc.region_rows(db, armory_ids=_ids(db, ctx))
    return render(request, "partials/map.html", ctx, k=kpisvc.kpis(db, *_scope(ctx)), rows=rows, map_svg=region_paths(rows))


@router.get("/partials/feed")
def p_feed(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "partials/feed.html", ctx, feed=alerts_feed(db, armory_ids=_ids(db, ctx)), k=kpisvc.kpis(db, *_scope(ctx)))


@router.get("/partials/regions")
def p_regions(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "partials/regions_table.html", ctx, rows=kpisvc.region_rows(db, armory_ids=_ids(db, ctx)))


@router.get("/partials/chart")
def p_chart(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "partials/chart.html", ctx, days=kpisvc.daily_ops(db, armory_ids=_ids(db, ctx)))


@router.get("/partials/topbar")
def p_topbar(request: Request, ctx: Ctx = Depends(get_ctx)):
    from ..main import render
    return render(request, "partials/topbar_status.html", ctx)


@router.get("/api/kpi")
def api_kpi(ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    return kpisvc.kpis(db, *_scope(ctx))


@router.get("/api/map")
def api_map(db: Session = Depends(get_db), ctx: Ctx = Depends(get_ctx)):
    return kpisvc.region_rows(db, armory_ids=_ids(db, ctx))


@router.get("/api/leadership")
def api_leadership(db: Session = Depends(get_db), ctx: Ctx = Depends(get_ctx)):
    ids = _ids(db, ctx)
    return _leadership_context(db, ctx, kpisvc.region_rows(db, armory_ids=ids), ids)

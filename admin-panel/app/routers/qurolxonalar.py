"""Qurolxonalar bo'limi: ro'yxat, qurolxona sahifasi, smena ochish vizardi, smena yopish, smena hisoboti."""
from __future__ import annotations

from datetime import datetime
from math import ceil
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Armory, ArmoryShift, Officer, Region, Unit
from ..services import kpi as kpisvc
from ..services import smena_svc as svc
from ..services.events import ALARM_BADGE, LEVEL_LABEL
from ..services.list_scope import location_context

router = APIRouter()
PER_PAGE = 50


# ---------------- yordamchilar ----------------
def _scope_ids(db: Session, ctx: Ctx) -> list[int] | None:
    return kpisvc.armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)


def _armory(db: Session, ctx: Ctx, armory_id: int) -> Armory:
    a = db.get(Armory, armory_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Qurolxona topilmadi")
    ids = _scope_ids(db, ctx)
    if ids is not None and a.id not in ids:
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqari qurolxona")
    return a


def _crumbs(a: Armory, *tail: tuple[str, str | None]) -> list:
    base = [("Qurolxonalar", "/qurolxonalar"), (a.unit.region.short, f"/hudud/{a.unit.region_id}"),
            (a.unit.name, f"/qurolxona/{a.id}" if tail else None)]
    return base + list(tail)


def _pager(total: int, page: int, per_page: int, params: dict) -> dict:
    pages = max(1, ceil(total / per_page))
    page = min(max(1, page), pages)
    qs = {k: v for k, v in params.items() if v not in ("", None, 0)}
    base = urlencode(qs)
    return {"total": total, "page": page, "pages": pages, "per_page": per_page, "start": (page - 1) * per_page,
            "has_prev": page > 1, "has_next": page < pages, "qs": (base + "&") if base else ""}


def _user_name(ctx: Ctx) -> str:
    return ctx.user.full_name if ctx and ctx.user else "Navbatchi"


def _responsible(db: Session, a: Armory) -> Officer | None:
    if a.responsible_officer_id:
        return db.get(Officer, a.responsible_officer_id)
    return None


def _alarm_badge(al) -> str:
    return ALARM_BADGE.get(al.type, LEVEL_LABEL.get(al.level, "SIGNAL"))


# ---------------- ro'yxat ----------------
@router.get("/qurolxonalar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), hudud: str = "", holat: str = "",
              q: str = "", sort: str = "", page: int = 1, bolinma: str = "", qurolxona: str = ""):
    from ..main import render
    location = location_context(db, ctx, hudud, bolinma, qurolxona)
    ids = location["ids"]
    rows = svc.armory_rows(db, ids, holat=holat, q=q, sort=sort)
    all_rows = rows if (not holat and not q) else svc.armory_rows(db, ids)
    summary = {"jami": len(all_rows), "onlayn": sum(1 for r in all_rows if r["online"]), "oflayn": sum(1 for r in all_rows if not r["online"]),
               "smena": sum(1 for r in all_rows if r["smena"] is not None), "muammo": sum(1 for r in all_rows if r["status"] != "good"),
               "yacheyka": sum(r["yacheyka"] for r in all_rows), "berilgan": sum(r["berilgan"] for r in all_rows),
               "kechikish": sum(r["kechikish"] for r in all_rows)}
    params = {**location["selected"], "holat": holat, "q": q, "sort": sort}
    pg = _pager(len(rows), page, PER_PAGE, params)
    def list_link(**changes):
        return "/qurolxonalar?" + urlencode({k: v for k, v in {**params, **changes}.items() if v not in (None, "", 0)})
    page_rows = rows[pg["start"]:pg["start"] + PER_PAGE]
    region_query = select(Region).order_by(Region.order)
    if ids is not None:
        region_query = region_query.where(Region.id.in_(
            select(Unit.region_id).join(Armory, Armory.unit_id == Unit.id).where(Armory.id.in_(ids))))
    regions = db.execute(region_query).scalars().all()
    return render(request, "qurolxonalar/list.html", ctx, active="qurolxonalar", breadcrumb=[("Qurolxonalar", None)],
                  rows=page_rows, pg=pg, summary=summary, regions_all=regions, f_hudud=location["selected"]["hudud"], f_holat=holat, f_q=q, f_sort=sort,
                  location_fields=location["fields"], location_selected=location["selected"], list_link=list_link,
                  title="Qurolxonalar")


# ---------------- qurolxona sahifasi ----------------
@router.get("/qurolxona/{armory_id}")
def detail(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    a = _armory(db, ctx, armory_id)
    k = kpisvc.kpis(db, "qurolxona", a.id)
    shift = svc.open_shift(db, a.id)
    devs = svc.devices(db, a.id)
    plan = svc.cabinet_plan(db, a)
    alarms = svc.open_alarms(db, a.id)
    return render(request, "qurolxonalar/detail.html", ctx, active="qurolxonalar", breadcrumb=_crumbs(a), a=a, k=k, shift=shift,
                  shift_stats=svc.shift_stats(db, a.id, shift.opened_at) if shift else None,
                  devices=devs, metrics_text=svc.metrics_text, device_tone=svc.device_tone, kind_label=svc.DEVICE_KIND_LABEL,
                  plan=plan, events=svc.recent_events(db, a.id, 30), alarms=alarms, alarm_badge=_alarm_badge,
                  history=svc.shift_history(db, a.id, 6), history_total=svc.shift_count(db, a.id), responsible=_responsible(db, a),
                  assigned=sum(1 for c in a.cabinets if c.status == "biriktirilgan"), selfcheck_label=svc.SELFCHECK_LABEL,
                  title=a.name)


@router.get("/qurolxona/{armory_id}/partials/reja")
def p_plan(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    a = _armory(db, ctx, armory_id)
    return render(request, "qurolxonalar/_reja.html", ctx, a=a, plan=svc.cabinet_plan(db, a))


@router.get("/qurolxona/{armory_id}/partials/hodisalar")
def p_events(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    a = _armory(db, ctx, armory_id)
    return render(request, "qurolxonalar/_hodisalar.html", ctx, a=a, events=svc.recent_events(db, a.id, 30),
                  alarms=svc.open_alarms(db, a.id), alarm_badge=_alarm_badge)


@router.get("/qurolxona/{armory_id}/partials/qurilmalar")
def p_devices(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    a = _armory(db, ctx, armory_id)
    return render(request, "qurolxonalar/_qurilmalar.html", ctx, a=a, devices=svc.devices(db, a.id), metrics_text=svc.metrics_text,
                  device_tone=svc.device_tone, kind_label=svc.DEVICE_KIND_LABEL)


# ---------------- smena ochish vizardi ----------------
def _wizard(request, ctx, db, a, *, error: str = "", form: dict | None = None):
    from ..main import render
    chk = svc.selfcheck(db, a)
    rec = svc.reconcile(db, a)
    perm = svc.permits(db, a)
    return render(request, "qurolxonalar/smena_ochish.html", ctx, active="qurolxonalar",
                  breadcrumb=_crumbs(a, ("Smena ochish", None)), a=a, chk=chk, rec=rec, perm=perm, shift=svc.open_shift(db, a.id),
                  can_open=ctx.can("smena"), opened_by=_user_name(ctx), error=error, form=form or {}, elig_label=svc.ELIG_LABEL,
                  title="Smena ochish · " + a.unit.name)


@router.get("/qurolxona/{armory_id}/smena/ochish")
def shift_open_page(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    a = _armory(db, ctx, armory_id)
    return _wizard(request, ctx, db, a)


@router.post("/qurolxona/{armory_id}/smena/ochish")
def shift_open_post(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db),
                    opened_by: str = Form(""), permits_confirmed: str = Form(""), reconcile_confirmed: str = Form(""),
                    reason: str = Form(""), note: str = Form("")):
    a = _armory(db, ctx, armory_id)
    if not ctx.can("smena"):
        raise HTTPException(status_code=403, detail="Smena ochish faqat navbatchi yoki qurolxona mas'uli uchun")
    if svc.open_shift(db, a.id) is not None:
        return RedirectResponse(f"/qurolxona/{a.id}", status_code=303)
    form = {"opened_by": opened_by, "reason": reason, "note": note, "permits_confirmed": permits_confirmed, "reconcile_confirmed": reconcile_confirmed}
    chk = svc.selfcheck(db, a)
    rec = svc.reconcile(db, a)
    if permits_confirmed != "1":
        return _wizard(request, ctx, db, a, error="Ruxsat ro'yxatini tasdiqlash majburiy (3-qadam).", form=form)
    if rec["nomuvofiq"] and reconcile_confirmed != "1":
        return _wizard(request, ctx, db, a, error="Yacheyka va inventar farqlari bor: ular bilan tanishganingizni tasdiqlang (2-qadam).", form=form)
    if not chk["ok"] and len(reason.strip()) < 5:
        return _wizard(request, ctx, db, a, error="O'z-tekshiruv xatolar bilan yakunlandi: smenani ochish uchun sabab (kamida 5 belgi) kiriting.", form=form)
    perm = svc.permits(db, a)
    svc.open_new_shift(db, a, _user_name(ctx)[:80], chk, rec, perm, note=note.strip()[:300], reason=reason.strip()[:200])
    db.commit()
    return RedirectResponse(f"/qurolxona/{a.id}", status_code=303)


# ---------------- smena yopish ----------------
def _close_page(request, ctx, db, a, s, *, error: str = "", form: dict | None = None):
    from ..main import render
    now = datetime.now()
    resp = _responsible(db, a)
    return render(request, "qurolxonalar/smena_yopish.html", ctx, active="qurolxonalar",
                  breadcrumb=_crumbs(a, ("Smena yopish", None)), a=a, shift=s,
                  unreturned=svc.unreturned(db, a.id, now) , alarms=svc.open_alarms(db, a.id), alarm_badge=_alarm_badge,
                  stats=svc.shift_stats(db, a.id, s.opened_at) if s else None, can_close=ctx.can("smena"), closed_by=_user_name(ctx),
                  responsible=resp, error=error, form=form or {}, last_closed=svc.shift_history(db, a.id, 1),
                  title="Smena yopish · " + a.unit.name)


@router.get("/qurolxona/{armory_id}/smena/yopish")
def shift_close_page(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    a = _armory(db, ctx, armory_id)
    return _close_page(request, ctx, db, a, svc.open_shift(db, a.id))


@router.post("/qurolxona/{armory_id}/smena/yopish")
def shift_close_post(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db),
                     closed_by: str = Form(""), close_confirm: str = Form(""), ack_unreturned: str = Form(""),
                     ack_alarms: str = Form(""), note: str = Form(""), shift_id: int = Form(0)):
    a = _armory(db, ctx, armory_id)
    if not ctx.can("smena"):
        raise HTTPException(status_code=403, detail="Smena yopish faqat navbatchi yoki qurolxona mas'uli uchun")
    s = svc.open_shift(db, a.id)
    if s is None:
        return RedirectResponse(f"/qurolxona/{a.id}", status_code=303)
    if shift_id != s.id:
        raise HTTPException(409, "Smena o'zgargan. Yopish sahifasini yangilab, joriy smenani tekshiring.")
    form = {"closed_by": closed_by, "close_confirm": close_confirm, "note": note, "ack_unreturned": ack_unreturned, "ack_alarms": ack_alarms}
    if len(close_confirm.strip()) < 3:
        return _close_page(request, ctx, db, a, s, error="Mas'ul shaxs tasdig'i (F.I.Sh.) majburiy.", form=form)
    if svc.unreturned(db, a.id) and ack_unreturned != "1":
        return _close_page(request, ctx, db, a, s, error="Qaytarilmagan qurollar bor: ro'yxat bilan tanishganingizni tasdiqlang.", form=form)
    if svc.open_alarms(db, a.id) and ack_alarms != "1":
        return _close_page(request, ctx, db, a, s, error="Ochiq signallar bor: ular keyingi smenaga o'tishini tasdiqlang.", form=form)
    svc.close_shift(db, a, s, _user_name(ctx)[:80], close_confirm.strip()[:80], note=note.strip()[:300])
    db.commit()
    return RedirectResponse(f"/qurolxona/{a.id}/smena/{s.id}", status_code=303)


# ---------------- smena hisoboti va tarixi ----------------
@router.get("/qurolxona/{armory_id}/smenalar")
def shift_list(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), page: int = 1):
    from ..main import render
    a = _armory(db, ctx, armory_id)
    total = svc.shift_count(db, a.id)
    pg = _pager(total, page, PER_PAGE, {})
    rows = svc.shift_history(db, a.id, PER_PAGE, pg["start"])
    return render(request, "qurolxonalar/smenalar.html", ctx, active="qurolxonalar", breadcrumb=_crumbs(a, ("Smenalar", None)),
                  a=a, rows=rows, pg=pg, title="Smenalar · " + a.unit.name)


@router.get("/qurolxona/{armory_id}/smena/{shift_id}")
def shift_report(armory_id: int, shift_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    a = _armory(db, ctx, armory_id)
    s = db.get(ArmoryShift, shift_id)
    if s is None or s.armory_id != a.id:
        raise HTTPException(status_code=404, detail="Smena topilmadi")
    until = s.closed_at or datetime.now()
    closing = (s.reconcile or {}).get("yopish")
    stats = (closing or {}).get("statistika") if s.closed_at else None
    if stats is None:
        stats = svc.shift_stats(db, a.id, s.opened_at, until)
    return render(request, "qurolxonalar/smena_hisobot.html", ctx, active="qurolxonalar",
                  breadcrumb=_crumbs(a, ("Smenalar", f"/qurolxona/{a.id}/smenalar"), (s.report_ref or f"Smena #{s.id}", None)),
                  a=a, s=s, stats=stats, events=svc.recent_events(db, a.id, 100, s.opened_at, until),
                  selfcheck_label=svc.SELFCHECK_LABEL, yopish=closing, until=until,
                  title=(s.report_ref or "Smena hisoboti"))

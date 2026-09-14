"""Hisobotlar: 7 hisobot (oldindan ko'rish, filtrlar, sahifalash), eksport CSV/XLSX/PDF, eksportlar jurnali."""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import ExportLog
from ..services import hisobot_svc as svc

router = APIRouter()
PER_PAGE = svc.PER_PAGE
CRUMB = ("Hisobotlar", "/hisobotlar")


def _qs(d: dict) -> str:
    return urlencode({k: v for k, v in d.items() if v not in (None, "", 0)})


def _pages(total: int, per_page: int = PER_PAGE) -> int:
    return max((total + per_page - 1) // per_page, 1)


def _optional_id(value: str, field: str) -> int | None:
    if not value.strip():
        return None
    try:
        result = int(value)
        if result <= 0:
            raise ValueError
        return result
    except ValueError:
        raise HTTPException(422, f"{field}: musbat raqam talab qilinadi")


# ---------------- Bosh sahifa ----------------
@router.get("/hisobotlar")
def index(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    f = svc.resolve_filters(db, ctx, "qurollanganlik")
    ov = svc.overview(db, f)
    cards = [{"slug": s, **svc.REPORTS[s], "count": ov[s][0], "sub": ov[s][1], "tone": ov[s][2]} for s in svc.REPORT_ORDER]
    visible_ids = svc.visible_export_ids(db, ctx)
    where = [ExportLog.id.in_(visible_ids)] if visible_ids is not None else []
    recent = list(db.execute(select(ExportLog).where(*where).order_by(ExportLog.ts.desc()).limit(6)).scalars())
    n_exports = db.scalar(select(func.count(ExportLog.id)).where(*where)) or 0
    return render(request, "hisobotlar/index.html", ctx, active="hisobotlar", breadcrumb=[CRUMB], title="Hisobotlar",
                  cards=cards, recent=recent, n_exports=n_exports, reports=svc.EXPORT_REPORTS, scope=svc.scope_label(db, f), now=datetime.now())


# ---------------- Eksportlar jurnali (slug'dan OLDIN e'lon qilinadi) ----------------
@router.get("/hisobotlar/eksportlar")
def exports_list(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), hisobot: str = "", fmt: str = "",
                 kim: str = "", holat: str = "", dan: str = "", gacha: str = "", page: int = 1):
    from ..main import render
    now = datetime.now()
    visible_ids = svc.visible_export_ids(db, ctx)
    scope_where = [ExportLog.id.in_(visible_ids)] if visible_ids is not None else []
    where = list(scope_where)
    if hisobot in svc.EXPORT_REPORTS:
        where.append(ExportLog.report == hisobot)
    if fmt in svc.FORMATS:
        where.append(ExportLog.fmt == fmt)
    if kim.strip():
        where.append(ExportLog.username.like(f"%{kim.strip()}%"))
    if holat == "amalda":
        where.append(ExportLog.valid_until >= now)
    elif holat == "muddati_otgan":
        where.append(ExportLog.valid_until < now)
    d0 = svc._parse_date(dan); d1 = svc._parse_date(gacha)
    if d0:
        where.append(ExportLog.ts >= d0)
    if d1:
        where.append(ExportLog.ts < d1 + timedelta(days=1))
    total = db.scalar(select(func.count(ExportLog.id)).where(*where)) or 0
    pages = _pages(total)
    page = min(max(page, 1), pages)
    logs = list(db.execute(select(ExportLog).where(*where).order_by(ExportLog.ts.desc(), ExportLog.id.desc())
                           .offset((page - 1) * PER_PAGE).limit(PER_PAGE)).scalars())
    rows = []
    for lg in logs:
        rows.append({"log": lg, "title": svc.EXPORT_REPORTS.get(lg.report, {}).get("title", lg.report), "valid": bool(lg.valid_until and lg.valid_until >= now),
                     "file": svc.file_status(lg)})
    users = list(db.scalars(select(ExportLog.username).where(*scope_where).distinct().order_by(ExportLog.username)))
    filt = {"hisobot": hisobot, "fmt": fmt, "kim": kim, "holat": holat, "dan": dan, "gacha": gacha}
    n_valid = db.scalar(select(func.count(ExportLog.id)).where(*scope_where, ExportLog.valid_until >= now)) or 0
    return render(request, "hisobotlar/eksportlar.html", ctx, active="hisobotlar", breadcrumb=[CRUMB, ("Eksportlar jurnali", "")],
                  title="Eksportlar jurnali", rows=rows, total=total, page=page, pages=pages, filt=filt, base_qs=_qs(filt),
                  reports=svc.EXPORT_REPORTS, formats=svc.FORMATS, users=users, n_valid=n_valid, now=now)


@router.get("/hisobotlar/eksportlar/{log_id}")
def export_detail(log_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), yangi: int = 0):
    from ..main import render
    lg = db.get(ExportLog, log_id)
    if lg is None:
        raise HTTPException(404, "Eksport yozuvi topilmadi")
    if not svc.can_view_export(db, ctx, lg):
        raise HTTPException(403, "Bu eksport vakolat doirangizdan tashqarida")
    if lg.report == "jurnal":
        return RedirectResponse(f"/jurnal/eksport/{lg.id}", status_code=303)
    now = datetime.now()
    p = svc.file_path(lg)
    spec = svc.EXPORT_REPORTS.get(lg.report, {"title": lg.report})
    ev = svc.export_event(db, lg)
    payload = (ev.payload or {}) if ev else {}
    filters = payload.get("filters") or {}
    return render(request, "hisobotlar/eksport.html", ctx, active="hisobotlar", breadcrumb=[CRUMB, ("Eksportlar jurnali", "/hisobotlar/eksportlar"), (lg.number, "")],
                  title=f"Eksport {lg.number}", log=lg, spec=spec, valid=bool(lg.valid_until and lg.valid_until >= now), file=svc.file_status(lg),
                  size=p.stat().st_size if p.exists() else 0, event=ev, payload=payload, filters=filters, filter_qs=_qs(filters), yangi=yangi, now=now,
                  fmt_label=svc.FORMATS.get(lg.fmt, (lg.fmt.upper(), ""))[0])


@router.get("/hisobotlar/eksportlar/{log_id}/fayl")
def export_file(log_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    if not ctx.can("eksport"):
        raise HTTPException(403, "Eksportga ruxsat yo'q")
    lg = db.get(ExportLog, log_id)
    if lg is None:
        raise HTTPException(404, "Eksport yozuvi topilmadi")
    if not svc.can_view_export(db, ctx, lg):
        raise HTTPException(403, "Bu eksport vakolat doirangizdan tashqarida")
    if lg.valid_until and lg.valid_until < datetime.now():
        raise HTTPException(410, "Eksportning amal qilish muddati tugagan")
    p = svc.file_path(lg)
    if not p.exists():
        raise HTTPException(404, "Fayl topilmadi")
    if svc.file_status(lg)[1] != "Hash mos":
        raise HTTPException(409, "Fayl hash raqami jurnalga mos emas")
    media = svc.FORMATS.get(lg.fmt, ("", "application/octet-stream"))[1]
    return FileResponse(str(p), media_type=media, filename=f"{lg.number}_{lg.report}.{lg.fmt}")


# ---------------- Hisobot sahifasi ----------------
@router.get("/hisobotlar/{slug}")
def report_page(slug: str, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), dan: str = "", gacha: str = "",
                hudud: str = "", bolinma: str = "", kesim: str = "", page: int = 1, xato: str = ""):
    from ..main import render
    if slug == "jurnal":
        return RedirectResponse("/jurnal", status_code=303)
    if slug not in svc.REPORTS:
        raise HTTPException(404, "Hisobot topilmadi")
    spec = svc.REPORTS[slug]
    now = datetime.now()
    f = svc.resolve_filters(db, ctx, slug, dan, gacha, _optional_id(hudud, "Hudud"), _optional_id(bolinma, "Bo'linma"), kesim, now=now)
    page = max(page, 1)
    cols, rows, total, summary = svc.build(db, slug, f, page=page, now=now)
    pages = _pages(total)
    if page > pages:
        page = pages
        cols, rows, total, summary = svc.build(db, slug, f, page=page, now=now)
    fq = f.qs()
    quick_dates = [{"days": days, "label": label, "qs": _qs({**fq, "dan": (now - timedelta(days=days - 1)).strftime("%Y-%m-%d"),
                                                           "gacha": now.strftime("%Y-%m-%d")})}
                   for days, label in ((1, "Bugun"), (7, "7 kun"), (30, "30 kun"), (90, "90 kun"))]
    units = svc.units_for(db, f.hudud)
    if f.scope_locked in ("bolinma", "qurolxona"):
        units = [unit for unit in units if unit.id == f.bolinma]
    return render(request, "hisobotlar/report.html", ctx, active="hisobotlar", breadcrumb=[CRUMB, (spec["title"], "")], title=spec["title"],
                  slug=slug, spec=spec, cols=cols, rows=rows, total=total, summary=summary, page=page, pages=pages, per_page=PER_PAGE,
                  f=f, fq=fq, base_qs=_qs(fq), units=units, scope=svc.scope_label(db, f), formats=svc.FORMATS,
                  valid_days=svc.VALID_DAYS, xato=xato, now=now, export_max=svc.EXPORT_MAX_ROWS, quick_dates=quick_dates)


@router.post("/hisobotlar/{slug}/eksport")
def report_export(slug: str, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), fmt: str = Form("csv"), maqsad: str = Form(""),
                  muddat: int = Form(7), dan: str = Form(""), gacha: str = Form(""), hudud: int | None = Form(None), bolinma: int | None = Form(None),
                  kesim: str = Form("")):
    if slug not in svc.REPORTS:
        raise HTTPException(404, "Hisobot topilmadi")
    if not ctx.can("eksport"):
        raise HTTPException(403, "Eksportga ruxsat yo'q")
    f = svc.resolve_filters(db, ctx, slug, dan, gacha, hudud, bolinma, kesim)
    back = f"/hisobotlar/{slug}?" + _qs(f.qs())
    if not maqsad.strip():
        return RedirectResponse(back + "&xato=maqsad", status_code=303)
    if fmt not in svc.FORMATS:
        return RedirectResponse(back + "&xato=format", status_code=303)
    try:
        lg = svc.create_export(db, ctx, slug, fmt, maqsad, muddat, f)
    except ValueError as e:
        db.rollback()
        return RedirectResponse(back + "&xato=" + str(e), status_code=303)
    db.commit()
    return RedirectResponse(f"/hisobotlar/eksportlar/{lg.id}?yangi=1", status_code=303)

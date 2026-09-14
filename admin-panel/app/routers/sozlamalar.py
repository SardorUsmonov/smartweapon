"""Central system settings and reviewed user administration."""
from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, ROLE_LABEL, SCOPE_LABEL, get_ctx
from ..models import Armory, Region, SettingsAudit, Unit, User
from ..security_models import UserChange
from ..services import settings_svc as svc


def require_admin(ctx: Ctx = Depends(get_ctx)):
    if not ctx.can("sozlamalar") or ctx.scope_kind != "respublika":
        raise HTTPException(403, "Tizim sozlamalari respublika administratori uchun.")


router = APIRouter(prefix="/sozlamalar", dependencies=[Depends(require_admin)])


def _back(tab="foydalanuvchilar", **params):
    return RedirectResponse("/sozlamalar?" + urlencode({"tab": tab, **params}), status_code=303)


@router.get("")
def index(request: Request, tab: str = "foydalanuvchilar", q: str = "", page: int = 1,
          ok: str = "", xato: str = "", ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    if tab not in svc.TABS:
        raise HTTPException(404, "Bo‘lim topilmadi.")
    page = max(1, page)
    query = select(User)
    if q.strip():
        query = query.where(or_(User.username.ilike(f"%{q.strip()}%"), User.full_name.ilike(f"%{q.strip()}%")))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    pages = max(1, (total + 49) // 50)
    page = min(page, pages) if tab == "foydalanuvchilar" else page
    users = db.scalars(query.order_by(User.id).offset((page - 1) * 50).limit(50)).all()
    changes = db.scalars(select(UserChange).where(UserChange.status == "pending").order_by(UserChange.created_at).limit(100)).all()
    pending_names = {u.id: u for u in db.scalars(select(User).where(User.id.in_({c.user_id for c in changes} | {c.requested_by for c in changes})))}
    audit_q = select(SettingsAudit).order_by(SettingsAudit.id.desc())
    audit_total = db.scalar(select(func.count(SettingsAudit.id))) or 0
    if tab == "audit":
        pages = max(1, (audit_total + 49) // 50)
        page = min(page, pages)
    audits = db.scalars(audit_q.offset((page - 1) * 50).limit(50)).all() if tab == "audit" else []
    return render(request, "sozlamalar/index.html", ctx, title="Sozlamalar", active="sozlamalar",
                  breadcrumb=[("Sozlamalar", None)], tab=tab, tabs=svc.TABS, users=users, changes=changes,
                  pending_names=pending_names, fields=svc.values(db, tab), integrations=svc.INTEGRATIONS,
                  audits=audits, audit_total=audit_total, role_labels=ROLE_LABEL, scope_labels=SCOPE_LABEL,
                  total=total, page=page, pages=pages, q=q, ok=ok, xato=xato)


def _form(request, ctx, db, user=None, error="", submitted=None):
    from ..main import render
    data = submitted if submitted is not None else (svc.snapshot(user) if user else {
        "full_name": "", "role": "tekshiruvchi", "scope_kind": "hudud", "scope_id": "", "mfa": True, "active": True})
    return render(request, "sozlamalar/user_form.html", ctx, title="Foydalanuvchini tahrirlash" if user else "Yangi foydalanuvchi",
                  active="sozlamalar", breadcrumb=[("Sozlamalar", "/sozlamalar"), ("Foydalanuvchi", None)],
                  account=user, data=data, error=error, role_labels=ROLE_LABEL, scope_labels=SCOPE_LABEL,
                  regions=db.scalars(select(Region).order_by(Region.order)).all(),
                  units=db.scalars(select(Unit).order_by(Unit.region_id, Unit.name)).all(),
                  armories=db.scalars(select(Armory).order_by(Armory.unit_id, Armory.name)).all(),
                  password_min=svc.int_setting(db, "parol_min_belgi", 8, 8, 64))


@router.get("/foydalanuvchi/yangi")
def new_form(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    return _form(request, ctx, db)


@router.get("/foydalanuvchi/{user_id}")
def edit_form(user_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Foydalanuvchi topilmadi.")
    return _form(request, ctx, db, user)


async def _request_change(request, ctx, db, user=None):
    form = dict(await request.form())
    proposed = {k: form.get(k, "") for k in ("full_name", "role", "scope_kind", "scope_id", "mfa", "active")}
    # Each scope selector has its own name; an unchecked or stale selector cannot set another scope.
    if proposed["scope_kind"] != "respublika":
        proposed["scope_id"] = form.get("scope_" + proposed["scope_kind"], proposed["scope_id"])
    try:
        if form.get("tasdiq") != "1":
            raise svc.SettingsError("O‘zgarish so‘rovini yuborishni tasdiqlang.")
        svc.request_user_change(db, ctx.user, proposed, str(form.get("sabab", "")), user=user,
                                username=str(form.get("username", "")), password=str(form.get("password", "")))
    except svc.SettingsError as exc:
        db.rollback()
        proposed.update(username=form.get("username", ""), sabab=form.get("sabab", ""))
        response = _form(request, ctx, db, user, str(exc), proposed)
        response.status_code = 400
        return response
    return _back(ok="So‘rov yuborildi. O‘zgarish boshqa administrator tasdiqlagach kuchga kiradi.")


@router.post("/foydalanuvchi/yangi")
async def create_user(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    return await _request_change(request, ctx, db)


@router.post("/foydalanuvchi/{user_id}")
async def edit_user(user_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Foydalanuvchi topilmadi.")
    return await _request_change(request, ctx, db, user)


@router.post("/sorov/{change_id}/{decision}")
def decide(change_id: int, decision: str, tasdiq: str = Form(""), ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    if decision not in {"tasdiqlash", "rad"}:
        raise HTTPException(404, "Amal topilmadi.")
    change = db.get(UserChange, change_id)
    if not change:
        raise HTTPException(404, "So‘rov topilmadi.")
    try:
        if tasdiq != "1":
            raise svc.SettingsError("Qaroringizni tasdiqlang.")
        svc.decide_change(db, ctx.user, change, decision == "tasdiqlash")
    except svc.SettingsError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))
    return _back(ok="Qaror saqlandi va auditga yozildi.")


@router.post("/{group}/saqlash")
async def save(group: str, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    if group not in {"autentifikatsiya", "chegaralar", "saqlash"}:
        raise HTTPException(404, "Bo‘lim topilmadi.")
    form = dict(await request.form())
    try:
        if form.get("tasdiq") != "1":
            raise svc.SettingsError("Sozlamalar o‘zgarishini tasdiqlang.")
        count = svc.save_settings(db, ctx.user, group, form, str(form.get("sabab", "")))
    except svc.SettingsError as exc:
        db.rollback()
        return _back(group, xato=str(exc))
    return _back(group, ok=f"{count} ta sozlama saqlandi. O‘zgarishlar auditga yozildi.")

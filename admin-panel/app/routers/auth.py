"""Panelga kirish, MFA tasdig'i, profil va sessiyani yakunlash."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..deps import Ctx, ROLE_LABEL, SCOPE_LABEL, get_ctx
from ..models import Armory, Region, Unit, User
from ..security_models import LoginSession
from ..services import auth_svc as svc

router = APIRouter()


def _anonymous_ctx(request: Request) -> Ctx:
    lang = request.cookies.get("aq_lang", config.DEFAULT_LANG)
    return Ctx(user=None, lang=lang if lang in ("lat", "cyr") else "lat")


def _login_form(request: Request, db: Session, *, next_path: str = "/", username: str = "", error: str = "", status_code: int = 200):
    from ..main import render
    users = list(db.scalars(select(User).where(User.active.is_(True)).order_by(User.username))) if config.DEMO_MODE else []
    response = render(request, "auth/login.html", _anonymous_ctx(request), title="Tizimga kirish", users=users,
                      role_labels=ROLE_LABEL, scope_labels=SCOPE_LABEL, next_path=svc.safe_next(next_path), username=username,
                      error=error, demo_mode=config.DEMO_MODE)
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


def _session_cookie(response, request: Request, db: Session, token: str):
    session = db.get(LoginSession, svc.token_hash(token))
    max_age = max(1, int((session.expires_at - datetime.now()).total_seconds()))
    response.set_cookie(svc.COOKIE, token, max_age=max_age, httponly=True, secure=request.url.scheme == "https", samesite="strict", path="/")
    response.delete_cookie("aq_user", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/kirish")
def login_page(request: Request, db: Session = Depends(get_db), next: str = "/"):
    user, _session = svc.session_user(db, request.cookies.get(svc.COOKIE))
    if user:
        return RedirectResponse(svc.safe_next(next), status_code=303)
    return _login_form(request, db, next_path=next)


@router.post("/kirish")
def login(request: Request, db: Session = Depends(get_db), username: str = Form(""), password: str = Form(""), next: str = Form("/")):
    next_path = svc.safe_next(next)
    token, needs_mfa, error = svc.password_login(db, username, password, next_path)
    if not token:
        return _login_form(request, db, next_path=next_path, username=username[:40], error=error, status_code=401)
    previous = request.cookies.get(svc.COOKIE)
    if previous:
        svc.logout(db, previous)
    response = RedirectResponse("/kirish/mfa" if needs_mfa else next_path, status_code=303)
    return _session_cookie(response, request, db, token)


def _mfa_form(request: Request, user: User, *, error: str = "", status_code: int = 200):
    from ..main import render
    response = render(request, "auth/mfa.html", _anonymous_ctx(request), title="Kirishni tasdiqlash", username=user.username,
                      full_name=user.full_name, error=error, demo_mode=config.DEMO_MODE)
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/kirish/mfa")
def mfa_page(request: Request, db: Session = Depends(get_db)):
    user, session = svc.session_user(db, request.cookies.get(svc.COOKIE), stage="mfa")
    if not user or not session:
        return RedirectResponse("/kirish", status_code=303)
    return _mfa_form(request, user)


@router.post("/kirish/mfa")
def mfa(request: Request, db: Session = Depends(get_db), code: str = Form("")):
    pending = request.cookies.get(svc.COOKIE, "")
    user, _session = svc.session_user(db, pending, stage="mfa")
    if not user:
        response = RedirectResponse("/kirish", status_code=303)
        response.delete_cookie(svc.COOKIE, path="/")
        return response
    token, next_path, error = svc.mfa_login(db, pending, code)
    if not token:
        user, _session = svc.session_user(db, pending, stage="mfa")
        if user:
            return _mfa_form(request, user, error=error, status_code=401)
        response = _login_form(request, db, error=error, status_code=401)
        response.delete_cookie(svc.COOKIE, path="/")
        return response
    return _session_cookie(RedirectResponse(svc.safe_next(next_path), status_code=303), request, db, token)


@router.get("/profil")
def profile(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    _user, session = svc.session_user(db, request.cookies.get(svc.COOKIE))
    scope = "Respublika"
    if ctx.scope_kind == "hudud":
        row = db.get(Region, ctx.scope_id)
        scope = row.name if row else "Hudud topilmadi"
    elif ctx.scope_kind == "bolinma":
        row = db.get(Unit, ctx.scope_id)
        scope = f"{row.region.name} › {row.name}" if row else "Bo'linma topilmadi"
    elif ctx.scope_kind == "qurolxona":
        row = db.get(Armory, ctx.scope_id)
        scope = f"{row.unit.region.name} › {row.unit.name} › {row.name}" if row else "Qurolxona topilmadi"
    response = render(request, "auth/profile.html", ctx, title="Mening profilim", breadcrumb=[("Mening profilim", "")],
                      role_label=ROLE_LABEL.get(ctx.role, ctx.role), scope_label=scope,
                      scope_kind_label=SCOPE_LABEL.get(ctx.scope_kind, ctx.scope_kind), session=session, demo_mode=config.DEMO_MODE)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/chiqish")
def logout_confirmation():
    return RedirectResponse("/profil", status_code=303)


@router.post("/chiqish")
def logout(request: Request, db: Session = Depends(get_db)):
    svc.logout(db, request.cookies.get(svc.COOKIE))
    response = RedirectResponse("/kirish", status_code=303)
    response.delete_cookie(svc.COOKIE, path="/")
    response.delete_cookie("aq_user", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response

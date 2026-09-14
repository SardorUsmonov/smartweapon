"""Aqlli qurolxona: Nazorat markazi (admin panel). FastAPI + Jinja2 + HTMX."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config
from .db import Base, SessionLocal, engine
from .i18n import t as translate
from .models import Alarm, Mode, Region
from . import security_models  # registers additive tables before startup
from . import backup_models
from .deps import ROLE_LABEL, SCOPE_LABEL, Ctx, get_ctx
from .security import csrf_middleware, protect_forms
from .services.live import hub

app = FastAPI(title=config.APP_TITLE, docs_url="/api/docs", redoc_url=None)
app.middleware("http")(csrf_middleware)
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))
templates.env.autoescape = True
from .icons import ICONS  # noqa: E402
templates.env.globals["ICONS"] = ICONS

NAV = [
    ("respublika", "Respublika", "/", "dashboard"),
    ("hududlar", "Hududlar", "/hududlar", "map"),
    ("qurolxonalar", "Qurolxonalar", "/qurolxonalar", "building"),
    ("yacheykalar", "Qurol kataklari", "/yacheykalar", "lock"),
    ("xodimlar", "Xodimlar", "/xodimlar", "users"),
    ("inventar", "Inventar", "/inventar", "box"),
    ("jurnal", "Jurnal", "/jurnal", "list"),
    ("signallar", "Signallar", "/signallar", "bell"),
    ("rejimlar", "Rejimlar", "/rejimlar", "flag"),
    ("hisobotlar", "Hisobotlar", "/hisobotlar", "file"),
    ("qurilmalar", "Qurilmalar", "/qurilmalar", "cpu"),
    ("sozlamalar", "Sozlamalar", "/sozlamalar", "settings"),
]


def fmt_num(v) -> str:
    try:
        return "{:,}".format(int(v)).replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


def fmt_dt(v, fmt: str = "%H:%M") -> str:
    if not v:
        return ""
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v)
        except ValueError:
            return v
    return v.strftime(fmt)


def ago(v) -> str:
    if not v:
        return ""
    d = datetime.now() - v
    s = int(d.total_seconds())
    if s < 60:
        return "%d s" % s
    if s < 3600:
        return "%d daq" % (s // 60)
    if s < 86400:
        return "%d soat" % (s // 3600)
    return "%d kun" % (s // 86400)


templates.env.filters["num"] = fmt_num
templates.env.filters["dt"] = fmt_dt
templates.env.filters["ago"] = ago


def render(request: Request, name: str, ctx, **kw) -> HTMLResponse:
    """Shablonni umumiy kontekst bilan chizadi (menyu, signal soni, rejim, til)."""
    db = SessionLocal()
    try:
        from .models import Armory, Unit
        from .services.kpi import armory_ids_for_scope
        ids = armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id) if ctx and ctx.user else []
        alarm_q = select(func.count(Alarm.id)).where(Alarm.resolved_at.is_(None))
        mode_q = select(Mode).where(Mode.ended_at.is_(None))
        if ids is not None:
            alarm_q = alarm_q.where(Alarm.armory_id.in_(ids))
            mode_q = mode_q.where(Mode.armory_id.in_(ids))
        active_alarms = db.scalar(alarm_q) or 0
        mode = db.execute(mode_q.order_by(Mode.started_at.desc())).scalars().first()
        mode_label = ""
        if mode:
            from .models import Armory
            arm = db.get(Armory, mode.armory_id) if mode.armory_id else None
            where = f"{arm.unit.region.short}, {arm.unit.name}" if arm else "Respublika"
            mode_label = f"{'TREVOGA' if mode.kind == 'trevoga' else 'YIG‘ILISH'} · {where} · {mode.issued_count}/{mode.target_count} berildi"
        region_q = select(Region).order_by(Region.order)
        if ids is not None:
            region_q = region_q.where(Region.id.in_(select(Unit.region_id).join(Armory).where(Armory.id.in_(ids))))
        regions = db.execute(region_q).scalars().all()
    finally:
        db.close()
    lang = ctx.lang if ctx else "lat"

    def t(s):
        return translate(s, lang)

    base = {
        "request": request, "ctx": ctx, "nav": NAV, "active_alarms": active_alarms, "mode": mode, "mode_label": mode_label,
        "regions": regions, "now": datetime.now(), "t": t, "lang": lang, "cfg": config, "active": kw.pop("active", ""),
        "breadcrumb": kw.pop("breadcrumb", []), "csrf_token": getattr(request.state, "csrf_token", ""),
    }
    base.update(kw)
    return protect_forms(templates.TemplateResponse(name, base), base["csrf_token"])


# ---- Xato sahifalari: brauzer uchun HTML, API va HTMX uchun avvalgidek JSON ----
ERROR_TEXT = {
    400: ("So‘rov noto‘g‘ri", "So‘rov ma’lumotlari qabul qilinmadi."),
    401: ("Kirish talab qilinadi", "Bu sahifani ko‘rish uchun tizimga kiring."),
    403: ("Ruxsat yo‘q", "Bu amal yoki sahifa sizning rolingiz uchun ochilmagan."),
    404: ("Sahifa topilmadi", "So‘ralgan manzil yoki yozuv mavjud emas."),
    405: ("Usul ruxsat etilmagan", "Bu manzil bunday so‘rovni qabul qilmaydi."),
    409: ("Ziddiyat", "Yozuv holati o‘zgargan. Sahifani yangilab, qayta urinib ko‘ring."),
    410: ("Muddati o‘tgan", "Bu havolaning amal qilish muddati tugagan."),
    422: ("So‘rov noto‘g‘ri", "Kiritilgan qiymatlar tekshiruvdan o‘tmadi."),
    500: ("Ichki xato", "Server so‘rovni bajara olmadi."),
}
_DEFAULT_DETAILS = {"Not Found", "Forbidden", "Unauthorized", "Method Not Allowed", "Internal Server Error", "Not Authenticated", ""}


def _wants_html(request: Request) -> bool:
    if request.headers.get("HX-Request") or request.url.path.startswith("/api/"):
        return False
    return "text/html" in request.headers.get("accept", "")


def _error_page(request: Request, status: int, detail) -> HTMLResponse:
    title, generic = ERROR_TEXT.get(status, ERROR_TEXT[500] if status >= 500 else ("Xato", "So‘rov bajarilmadi."))
    message = detail if isinstance(detail, str) and detail not in _DEFAULT_DETAILS else generic
    lang = request.cookies.get("aq_lang", config.DEFAULT_LANG)
    lang = lang if lang in ("lat", "cyr") else "lat"
    user = None
    try:
        from .services.auth_svc import COOKIE, session_user
        db = SessionLocal()
        try:
            user, _ = session_user(db, request.cookies.get(COOKIE))
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - xato sahifasi hech qachon o'zi xato bermasin
        user = None
    referer = request.headers.get("referer", "")
    origin = str(request.base_url).rstrip("/")
    back = referer if referer.startswith(origin + "/") and referer != str(request.url) else ""
    try:
        if user is not None:
            ctx = Ctx(user=user, lang=lang)
            resp = render(request, "xato.html", ctx, active="", title=title, message=message, status=status, back=back,
                          role_label=ROLE_LABEL.get(user.role, user.role), scope_label=SCOPE_LABEL.get(user.scope_kind, user.scope_kind))
        else:
            def t(s):
                return translate(s, lang)
            resp = templates.TemplateResponse("auth/xato.html", {
                "request": request, "t": t, "lang": lang, "cfg": config, "csrf_token": getattr(request.state, "csrf_token", ""),
                "title": title, "message": message, "status": status})
        resp.status_code = status
        return resp
    except Exception:  # noqa: BLE001
        return HTMLResponse(f"<!doctype html><meta charset='utf-8'><h1>{status}</h1><p>{translate(title, lang)}</p>", status_code=status)


@app.exception_handler(StarletteHTTPException)
async def _http_exception(request: Request, exc: StarletteHTTPException):
    headers = dict(getattr(exc, "headers", None) or {})
    if 300 <= exc.status_code < 400:
        return Response(status_code=exc.status_code, headers=headers)
    if not _wants_html(request):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)
    page = _error_page(request, exc.status_code, exc.detail)
    for key, value in headers.items():
        page.headers[key] = value
    return page


@app.exception_handler(RequestValidationError)
async def _validation_exception(request: Request, exc: RequestValidationError):
    if not _wants_html(request):
        return JSONResponse({"detail": jsonable_encoder(exc.errors())}, status_code=422)
    return _error_page(request, 422, None)


@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception):
    if not _wants_html(request):
        return JSONResponse({"detail": "Ichki xato"}, status_code=500)
    return _error_page(request, 500, None)


@app.on_event("startup")
def _startup():
    Base.metadata.create_all(engine)
    if not config.DB_PATH.exists() or _is_empty():
        from .seed import seed
        seed()
    from .services.auth_svc import bootstrap_demo
    with SessionLocal() as db:
        bootstrap_demo(db)


def _is_empty() -> bool:
    db = SessionLocal()
    try:
        return (db.scalar(select(func.count(Region.id))) or 0) == 0
    finally:
        db.close()


@app.get("/til/{lang}")
def set_lang(lang: str, request: Request):
    from urllib.parse import urlsplit
    from .services.auth_svc import safe_next
    try:
        source = urlsplit(request.headers.get("referer", "/"))
    except ValueError:
        source = urlsplit("/")
    target = source.path + ("?" + source.query if source.query else "")
    resp = RedirectResponse(safe_next(target), status_code=303)
    resp.set_cookie("aq_lang", "cyr" if lang == "cyr" else "lat", max_age=365 * 86400)
    return resp


from .routers import dashboard, sim, ws  # noqa: E402

app.include_router(dashboard.router, dependencies=[Depends(get_ctx)])
app.include_router(sim.router, dependencies=[Depends(get_ctx)])
app.include_router(ws.router)

# keyingi bo'limlar (mavjud bo'lsa ulanadi)
for _mod in ("hududlar", "qurolxonalar", "yacheykalar", "xodimlar", "inventar", "jurnal", "signallar", "rejimlar",
             "hisobotlar", "qurilmalar", "sozlamalar", "auth"):
    try:
        _m = __import__(f"app.routers.{_mod}", fromlist=["router"])
        app.include_router(_m.router, dependencies=[] if _mod == "auth" else [Depends(get_ctx)])
    except ModuleNotFoundError as exc:
        if exc.name != f"app.routers.{_mod}":
            raise

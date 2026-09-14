"""CSRF protection for browser forms, including server-rendered HTMX fragments."""
import hmac
import re
import secrets
from urllib.parse import parse_qs, urlsplit

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

CSRF_COOKIE = "aq_csrf"
FORM = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
POST_METHOD = re.compile(r"\bmethod\s*=\s*(['\"])post\1", re.IGNORECASE)


def protect_forms(response: HTMLResponse, token: str) -> HTMLResponse:
    """Inject once at rendering, so non-JavaScript and partial forms also work."""
    if not token:
        return response
    def add(match):
        tag = match.group(0)
        if POST_METHOD.search(tag):
            return tag + f'<input type="hidden" name="csrf_token" value="{token}">'
        return tag
    response.body = FORM.sub(add, response.body.decode("utf-8")).encode("utf-8")
    response.headers["content-length"] = str(len(response.body))
    return response


async def csrf_middleware(request: Request, call_next):
    existing = request.cookies.get(CSRF_COOKIE, "")
    valid_cookie = bool(re.fullmatch(r"[A-Za-z0-9_-]{40,80}", existing))
    token = existing if valid_cookie else secrets.token_urlsafe(32)
    request.state.csrf_token = token
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        same_origin = not origin or origin == str(request.base_url).rstrip("/")
        submitted = request.headers.get("X-CSRF-Token", "")
        if not submitted:
            body = await request.body()
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/x-www-form-urlencoded"):
                submitted = parse_qs(body.decode("utf-8", errors="replace")).get("csrf_token", [""])[0]
            elif content_type.startswith("multipart/form-data"):
                form = await request.form()
                submitted = str(form.get("csrf_token", ""))
        if (not valid_cookie or not same_origin or not submitted
                or not hmac.compare_digest(submitted.encode(), token.encode())):
            return JSONResponse({"detail": "Shaklning amal qilish muddati tugagan. Sahifani yangilang va qayta yuboring."}, status_code=403)
    response = await call_next(request)
    if not request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
        if not valid_cookie:
            response.set_cookie(CSRF_COOKIE, token, httponly=True, samesite="strict", secure=request.url.scheme == "https")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response

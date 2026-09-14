"""Umumiy bog'liqliklar: baza, foydalanuvchi, til, vakolat doirasi."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import DEFAULT_LANG
from .db import get_db
from .models import User

ROLE_LABEL = {
    "administrator": "Administrator", "tekshiruvchi": "Tekshiruvchi", "rahbariyat": "Rahbariyat",
    "navbatchi": "Navbatchi/operator", "qurolxona_masuli": "Qurolxona mas'uli",
}
SCOPE_LABEL = {"respublika": "Respublika", "hudud": "Hudud", "bolinma": "Bo'linma", "qurolxona": "Qurolxona"}


@dataclass
class Ctx:
    user: User | None
    lang: str

    @property
    def scope_kind(self) -> str:
        return self.user.scope_kind if self.user else "respublika"

    @property
    def scope_id(self) -> int | None:
        return self.user.scope_id if self.user else None

    @property
    def role(self) -> str:
        return self.user.role if self.user else "tekshiruvchi"

    def can(self, action: str) -> bool:
        """Rollar matritsasi (02 §2), soddalashtirilgan."""
        if not self.user or not self.user.active:
            return False
        if action == "simulyator":
            return self.role == "administrator" and self.scope_kind == "respublika"
        if action in {"sozlamalar", "foydalanuvchilar"}:
            return self.role == "administrator" and self.scope_kind == "respublika"
        r = self.role
        table = {
            "biriktirish": {"qurolxona_masuli"}, "bloklash": {"qurolxona_masuli"}, "inventar": {"qurolxona_masuli"},
            "signal_ack": {"qurolxona_masuli", "navbatchi"}, "rejim": {"navbatchi"}, "smena": {"navbatchi", "qurolxona_masuli"},
            "sozlamalar": {"administrator"}, "foydalanuvchilar": {"administrator"}, "qurilmalar": {"administrator"},
            "eksport": {"qurolxona_masuli", "navbatchi", "administrator", "tekshiruvchi", "rahbariyat"},
            "simulyator": {"administrator", "navbatchi", "qurolxona_masuli", "tekshiruvchi", "rahbariyat"},
        }
        return r in table.get(action, set())


def get_ctx(request: Request, db: Session = Depends(get_db)) -> Ctx:
    from urllib.parse import quote
    from .services.auth_svc import COOKIE, safe_next, session_user
    lang = request.cookies.get("aq_lang", DEFAULT_LANG)
    user, _ = session_user(db, request.cookies.get(COOKIE))
    if user is None:
        path = safe_next(request.url.path + ("?" + request.url.query if request.url.query else ""))
        location = "/kirish?next=" + quote(path, safe="")
        if request.headers.get("HX-Request"):
            raise HTTPException(401, "Sessiya tugagan. Qayta kiring.", headers={"HX-Redirect": location})
        if request.method == "GET" and not request.url.path.startswith("/api/"):
            raise HTTPException(303, headers={"Location": location})
        raise HTTPException(401, "Tizimga kirish talab qilinadi.")
    if user.role not in ROLE_LABEL or user.scope_kind not in SCOPE_LABEL or (user.scope_kind != "respublika" and user.scope_id is None):
        raise HTTPException(403, "Foydalanuvchi vakolat doirasi noto‘g‘ri sozlangan.")
    return Ctx(user=user, lang=lang if lang in ("lat", "cyr") else "lat")

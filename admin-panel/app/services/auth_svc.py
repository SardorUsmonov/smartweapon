"""Password verification and opaque, revocable server-side demo sessions."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import config
from ..models import Setting, User
from ..security_models import Credential, LoginSession
from .events import record_event

COOKIE = "aq_session"
DEMO_USERS = {"admin", "admin2", "tekshiruvchi", "rahbar", "hudud_tk", "navbatchi", "masul"}


def safe_next(value: str | None) -> str:
    value = value or "/"
    try:
        parts = urlsplit(value)
    except ValueError:
        return "/"
    if (not value.startswith("/") or value.startswith("//") or parts.scheme or parts.netloc
            or "\\" in value or any(ord(c) < 32 for c in value) or len(value) > 400):
        return "/"
    return value if parts.path not in ("/kirish", "/kirish/mfa", "/chiqish") else "/"


def int_setting(db: Session, key: str, default: int, minimum: int = 1, maximum: int = 1440) -> int:
    row = db.get(Setting, key)
    try:
        return min(maximum, max(minimum, int(row.value))) if row else default
    except (ValueError, TypeError):
        return default


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000).hex()
    return f"pbkdf2_sha256$260000${salt}${digest}"


def check_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, wanted = stored.split("$")
        if algorithm != "pbkdf2_sha256" or not 100_000 <= int(rounds) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, wanted)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def bootstrap_demo(db: Session) -> None:
    """Provide the documented demo accounts, without replacing existing credentials."""
    if not config.DEMO_MODE:
        return
    second = db.scalar(select(User).where(User.username == "admin2"))
    if second is None:
        second = User(username="admin2", full_name="Ikkinchi demo administrator", role="administrator",
                      scope_kind="respublika", mfa=True, active=True)
        db.add(second)
        db.flush()
        record_event(db, "sozlama_ozgardi", title="Demo tasdiqlovchi yaratildi",
                     payload={"action": "demo_bootstrap", "username": "admin2"})
    for user in db.scalars(select(User).where(User.username.in_(DEMO_USERS))):
        if db.get(Credential, user.id) is None:
            db.add(Credential(user_id=user.id, password_hash=hash_password("demo")))
    for key, value in {"sessiya_daqiqa": "60", "parol_min_belgi": "8", "kirish_blok_urinish": "3", "kirish_blok_daqiqa": "15"}.items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=value))
    db.commit()


def revoke_sessions(db: Session, user_id: int) -> None:
    db.execute(delete(LoginSession).where(LoginSession.user_id == user_id))


def session_user(db: Session, token: str | None, *, stage: str = "active") -> tuple[User | None, LoginSession | None]:
    if not token or len(token) > 200:
        return None, None
    session = db.get(LoginSession, token_hash(token))
    if not session or session.stage != stage or session.expires_at <= datetime.now():
        return None, None
    user = db.get(User, session.user_id)
    if not user or not user.active:
        return None, None
    credential = db.get(Credential, user.id)
    if credential and credential.locked_until and credential.locked_until > datetime.now():
        return None, None
    return user, session


def _new_session(db: Session, user: User, stage: str, next_path: str) -> str:
    now = datetime.now()
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    minutes = 5 if stage == "mfa" else int_setting(db, "sessiya_daqiqa", 60, 5, 480)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, stage=stage, created_at=now,
                        expires_at=now + timedelta(minutes=minutes), next_path=safe_next(next_path)))
    db.flush()
    return token


def _failure(db: Session, user: User, credential: Credential, step: str) -> str:
    credential.failures += 1
    attempts = int_setting(db, "kirish_blok_urinish", 3, 3, 10)
    if credential.failures >= attempts:
        minutes = int_setting(db, "kirish_blok_daqiqa", 15, 1, 120)
        credential.locked_until = datetime.now() + timedelta(minutes=minutes)
        revoke_sessions(db, user.id)
    record_event(db, "rad_etildi", title="Panelga kirish rad etildi", method="PANEL", result="rad",
                 reason="login_failed", payload={"username": user.username, "step": step})
    db.commit()
    return "Kirish ma’lumotlari noto‘g‘ri yoki hisob vaqtincha bloklangan."


def password_login(db: Session, username: str, password: str, next_path: str = "/") -> tuple[str | None, bool, str]:
    user = db.scalar(select(User).where(User.username == username.strip(), User.active.is_(True)))
    credential = db.get(Credential, user.id) if user else None
    failure = "Kirish ma’lumotlari noto‘g‘ri yoki hisob vaqtincha bloklangan."
    if not user or not credential:
        # Equivalent expensive work avoids a cheap username timing oracle.
        hashlib.pbkdf2_hmac("sha256", password[:512].encode(), b"unknown-panel-user", 260_000)
        return None, False, failure
    if credential.locked_until and credential.locked_until > datetime.now():
        return None, False, failure
    if credential.locked_until:
        credential.failures = 0
        credential.locked_until = None
    if len(password) > 512 or not check_password(password, credential.password_hash):
        return None, False, _failure(db, user, credential, "password")
    if user.mfa and not config.DEMO_MODE:
        return None, False, "Haqiqiy MFA adapteri sozlanmagan. Administratorga murojaat qiling."
    needs_mfa = bool(user.mfa)
    # Do not reset failures before MFA: otherwise password re-entry bypasses OTP lockout.
    if not needs_mfa:
        credential.failures = 0
        credential.locked_until = None
        record_event(db, "auth_ok", title="Panelga kirildi", method="PANEL", payload={"username": user.username})
    token = _new_session(db, user, "mfa" if needs_mfa else "active", next_path)
    db.commit()
    return token, needs_mfa, ""


def mfa_login(db: Session, token: str, code: str) -> tuple[str | None, str, str]:
    user, session = session_user(db, token, stage="mfa")
    if not user or not session:
        return None, "/", "Tasdiqlash muddati tugagan. Qayta kiring."
    credential = db.get(Credential, user.id)
    if not config.DEMO_MODE or not hmac.compare_digest(code.strip().encode(), b"123456"):
        return None, "/", _failure(db, user, credential, "mfa")
    next_path = session.next_path
    db.delete(session)
    credential.failures = 0
    credential.locked_until = None
    active_token = _new_session(db, user, "active", next_path)
    record_event(db, "auth_ok", title="Panelga kirildi", method="PANEL_MFA",
                 payload={"username": user.username, "mfa": "demo"})
    db.commit()
    return active_token, next_path, ""


def logout(db: Session, token: str | None) -> None:
    if not token:
        return
    user, session = session_user(db, token)
    if user:
        record_event(db, "texnik_xizmat", title="Panel sessiyasi yakunlandi", method="PANEL",
                     payload={"username": user.username, "action": "logout"})
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
    db.commit()

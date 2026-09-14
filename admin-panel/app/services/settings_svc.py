"""Validated system settings and two-administrator user changes."""
from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..deps import ROLE_LABEL, SCOPE_LABEL
from ..models import Armory, Region, Setting, SettingsAudit, Unit, User
from ..security_models import Credential, UserChange
from .auth_svc import hash_password, int_setting, revoke_sessions
from .events import record_event

# key: label, group, default, minimum, maximum, unit
SETTING_FIELDS = {
    "sessiya_daqiqa": ("Sessiya davomiyligi", "autentifikatsiya", 60, 5, 480, "daqiqa"),
    "parol_min_belgi": ("Yangi parolning eng kam uzunligi", "autentifikatsiya", 8, 8, 64, "belgi"),
    "kirish_blok_urinish": ("Kirishni bloklash uchun xato urinishlar", "autentifikatsiya", 3, 3, 10, "marta"),
    "kirish_blok_daqiqa": ("Kirish bloki davomiyligi", "autentifikatsiya", 15, 1, 120, "daqiqa"),
    "eshik_ochiq_ogohlantirish_s": ("Eshik ochiq: ogohlantirish", "chegaralar", 60, 5, 3600, "soniya"),
    "eshik_ochiq_signal_s": ("Eshik ochiq: signal", "chegaralar", 180, 10, 7200, "soniya"),
    "qulf_qayta_s": ("Qayta qulflash muddati", "chegaralar", 15, 1, 300, "soniya"),
    "rad_blok_urinish": ("Terminalda rad urinishlar chegarasi", "chegaralar", 3, 3, 10, "marta"),
    "rad_blok_daqiqa": ("Terminal bloki davomiyligi", "chegaralar", 15, 1, 120, "daqiqa"),
    "batareya_past_pct": ("Past batareya chegarasi", "chegaralar", 20, 5, 80, "%"),
    "urilish_g": ("Urilish chegarasi", "chegaralar", 2.0, 0.1, 20, "g"),
    "qaytarish_grace_min": ("Qaytarish uchun qo‘shimcha vaqt", "chegaralar", 30, 0, 240, "daqiqa"),
    "favqulodda_tasdiqlovchilar": ("Tasdiqlovchilar soni", "chegaralar", 2, 2, 5, "kishi"),
    "video_saqlash_kun": ("Video saqlash muddati", "saqlash", 90, 1, 3650, "kun"),
    "foto_saqlash_kun": ("Foto saqlash muddati", "saqlash", 365, 1, 3650, "kun"),
    "audit_saqlash_yil": ("Audit saqlash muddati", "saqlash", 5, 1, 25, "yil"),
}
TABS = {"foydalanuvchilar": "Foydalanuvchilar", "autentifikatsiya": "Kirish siyosati", "chegaralar": "Chegaralar",
        "saqlash": "Saqlash muddatlari", "integratsiyalar": "Integratsiyalar", "audit": "Sozlamalar auditi"}
INTEGRATIONS = [("HR", "Xodimlar ma’lumotlari"), ("Navbatchilik", "Navbat va smenalar"),
                ("Kirish nazorati", "Karta va biometrik terminal"), ("Videokuzatuv", "Kamera va video arxiv"),
                ("SIEM", "Markaziy xavfsizlik hodisalari")]


class SettingsError(ValueError):
    pass


def snapshot(user: User) -> dict:
    return {k: getattr(user, k) for k in ("full_name", "role", "scope_kind", "scope_id", "mfa", "active")}


def audit(db: Session, actor: User, key: str, old, new, reason: str, approved_by: str = "") -> None:
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True)
    db.add(SettingsAudit(username=actor.username, key=key, old=encode(old), new=encode(new),
                         ts=datetime.now(), approved_by=approved_by))
    record_event(db, "sozlama_ozgardi", title="Sozlamalar o‘zgardi", reason=reason[:60],
                 payload={"username": actor.username, "key": key, "old": old, "new": new,
                          "reason": reason, "approved_by": approved_by})


def reason_required(value: str) -> str:
    value = value.strip()
    if not 5 <= len(value) <= 300:
        raise SettingsError("Sabab 5–300 belgidan iborat bo‘lishi kerak.")
    return value


def values(db: Session, group: str) -> list[dict]:
    rows = []
    for key, (label, tab, default, minimum, maximum, unit) in SETTING_FIELDS.items():
        if tab == group:
            setting = db.get(Setting, key)
            rows.append({"key": key, "label": label, "value": setting.value if setting else str(default),
                         "min": minimum, "max": maximum, "unit": unit, "step": "0.1" if key == "urilish_g" else "1"})
    return rows


def save_settings(db: Session, actor: User, group: str, submitted: dict, reason: str) -> int:
    reason = reason_required(reason)
    proposed = {}
    for row in values(db, group):
        raw = str(submitted.get(row["key"], "")).strip()
        try:
            value = float(raw) if row["step"] == "0.1" else int(raw)
        except ValueError:
            raise SettingsError(f"{row['label']}: son kiriting.")
        if not row["min"] <= value <= row["max"]:
            raise SettingsError(f"{row['label']}: {row['min']}–{row['max']} oralig‘ida bo‘lishi kerak.")
        proposed[row["key"]] = str(value)
    if not proposed:
        raise SettingsError("Bunday sozlamalar bo‘limi yo‘q.")
    if group == "chegaralar" and int(proposed["eshik_ochiq_signal_s"]) <= int(proposed["eshik_ochiq_ogohlantirish_s"]):
        raise SettingsError("Signal muddati ogohlantirish muddatidan katta bo‘lishi kerak.")
    changed = 0
    for key, value in proposed.items():
        row = db.get(Setting, key)
        old = row.value if row else None
        if old == value:
            continue
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))
        audit(db, actor, key, old, value, reason)
        changed += 1
    db.commit()
    return changed


def validate_user(db: Session, proposed: dict) -> dict:
    full_name = str(proposed.get("full_name", "")).strip()
    if not 3 <= len(full_name) <= 120:
        raise SettingsError("F.I.Sh. 3–120 belgidan iborat bo‘lishi kerak.")
    role, kind = proposed.get("role"), proposed.get("scope_kind")
    if role not in ROLE_LABEL or kind not in SCOPE_LABEL:
        raise SettingsError("Rol va vakolat doirasini ro‘yxatdan tanlang.")
    scope_id = None
    if kind != "respublika":
        try:
            scope_id = int(proposed.get("scope_id") or "")
        except (TypeError, ValueError):
            raise SettingsError("Vakolat obyektini tanlang.")
        model = {"hudud": Region, "bolinma": Unit, "qurolxona": Armory}[kind]
        if not db.get(model, scope_id):
            raise SettingsError("Tanlangan vakolat obyekti topilmadi.")
    def checkbox(key: str) -> bool:
        value = proposed.get(key)
        if value in (True, "1", "on"):
            return True
        if value in (None, False, "", "0", "off"):
            return False
        raise SettingsError("Faollik va MFA qiymatlari noto‘g‘ri.")

    mfa = checkbox("mfa")
    if role == "administrator" and not mfa:
        raise SettingsError("Administrator uchun MFA majburiy.")
    return {"full_name": full_name, "role": role, "scope_kind": kind, "scope_id": scope_id,
            "mfa": mfa, "active": checkbox("active")}


def request_user_change(db: Session, actor: User, proposed: dict, reason: str, *,
                        user: User | None = None, username: str = "", password: str = "") -> UserChange:
    reason = reason_required(reason)
    proposed = validate_user(db, proposed)
    if user is None:
        username = username.strip()
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_.-]{2,39}", username):
            raise SettingsError("Login 3–40 ta lotin harfi, raqam, nuqta, chiziq yoki pastki chiziqdan iborat bo‘lsin.")
        if db.scalar(select(User.id).where(User.username == username)):
            raise SettingsError("Bu login band.")
        minimum = int_setting(db, "parol_min_belgi", 8, 8, 64)
        if not minimum <= len(password) <= 128:
            raise SettingsError(f"Parol {minimum}–128 belgidan iborat bo‘lishi kerak.")
        user = User(username=username, full_name=proposed["full_name"], role="tekshiruvchi",
                    scope_kind=proposed["scope_kind"], scope_id=proposed["scope_id"], active=False, mfa=True)
        db.add(user)
        db.flush()
        db.add(Credential(user_id=user.id, password_hash=hash_password(password)))
        audit(db, actor, f"user.{user.id}.create", None, {"username": username, "active": False}, reason)
    if db.scalar(select(UserChange.id).where(UserChange.user_id == user.id, UserChange.status == "pending")):
        raise SettingsError("Bu foydalanuvchi uchun tasdiq kutilayotgan so‘rov bor.")
    before = snapshot(user)
    if before == proposed:
        raise SettingsError("O‘zgarish kiritilmagan.")
    change = UserChange(user_id=user.id, requested_by=actor.id, before=before, proposed=proposed,
                        reason=reason, created_at=datetime.now(), status="pending")
    db.add(change)
    db.flush()
    audit(db, actor, f"user.{user.id}.request", before, {"change_id": change.id, "proposed": proposed}, reason)
    db.commit()
    return change


def decide_change(db: Session, actor: User, change: UserChange, approve: bool) -> None:
    if change.status != "pending":
        raise SettingsError("Bu so‘rov bo‘yicha qaror allaqachon qabul qilingan.")
    if change.requested_by == actor.id:
        raise SettingsError("O‘z so‘rovingizni tasdiqlay olmaysiz. Boshqa administrator talab qilinadi.")
    user = db.get(User, change.user_id)
    if not user:
        raise SettingsError("Foydalanuvchi topilmadi.")
    if approve:
        if snapshot(user) != change.before:
            raise SettingsError("Foydalanuvchi ma’lumotlari o‘zgargan. So‘rovni rad etib, yangisini yarating.")
        proposed = validate_user(db, change.proposed)
        removing_admin = (user.active and user.role == "administrator" and user.scope_kind == "respublika"
                          and not (proposed["active"] and proposed["role"] == "administrator" and proposed["scope_kind"] == "respublika"))
        admin_count = db.scalar(select(func.count(User.id)).where(User.active.is_(True), User.role == "administrator", User.scope_kind == "respublika"))
        if removing_admin and admin_count <= 2:
            raise SettingsError("Ikki shaxs tasdig‘i uchun kamida ikkita faol respublika administratori qolishi kerak.")
    claimed = db.execute(update(UserChange).where(UserChange.id == change.id, UserChange.status == "pending")
                         .values(status="approved" if approve else "rejected", decided_by=actor.id, decided_at=datetime.now()))
    if claimed.rowcount != 1:
        db.rollback()
        raise SettingsError("So‘rov bo‘yicha boshqa administrator qaror qabul qildi.")
    if approve:
        for key, value in proposed.items():
            setattr(user, key, value)
        revoke_sessions(db, user.id)
        requester = db.get(User, change.requested_by)
        record_event(db, "huquq_berish_tasdiqlandi", title="Foydalanuvchi o‘zgarishi tasdiqlandi",
                     approver1=requester.username if requester else str(change.requested_by), approver2=actor.username,
                     payload={"change_id": change.id, "username": user.username, "before": change.before, "after": proposed})
    audit(db, actor, f"user.{user.id}.decision", change.before,
          {"change_id": change.id, "decision": "approved" if approve else "rejected", "proposed": change.proposed},
          change.reason, approved_by=actor.username)
    db.commit()

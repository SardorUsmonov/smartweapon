"""Additive tables for panel sessions and reviewed user changes.

Keeping credentials separate preserves existing User rows on SQLite upgrades.
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Credential(Base):
    __tablename__ = "auth_credential"
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    password_hash: Mapped[str] = mapped_column(Text)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LoginSession(Base):
    __tablename__ = "auth_session"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    stage: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    next_path: Mapped[str] = mapped_column(String(400), default="/")


class UserChange(Base):
    __tablename__ = "user_change"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("user.id"))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    before: Mapped[dict] = mapped_column(JSON)
    proposed: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

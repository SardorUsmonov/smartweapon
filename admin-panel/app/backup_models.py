"""Verified local backup artifacts, without modifying legacy Backup rows."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class BackupArtifact(Base):
    __tablename__ = "backup_artifact"
    backup_id: Mapped[int] = mapped_column(ForeignKey("backup.id"), primary_key=True)
    relative_path: Mapped[str] = mapped_column(String(160), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    manifest: Mapped[dict] = mapped_column(JSON)
    verified_at: Mapped[datetime] = mapped_column(DateTime)
    source_backup_id: Mapped[int | None] = mapped_column(ForeignKey("backup.id"), nullable=True)

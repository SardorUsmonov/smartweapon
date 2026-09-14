"""Real SQLite snapshots and restore rehearsals. Never overwrite the live DB."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .. import config
from ..backup_models import BackupArtifact
from ..models import Backup, Event
from .events import record_event, verify_chain


class BackupError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def backup_directory() -> Path:
    source = config.DB_PATH.resolve()
    return source.parent / (source.stem + "-backups")


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def manifest_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".manifest.json")


def _read_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)


def inspect_snapshot(path: Path) -> dict:
    """Read-only SQL integrity and the *entire* event chain, including old defects."""
    try:
        with closing(_read_connection(path)) as connection:
            result = [row[0] for row in connection.execute("PRAGMA integrity_check")]
            if result != ["ok"]:
                raise BackupError("SQLite yaxlitligi tekshiruvdan o‘tmadi.", 409)
            tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            if "event" not in tables or "user" not in tables:
                raise BackupError("Bu fayl admin panel bazasi emas.", 409)
            counts = {name: connection.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                      for name in sorted(tables)}
        check_engine = create_engine("sqlite://", creator=lambda: _read_connection(path))
        try:
            with Session(check_engine) as check_db:
                count = check_db.scalar(select(func.count(Event.id))) or 0
                audit = verify_chain(check_db, limit=max(count, 1))
        finally:
            check_engine.dispose()
        return {"sqlite_integrity": "ok", "table_counts": counts, "audit": audit}
    except BackupError:
        raise
    except Exception as exc:
        raise BackupError("Nusxani o‘qish yoki yaxlitligini tekshirish amalga oshmadi.", 409) from exc


def _remove_owned(path: Path) -> None:
    # Only files created by this operation are passed here; never the source DB.
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"), Path(str(path) + "-journal")):
        candidate.unlink(missing_ok=True)


def snapshot_to_new(source: Path, destination: Path, *, source_backup_id: int | None = None,
                    expected: dict | None = None) -> dict:
    """Online SQLite backup into an exclusively created new path, with manifest."""
    source, destination = source.resolve(), destination.absolute()
    sidecar = manifest_path(destination)
    if not source.is_file():
        raise BackupError("Manba baza fayli topilmadi.", 404)
    if destination.exists() or destination.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise BackupError("Natija yo‘li band. Faqat yangi faylga tiklash mumkin.", 409)
    created = sidecar_created = False
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        created = True
        if expected is None:
            with closing(_read_connection(source)) as original, closing(sqlite3.connect(destination)) as copy:
                original.backup(copy, pages=256, sleep=0.05)
                # Finish with a standalone file; no WAL sidecar is needed for restoration.
                copy.execute("PRAGMA journal_mode=DELETE").fetchone()
        else:
            # Hash the exact bytes copied so concurrent changes cannot evade the
            # preflight SHA check, even if row counts and event hashes still match.
            digest = hashlib.sha256()
            with source.open("rb") as original, destination.open("wb") as copy:
                while chunk := original.read(1024 * 1024):
                    digest.update(chunk)
                    copy.write(chunk)
            if digest.hexdigest() != expected["sha256"]:
                raise BackupError("Nusxa tiklash vaqtida o‘zgardi. Tiklash to‘xtatildi.", 409)
        checks = inspect_snapshot(destination)
        if expected is not None and (checks["table_counts"] != expected["table_counts"] or checks["audit"] != expected["audit"]):
            raise BackupError("Tiklangan nusxa manba tekshiruvi bilan mos kelmadi.", 409)
        manifest = {"format": "aq-sqlite-backup-v1", "file": destination.name,
                    "created_at": datetime.now(timezone.utc).isoformat(), "source_file": source.name,
                    "source_backup_id": source_backup_id, "sha256": file_hash(destination),
                    "size_bytes": destination.stat().st_size, **checks}
        descriptor = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        sidecar_created = True
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
        return manifest
    except Exception as exc:
        if created:
            _remove_owned(destination)
        if sidecar_created:
            sidecar.unlink(missing_ok=True)
        if isinstance(exc, BackupError):
            raise
        raise BackupError("Mahalliy zaxira faylini yozib bo‘lmadi. Disk va papka ruxsatlarini tekshiring.", 500) from exc


def artifact_paths(artifact: BackupArtifact) -> tuple[Path, Path]:
    root = backup_directory().resolve()
    path = (root / artifact.relative_path).resolve()
    if not path.is_relative_to(root) or path == config.DB_PATH.resolve():
        raise BackupError("Nusxa fayli yo‘li yaroqsiz.", 409)
    return path, manifest_path(path)


def validate_files(path: Path, *, artifact: BackupArtifact | None = None) -> dict:
    sidecar = manifest_path(path)
    if not path.is_file() or not sidecar.is_file():
        raise BackupError("Nusxa yoki uning manifest fayli topilmadi.", 404)
    try:
        manifest = json.loads(sidecar.read_text(encoding="utf-8"))
        valid = (manifest["format"] == "aq-sqlite-backup-v1" and manifest["file"] == path.name
                 and manifest["size_bytes"] == path.stat().st_size and manifest["sha256"] == file_hash(path))
        if artifact is not None:
            valid = (valid and artifact.sha256 == manifest["sha256"] and artifact.size_bytes == manifest["size_bytes"]
                     and artifact.manifest_sha256 == file_hash(sidecar) and artifact.manifest == manifest)
        if not valid:
            raise ValueError("mismatch")
        return manifest
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise BackupError("Nusxa yoki manifest SHA-256 tekshiruvidan o‘tmadi. Tiklash to‘xtatildi.", 409) from exc


def _persist(db: Session, actor: str, kind: str, path: Path, manifest: dict, note: str) -> BackupArtifact:
    now = datetime.now()
    broken = manifest["audit"]["broken"]
    summary = f"SQLite: OK; audit: {broken} nomuvofiqlik" if broken else "SQLite va audit yaxlitligi: OK"
    row = Backup(scope="markaz", kind=kind, ts=now, size_mb=math.ceil(manifest["size_bytes"] / (1024 * 1024)),
                 ok=True, note=(summary + (" · " + note.strip() if note.strip() else ""))[:160])
    try:
        db.add(row)
        db.flush()
        artifact = BackupArtifact(backup_id=row.id, relative_path=path.relative_to(backup_directory()).as_posix(),
                                  sha256=manifest["sha256"], manifest_sha256=file_hash(manifest_path(path)),
                                  size_bytes=manifest["size_bytes"], manifest=manifest, verified_at=now,
                                  source_backup_id=manifest["source_backup_id"])
        db.add(artifact)
        record_event(db, "zaxira_nusxa", approver1=actor, simulated=False, level="WARNING" if broken else "INFO",
                     title="Tiklash sinovi bajarildi" if kind == "tiklash_sinovi" else "Mahalliy zaxira nusxa olindi",
                     detail=summary, payload={"backup_id": row.id, "kind": kind, "file": artifact.relative_path,
                     "sha256": artifact.sha256, "size_bytes": artifact.size_bytes,
                     "source_backup_id": artifact.source_backup_id, "audit": manifest["audit"], "kim": actor,
                     "izoh": note.strip()[:300]})
        db.commit()
        return artifact
    except Exception as exc:
        db.rollback()
        _remove_owned(path)
        manifest_path(path).unlink(missing_ok=True)
        raise BackupError("Nusxa natijasini bazaga qayd etib bo‘lmadi.", 500) from exc


def create_backup(db: Session, actor: str, kind: str = "kunlik", note: str = "") -> BackupArtifact:
    if kind not in {"kunlik", "haftalik"}:
        raise BackupError("Nusxa turini ro‘yxatdan tanlang.")
    folder = backup_directory()
    try:
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise BackupError("Zaxira papkasini yaratib bo‘lmadi. Papka ruxsatlarini tekshiring.", 500) from exc
    path = folder / f"{kind}-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex}.sqlite3"
    manifest = snapshot_to_new(config.DB_PATH, path)
    return _persist(db, actor, kind, path, manifest, note)


def restore_test(db: Session, actor: str, backup_id: int | None = None, note: str = "") -> BackupArtifact:
    query = select(BackupArtifact).join(Backup, Backup.id == BackupArtifact.backup_id).where(Backup.kind.in_(["kunlik", "haftalik"]))
    if backup_id is not None:
        query = query.where(Backup.id == backup_id)
    artifact = db.scalars(query.order_by(Backup.ts.desc(), Backup.id.desc())).first()
    if artifact is None:
        raise BackupError("Haqiqiy nusxa topilmadi. Avval mahalliy nusxa oling.", 404)
    source, _ = artifact_paths(artifact)
    expected = validate_files(source, artifact=artifact)
    folder = backup_directory() / "restore-tests"
    try:
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise BackupError("Tiklash sinovi papkasini yaratib bo‘lmadi.", 500) from exc
    path = folder / f"restore-{artifact.backup_id}-{uuid4().hex}.sqlite3"
    manifest = snapshot_to_new(source, path, source_backup_id=artifact.backup_id, expected=expected)
    return _persist(db, actor, "tiklash_sinovi", path, manifest, note)


def main() -> int:
    parser = argparse.ArgumentParser(description="SQLite backup / restoration into a NEW file; existing files are never overwritten.")
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("output", type=Path)
    backup.add_argument("--source", type=Path, default=config.DB_PATH)
    restore = commands.add_parser("restore-copy")
    restore.add_argument("source", type=Path)
    restore.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        expected = validate_files(args.source.resolve()) if args.command == "restore-copy" else None
        result = snapshot_to_new(args.source, args.output, expected=expected)
        print(json.dumps({"output": str(args.output.resolve()), "manifest": str(manifest_path(args.output).resolve()),
                          "sha256": result["sha256"], "sqlite_integrity": result["sqlite_integrity"],
                          "audit": result["audit"]}, ensure_ascii=False, indent=2))
        return 0
    except BackupError as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

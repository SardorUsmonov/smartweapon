"""Actual local snapshots and restore copies, using only isolated temporary files."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(tempfile.mkdtemp(prefix="aq_backup_flow_"))
SOURCE = SCRATCH / "test.sqlite3"
shutil.copy2(ROOT.parent / ".backups/admin-panel-20260912-141835/aq_central.sqlite3", SOURCE)
os.environ["AQ_DB"] = str(SOURCE)
os.environ["AQ_DEMO"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from app.main import app
from app.db import Base, SessionLocal
from app.models import Backup, Event, User
from app.backup_models import BackupArtifact
from app.services import backup_svc as svc
from app.services.events import record_event


def dump(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {table: connection.execute('SELECT * FROM "' + table + '" ORDER BY rowid').fetchall() for table in tables}


def post(client, path, **data):
    data["csrf_token"] = client.cookies["aq_csrf"]
    return client.post(path, data=data, follow_redirects=False)


def login(client, name):
    client.get("/kirish")
    result = post(client, "/kirish", username=name, password="demo")
    assert result.status_code == 303, result.text
    if result.headers["location"] == "/kirish/mfa":
        assert post(client, "/kirish/mfa", code="123456").status_code == 303


def latest():
    with SessionLocal() as db:
        return db.scalars(select(BackupArtifact).order_by(BackupArtifact.backup_id.desc())).first()


def count():
    with SessionLocal() as db:
        return db.scalar(select(func.count(BackupArtifact.backup_id)))


with TestClient(app) as admin, TestClient(app) as reader, TestClient(app) as scoped, TestClient(app) as anonymous:
    login(admin, "admin")
    login(reader, "tekshiruvchi")
    login(scoped, "navbatchi")
    response = admin.get("/qurilmalar/zaxira")
    assert response.status_code == 200 and response.context["ov"]["legacy_count"] > 0
    assert "Eski demo" in response.text and "NAS ga uzatish ulanmagan" in response.text
    assert all(item is None for item in response.context["ov"]["last"].values())
    assert post(admin, "/qurilmalar/zaxira/tiklash-sinovi").status_code == 404
    assert count() == 0
    assert admin.post("/qurilmalar/zaxira/nusxa").status_code == 403
    assert admin.post("/qurilmalar/zaxira/nusxa", headers={"X-CSRF-Token": admin.cookies["aq_csrf"], "Origin":"https://foreign.example"}).status_code == 403
    assert reader.get("/qurilmalar/zaxira").status_code == 200
    assert scoped.get("/qurilmalar/zaxira").status_code == 403
    for client in (reader, scoped):
        for action in ("nusxa", "tiklash-sinovi"):
            assert post(client, "/qurilmalar/zaxira/" + action).status_code == 403
    anonymous.get("/kirish")
    assert post(anonymous, "/qurilmalar/zaxira/nusxa").status_code == 401
    assert count() == 0
    assert post(admin, "/qurilmalar/zaxira/nusxa", tur="invented").status_code == 400
    print("Legacy labels, no fake restore, real authentication, roles, scope and CSRF passed")

    before = dump(SOURCE)
    response = post(admin, "/qurilmalar/zaxira/nusxa", tur="kunlik", izoh="Actual snapshot")
    assert response.status_code == 303, response.text
    assert response.headers["location"].endswith("nusxa_ogoh")
    artifact = latest()
    path, sidecar = svc.artifact_paths(artifact)
    assert path.is_relative_to(SCRATCH) and sidecar.exists()
    assert dump(path) == before, "Every table and every row must match the source snapshot"
    manifest = svc.validate_files(path, artifact=artifact)
    assert manifest["audit"]["broken"] == 7 and not manifest["audit"]["ok"]
    assert manifest["audit"]["checked"] == len(before["event"])
    assert artifact.sha256 == svc.file_hash(path) and artifact.size_bytes == path.stat().st_size
    after = dump(SOURCE)
    for table, rows in before.items():
        assert after[table][:len(rows)] == rows, table
    assert len(after["event"]) == len(before["event"]) + 1
    assert len(after["backup"]) == len(before["backup"]) + 1
    response = admin.get(response.headers["location"])
    assert response.status_code == 200 and "Audit ogohlantirishi" in response.text
    assert len(response.context["available"]) == 1
    print("Online snapshot equals every source row; manifest SHA/size and 7 historical defects preserved")

    source_bytes = path.read_bytes()
    response = post(admin, "/qurilmalar/zaxira/tiklash-sinovi", backup_id=artifact.backup_id)
    assert response.status_code == 303 and response.headers["location"].endswith("tiklash_ogoh"), response.text
    restored = latest()
    restored_path, _ = svc.artifact_paths(restored)
    assert restored.source_backup_id == artifact.backup_id and restored_path.parent.name == "restore-tests"
    assert dump(restored_path) == dump(path) and path.read_bytes() == source_bytes
    assert restored_path.read_bytes() == source_bytes, "Restore must copy the exact verified bytes"
    assert svc.inspect_snapshot(restored_path)["audit"] == manifest["audit"]
    assert restored_path != SOURCE and count() == 2
    with SessionLocal() as db:
        events = list(db.scalars(select(Event).where(Event.type == "zaxira_nusxa").order_by(Event.id.desc()).limit(2)))
        assert all(not event.simulated and event.level == "WARNING" for event in events)
    print("Restore into a separate file equals every source row; original snapshot and audit remain unchanged")

    original_manifest = sidecar.read_bytes()
    path.write_bytes(source_bytes + b"TAMPER")
    assert post(admin, "/qurilmalar/zaxira/tiklash-sinovi", backup_id=artifact.backup_id).status_code == 409
    path.write_bytes(source_bytes)
    sidecar.write_bytes(original_manifest + b" ")
    assert post(admin, "/qurilmalar/zaxira/tiklash-sinovi", backup_id=artifact.backup_id).status_code == 409
    sidecar.write_bytes(original_manifest)
    moved = path.with_suffix(".temporarily-missing")
    path.rename(moved)
    try:
        assert post(admin, "/qurilmalar/zaxira/tiklash-sinovi", backup_id=artifact.backup_id).status_code == 404
    finally:
        moved.rename(path)
    for value, expected in (("../../../file",400),("0",400),("999999999",404)):
        assert post(admin, "/qurilmalar/zaxira/tiklash-sinovi", backup_id=value).status_code == expected
    assert count() == 2, "Failed attempts must not create successful artifacts"
    assert post(admin, "/qurilmalar/zaxira/nusxa", tur="haftalik").status_code == 303
    with SessionLocal() as db:
        assert db.get(Backup, latest().backup_id).kind == "haftalik"
    for lang in ("lat", "cyr"):
        admin.cookies.set("aq_lang", lang)
        assert admin.get("/qurilmalar/zaxira?tur=kunlik&page=1").status_code == 200
    print("File/manifest tamper, missing paths, invalid IDs, weekly category and both languages passed")

    # Path confinement applies even to inconsistent persisted metadata.
    changed = artifact.relative_path
    artifact.relative_path = "../outside.sqlite3"
    try:
        svc.artifact_paths(artifact)
        raise AssertionError("Path escaped the backup directory")
    except svc.BackupError:
        pass
    artifact.relative_path = changed

    cli_copy = SCRATCH / "cli.sqlite3"
    source_before_cli = dump(SOURCE)
    command = [sys.executable, "-B", "-X", "utf8", "-m", "app.services.backup_svc"]
    result = subprocess.run(command + ["backup", str(cli_copy)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stderr
    assert dump(cli_copy) == source_before_cli and dump(SOURCE) == source_before_cli
    cli_restored = SCRATCH / "cli-restored.sqlite3"
    result = subprocess.run(command + ["restore-copy", str(cli_copy), str(cli_restored)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stderr
    assert dump(cli_restored) == dump(cli_copy)
    original_hash = svc.file_hash(SOURCE)
    result = subprocess.run(command + ["restore-copy", str(cli_copy), str(SOURCE)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 2 and svc.file_hash(SOURCE) == original_hash
    occupied = SCRATCH / "occupied.sqlite3"
    occupied.write_bytes(b"must remain")
    result = subprocess.run(command + ["backup", str(occupied)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 2 and occupied.read_bytes() == b"must remain"
    assert dump(SOURCE) == source_before_cli
    print("CLI backup/restore-copy, no overwrite, no source data mutation and path confinement passed")

    clean_source = SCRATCH / "clean-source.sqlite3"
    clean_engine = create_engine(f"sqlite:///{clean_source}")
    Base.metadata.create_all(clean_engine)
    with Session(clean_engine) as clean_db:
        record_event(clean_db, "zaxira_nusxa", title="Fresh audit fixture", simulated=False)
        clean_db.commit()
    clean_engine.dispose()
    clean_output = SCRATCH / "clean-output.sqlite3"
    clean_result = svc.snapshot_to_new(clean_source, clean_output)
    assert clean_result["audit"] == {"checked":1, "broken":0, "first_broken":None, "ok":True}
    assert dump(clean_source) == dump(clean_output)
    print("Fresh audit fixture produces an intact backup without a historical warning")

print("PASS scratch:", SCRATCH)

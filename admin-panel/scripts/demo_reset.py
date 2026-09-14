"""Namoyish oldidan bazani yangilash.

Joriy bazani `data/arxiv/` ga vaqt belgisi bilan ko'chiradi va yangi sintetik demo
ma'lumot kiritadi (30 kunlik tarix, yangi sinxron vaqtlari, faol o'quv trevoga).
Serverni avval to'xtating: ishlayotgan server bilan baza almashtirilmaydi.

    python -B -X utf8 scripts/demo_reset.py            # AQ_SEED (standart: small)
    python -B -X utf8 scripts/demo_reset.py medium     # kattaroq flot
"""
from __future__ import annotations

import os
import shutil
import socket
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402


def server_running(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    port = int(os.environ.get("AQ_PORT", "8080"))
    if server_running(port):
        print(f"Server {port} portda ishlayapti. Avval uni to'xtating (Ctrl+C), keyin qayta urinib ko'ring.")
        return 2
    size = sys.argv[1] if len(sys.argv) > 1 else config.SEED_SIZE
    db_path: Path = config.DB_PATH
    archive_dir = db_path.parent / "arxiv"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    moved = []
    for suffix in ("", "-wal", "-shm"):
        source = db_path.with_name(db_path.name + suffix)
        if source.exists():
            target = archive_dir / f"{db_path.stem}-{stamp}{db_path.suffix}{suffix}"
            shutil.move(str(source), str(target))
            moved.append(target.name)
    if moved:
        print("Arxivlandi:", ", ".join(moved), "→", archive_dir)

    # Jadval ro'yxati to'liq bo'lishi uchun qo'shimcha modellar ham import qilinadi.
    from app import backup_models, security_models  # noqa: F401
    from app.db import Base, SessionLocal, engine
    from app.seed import seed
    from app.services.auth_svc import bootstrap_demo

    Base.metadata.create_all(engine)
    started = datetime.now()
    stats = seed(size=size)
    with SessionLocal() as db:
        bootstrap_demo(db)
    took = (datetime.now() - started).total_seconds()
    print(f"Yangi demo baza: {db_path}")
    print(f"  hajm={stats.get('size')} hududlar={stats.get('regions')} qurolxonalar={stats.get('armories')} "
          f"kataklar={stats.get('cabinets')} xodimlar={stats.get('officers')} hodisalar={stats.get('events')} "
          f"faol signallar={stats.get('active_alarms')}  ({took:.1f} s)")
    print("Endi serverni ishga tushiring: python -B -X utf8 run.py  → kirish: admin / demo / 123456")
    print("Namoyish davomida Simulyator → Avto-rejim yoqilgan bo'lsin: obyektlar sinxron xabar yuborib turadi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

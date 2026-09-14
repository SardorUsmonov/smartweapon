"""Aqlli qurolxona admin paneli: sozlamalar."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# role=central (respublika markaziy serveri) yoki role=armory (qurolxona kontrolleri)
ROLE = os.environ.get("AQ_ROLE", "central")
DB_PATH = Path(os.environ.get("AQ_DB", DATA_DIR / f"aq_{ROLE}.sqlite3"))
# sintetik flot hajmi: small (~300 yacheyka), medium (~1 100), full (~5 500)
SEED_SIZE = os.environ.get("AQ_SEED", "small")
SEED_DAYS = int(os.environ.get("AQ_SEED_DAYS", "30"))
TZ_OFFSET_HOURS = 5  # Asia/Tashkent
DEFAULT_LANG = os.environ.get("AQ_LANG", "lat")  # lat | cyr
DEMO_MODE = os.environ.get("AQ_DEMO", "1") == "1"
APP_TITLE = "Nazorat markazi"
APP_SUBTITLE = "Qurol saqlash tizimi"
ORG_NAME = "O'zbekiston Respublikasi Ichki ishlar vazirligi"

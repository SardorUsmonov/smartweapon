# Smart Weapon — aqlli qurol-aslaha shkafi va "Nazorat markazi" admin paneli

O'zbekiston Respublikasi IIV uchun aqlli individual qurol saqlash shkafi prototipi va uni respublika miqyosida boshqaradigan admin panel.

## Papkalar

| Papka | Mazmuni |
|---|---|
| `admin-panel/` | FastAPI + Jinja2 + HTMX + SQLite admin panel (demo). Ishga tushirish va demo hisoblar: [admin-panel/README.md](admin-panel/README.md) |
| `docs/admin-panel/` | Talablar, arxitektura, TZ bilan moslik, dizayn tizimi, ish rejasi va tekshiruv dalillari (01–15 raqamli hujjatlar) |
| `docs/manbalar/` | Tadqiqot hujjati, "Aqlli qurolxona" texnik topshirig'i (TZ v1.0), hisobot, renderlar |
| `cad/manba/` | Shkafning dastlabki CAD manbalari |
| `.backups/admin-panel-20260912-141835/` | Testlar ishlatadigan boshlang'ich demo baza (o'zgartirilmaydi) |

## Tez boshlash

```powershell
cd admin-panel
python -m pip install -r requirements.txt
python -B -X utf8 run.py
```

Manzil: http://127.0.0.1:8080 — demo hisoblar uchun parol `demo`, MFA kodi `123456` (`admin`, `admin2`, `tekshiruvchi`, `rahbar`, `hudud_tk`, `navbatchi`, `masul`). Birinchi ishga tushishda bo'sh bazaga sintetik ma'lumot kiritiladi.

Tekshiruvlar (vaqtinchalik bazalarda, 14 skript):

```powershell
cd admin-panel
python -m pip install -r requirements-dev.txt
$env:AQ_DEMO = '1'
Get-ChildItem tests\verify_*.py | ForEach-Object { python -B -X utf8 $_.FullName }
```

## Holat

Demo admin panel funksional jihatdan tugallangan: 12 bo'lim, kirish/MFA (demo), hash zanjirli jurnal, hisobotlar va eksport, smena vizardlari, zaxira/tiklash, 3D relyef xarita bilan respublika dashboardi. Real apparat, haqiqiy MFA, TLS va tashqi integratsiyalar keyingi bosqich: [docs/admin-panel/09-keyingi-bosqich.md](docs/admin-panel/09-keyingi-bosqich.md), TZ bilan farqlar: [docs/admin-panel/13-tz-moslik-tekshiruvi.md](docs/admin-panel/13-tz-moslik-tekshiruvi.md).

Repozitoriyga kirmaydiganlar: ishchi baza (`admin-panel/data/`), lokal vositalar (`admin-panel/.tools/`), internet-preview tokeni, server loglari.

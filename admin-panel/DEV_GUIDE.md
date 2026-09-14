# Ishlab chiquvchi yo'riqnomasi (bo'lim qurish konvensiyalari)

Ilova: FastAPI + Jinja2 + HTMX + SQLite. Papka: `D:\Сардоррр\Smart Weapon\admin-panel`. Ishga tushirish: `python -X utf8 -m uvicorn app.main:app --port 8080 --app-dir <papka>`.
Dizayn: qorong'i "Nazorat markazi" (tokenlar `app/static/css/tokens.css`, komponentlar `app/static/css/app.css`, mos rasm `../docs/admin-panel/dizayn/malumot-dashboard.jpg`). Til: o'zbek lotin; har bir matn `{{ t("…") }}` orqali (kirill almashtirgich).

## Joriy integratsiya (2026-09-12)

Kirish endi `aq_session` orqali serverdagi xeshlangan sessiyaga bog‘langan. `aq_user` cookie vakolat bermaydi. Login: `/kirish`, demo parol `demo`, MFA `123456`; `admin2` ikkinchi tasdiqlovchi. Sessiya, MFA va foydalanuvchi o‘zgarishi jadvallari `security_models.py` da; haqiqiy nusxa manifesti `backup_models.py` da qo‘shimcha ro‘yxatdan o‘tadi. Yangi routerlarda `get_ctx` va `Ctx.can` tekshiruvlari majburiy; scope filtri ro‘yxat, tafsilot, partial, API va eksportda bir xil qo‘llanadi.

POST formalari `main.render` orqali chiqarilganda CSRF maydoni avtomatik qo‘shiladi; HTMX CSRF sarlavhasini yuboradi. TestClient bilan ham avval login sahifasidan CSRF cookie olish va POST da yuborish kerak. `tests/verify_auth.py` va `tests/verify_integration.py` amaldagi namunalar. Sinovlar uchun `requirements-dev.txt` o‘rnating va README dagi buyruqni ishlating; barcha tekshiruvlar vaqtinchalik bazalarda bajariladi.

Quyidagi umumiy fayllarni tahrirlamaslik qoidasi parallel bo‘lim ijrochilari o‘rtasidagi fayl egaligiga tegishli. Umumiy integratsiya o‘zgarishlarini asosiy integrator kelishilgan holda bajaradi. Moslashuvchan maket uchun `sections/layout.css` bo‘lim CSS fayllaridan keyin ulanadi.

Zaxira UI haqiqiy lokal SQLite nusxa va alohida test fayliga tiklashdan foydalanadi. NAS va avtomatik jadval ulanmagan. `Backup` dagi eski seed tarixlari real fayllardan alohida belgilanadi. Ishchi bazani tiklash sinovi orqali almashtirish mumkin emas. Nusxa/tiklash buyruqlari va demo chegaralari README da.

## Fayllar (o'qib chiqing)
- `app/models.py` — barcha jadvallar (Region, Unit, Armory, Cabinet, Officer, Eligibility, Shift, Item, Custody, Event, Alarm, Mode, ArmoryShift, Device, Backup, User, ExportLog, SettingsAudit, Setting).
- `app/services/events.py` — `record_event(db, type, cabinet=, armory=, officer=, ...)` append-only jurnal + hash zanjiri; `EVENT_RULES`, `verify_chain(db)`.
- `app/services/kpi.py` — `kpis(db, scope_kind, scope_id)`, `region_rows(db)`, `daily_ops(db, days, armory_ids)`, `armory_ids_for_scope`.
- `app/services/sim.py` — simulyator harakatlari (olish/qaytarish, signallar, rejimlar). `mode_start/mode_stop/mode_progress`.
- `app/services/mapsvg.py` — `region_paths(rows, link_base=...)` xarita SVG.
- `app/services/live.py` — `hub.broadcast_threadsafe({...})` jonli xabar (record_event dan keyin `sim._notify` ishlatadi).
- `app/deps.py` — `Ctx` (user, lang, scope_kind, scope_id, role, `can(action)`), `get_ctx`. `app/db.py` — `get_db`.
- `app/main.py` — `render(request, template, ctx, active=..., breadcrumb=[(label, href), ...], **kw)`; NAV; filtrlar `num`, `dt`, `ago`; router avtoulash: `app/routers/<nom>.py` ichida `router = APIRouter()` bo'lsa yetarli (nomlar: hududlar, qurolxonalar, yacheykalar, xodimlar, inventar, jurnal, signallar, rejimlar, hisobotlar, qurilmalar, sozlamalar, auth).
- `app/templates/base.html`, `macros.html` (icon, kpi, card_head [call bloki bilan], level_badge, level_icon, status_chip, cab_status, num_cell, empty), `dashboard.html`, `partials/*.html`, `sim.html` — namuna sifatida o'qing.
- `app/icons.py` — ikonka nomlari (`ICONS`), emoji ishlatilmaydi.

## Router namunasi
```python
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Cabinet
router = APIRouter()

@router.get("/yacheykalar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), holat: str = "", q: str = "", page: int = 1):
    from ..main import render            # import ichida (sikl oldini olish)
    ...
    return render(request, "yacheykalar/list.html", ctx, active="yacheykalar", breadcrumb=[("Yacheykalar", "/yacheykalar")], rows=rows, title="Yacheykalar")
```
- Shablon: `{% extends "base.html" %}{% from "macros.html" import icon, card_head, ... with context %}{% block content %}…{% endblock %}`.
- Sahifa sarlavhasi: `<div class="page-head"><h1 class="page-title">{{ t("…") }}<small>…</small></h1><div class="page-actions">…</div></div>`.
- Kartochka: `<section class="card">{% call card_head("Sarlavha") %}…o'ng tomondagi meta…{% endcall %} … </section>`.
- Jadval: `<table class="tbl">` (`th.l`/`td.l` chapga), qatorga o'tish: `<tr class="row-link" data-href="/…">`.
- Chiplar: `.chip.chip-green|yellow|red|gray`, belgilar `.badge.b-red|b-red-fill|b-yellow|b-blue|b-violet`, tugmalar `.btn .btn-primary .btn-danger .btn-ghost .btn-sm .btn-xs`, filtrlar `<div class="filters">`, `.grid-2 .grid-3 .stack .kv .notice(.red|.yellow|.green) .pill(.on) .pager .empty`.
- Formalar: oddiy `POST` + `RedirectResponse(status_code=303)`; xavfli harakatlar (bloklash, favqulodda so'rov, rol berish) uchun sabab maydoni va tasdiq. HTMX faqat jonli qismlar uchun: `hx-get="/…/partials/…" hx-trigger="live from:body, every 30s" hx-swap="innerHTML"`.
- Huquqlar: `ctx.can("bloklash")` va h.k.; ruxsat bo'lmasa tugmani ko'rsatmang va serverda 403 qaytaring.
- Har o'zgartirish `record_event(...)` bilan jurnalga yoziladi (turi `EVENT_RULES` da bo'lsin; yangi tur kerak bo'lsa `events.py` ga qo'shmang, mavjudini tanlang yoki `payload` ga yozing). Panel HECH QACHON qulf ochmaydi.
- Sana/vaqt: `datetime.now()` (mahalliy), ko'rsatish `| dt("%d.%m.%Y %H:%M")`.
- Sahifalash: `page`, `per_page=50`, `.pager`.
- Umumiy fayllarni (main.py, base.html, macros.html, app.css, models.py, events.py) O'ZGARTIRMANG. Qo'shimcha CSS kerak bo'lsa `app/static/css/sections/<bo'lim>.css` yarating va shablonda `{% block head %}<link rel="stylesheet" href="/static/css/sections/<bo'lim>.css">{% endblock %}`. Yangi xizmat kerak bo'lsa `app/services/<bo'lim>_svc.py`.
- Sinov: `python -B -X utf8 tests/verify_integration.py` — vaqtinchalik bazada login/MFA, sahifalar va vakolat doirasini tekshiradi. Boshqa `tests/verify_*.py` skriptlari tegishli jarayonlarni qamrab oladi. TestClient startup ishlashi uchun `with TestClient(app) as client:` kontekstidan foydalaning; himoyalangan sahifani tekshirishdan oldin haqiqiy login oqimini bajaring.

## Bo'limlar va talablar (02-talablar §5, TZ, 06-dizayn tizimi)
1. **hududlar** — `/hududlar` (14 hudud kartochkalari/jadvali KPI bilan, saralash), `/hudud/{id}` (hudud sahifasi: hudud KPI, bo'linmalar jadvali (Unit) har biri bo'yicha yacheyka/berilgan/kechikish/signal/oflayn, hudud signal lentasi, qurolxonalar ro'yxati). Breadcrumb Respublika › Hudud.
2. **qurolxonalar** — `/qurolxonalar` (ro'yxat, filtr: hudud, holat onlayn/oflayn), `/qurolxona/{id}` (qurolxona sahifasi: KPI, yacheykalar rejasi devor/qator bo'yicha (A/B devor, holat rangi, bosilsa yacheyka), qurilmalar holati, joriy smena, so'nggi hodisalar), **smena ochish vizardi** `/qurolxona/{id}/smena/ochish` (o'z-tekshiruv natijalari: server, baza, kamera, terminal, kontroller, UPS, disk — Device jadvalidan; yacheyka va inventar solishtiruvi; ruxsat ro'yxatini tasdiqlash; ArmoryShift yaratish, event `smena_ochildi`), **smena yopish** `/qurolxona/{id}/smena/yopish` (qaytarilmagan qurollar ro'yxati, ochiq signallar, mas'ul tasdig'i, smena hisoboti sahifasi, event `smena_yopildi`). Rollar: navbatchi, qurolxona_masuli.
3. **yacheykalar** — `/yacheykalar` (ro'yxat: label, qurolxona, hudud, xodim, holat, AK/PM mavjudligi, eshik, batareya; filtrlar holat/hudud/qidiruv; sahifalash), `/yacheyka/{id}` (yacheyka kartasi: 2D raqamli egizak SVG — 5 zona (0–1150 AK+sumka, 1150–1450 o'q-dori/bronjilet, 1450–1700 PM+magazin+kishan, 1700–1950 dubulg'a+gaz niqobi, 1950–2000 texnik) uyalar bilan, har uyada jihoz holati va qulf (Cabinet.ak_present, pm_present, ak_clamp_locked, pm_box_locked, door_open, door_locked); terminal ko'zgusi (terminal_state, matnlar `sim.TERMINAL_TEXT`, LED rangi); telemetriya (mains, battery_pct, temp_c, controller_online, last_seen); biriktirilgan xodim; jihozlar ro'yxati (Item); hodisalar vaqt chizig'i (Event, oxirgi 50); harakatlar: bloklash/blokdan chiqarish (sabab, event `shkaf_bloklandi`/`shkaf_blokdan_chiqdi`), xizmat rejimi, biriktirish/ajratish (xodim tanlash; event `biriktirildi`/`ajratildi`); jonli yangilanish partial). Rollar: qurolxona_masuli.
4. **xodimlar** — `/xodimlar` (ro'yxat: F.I.Sh., tabel, bo'linma, lavozim, holat, yacheyka, qurollangan/yo'q (ochiq Custody); filtr hudud/bo'linma/holat/qidiruv; sahifalash), `/xodim/{id}` (karta: 5 yaroqlilik yozuvi (Eligibility) muddatlari bilan, kredensiallar (karta, yuz, barmoq holati), ruxsatlar AVTOMAT/TO'PPONCHA (permit_ak/permit_pm), navbat (Shift), yacheyka, custody tarixi, rad etishlar (Event), harakatlar: xizmat holatini o'zgartirish (ta'til, kasallik → bloklash), ruxsatni bekor qilish). `/qidiruv?q=` — xodim, yacheyka (label/serial), jihoz seriya raqami bo'yicha umumiy qidiruv natijalari.
5. **inventar** — `/inventar` (tab: qurol/magazin/o'q-dori/jihoz; jadval: model, seriya, RFID, yacheyka, xodim, holat, ko'rik holati; filtrlar holat (`?holat=yo'q`), kechikish (`?kechikish=1`), farq (`?farq=1` → match_ok False custody), hudud; sahifalash), `/jihoz/{id}` (karta + chain of custody (Custody) vaqt chizig'i; ko'rik/ta'mir holatini o'zgartirish; ushlab turish (hold) — berish bloklanadi), `/inventarizatsiya` (sessiya boshlash: qurolxona tanlash, RFID skan simulyatsiyasi (Item.state bilan solishtirish), farqlar ro'yxati, aktni yakunlash (PDF reportlab bilan), event `inventarizatsiya`).
6. **jurnal** — `/jurnal` (append-only Event jadvali: vaqt, daraja, tur, hudud/bo'linma/qurolxona, yacheyka, xodim, jihoz, usul, natija, sabab; filtrlar: sana oralig'i, hudud, tur (`?tur=operatsiya|rad_etildi|favqulodda|...`), daraja, xodim, yacheyka, oflayn belgisi; sahifalash 100; `/jurnal/{id}` batafsil (payload, hash, prev_hash); "Yaxlitlikni tekshirish" tugmasi → `verify_chain` natijasi; eksport CSV (ExportLog yozuvi bilan, maqsad maydoni); `/jurnal/favqulodda` alohida tab: favqulodda ochilishlar va mexanik kalit hodisalari (tahrirlash yo'q).
7. **signallar** — `/signallar` (signal markazi: faol signallar 4 daraja (INFO/WARNING/CRITICAL/SECURITY) rang va belgi bilan, filtr daraja/hudud/holat (faol/tasdiqlangan/yechilgan), tasdiqlash (ack) va yechish tugmalari (sabab), CRITICAL/SECURITY uchun "tasdiq talab qiladi" kartochkasi ustida, qorovul postiga yo'naltirilgan belgisi, foto/video havola o'rnida "kamera kadri (simulyatsiya)" bloki; jonli partial (live); `/signal/{id}` batafsil; yechilgan signallar tarixi). Rollar: qurolxona_masuli, navbatchi.
8. **rejimlar** — `/rejimlar` (faol rejimlar (Mode) jonli: turi, qamrov, boshlagan, tasdiqlovchi, boshlanish vaqti, berildi/jami, navbat, o'rtacha vaqt, progress bar; har yacheyka holati (qurolxona yacheykalari ro'yxati: olindi/kutmoqda); rejim boshlash formasi (qurolxona, tur, boshlovchi, ikkinchi tasdiqlovchi, sabab — `sim.mode_start`), tugatish (`sim.mode_stop`), tarix). Rollar: navbatchi.
9. **hisobotlar** — `/hisobotlar` (7 hisobot: berish-qaytarish jurnali, joriy qurollanganlik, insidentlar, administrator harakatlari (SettingsAudit + SECURITY hodisalar), texnik holat (Device/Armory), kechikishlar, inventar farqlari; filtrlar: sana oralig'i, hudud, bo'linma; oldindan ko'rish jadvali; eksport CSV/XLSX (openpyxl)/PDF (reportlab); har eksport ExportLog ga raqam (`E-2026-000123`), kim, maqsad (majburiy), amal qilish muddati, fayl hash bilan yoziladi va event `eksport_qilindi`; `/hisobotlar/eksportlar` jurnali).
10. **qurilmalar** — `/qurilmalar` (5 daraja daraxti: respublika › hudud › qurolxona › terminal/kontrollerlar; Device jadvali: kamera, kommutator, UPS, NAS, server, terminal; holat, ko'rsatkichlar (CPU, RAM, disk, batareya, oqim), last_seen; filtr holat; `/qurilma/{id}`; demo harakatlar: self-test, vaqt sinxroni, xizmat rejimi (event `texnik_xizmat`)). `/qurilmalar/zaxira` haqiqiy SQLite nusxa va manifest yaratadi; tiklash sinovi alohida faylga nusxalaydi, SHA-256, SQLite va auditni tekshiradi. Natija `Backup` va `BackupArtifact` orqali qayd etiladi. Eski seed yozuvi tekshirilgan nusxa sifatida hisoblanmaydi. NAS va avtomatik jadval ulanmagan. Zaxira amallari markaziy administratorga tegishli.
11. **sozlamalar** — `/sozlamalar` (tablar: foydalanuvchilar va rollar (User CRUD; rol berish so'rovi → ikkinchi tasdiq: pending holat, boshqa administrator tasdiqlaydi; event `huquq_berish_tasdiqlandi`), autentifikatsiya siyosati (Setting kalitlari), chegaralar (Setting: eshik_ochiq_*, rad_blok_*, batareya_past_pct, urilish_g, qaytarish_grace_min, favqulodda_tasdiqlovchilar), saqlash muddatlari (video_saqlash_kun, foto_saqlash_kun, audit_saqlash_yil), integratsiyalar holati (statik ro'yxat: HR, navbatchilik, kirish nazorati, videokuzatuv, SIEM — "ulanmagan"), sozlamalar auditi (SettingsAudit: har o'zgarish kim/qachon/eski/yangi; event `sozlama_ozgardi`), til). Rollar: administrator.
12. **auth** — `/kirish`: login + parol (demo hisoblarda `demo`) + MFA qadami (demo kodi `123456`) → tasodifiy `aq_session` cookie; uning faqat hashi serverda saqlanadi. `/profil` da rol, vakolat va sessiya muddati ko‘rsatiladi; chiqish CSRF bilan himoyalangan POST orqali. Xato urinishlar/blok bazada saqlanadi (boshlang‘ich: 3 urinish, 15 daqiqa); demo bo‘lmagan MFA sozlanmaguncha rad etiladi. Dizayn: markazda kartochka, gerb, tizim nomi.

Barcha bo'limlar: `active=<bo'lim nomi>`, breadcrumb, `title`. Ro'yxat sahifalarida har qatorda hudud va qurolxona nomi ko'rinsin. Har sahifa ekranga sig'sin, uzun ro'yxatlar sahifalansin. Bo'sh holat uchun `empty()` makrosi.

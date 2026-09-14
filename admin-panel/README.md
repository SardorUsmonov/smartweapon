# Aqlli qurolxona — Nazorat markazi

FastAPI + Jinja2 + HTMX + SQLAlchemy/SQLite asosidagi mahalliy demo admin panel. Ma’lumotlar sintetik; haqiqiy apparat integratsiyasi ulanmagan. O‘zbek lotin va kirill interfeysi mavjud.

## Ishga tushirish (Windows PowerShell)

Python 3.11 bilan tekshirilgan. Ushbu `admin-panel` papkasida:

```powershell
python -m pip install -r requirements.txt
python -B -X utf8 run.py
```

Manzil: <http://127.0.0.1:8080>. Server faqat mahalliy `127.0.0.1` manzilini tinglaydi. Terminaldagi `Ctrl+C` uni to‘xtatadi. Kod tahrirlanayotgan vaqtda `python -B -X utf8 run.py --reload` ishlatish mumkin.

Standart baza: `data/aq_central.sqlite3`. Mavjud yozuvlar saqlanadi; yangi sessiya, tasdiqlash va zaxira jadvallari qo‘shimcha yaratiladi. Bo‘sh bazaga birinchi ishga tushishda demo ma’lumotlar kiritiladi. Mavjud bazani qayta seed qilish kundalik ish jarayoniga kirmaydi.

Alohida yangi demo kerak bo‘lsa, yangi fayl nomini tanlang:

```powershell
$env:AQ_DB = 'data\demo-alohida.sqlite3'
$env:AQ_SEED = 'small'
$env:AQ_PORT = '8081'
python -B -X utf8 run.py
```

Standart bazaga qaytish uchun serverni to‘xtating, shu terminalda `Remove-Item Env:AQ_DB -ErrorAction SilentlyContinue` va `Remove-Item Env:AQ_PORT -ErrorAction SilentlyContinue` bajaring, so‘ng `run.py` ni qayta ishga tushiring.

## Namoyish oldidan

Namoyishdan 5–10 daqiqa oldin, server to‘xtatilgan holda:

```powershell
python -B -X utf8 scripts\demo_reset.py
python -B -X utf8 run.py
```

Skript joriy bazani `data\arxiv\` ga vaqt belgisi bilan ko‘chiradi va yangi demo ma’lumot kiritadi (30 kunlik tarix, yangi sinxron vaqtlari, Yunusobodda faol o‘quv trevoga). Server ishlayotgan bo‘lsa skript bazaga tegmaydi va to‘xtatishni so‘raydi.

Kirgandan so‘ng **Simulyator → Avto-rejim** ni yoqing: har intervalda tasodifiy hodisa yoziladi va onlayn obyektlar sinxron xabar yuboradi, shu sabab xaritadagi hududlar 15 daqiqadan keyin «eskirgan» holatga tushmaydi. Bosish yo‘li va vaqt taqsimoti: `../docs/admin-panel/16-prezentatsiya-ssenariysi.md`.

## Demo kirish

Barcha boshlang‘ich demo hisoblar uchun **parol: `demo`**, **MFA kodi: `123456`**.

| Login | Rol va qamrov |
|---|---|
| `admin` | Respublika administratori |
| `admin2` | Ikkinchi administrator; foydalanuvchi o‘zgarishini tasdiqlash |
| `tekshiruvchi` | Respublika bo‘yicha ko‘rish va hisobotlar |
| `rahbar` | Respublika rahbariyati |
| `hudud_tk` | Toshkent shahri rahbariyati |
| `navbatchi` | Yunusobod qurolxonasi navbatchisi |
| `masul` | Yunusobod qurolxonasi mas’uli |

Yangi foydalanuvchi Sozlamalar orqali yaratiladi. So‘rovni boshqa administrator tasdiqlaguncha hisob nofaol. O‘z so‘rovini tasdiqlash mumkin emas. Tasdiqlangan rol/vakolat o‘zgarishi eski sessiyalarni bekor qiladi. Mavjud parollar ishga tushishda qayta yozilmaydi.

Sessiya muddati va xato urinishlar chegarasi sozlanadi; boshlang‘ich qiymatlar 60 daqiqa, 3 xato urinishdan so‘ng 15 daqiqa blok. Chiqish profil sahifasidagi tugma orqali bajariladi.

## Ish jarayonlari

- Hudud → bo‘linma → qurolxona → yacheyka orqali tafsilotlarga o‘tiladi. Qidiruv, filtrlar, sahifalash va jonli qismlar foydalanuvchi vakolatini hisobga oladi.
- Smenani ochishda qurilmalar, inventar solishtiruvi va ruxsat ro‘yxati tekshiriladi. Yopishda ochiq masalalar ko‘rsatiladi va zarur tasdiqlar olinadi. Yopilgan smena hisoboti o‘sha paytdagi saqlangan natijani ko‘rsatadi.
- Hisobot eksportida maqsad kiritiladi. CSV/XLSX/PDF fayli eksportlar jurnalida raqam, muddat va SHA-256 bilan qayd etiladi. Muddati o‘tgan yoki o‘zgartirilgan faylni yuklash rad etiladi.
- Jurnaldagi «Yaxlitlik» hodisa zanjirlarini tekshiradi. Audit yozuvlari panel orqali tahrirlanmaydi.

## Zaxira va tiklash

Qurilmalar → Zaxira nusxalash orqali markaziy administrator haqiqiy SQLite nusxa oladi. Fayllar `AQ_DB` yonidagi `<baza-nomi>-backups` papkasida saqlanadi. Kunlik/haftalik — qo‘lda tanlanadigan toifalar; avtomatik jadval va NAS ulanishi yoqilmagan.

«Tiklash sinovi» nusxani alohida test fayliga tiklaydi, fayl hashini, SQLite yaxlitligini va auditni tekshiradi. Ishchi bazani almashtirmaydi. Dastlabki seed yozuvlari alohida demo tarix sifatida ko‘rsatiladi; ular real fayl mavjudligini tasdiqlamaydi.

Buyruq orqali yangi nusxa va alohida tiklangan fayl:

```powershell
python -B -X utf8 -m app.services.backup_svc backup data\manual-backup.sqlite3
python -B -X utf8 -m app.services.backup_svc restore-copy data\manual-backup.sqlite3 data\recovered.sqlite3
```

Chiqish fayli yangi bo‘lishi kerak; mavjud fayl ustiga yozilmaydi. Nusxa bilan uning yonidagi manifest faylini birga saqlang. Tiklangan bazani ko‘rish uchun ishlayotgan serverni to‘xtating, `$env:AQ_DB = 'data\recovered.sqlite3'` ni belgilang va panelni qayta boshlang. Eski bazaga qaytish uchun serverni to‘xtatib `AQ_DB` ni eski manzilga qaytaring. SQLite ishlayotgan paytda `.sqlite3` faylini oddiy nusxalash WALdagi ma’lumotni qoldirib ketishi mumkin; yuqoridagi nusxalash vositasidan foydalaning.

Nusxa tarkibida foydalanuvchi va sessiya jadvallari ham bor; ularni ochiq veb papkaga joylashtirmang. Eksport fayllari bazadan alohida saqlanadi, ularning papkalarini ham alohida saqlash kerak.

## Tekshiruvlar

```powershell
python -m pip install -r requirements-dev.txt
$env:AQ_DEMO = '1'
Get-ChildItem tests\verify_*.py | ForEach-Object {
    python -B -X utf8 $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Sinov xatosi: $($_.Name)" }
}
```

Skriptlar vaqtinchalik bazalarda ishlaydi. Eski bazaga moslik sinovlari loyihadagi `.backups/admin-panel-20260912-141835/aq_central.sqlite3` boshlang‘ich nusxasiga tayanadi; uni test fixture sifatida saqlang. Yangi seed uchun alohida integratsiya sinovi mavjud.

## Demo chegaralari

- MFA kodi simulyatsiya. `AQ_DEMO=0` uni o‘chiradi; haqiqiy MFA adapteri hali ulanmagan, shu sabab MFA talab etilgan hisoblar kirishi rad etiladi. Bu parametrning o‘zi panelni real foydalanishga tayyor qilmaydi.
- HR, navbatchilik, terminal, kamera va SIEM integratsiyalari ulanmagan. Simulyator sintetik holatlarni o‘zgartiradi.
- Qurilma chegaralari sozlama sifatida saqlanadi; apparatga uzatilmaydi. Saqlash muddatlari avtomatik ma’lumot o‘chirishni ishga tushirmaydi.
- Dastlabki bazada 7 ta eski demo hodisasining hash zanjiri noto‘g‘ri. Sabab eski seed generatoridagi payload/oldingi hash nomuvofiqligi. Ular yashirin qayta yozilmadi. Yangi yaratilgan demo bazaning to‘liq zanjiri tekshiruvdan o‘tadi; eski bazadan olingan nusxada shu 7 nomuvofiqlik ham saqlanadi.
- Eski inventar holati bilan ochiq berish qaydlari orasidagi farqlar alohida belgilanadi. «Xodimlardagi qurollar» har jihozni bir marta sanaydi; ochiq va takroriy qaydlar soni alohida. Boshlang‘ich bazada 182 jihozga 183 ochiq qayd bor. Yangi seed mos holat yaratadi, eski tarix o‘zgarmaydi.

Ish rejasi: `../docs/admin-panel/07-ish-reja.md`. Tekshiruv dalillari: `../docs/admin-panel/08-yakuniy-tekshiruv.md`. Real foydalanishga o‘tish bosqichlari: `../docs/admin-panel/09-keyingi-bosqich.md`. Dasturchi konvensiyalari: `DEV_GUIDE.md`.

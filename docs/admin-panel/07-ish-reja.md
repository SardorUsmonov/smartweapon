# Admin panelni yakunlash ish rejasi

Boshlanish: 2026-09-12. Foydalanuvchi topshirig‘i: ish rejasini tuzish va mavjud admin panelni davom ettirish.

## Maqsad va chegaralar

Mavjud FastAPI + Jinja2 + HTMX + SQLite ilovasining demo versiyasini yakunlash. «Nazorat markazi» dizayni, o‘zbek lotin/kirill interfeysi va mavjud ma’lumotlar saqlanadi. Haqiqiy kamera, terminal yoki kontroller bilan integratsiya keyingi, alohida bosqich. Paneldan jismoniy qulf ochish qo‘shilmaydi.

Asos: `DEV_GUIDE.md`, `02-talablar-xaritasi.md`, `05-tz-moslashtirish.md`, `06-dizayn-tizimi.md` va amaldagi kod. Hujjatdagi talabning mavjudligi uning ishlayotganiga dalil hisoblanmaydi: har bosqich amalda tekshiriladi.

## Ishlar va qabul mezonlari

- [x] Boshlang‘ich kod va SQLite bazasining zaxira nusxasini olish.
  - Nusxa: `.backups/admin-panel-20260912-141835/` (`source.zip`, `aq_central.sqlite3`, `manifest.json`).
- [x] 1. Mavjud xatolarni tuzatish.
  - Yetti hisobotning har biri va bo‘linma tafsiloti ochiladi.
  - Hisobot filtrlari ishlaydi; CSV/XLSX/PDF yuklanadi, eksport maqsadi va fayl hashi qayd etiladi.
- [x] 2. Yacheykalar bo‘limini tugatish.
  - Ro‘yxat, qidiruv, filtrlar, sahifalash, karta, telemetriya, 2D holat tasviri, hodisalar va xato sahifalari.
  - Mavjud amallar rol/vakolat hamda tegishli amallarda sabab va tasdiq tekshiruvlaridan o‘tadi; auditga yoziladi.
- [x] 3. Jurnal va smenalar tarixini tugatish.
  - Hodisa tafsiloti, favqulodda hodisalar, yaxlitlik tekshiruvi, eksport shakli va eksport tafsiloti.
  - Smenalar tarixi va hisobotlarga o‘tish; bo‘sh holatlar.
- [x] 4. Demo ma’lumotlar va audit yaxlitligi.
  - Yangi yaratilgan demo bazaning to‘liq hodisa zanjiri tekshiruvdan o‘tadi.
  - Oldingi audit yozuvlari yashirincha qayta yozilmaydi. Mavjud bazadagi aniqlangan nomuvofiqlik va uning kelib chiqishi hujjatlashtiriladi.
- [x] 5. Kirish va foydalanuvchi sessiyasi.
  - Login, demo MFA qadami, xato urinishlar bloki, sessiya muddati va chiqish.
  - Foydalanuvchi nomini cookie orqali almashtirish vakolat bermaydi; autentifikatsiyasiz ma’lumot va amallar himoyalanadi.
- [x] 6. Sozlamalar va foydalanuvchilar.
  - Foydalanuvchi qo‘shish/tahrirlash/faolsizlantirish, vakolat doirasi, rol o‘zgarishini boshqa administrator tasdiqlashi.
  - Tizim chegaralari, saqlash muddatlari, autentifikatsiya siyosati, integratsiyalar holati va sozlamalar auditi.
- [x] 7. Yakuniy integratsiya va foydalanish tekshiruvi.
  - Asosiy sahifalar, ichki havolalar, lotin/kirill, qidiruv, filtrlar va jonli qismlar.
  - Rollar va vakolat doiralari, ruxsatsiz amallar, smena, inventarizatsiya, signallar va eksport oqimlari.
  - Brauzerda asosiy ekranlar; tor va katta ekranlarda maketning foydalanishga yaroqliligi.
  - Ishga tushirish, demo kirish va zaxiradan tiklash yo‘riqnomasi; sinov natijalari.

## Ish tartibi

Yacheykalar, jurnal/smenalar hamda hisobot/bo‘linma tuzatishlari alohida agentlarga berilgan. Asosiy agent integratsiya, autentifikatsiya, sozlamalar, audit, sinov va hujjatlarni boshqaradi. Bir faylni bir vaqtda ikki agent tahrirlamaydi.

Sinovlar alohida `AQ_DB` bazalarida o‘tkaziladi. Foydalanuvchining asosiy bazasi avtomatik qayta to‘ldirilmaydi va o‘chirilmaydi. Yangi ma’lumotlar uchun yaratiladigan jadvallar hamda zarur moslashtirishlar mavjud yozuvlarni saqlashi shart.

## Boshlang‘ich tekshiruv

- 14 hudud, 18 qurolxona, 321 yacheyka, 295 xodim; 24 426 hodisa.
- 11 ta shablon yo‘q: yacheykalar uchun 5, jurnal uchun 5, smenalar tarixi uchun 1.
- `/kirish` va `/sozlamalar` modullari yo‘q.
- 5 hisobotda sana arifmetikasi xatosi; bo‘linma sahifasida `cab_status` nomi makros va ma’lumot uchun bir xil ishlatilgan.
- 7 ta eski demo hodisasi hash tekshiruvidan o‘tmaydi. Dastlabki ssenariy yozuvlarida hash tanasi va oldingi hash noto‘g‘ri tuzilgan.

## Natijalar

2026-09-12 holati: 1–7-bosqichlar mahalliy demo doirasida bajarildi. Yakuniy dalillar `08-yakuniy-tekshiruv.md` da. Real foydalanishga o‘tish uchun alohida reja `09-keyingi-bosqich.md` da.

O‘n ikkita sinov skripti birgalikdagi so‘nggi ishga tushirishda xatosiz tugadi. Sinovlar vaqtinchalik bazalarda bajarildi:

- `verify_auth.py`: login, CSRF, MFA, sessiya almashishi/muddati, chiqish, xato urinishlar bloki va soxta cookie rad etilishi.
- `verify_settings.py`: hisob yaratish, ikkinchi administrator tasdig‘i, o‘z so‘rovini tasdiqlashning rad etilishi, sessiyalarni bekor qilish va sozlamalar auditi.
- `verify_yacheykalar.py`: yacheyka holatlari, 11 filtr, 15 sahifa/partial, rol va vakolat doiralari; inventarizatsiya, signallar va mavjud rejim jarayonlari.
- `verify_jurnal.py`: jurnal, kirill, filtr/sahifalash, 770 qatorli CSV, eksport yaxlitligi va hududiy chegaralar; smena sahifalariga 80 ta lotin/kirill GET so‘rovi.
- `verify_reports.py`: 7 hisobot uchun 42 ko‘rish holati va 21 CSV/XLSX/PDF eksporti; 18 bo‘linma tafsiloti; eksport hash, muddat va vakolat tekshiruvi.
- `verify_integration.py`: 45 sahifa/API, yangi 30 kunlik demo audit zanjiri va buzilishni aniqlash; jonli xabarlarning vakolat doirasi; Python/Jinja sintaksisi.
- `verify_smena.py`: haqiqiy login/MFA bilan smena ochish/yopish, eskirgan forma va yopilgan hisobot; 52 farq va 106 signalning to‘liq saqlanishi.
- `verify_backups.py`: haqiqiy SQLite nusxa, manifest/hash, alohida tiklash, eski auditning saqlanishi, xato fayl/yo‘l/rol/CSRF holatlari.
- `verify_export_renderers.py`: Unicode PDF, uzun raqamlar va yetakchi nollar, Excel sana/sonlari, CSV formulalaridan himoya, uzun matn maketi.
- `verify_navigation_filters.py`: 18 haqiqiy tafsilot havolasi, vakolat va joylashuv kesishmasi, forma, sahifalash va jonli qismlarda tanlovni saqlash.
- `verify_restrictions.py`: demo rad javobida holatning saqlanishi, takroriy amal, hisoblagich, qurilma xizmatidan chiqishda oldingi nosozlikni saqlash; HTMXda to‘g‘ri va xavfsiz xabar.
- `verify_inventory_consistency.py`: «Berilgan 8» havolasi → 8 jihoz; 182 jihoz/183 ochiq qayd/1 takror, vakolat, sahifalash, nomuvofiqlik va 100 qatorli tarix chegarasi; 19 eski jadvaldagi har bir qator saqlanishi, yangi seed holati va audit.

Yakuniy qabul tekshiruvlari:

- [x] Smenani muvaffaqiyatli ochish → yopish → tarix/hisobot: `verify_smena.py` o‘tdi. Shaxs sessiyadan olinadi; eskirgan forma yangi smenani yopmaydi; yopilgan hisobot natijasi saqlanadi. 52 ta farq va 106 ta signal kesilmasligi tekshirildi.
- [x] Haqiqiy SQLite zaxiralash va alohida faylga tiklash: `verify_backups.py` o‘tdi. Har bir asl qator saqlanadi; hash/manifest, buzilgan yoki yo‘q fayl, rol/CSRF va ustiga yozishni rad etish tekshirildi. 8081 sinov serverida ikki amal brauzer orqali ham bajarildi. NAS va avtomatik jadval ulanmagan deb ko‘rsatiladi.
- [x] Katta va tor ekranlar: 1440×900, 390×844 va odatiy 1280×720 ko‘rildi. Asosiy 12 sahifada butun sahifaning yon tomonga chiqishi bartaraf etildi. Keng jadvallar o‘z maydonida suriladi. PDF va native Excel namunalari `verification-20260912/export-samples/` da.
- [x] README: demo login, ishga tushirish, sinov va nusxa/tiklash buyruqlari yozildi. DEV_GUIDE sessiya/CSRF namunalari yangilandi.
- [x] Asosiy 8080 server yangi kod bilan ishga tushdi; login/MFA orqali Hududlar ochildi. `scripts/check_preserved_rows.py` barcha 19 eski jadvaldagi har bir eski qator o‘zgarmaganini tasdiqladi. Dalil: `verification-20260912/preservation.log`.
- [x] Yakuniy ko‘rikda topilgan ichki havola filtrlari: bo‘linma/qurolxona/xodimga o‘tishda tanlangan qamrovni saqlash va live/pager orqali tekshirish.
- [x] Simulyator taqiq holatini hisobga olishi: inventar hold, xodimning xizmat/ruxsat holati, mavjud yaroqlilik shartlari; rad etishda qulf/custody o‘zgarmasligi va rejim hisoblagichi oshmasligi. Rad javobida muvaffaqiyat belgisi chiqmaydi.
- [x] Barcha tuzatishlardan keyin 12 ta sinov skripti o‘tdi; 8080 server qayta ishga tushdi, asl qatorlar yana tekshirildi.
- [x] Inventar hisobi: eski va yangi seedda Custody ochiq bo‘lsa ham Item.state «mavjud» qolishi aniqlandi. Endi ochiq qaydlar alohida filtrlanadi, jihoz bir marta sanaladi, saqlangan inventar holati va nomuvofiqlik oshkora ko‘rsatiladi. Yangi seed mos holat yaratadi; eski yozuvlar o‘zgarmaydi. Brauzerda bo‘linma #2 «Berilgan 8» → aynan 8 jihoz tasdiqlandi; tor ekranda chiqish yo‘q.

Haqiqiy foydalanish uchun alohida bosqich: real MFA adapteri, terminal/kamera/HR/SIEM ulanishlari, qurilma sozlamalarini qo‘llash va avtomatik saqlash siyosati. Demo MFA kodi doimiy; integratsiyalar hozir ulanmagan. Eski bazadagi 7 ta seed hash nomuvofiqligi saqlanadi va oshkora ko‘rsatiladi; yangi seed zanjiri to‘liq tekshiruvdan o‘tdi.

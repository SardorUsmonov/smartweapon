# Demo admin panel — qabul dalillari

Sana: 2026-09-12. Qamrov: `07-ish-reja.md` dagi mahalliy demo. Haqiqiy apparat, real MFA va tashqi tizimlar alohida bosqich.

Qabul holati: mahalliy demo bo‘yicha 1–7-bosqich bajarildi. Yakuniy 12 ta sinov skripti xatosiz tugadi, yangilangan 8080 server va brauzerdagi asosiy jarayonlar tekshirildi. Bu real foydalanishga tayyorlik yoki foydalanuvchining rasmiy qabuli degani emas; keyingi ishlar `09-keyingi-bosqich.md` da.

## Talablar va dalillar

| Bosqich | Dalil |
|---|---|
| Boshlang‘ich zaxira | `.backups/admin-panel-20260912-141835/source.zip`, asl SQLite nusxasi, `manifest.json`; server yangilanishidan oldin `pre-activation.sqlite3` va manifest ham olindi |
| Hisobot va bo‘linma xatolari | `verify_reports.log`: 7 hisobot × 6 holat, 21 eksport, 18 bo‘linma; CSV/XLSX qator mazmuni, vakolat, hash va muddat |
| Yacheykalar | `verify_yacheykalar.log`: 11 filtr, 15 holat/partial, amallar va audit; nosozlik/xizmat taqiqi qayta tiklanishi |
| Jurnal va smena | `verify_jurnal.log`, `verify_smena.log`: CSV 770 qator, kirill, scope, audit; haqiqiy login bilan to‘liq smena jarayoni, takroriy/eskirgan forma va yopilgan hisobot |
| Seed va audit | `verify_integration.log`: yangi 30 kunlik demo zanjiri, keyingi append va qasddan buzilishni aniqlash. Asl bazadagi 7 eski xato saqlanadi |
| Kirish va sessiya | `verify_auth.log`: parol, MFA, CSRF, blok, token almashishi, muddati o‘tishi, chiqish, soxta cookie va noto‘g‘ri yo‘naltirishlar |
| Sozlamalar | `verify_settings.log`: ikkinchi administrator tasdig‘i, eski sessiyani bekor qilish, noto‘g‘ri qiymatlar, oxirgi ikki administratorni saqlash, audit |
| Zaxira/tiklash | `verify_backups.log`: haqiqiy SQLite fayli va manifest, barcha qatorlarning tengligi, alohida tiklash, 7 tarixiy xatoni yashirmaslik, hash/yo‘l/rol/CSRF va toza zanjirli fixture |
| Umumiy integratsiya | `verify_integration.log`: 45 sahifa/API, lotin/kirill, scope bo‘yicha xarita va jonli xabarlar, sessiyasiz yoki bekor qilingan WebSocket rad etilishi |
| Eksport maketi | `verify_export_renderers.log` va `export-samples/`: kirill, yetakchi nollar, uzun seriya/RFID, typed sana/son, uzun izoh; PDF va Excel ko‘rinishi |
| Filtrli navigatsiya | `verify_navigation_filters.log`: 18 haqiqiy havola, markaz/hudud/qurolxona vakolati bilan joylashuv kesishmasi; forma, sahifalash va jonli qismlarda filtrlar |
| Demo rad javobi | `verify_restrictions.log`: holat va audit saqlanishi, takroriy amal, hisoblagich; qurilmaning oldingi nosozligi va HTMXda rad javobini to‘g‘ri ko‘rsatish |
| Inventar hisobi | `verify_inventory_consistency.log`: haqiqiy «Berilgan 8» havolasi → 8 jihoz; distinct jihozlar va takroriy manba qaydlari; vakolat, sahifalash va nomuvofiqlik belgisi; yangi seed holati/audit va 19 eski jadval saqlanishi |
| Asl ma’lumotni saqlash | `preservation.log`: 19 jadvaldagi barcha eski qatorlar, jumladan 24 426 audit hodisasi o‘zgarmagan; yangi hisob/sozlama/sessiya jadvallari qo‘shimcha |
| Asosiy baza yaxlitligi | `source-integrity.json`: SQLite `ok`; 24 428 audit yozuvi tekshirildi, avvaldan mavjud 7 ta nomuvofiqlik saqlangan, birinchisi #24412 |

Jadvaldagi `.log` fayllar `verification-20260912/` papkasida. Testlar vaqtinchalik bazalarda bajariladi; asl bazaga biznes sinovlari kiritilmagan.

## Brauzer va eksport ko‘rigi

- 390×844: dashboard, yacheykalar ro‘yxati/kartasi, jurnal/tafsilot, sozlamalar/yangi hisob, hisobot, xodim, qurolxona, qurilmalar/karta tekshirildi. Kirish va MFA formasi ham ko‘rildi. Topilgan umumiy gorizontal chiqishlar tuzatildi.
- 1440×900: yuqori panel, hisobot/eksport formasi, sozlamalar, yacheyka, jurnal va zaxiralash ko‘rildi. Odatiy 1280×720 ekranda Hududlar ochildi; vaqtinchalik o‘lcham sozlamasi bekor qilindi.
- Yangi joylashuv filtrlari bilan inventar, signal va qurilmalar sahifalari 390×844 da yana ko‘rildi: umumiy sahifa va asosiy maydonning gorizontal chiqishi 0 piksel. Inventar KPI kartalari tor ekranda ikki ustunga joylashtirildi.
- Yakuniy serverda bo‘linma #2 «Berilgan 8» havolasi aynan 8 jihozni ochdi; inventar va berish qaydlari orasidagi 8 ta farq belgisi ko‘rindi. KPI «Uyada 16», «Xodimlardagi qurollar 8», «Kechikish 8» ko‘rsatdi. Yangi ko‘rinish 390×844 da qayta tekshirildi, o‘lcham qaytarilib Hududlar ochiq qoldirildi.
- Brauzerda sinov bazasidan haqiqiy nusxa olish → alohida tiklash bajarildi. Login → MFA → profil → chiqish → qayta kirish bajarildi. Konsolda tekshiruv paytida JavaScript xatosi qayd etilmadi.
- Keng 1 042 qatorli PDFning 26 sahifasi kontakt varag‘ida va namuna sahifalari to‘liq o‘lchamda ko‘rildi. 7 PDFdagi jami 34 sahifaning matn chegaralari tekshirildi.
- Native Excel orqali kirill namunasidagi `00123`, `00123456789012345678`, RFID va sana ko‘rsatilishi tekshirildi. Ikkala varaq tasviri, PDF/XLSX namunalari va PDF chegaralari dalili `export-samples/` da.

## Ishga tushirish va chegaralar

Amaldagi yo‘riqnoma: `../../admin-panel/README.md`. Demo kirish: `admin` / `demo`, MFA `123456`; ikkinchi tasdiqlovchi `admin2`.

Asl ma’lumotlar tarixiy sanalarda saqlangan. Bugungi KPI kechikishlari shu sanalardan hisoblanadi; panelni «yangi» ko‘rsatish uchun tarix qayta yozilmadi. 7 ta eski seed hash xatosi manba nusxada ham mavjud (birinchisi #24412); yangi zanjir generatori tuzatilgan. Nusxa/tiklashda bu farq ogohlantirish sifatida ochiq ko‘rsatiladi.

Inventar bo‘yicha topilgan tarixiy tafovut: boshlang‘ich bazada 183 ta ochiq berish qaydi 182 ta alohida jihozga tegishli. Bo‘linma #2 dagi 8 ta ochiq qaydda saqlangan inventar holati «mavjud» qolgan. Panel endi jihozlar va manba qaydlarini alohida hisoblaydi, saqlangan holat va nomuvofiqlikni ko‘rsatadi. Eski qaydlar o‘chirilmadi, birlashtirilmadi yoki qayta yozilmadi. Yangi seed mos inventar holatini yaratadi. «Uyada» hisobi o‘zi ruxsat yoki tayyorlikni tasdiqlamaydi.

Tashqi integratsiyalar, avtomatik NAS jadvali, haqiqiy MFA, apparatga chegaralarni uzatish va avtomatik ma’lumot saqlash/o‘chirish siyosati ushbu demo qabuliga kirmaydi. Ishchi jismoniy qurilmalarga boshqaruv qo‘shilmagan.

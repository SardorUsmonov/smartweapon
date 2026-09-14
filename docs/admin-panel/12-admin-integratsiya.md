# Tanlangan dizaynni asosiy admin panelga birlashtirish

Sana: 14.09.2026. Asosiy manzil: http://127.0.0.1:8080/.
8092 portidagi interaktiv maket tasdiqlangan ko‘rinish uchun manba; undagi namunaviy raqamlar asosiy bazaga ko‘chirilmaydi.

## Qabul mezonlari

- Asosiy menyuning har bir bo‘limi haqiqiy sahifani ochadi; amaldagi rol va hudud bo‘yicha ruxsatlar saqlanadi.
- Xarita, hudud tanlash, yaqinlashtirish, filtr va qaytarish boshqaruvlari ishlaydi. Tafsilot havolalari aynan tanlangan hududning ro‘yxatlarini ochadi.
- Ogohlantirishlar kichik ekranda ham xaritadan oldin ko‘rinadi; tanlov konturi holat rangini almashtirmaydi.
- Hisoblar bazadagi yozuvlardan olinadi. Signal va aloqa uzilishi alohida; yo‘q/eskirgan xabarlar yashirilmaydi. Oldingi davr ishonchli manbasi bo‘lmasa, o‘zgarish taxmin qilinmaydi.
- 30 soniyalik HTMX yangilanishi tanlangan hudud, filtr, masshtab va klaviatura fokusini buzmaydi.
- Kunduzgi/tungi rejim tanlovi sahifalar va qayta yuklashdan keyin saqlanadi.
- Asosiy sahifalar, filtrlar, formalar va mavjud biznes jarayonlari alohida sinov bazasida tekshiriladi; brauzer tekshiruvi natijasi alohida qayd etiladi.

## Tekshirilgan havola shartlari

`id` — Region jadvalidagi sonli identifikator; xarita geometriyasining ISO kodi emas.

| Ko‘rsatkich yoki amal | Manzil |
| --- | --- |
| Hudud tafsiloti | `/hudud/{id}` |
| Hudud qurolxonalari | `/qurolxonalar?hudud={id}` |
| Oflayn obyektlar | `/qurolxonalar?hudud={id}&holat=oflayn` |
| Onlayn obyektlar | `/qurolxonalar?hudud={id}&holat=onlayn` |
| Hudud qurollari | `/inventar?hudud={id}` |
| Xodimlardagi qurollar | `/inventar?hudud={id}&berilgan=1` |
| Qaytarish kechikishi | `/inventar?hudud={id}&kechikish=1` |
| Faol signallar | `/signallar?hudud={id}` |
| Ogohlantirishlar | `/signallar?hudud={id}&daraja=WARNING` |
| Alohida kritik / xavfsizlik darajasi | `/signallar?hudud={id}&daraja=CRITICAL` / `SECURITY` |
| Tasdiq kutayotgan signallar | `/signallar?hudud={id}&holat=kutmoqda` |

Birlashtirishdan oldingi routerda `daraja` bitta aniq qiymat qabul qiladi. CRITICAL+SECURITY yig‘indisini faqat CRITICAL ro‘yxatiga bog‘lash noto‘g‘ri; havola yozuvi yoki filtr mantiqi bunga mos bo‘lishi kerak.

## Saqlanishi kerak bo‘lgan mavjud ishlash shartlari

- `app.js` jonli ulanish belgisi uchun `.sys-ok`, ichidagi `.dot` va oxirgi matn tugunidan foydalanadi.
- Soat `#clock-time`, `#clock-date`, `body[data-now]` orqali ishlaydi. Til `body[data-lang]` orqali olinadi.
- `#topbar-status` faol rejimni `/partials/topbar` orqali yangilaydi.
- `theme.js` `data-theme-toggle` boshqaruvlari va `aq-theme` saqlash kalitidan foydalanadi.
- Bo‘sh eksport, oflayn obyekt inventarizatsiyasi, joriy holat, faol rejim va vakolat bo‘yicha ataylab o‘chirilgan boshqaruvlar saqlanadi.
- To‘liq admin mavjud menyusi: Respublika, Hududlar, Qurolxonalar, Qurol kataklari, Xodimlar, Inventar, Jurnal, Signallar, Rejimlar, Hisobotlar, Qurilmalar, Sozlamalar; Simulyator faqat ruxsati bor foydalanuvchiga.

## Dalillar

Boshlang‘ich kod tekshiruvi bajarildi. Asosiy agent tomonidan haqiqiy 8080 panelida quyidagilar brauzerda tekshirildi:

- Hududlar, Qurolxonalar, Qurol kataklari, Xodimlar, Inventar, Jurnal, Signallar, Rejimlar, Hisobotlar, Qurilmalar, Sozlamalar va Simulyator — 12 ta menyu havolasi bosildi; manzil va sahifa sarlavhasi mos chiqdi.
- Qurolxonalar sahifasida Toshkent sh. filtri yuborildi: 3 ta obyekt ro‘yxati chiqdi; Yunusobod qurolxonasi tafsiloti ochildi.
- Global qidiruvda `Y-001` yuborildi: 18 ta mos katak natijasi chiqdi; natijadan `/yacheyka/1` tafsiloti ochildi.
- Ushbu brauzer tekshiruvida login/MFA dan boshqa biznes holati o‘zgartirilmadi.
- Qurol katagi tafsiloti 390×844 mobil o‘lchamda tekshirildi: hujjat kengligi 390 px, asosiy maydon ichki kengligi va scroll kengligi 380/380 px; gorizontal menyu aylantiriladi, sahifa chetdan chiqmaydi.
- 820×900 planshet o‘lchamida hujjat kengligi 820 px, asosiy maydon 654/654 px. Yuqoridagi boshqaruvlar x=326–798 oralig‘ida, faol rejim satri x=22–798 oralig‘ida joylashdi; joriy faol rejim ko‘rindi.

Integratsiya shabloni qo‘shilgach 12 ta mavjud regressiya to‘plami qayta bajarildi va barchasi o‘tdi. Har bir skript ilovani yuklashdan oldin o‘z vaqtinchalik bazasini o‘rnatadi; haqiqiy panel bazasida jarayonlar bajarilmadi.

Loglar: `verification-20260914/integration-152930/`.

| To‘plam | Natija va qamrov |
| --- | --- |
| `verify_auth.py` | O‘tdi: kirish, CSRF, MFA demo, sessiya, bloklash, chiqish |
| `verify_integration.py` | O‘tdi: 45 sahifa/API, til, audit, scoped jonli oqim, shablon va sintaksis |
| `verify_navigation_filters.py` | O‘tdi: 18 haqiqiy tafsilot havolasi, formalar, filtrlash, sahifalash, HTMX, signal qaytish manzili |
| `verify_yacheykalar.py` | O‘tdi: katak holatlari, ruxsatlar, inventarizatsiya, signallar, rejimlar |
| `verify_settings.py` | O‘tdi: sozlamalar, so‘rov/tasdiq/rad, sessiya bekor qilish, tekshiruvlar |
| `verify_smena.py` | O‘tdi: ochish/yopish, nazorat ro‘yxati, tarix/hisobot, takroriy amallar |
| `verify_reports.py` | O‘tdi: filtrlar, CSV/XLSX/PDF, audit, hajm/hash/muddat va vakolatlar |
| `verify_export_renderers.py` | O‘tdi: Unicode, identifikatorlar, Excel turlari va xavfsiz CSV |
| `verify_inventory_consistency.py` | O‘tdi: noyob jihoz hisobi, tarixiy ziddiyatlar, 19 dastlabki jadval saqlanishi |
| `verify_restrictions.py` | O‘tdi: cheklovlar, ruxsatlar, qurilma xizmat holatlari, oldingi audit saqlanishi |
| `verify_jurnal.py` | O‘tdi: jurnal/eksport, yaxlitlik, vakolatlar, 80 lotin/kirill smena sahifasi |
| `verify_backups.py` | O‘tdi: SQLite nusxa va alohida faylga tiklash, hash/yaxlitlik, manba o‘zgarmasligi |

Signal hudud filtri xarita bilan bir manbaga moslangach, `verify_integration.py`, `verify_navigation_filters.py` va `verify_yacheykalar.py` qayta bajarildi — uchalasi ham o‘tdi. Yakuniy natijalar `_after_signal_fix.log` bilan saqlangan.

Yangi ikkita to‘plam ham o‘tdi; jami 14 ta alohida tekshiruv to‘plami:

- `verify_leadership_data.py`: joriy va oldingi davr hisobi, CRITICAL+SECURITY birlashtirilishi, INFO farqi, nul/0, eng eski sinxronlash, yo‘q/eskirgan ma’lumot, markaziy/hudud/bo‘linma/qurolxona vakolati. Null yoki noto‘g‘ri tarixiy signal hududi bo‘lganda ham xarita hisobi haqiqiy tegishli qurolxona hududiga asoslanib, signal ro‘yxati, jonli qismi va tarix havolalariga mosligi tekshirildi. Anonim API rad etiladi, javoblar keshlanmaydi, kirill nomlari ishlaydi.
- `verify_leadership_links.py`: yangi bloklardan chiqqan 53 ta haqiqiy havola to‘rtta vakolat darajasida ochildi; hudud havolalari va ichki ma’lumot doirasi mos. Begona hudud rad etildi; barcha mahalliy CSS/JS aktivlari 200 javob berdi; HTMX `innerHTML` almashtirish sharti va kirill shabloni tekshirildi. Faqat markazga biriktirilgan jiddiy signal mavjud bo‘lsa ham yolg‘on “jiddiy signal yo‘q” xulosasi chiqmasligi tekshirildi. Yakuniy log: `verify_leadership_links_final.log`.

### Yangi xarita brauzer tekshiruvi

Asosiy agent haqiqiy 8080 panelida quyidagilarni tasdiqladi:

- Toshkent shahri (`UZ-TK`) tanlandi: 3 jiddiy signal, 0 ogohlantirish, 3 qurolxona, 100 qurol, 3 onlayn va 0 oflayn obyekt. Bazadagi 10-sentyabr xabari eskirgan sifatida ko‘rsatildi.
- Signal tafsiloti havolasi `/signallar?hudud=1` manzilini ochdi va aynan 3 signal kartasi chiqdi. 9-raqamli signal tafsiloti ochildi; administrator uchun ko‘rish huquqi saqlangan, signal holatini o‘zgartirish bajarilmadi.
- Toshkent tanlovi, yaqinlashtirish, “Muammoli hududlar” filtri va xarita `viewBox` qiymati haqiqiy HTMX yangilanishidan keyin saqlandi. `15:36:24 → 15:37:54 (UTC+5)` yangilanishi kuzatildi; `.main.scrollTop` 181 qiymatida qoldi.
- Tungi rejimda jiddiy holat hududining to‘ldirish rangi legendadagi jiddiy rang bilan aynan bir xil.
- 1280×720 ish stoli o‘lchamida xarita va tafsilotlar KPI kartalaridan oldin joylashdi. Muhim signal hamda aloqa sonlari birinchi ekranda ko‘rinadi.
- Ildiz hujjatning keraksiz aylanishi tuzatildi: hujjat balandligi va scroll balandligi 720/720 px, `scrollY=0`; asosiy maydonning ichki va scroll kengligi 1096/1096 px. Aylanish asosiy kontent ichida qoladi.

- Navoiy viloyati SVG yozuvi klaviaturadagi Enter bilan tanlandi. Yaqinlashtirish va muammoli hududlar filtri yoqildi; “Umumiy holat” ikkalasini o‘chirib, respublika tanlovi va boshlang‘ich `viewBox=-28 -36 944 600` qiymatini qaytardi.
- Farg‘ona tezkor havolasi to‘g‘ri hududni tanladi: 0 jiddiy signal, 1 ogohlantirish, 2 qurolxona, 66 qurol. To‘rtta kichik hudud tezkor havolasi ham 44 px balandlikda.
- Kunduzgi rejim sahifa qayta yuklangandan keyin saqlandi. Jiddiy hudud to‘ldirish rangi `rgb(223, 161, 163)` bo‘lib, legendadagi rang bilan aynan mos.
- 390×844 mobil xarita sahifasi tasvir va DOM orqali tekshirildi: ustuvor xulosa y=288, tafsilotlar y=617, xarita y=1188 va KPI y=1908. Muhim xulosa birinchi ekranda, tafsilotlar xaritadan oldin. Hujjat kengligi 390/390 px va balandligi 844 px; asosiy kontent kengligi 380/380 px. Har bir mobil tegish amali alohida qayta bajarilmadi; mobil joylashuv tekshirildi.
- Kirillga o‘tkazilganda yangi “Муҳим сигналлар” va “Биринчи навбатда” yozuvlari to‘g‘ri chiqdi. Tekshiruv oxirida lotin yozuvi, kunduzgi rejim va odatiy oyna o‘lchami tiklandi.
- Konsolda integratsiya jarayonining oldingi 10:25 vaqtidagi xatosi saqlangan edi; qayta ishga tushirilgan joriy server loglari toza, yangi xato kuzatilmadi va muvaffaqiyatli yangilanish ko‘rildi. Yakuniy ko‘rinish tiklangach server `out.log` yozuvlarida barcha jonli qismlar, jumladan `/partials/executive`, 200 javob qaytargani tasdiqlandi.

Yuqoridagi brauzer tekshiruvlari menyu, xarita va vakolatga mos tafsilot oqimlarini tasdiqlaydi. Har bir tugmaning barcha kombinatsiyasi qo‘lda bosilgani yoki haqiqiy apparat ulanishlari tekshirilgani da’vo qilinmaydi. Biznes jarayonlari alohida sinov bazalarida regressiya to‘plamlari bilan tekshirildi; ular haqiqiy apparatlarga buyruq yubormaydi.

Oldingi holat bo‘yicha 12 ta regressiya to‘plami o‘tgan; ular yangi dizayn integratsiyasining yakuniy tekshiruvi o‘rnini bosmaydi. Oldingi loglar: `verification-20260914/status-150412/`.

## Tashqi tizimlar chegarasi

Bu ish mavjud demo admin jarayonlarini tanlangan dizayn bilan bog‘laydi. Haqiqiy kamera, kontroller, HR, biometrika, ishlab chiqarish MFA va avtomatik NAS zaxiralash ulanishlari ushbu vizual integratsiya natijasida paydo bo‘lmaydi.

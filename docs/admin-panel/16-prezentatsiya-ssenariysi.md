# Prezentatsiya ssenariysi (10–12 daqiqa)

Sana: 2026-09-14. Maqsad: "Nazorat markazi" demo panelini rahbariyat yoki buyurtmachiga ko'rsatish. Bu konsept-namoyish: ma'lumotlar sintetik, apparat o'rnida simulyator ishlaydi. TZ bo'yicha qabul sinovi emas.

## Tayyorgarlik (namoyishdan 10 daqiqa oldin)

1. Kompyuter: Windows, Python 3.11, `admin-panel` papkasida bog'liqliklar o'rnatilgan (`python -m pip install -r requirements.txt`). Internet shart emas.
2. Brauzer: Chrome yoki Edge, oyna kengligi kamida 1280 px (xarita va tafsilot yonma-yon turadi). 3D xarita WebGL talab qiladi; ishlamasa xarita ustidagi "Tekis" tugmasi bilan SVG xaritaga o'tiladi.
3. Bazani yangilash va serverni ishga tushirish (PowerShell, `admin-panel` papkasida, server to'xtatilgan holda):

```powershell
python -B -X utf8 scripts\demo_reset.py
python -B -X utf8 run.py
```

4. Brauzerda http://127.0.0.1:8080 → `admin` / `demo` → MFA `123456`.
5. Simulyator (chap menyu, eng pastda) → "Avto-rejim" (interval 4 s). Bu obyektlarni "tirik" qiladi: hodisalar oqadi, xarita eskirmaydi.
6. Ikkinchi brauzer oynasida (yoki maxfiy oynada) `navbatchi` / `demo` / `123456` bilan kirib qo'ying: smena va rejim qadamlari uchun.
7. Til: yuqori o'ngdagi "Ўзб" tugmasi kirillga o'tkazadi; kerak bo'lsa oldindan tanlang.

Namoyish davomida hech qanday tugma jismoniy qulfni ochmaydi; buni auditoriyaga aytish foydali.

## Bosish yo'li

| # | Vaqt | Ekran | Nima ko'rsatiladi | Gap mazmuni |
|---|---|---|---|---|
| 1 | 0:00–1:30 | Bosh sahifa `/` (admin) | 3D relyef xarita: hudud ranglari (barqaror, ogohlantirish, jiddiy), belgi raqamlari; hududni bosish → o'ngdagi tafsilot o'zgaradi; "Tanlangan hudud" → kamera yaqinlashadi; "Yuqoridan / Qiya" ko'rinishlar; "Umumiy holat" qaytaradi | Respublika bo'yicha bir qarashda holat: qaysi hududda jiddiy signal, aloqa, obyekt va qurollar soni. Xarita bazadagi yozuvlardan hisoblanadi, 30 soniyada yangilanadi |
| 2 | 1:30–2:30 | Pastga aylantirish | "Birinchi navbatda" xulosasi, 4 KPI, hududlar tasmasi, batafsil KPI, hududlar jadvali, 7 kunlik grafik, signal lentasi | Rahbar uchun ustuvor uchta narsa; pastda operativ tafsilot |
| 3 | 2:30–3:30 | Toshkent sh. → `/hudud/1` | Hudud KPI, bo'linmalar jadvali, "Yunusobod tumani IIB" qatori | Drill-down: respublika → hudud → bo'linma → qurolxona |
| 4 | 3:30–4:30 | Yunusobod qurolxonasi `/qurolxona/1` | Kataklar rejasi (A va B devor, holat ranglari), qurilmalar holati, joriy smena, so'nggi hodisalar; yuqorida faol TREVOGA banneri | Obyekt darajasi: TZ dagi operator konsoli |
| 5 | 4:30–5:30 | Katak `Y-001` → `/yacheyka/1` | 2D raqamli egizak: 5 zona (AK-74, o'q-dori, PM, dubulg'a, texnik), har uyada jihoz holati va qulf; terminal ko'zgusi; telemetriya; biriktirilgan xodim; hodisalar | Har katak = bitta xodim; datchiklar va qulflar holati alohida ko'rinadi |
| 6 | 5:30–7:00 | Simulyator `/simulyator` (Yunusobod) | Y-002 uchun "AK olish" → so'ng "Kirish rad etildi"; boshqa katakda "Buzishga urinish (tamper)"; qurolxona uchun "Qurolxona oflayn" → "Aloqa tiklandi" | Apparat o'rnida hodisalarni chaqiramiz; har hodisa jurnalga hash zanjiri bilan yoziladi, ekranda ovozli va vizual signal chiqadi |
| 7 | 7:00–8:00 | Signal markazi `/signallar` | To'rt daraja (INFO/WARNING/CRITICAL/SECURITY), "tasdiq talab qiladi" kartochkalari, kamera kadri (simulyatsiya), tasdiqlash va yechish (sabab bilan) | TZ 6.4: rang, ovoz, tasdiq talab qiluvchi karta; qorovul postiga yo'naltirish belgisi |
| 8 | 8:00–8:45 | Jurnal `/jurnal` → "Yaxlitlikni tekshirish" `/jurnal/yaxlitlik` | Append-only jurnal, filtrlar; yaxlitlik natijasi: yangi bazada barcha yozuvlar mos | TZ 9: hash zanjiri, administrator jurnalni o'chira olmaydi |
| 9 | 8:45–9:45 | Hisobotlar `/hisobotlar` → "Berish-qaytarish jurnali" → Eksport (maqsad: "Namoyish", PDF) → Eksportlar jurnali | Raqam, kim, maqsad, muddat, SHA-256 | TZ 6.5 va 12: har eksport hisobga olinadi, muddati o'tgan fayl yuklanmaydi |
| 10 | 9:45–10:30 | Qurilmalar `/qurilmalar` → Zaxira nusxalash `/qurilmalar/zaxira` → "Kunlik nusxa olish" → "Tiklash sinovi" | Haqiqiy SQLite nusxa, manifest, alohida faylga tiklash va tekshiruv | TZ 10: zaxira va tiklash amalda; NAS va jadval keyingi bosqich |
| 11 | 10:30–11:30 | Ikkinchi oyna, `navbatchi`: `/qurolxona/1/smena/yopish` → qaytarilmaganlar va ochiq signallar → tasdiq bilan yopish; `/rejimlar` → faol trevoga → tugatish | Smena yopish vizardi, rejim jurnali (kim boshladi, ikkinchi tasdiqlovchi) | TZ 7.4 va 6.6: smena va yig'in/trevoga rejimi |
| 12 | 11:30–12:00 | Sozlamalar `/sozlamalar` (admin) | Foydalanuvchilar, kirish siyosati, chegaralar, saqlash muddatlari, integratsiyalar holati ("ulanmagan"), sozlamalar auditi; yangi foydalanuvchi so'rovi → `admin2` tasdiqlaydi (vaqt bo'lsa) | Ikki administrator nazorati; nima real, nima keyingi bosqich |

Vaqt yetmasa 9 va 12-qadamlarni qisqartiring; 1, 4, 5, 6, 7 asosiy.

## Savollarga tayyor javoblar

- **Bu real qurilmalar bilan ishlayaptimi?** Yo'q. Bu dasturiy prototip: shkaf kontrolleri, terminal va kamera o'rnida simulyator ishlaydi; ma'lumotlar sintetik. Keyingi bosqichda real stend ulanadi.
- **Panel qulf ochadimi?** Yo'q, hech qachon. Ochish faqat terminalda identifikatsiya bilan; panel kuzatadi, tasdiqlaydi va hisobga oladi.
- **MFA haqiqiymi?** Namoyishda doimiy kod; real provayder keyingi bosqichda.
- **Jurnalni o'zgartirib bo'ladimi?** Yo'q: har yozuv oldingisining hashini o'z ichiga oladi, "Yaxlitlikni tekshirish" buzilishni topadi.
- **Nechta obyekt ko'tara oladi?** Demo bazada 18 qurolxona va 321 katak; seed 5 500 katakgacha sintetik flot yaratadi. Yuklama sinovi hali o'tkazilmagan.
- **Nima qoldi?** TZ bo'yicha farqlar 13-hujjatda; real foydalanishga o'tish rejasi 09-hujjatda.

## Xavf va zaxira yo'l

- Xarita yuklanmasa: "Tekis" tugmasi yoki hududlar tasmasi orqali davom eting.
- Sessiya 60 daqiqadan keyin tugaydi: uzoq tanaffusdan so'ng qayta kiring.
- Avto-rejim o'chiq qolsa, 15 daqiqadan keyin hududlar "Eskirgan" bo'lib ko'rinadi: Simulyatorda yoqing, keyingi yangilanishda tuzaladi.
- Kirill rejimida Sozlamalar ro'yxatidagi foydalanuvchi ismlari va xodim kartasi sarlavhasi lotinda qoladi (ma'lum kamchilik, 14-hujjat).
- Planshet yoki telefonda Signal markazi KPI nomlari kesiladi (ma'lum kamchilik); namoyishni ish stolida o'tkazing.

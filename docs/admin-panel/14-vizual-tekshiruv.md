# Vizual ko'rinish tekshiruvi

Sana: 2026-09-14. Server: `python -m uvicorn app.main:app --port 8080` (launch.json "admin-panel"), hisob `admin`. Brauzer: ilova ichidagi Chromium, 1116 px ish stoli, 768 px planshet, 375 px mobil.

Usul: 33 sahifa ochildi; har birida JavaScript orqali avtomatik tekshirildi — gorizontal chiqish (`document.scrollWidth`, `.main` scrollWidth, konteynerdan tashqariga chiqqan elementlar), buzilgan rasmlar (`naturalWidth=0`), shablon qoldiqlari (`{{`, `None`, `undefined`, `NaN`), konsol xatolari; skrinshotlar ko'zdan kechirildi. Tungi rejim 4 sahifada, kirill yozuvi 5 sahifada, mobil 6 sahifada, planshet 1 sahifada.

## Natija

Maket tuzilmasi buzilmagan: 33 sahifaning birortasida ham sahifa darajasida gorizontal chiqish, buzilgan rasm, shablon qoldig'i yoki konsol xatosi yo'q (server o'chib turgan paytdagi ulanish xatolari hisobga olinmadi). Keng jadvallar o'z kartochkasi ichida suriladi. Tungi rejimda xarita ranglari legenda bilan aynan mos (jiddiy `rgb(146,86,94)`, ogohlantirish `rgb(128,107,67)`, barqaror `rgb(64,94,114)`), yozuvlar och rangda. Kirill rejimida bosh sahifa, kataklar, signallar sahifalarida lotincha qoldiq 0.

## Topilgan kamchiliklar

| № | Kamchilik | Qayerda | Dalil |
|---|---|---|---|
| 1 | Xato sahifalari xom JSON ko'rinishida: `{"detail":"Not Found"}`, `{"detail":"Xodim topilmadi"}`, 403 `{"detail":"Rejimni boshqarish faqat navbatchi/operator roli uchun"}`. Faqat kataklar bo'limida bezatilgan "topilmadi" sahifasi bor. | `/bunday-sahifa-yoq`, `/xodim/99999`, `/rejimlar/boshlash` (admin) | `app/main.py` da `exception_handler` yo'q; `yacheykalar/xato.html` faqat `app/routers/yacheykalar.py:81` da |
| 2 | Signal markazi KPI kartochkalari 375 va 768 px da 4 ustunda qoladi, nomlari kesiladi: SECUI, CRITI, WARI, TASD, QORO, BUGU. | `/signallar` mobil va planshet | `app/static/css/sections/signallar.css:117` — `.sig-levels` uchun 1500 px dan past faqat `repeat(4, …)`, tor ekran uchun qoida yo'q |
| 3 | Kirill rejimida uch joyda lotin qoladi: xodim kartasi sarlavhasi (brauzer sarlavhasi kirillda, h1 lotinda), Sozlamalar foydalanuvchilar ro'yxatidagi F.I.Sh., Signal markazi izohidagi daraja nomlari (AXBOROT · OGOHLANTIRISH · SIGNAL · XAVFSIZLIK — 7+ harfli katta harfli so'zlar transliteratsiya qilinmaydi). | `/xodim/1`, `/sozlamalar`, `/signallar` | `xodimlar/detail.html:7` (`off.full_name` t() siz), `sozlamalar/index.html:13-17`, `signallar/list.html:6`, `app/i18n.py` katta harf qoidasi |
| 4 | Kirish sahifasida `/favicon.ico` 404 (link `iiv-gerb.jpg` ga berilgan, lekin brauzer standart favicon ham so'raydi). Ko'rinishga ta'sir qilmaydi, faqat log. | `/kirish` | server log |
| 5 | Sintetik F.I.Sh. jinsi mos kelmaydi: "Jo'rayev Zilola Shavkatovich", "Yusupov Dilnoza Kamolovich" — ayol ismi + erkak familiya/otasining ismi. | Xodimlar ro'yxati va kartasi | `app/seed.py:30-48` (FIRST ro'yxatida ayol ismlari, PATRO faqat erkak) |

## Demo ma'lumot taassuroti (maket xatosi emas, lekin ko'rinishga ta'sir qiladi)

- Har sahifa tepasida TREVOGA banneri: rejim 10.09.2026 dan beri faol (97 soat).
- Bosh sahifada 14 hududning hammasi "Eskirgan" (oxirgi sinxronlash 10.09), chunki simulyator avto rejimda ishlamaydi.
- Jurnal › Yaxlitlik sahifasi "Yaxlitlik buzilishi aniqlandi — 7 nomuvofiq yozuv" ko'rsatadi (eski seed xatosi, README da hujjatlashtirilgan). Namoyish uchun yangi bazani seed qilish tavsiya etiladi.
- Zaxira sahifasida kunlik/haftalik kartalar "—" bilan bo'sh (haqiqiy nusxa hali olinmagan).

## Yangilanish (2026-09-14, kechqurun)

- 1-kamchilik tuzatildi: `app/main.py` da umumiy xato ishlovchilari qo'shildi. Brauzer so'rovlari (`Accept: text/html`) uchun 401/403/404/405/409/410/422/500 kodlari `xato.html` (kirgan foydalanuvchi, panel qobig'i bilan, rol va vakolat ko'rsatiladi) yoki `auth/xato.html` (kirmagan) sahifasida chiqadi; API (`/api/*`), HTMX (`HX-Request`) va testlar uchun avvalgi JSON javob va sarlavhalar (`HX-Redirect`, 303 `Location`) saqlangan.
- Namoyish ma'lumotlari: `scripts/demo_reset.py` joriy bazani `data/arxiv/` ga arxivlab yangi seed qiladi; simulyator avto-rejimi endi har intervalda onlayn obyektlarning `last_sync` / `last_seen` vaqtini yangilaydi (`services/sim.py::heartbeat`), shu sabab xarita 15 daqiqadan keyin "Eskirgan" holatga tushmaydi.
- 2, 3, 5-kamchiliklar hali ochiq.

## Tavsiya

1-kamchilik uchun `app/main.py` ga `HTTPException` va 404 uchun umumiy HTML handler (base.html asosida, kirill/lotin bilan) qo'shish; 2 uchun `signallar.css` ga 900 px dan past 2 ustun, 480 px dan past 1 ustun qoidasi; 3 uchun uchta shablonda `t()` va `i18n.py` da katta harfli so'zlar uchun istisno; 5 uchun seed da ism-familiya-otasining ismini jins bo'yicha juftlash.

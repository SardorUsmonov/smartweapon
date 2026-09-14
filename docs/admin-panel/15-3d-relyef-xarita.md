# Bosh sahifa: xarita birinchi, 3D relyef va hajmli dizayn tili

Sana: 2026-09-14. Foydalanuvchi topshirig'i: panelga kirganda birinchi bo'lib O'zbekiston xaritasi bilan "Hududlar holati" tursin; panel iloji boricha 3D ko'rinishga o'tkazilsin va chiroyli vizual dizayn bo'lsin.

## Nima o'zgardi

**Bosh sahifa tartibi** (`app/templates/partials/executive.html`): sarlavha → xarita + hudud tafsiloti (birinchi ekran) → "Hisob yangilandi" → "Birinchi navbatda" → 4 KPI → hududlar tasmasi → pastdagi batafsil bloklar. Mobil va past ekranlarda ham shu tartib.

**3D relyef xarita** (`app/static/js/leadership-map-3d.js`, three.js r180 `app/static/vendor/three/`, CDN ishlatilmaydi):
- 14 hudud `uz_regions.json` geometriyasidan bir xil balandlikda ekstruziya qilinadi (balandlik faqat ko'rinish uchun, ma'lumot emas); yorug'lik, soya, qiya kamera, aylantirish (surish), "Qiya / Yuqoridan" ko'rinish, +/− masshtab, boshlang'ich holat.
- Ranglar `leadership-map.css` dagi `--lm-map-*` tokenlaridan o'qiladi, shu sabab kunduzgi/tungi rejimda legenda bilan bir xil.
- Yorliqlar HTML (nom + signal soni), to'qnashuvsiz joylashtiriladi; tor sahnada (< 560 px) faqat signalli, tanlangan yoki kursor ostidagi hudud yorlig'i ko'rsatiladi, qolganlari hududlar tasmasida.
- Hudud ustiga kelganda ko'tariladi va tooltip chiqadi; bosilganda (canvas, yorliq, Enter) hudud tanlanadi.
- **SVG xarita (`leadership-map.js`) ma'lumot, havola, tanlov, filtr va masshtab manbai bo'lib qoladi**; 3D qatlam uning `is-selected`, `is-zoomed`, `is-muted` sinflarini MutationObserver orqali ko'zgu qiladi. Shu sabab `verify_leadership_links.py` va `verify_leadership_data.py` shartlari o'zgarmadi.
- 30 soniyalik HTMX yangilanishida bitta renderer saqlanadi, kamera holati yo'qolmaydi (tekshirildi: 1 canvas, 14 yorliq, tanlov saqlanadi).
- "Hajmli / Tekis" tugmasi (`localStorage` kaliti `aq-map-view`); WebGL bo'lmasa yoki modul yuklanmasa avvalgi SVG xarita ishlaydi, tugma yashiriladi.

**Hajmli dizayn tili** (`app/static/css/sections/relief.css`, barcha sahifalarda `base.html` va `auth/base.html` orqali): bitta "plastina" ierarxiyasi — asosiy yuzalar (kartochkalar, KPI, xarita paneli, tafsilot, kirish kartasi) ko'rinadigan yon qirra va yumshoq soya bilan; jadval va ro'yxatlar tekis o'qish tekisligida; faqat bosiladigan elementlar (KPI havolalari, tugmalar) hoverda ko'tariladi yoki bosilganda pastga tushadi; `prefers-reduced-motion` hurmat qilinadi; mobil ekranda soyalar kamaytiriladi.

**Boshqa**: 1000–1199 px kenglikda tafsilot paneli xarita yonida qoladi (hududni bosganda sahifa pastga sirpanmaydi); `leadership-map.css` ga 3D sahna uslublari qo'shildi.

## Fayllar

| Fayl | Holat |
|---|---|
| `app/static/js/leadership-map-3d.js` | yangi |
| `app/static/css/sections/relief.css` | yangi |
| `app/static/css/sections/leadership-map.css` | 3D sahna va hero tartibi qo'shildi |
| `app/templates/partials/executive.html` | bloklar tartibi, ko'rinish tugmasi, yangi satrlar |
| `app/templates/base.html` | `relief.css`, importmap, modul skripti |
| `app/templates/auth/base.html` | `relief.css` |

Oldingi nusxalar: `admin-panel/.backups/3d-hero-20260914/`.

## Tekshirildi

- 1400×900: xarita chapda, tafsilot o'ngda; hover tooltip; canvasdan, yorliqdan va Enter orqali tanlash; "Tanlangan hudud" kamerani hududga olib boradi; "Umumiy holat" qaytaradi; "Yuqoridan" ko'rinish shimol yuqorida; tungi rejimda ranglar legenda bilan mos.
- 375×812: gorizontal chiqish yo'q, sahna 340 px, 6 ta signalli yorliq ko'rsatiladi, tartib xarita → tafsilot → xulosa → KPI.
- Tekis/Hajmli almashinuvi (canvas olib tashlanadi, SVG ko'rinadi va aksincha), 30 soniyalik yangilanishdan keyin bitta canvas.
- Konsolda xato yo'q. Testlar: `verify_leadership_links`, `verify_leadership_data`, `verify_integration`, `verify_navigation_filters`, `verify_auth` o'tdi; to'liq to'plam yakunda qayta ishga tushirildi.

## Cheklovlar

- Sichqoncha g'ildiragi xaritani kattalashtirmaydi (sahifa aylanishi buzilmasligi uchun); masshtab tugmalar orqali.
- Balandlik ma'lumotni anglatmaydi; hududlar orasidagi farq faqat rang va belgi raqami.
- 3D faqat bosh sahifada; boshqa sahifalar hajmli uslubni CSS orqali oladi.

# Vaziyat markazi ko‘rinishi

Tanlangan vizual yo‘nalish: [AkademiaDev — vaziyat markazi](https://akademiadev.ru/cases/vizualizaciya-dannyh-v-situacionnom-centre-ministerstva-transporta/).

Ko‘rinish asosiy FastAPI/Jinja/HTMX paneliga (`http://127.0.0.1:8080/`) joriy qilindi. `8091` dagi avvalgi alohida prototip asosiy ilova emas.

- Standart oq fon, oltin urg‘ular, sokin navigatsiya va jadvallar; tungi rejimda qora-ko‘kimtir fon.
- Respublika sahifasining asosiy qismida O‘zbekistonga markazlangan Yandex Maps vidjeti; hududlar holati va tafsilotlarga o‘tish xarita ostidagi tanlov orqali beriladi. Amaldagi xarita tafsilotlari oxirgi bo‘limda.
- Rahbariyat uchun to‘rtta umumiy ko‘rsatkich va ustuvor faol signallar.
- Quyi qismda mavjud batafsil KPI, hududlar jadvali, operatsiyalar grafigi va signal lentasi.
- Kichik ekranda umumiy sonlar xaritadan keyin, ogohlantirishlar keyingi qatorda joylashadi.

`/partials/executive` mavjud vakolat doirasida bazadan hisoblaydi va 30 soniyada yangilanadi. Oxirgi sinxronlash vaqti `Armory.last_sync` dan olinadi. Namoyish rejimi alohida ko‘rsatiladi. Asosiy operatsiyalar, ruxsatlar va ma’lumotlar bazasi tuzilishi o‘zgartirilmagan.

Umumiy uslublar: `app/static/css/sections/situation.css`; bosh sahifa: `sections/executive.css`; kontent: `templates/partials/executive.html`; agregatlar: `services/executive.py`. Amaldagi Yandex vidjeti `sections/yandex-map.css` va `js/situation-yandex.js` bilan ulanadi. Avvalgi OSM, 3D va SVG xarita fayllari tarix sifatida saqlangan; Yandex bosh sahifasida yuklanmaydi.

Oldingi fayllarning nusxalari loyiha ildizidagi `.backups/admin-panel-situation-20260912`, `.backups/situation-data-20260912`, `.backups/situation-map-original` papkalarida saqlangan.

Quyidagi dastlabki tekshiruvlar va eski xarita bo‘limlari o‘sha paytdagi variantlar tarixini qayd qiladi; ular Yandex vidjetining tekshiruvi hisoblanmaydi.

Tekshiruvlar: `verify_auth.py` va `verify_navigation_filters.py` alohida sinov bazalarida o‘tdi. Respublika hamda hudud vakolatlari bilan yangi HTML/HTMX qismlari, bazaga mos sonlar, signal havolalari va kirill yozuvi tekshirildi. Brauzerda 1440 px, 390 px va odatiy oyna o‘lchamida ko‘rinish tekshirildi; asosiy sahifa va hududlar sahifasida tashqi gorizontal siljish yo‘q.

Xarita sichqoncha hamda Enter orqali hudud sahifasini ochadi. Surish havolani tasodifan ochmaydi. Yaqinlashtirish va surish holati 30 soniyalik HTMX yangilanishidan keyin saqlanishi brauzerda tasdiqlandi. Asosiy JS va umumiy uslublarda yangi versiya kaliti bor, shu sabab eski brauzer keshi yangilanishni to‘sib qolmaydi.

## Kunduzgi va tungi rejim — 14.09.2026

Yuqori panel va kirish sahifasidagi oy/quyosh tugmasi sahifani qayta yuklamasdan rejimni almashtiradi. Birinchi ochilish oq rejimda. Tanlov brauzerning shu manziliga tegishli `localStorage` ichida `aq-theme` kaliti bilan saqlanadi; sahifalararo o‘tish va yangilashdan keyin tiklanadi. Xotiraga yozish cheklangan bo‘lsa, tugma joriy sahifada ishlashda davom etadi.

Umumiy `theme.css` rang tokenlari, xarita gradientlari va yozuvlari, jadvallar, kartochkalar hamda ogohlantirishlarni ikki rejimga moslaydi. `theme.js` CSS yuklanishidan oldin saqlangan tanlovni qo‘llaydi. Ikkala asosiy shablon `partials/theme_toggle.html` dan foydalanadi; tugmaning tushuntirishlari lotin va kirill yozuvida chiqadi.

Tekshirildi: JS sintaksisi, oq/tungi ko‘rinish, yangilash va sahifalararo o‘tishda tanlov saqlanishi, Enter orqali almashtirish, 390 px va 1440 px ekranlar, hududlar kartochkalari, kirish sahifasi va kirill yozuvi. Asosiy panel yakunda oq rejimda qoldirildi.

## Asosiy qismlarning 3D ko‘rinishi — 14.09.2026 (xaritaning avvalgi varianti)

`situation-3d.js` mavjud hudud geometriyasidan bir xil balandlikdagi hajmli model yaratadi. Balandlik faqat dizayn elementi; statistik qiymatni anglatmaydi. Hudud holati rangli belgida, ko‘rsatkichlar esa hudud nomi ustiga kelganda ko‘rsatiladi. Hudud modeli yoki nomi ustiga bosish tegishli sahifani ochadi. Boshqaruvlar: surib aylantirish, `+` / `−` orqali yaqinlashtirish, yuqoridan ko‘rish va boshlang‘ich holatga qaytarish.

Three.js r180 va uning MIT litsenziyasi `app/static/vendor/three/` ichida saqlanadi. Xarita tashqi CDN ishlatmaydi. WebGL yuklanmasa, mavjud SVG xarita ishlashda davom etadi. Nomlar va havolalar har bir yangilanishda server yaratgan SVG dan olinadi, shuning uchun foydalanuvchi vakolatlari saqlanadi.

Xarita doimiy animatsiya siklisiz, faqat o‘zgarish bo‘lganda chiziladi. Bitta renderer jonli HTMX yangilanishlari davomida saqlanadi. `depth.css` asosiy to‘rtta KPI va muhim ogohlantirishlar paneliga yoritilgan qirra, hajm va soya beradi. Harakatni kamaytirish sozlamasida kartochka animatsiyasi o‘chiriladi. Oq/tungi rejimlar saqlangan.

Brauzer tekshiruvlari: 390 px ekranda 14 ta nom bir-birini to‘smaydi; 1440 px va odatiy oynada ko‘rinish tekshirildi. Hudud modelini bosish va nomida Enter ishlatish to‘g‘ri sahifani ochdi; surish tasodifiy navigatsiya qilmadi. 14 ta 3D havola va tavsif server SVG si bilan aynan mos. 35 soniya kutib jonli yangilanishdan so‘ng yuqoridan ko‘rish holati saqlandi, canvas soni 1 ta bo‘ldi, zaxira SVG ko‘rinmadi. HTMX atributlarni tiklash bosqichidan keyin `is-3d` sinfi qayta qo‘llanadi. JS sintaksisi tekshirildi, brauzerda xato va ogohlantirishlar qayd etilmadi.

## OpenStreetMap xaritasi — 14.09.2026 (avvalgi variant)

Foydalanuvchi tanlagan OpenStreetMap xaritasi bosh sahifadagi 3D xaritaning o‘rniga qo‘yildi. O‘zbekiston Respublikasi chegarasi oltin chiziq bilan ajratiladi. Boshlang‘ich ko‘rinish mamlakat chegarasiga moslanadi. `+` / `−`, surish, klaviatura boshqaruvi va “O‘zbekiston” tugmasi bor.

`situation-osm.js`, `sections/osm-map.css` va mahalliy Leaflet 1.9.4 ishlatiladi. Geografiya manbalari hamda litsenziya `app/static/data/OSM-SOURCES.md` da qayd qilingan. 14 belgi hudud bo‘yicha umumiy holatni bildiradi, obyektlarning aniq joylashuvini emas. Havolalar va ko‘rsatkichlar serverning amaldagi vakolat doirasidan olinadi.

HTMX yangilanishida bitta xarita konteyneri qayta ulanadi va surish/yaqinlashtirish holati saqlanadi. Internet bo‘lmaganda mahalliy chegara qoladi va yuklash xabari ko‘rsatiladi; Leaflet yoki geografiya yuklanmasa, avvalgi SVG sxema ishlaydi. Xarita rasmlari odatiy HTTP keshidan foydalanadi, ommaviy yuklash yoki tile proksi yo‘q. `referrerPolicy` faqat xarita rasmlarida saytning origin manzilini yuboradi; maxfiy URL yo‘llari va tokenlar yuborilmaydi.

Oq/tungi interfeys va KPI kartochkalarining hajmli ko‘rinishi saqlangan. Eski 3D modul asosiy sahifada yuklanmaydi. Shablonlarning oldingi nusxalari `.backups/osm-map-20260914` ichida.

Tekshirildi: JS sintaksisi; 14 ta takrorlanmas hudud kodi va ularning O‘zbekiston ichida joylashishi; GeoJSON halqalarining yopiqligi. Brauzerda haqiqiy OSM fon rasmlari, ajratilgan chegara, yaqinlashtirish/surish/tiklash, sichqoncha va Enter orqali Navoiy sahifasiga o‘tish tasdiqlandi. Jonli yangilanishdan keyin xarita joyi o‘zgarmadi, bitta xarita va 14 ta belgi qoldi. 390 px ekranda sahifa kengligi 390 px, xarita 350 px; tashqi gorizontal siljish yo‘q. Oq va tungi rejim tekshirilib, foydalanuvchining kirill/tungi tanlovi tiklandi. Tuzatilgan sahifada brauzer xatolari qayd etilmadi.

### Faqat O‘zbekiston va panelga mos ranglar — 14.09.2026

Keyingi so‘rov bo‘yicha atrofdagi davlatlar to‘liq yashirildi. OSM rasmlarining tilePane qatlamiga mamlakat poligoni bo‘yicha SVG clipPath qo‘llanadi; tashqi niqob panel foni bilan bir xil va to‘liq yopiq. Even-odd qoidasi ko‘p poligonlar va ichki teshiklarni saqlaydi. Proyeksiya ko‘rish joyi, masshtab, sensorli zoom va oyna o‘lchami o‘zgarganda yangilanadi; klip ham xarita bilan HTMX yangilanishlari orasida saqlanadi. Surish chegarasi O‘zbekiston atrofida, minimal masshtab mamlakat to‘liq sig‘adigan o‘lchamga mos.

Tungi rejimda xarita to‘q ko‘kimtir palitrada, oq rejimda sokin och ranglarda. Oltin chegara, holat belgilarining ranglari, tugmalar va manba yozuvi umumiy dizayn tokenlaridan olinadi. Belgilar 36 px bosish maydoniga ega, nom va ko‘rsatkichlar serverdagi lotin/kirill tarjimasidan keladi. Qo‘shimcha OSM tugmasi olib tashlandi; zarur manba havolasi xarita chetida ko‘rinadi. Oldingi fayllar `.backups/uzbekistan-only-20260914` ichida saqlangan.

Tekshirildi: oq/tungi ko‘rinish, surish/zoomda faqat mamlakat ichidagi rasmlar qolishi, avtomatik yangilanishdan keyin klip va ko‘rish joyi saqlanishi, bitta xarita va bitta clipPath mavjudligi. 14 ta belgining tavsifi tarjima qilingan server ma’lumotlariga mos. Oynani katta-kichik o‘lchamga almashtirishda yangi fit avvalgi minimal zoom bilan cheklanmaydi; 390 px ekranda 350 px xarita ichiga 277 px mamlakat to‘liq sig‘ishi tekshirildi.

### Xarita ravshanligi va hudud nomlari — 14.09.2026

Chegarada kesilgan raster yozuvlar o‘rniga OSM Shortbread vektor geometriyasi ishlatiladi. `osm-vector-layer.js` mahalliy canvaslarda yer, suv va yo‘llarni alohida chizadi. Kunduzgi och palitra va tungi ko‘kimtir palitra CSS tokenlaridan olinadi; rejim almashtirilganda mavjud geometriya qayta chiziladi. Umumiy ko‘rinishda asosiy yo‘llar ko‘rinishi uchun eng kichik manba masshtabi 6. Rasm ichidagi tayyor yozuvlar chizilmaydi.

14 hududning qisqa nomi server tarjimasidan olinib, alohida HTML belgi sifatida chiqariladi. `osm-label-layout.js` nomlarni geografik nuqtaga yaqinlashtiradi, to‘qnashuvlarni ajratadi va xarita chegarasi hamda boshqaruv tugmalaridan saqlaydi. Hududning asl nuqtasi va yozuv orasidagi ingichka chiziq joylashuvni tushuntiradi. Balandligi 30 px bo‘lgan belgilar butun nom bo‘ylab bosiladi; holat rangli nuqta va to‘liq tavsif orqali beriladi. Xarita balandligi 425 px ga oshirilgan. Faqat O‘zbekistonni ko‘rsatadigan klip, manba havolasi va mavjud vakolatlar saqlangan.

Vektor parserlar va litsenziyalar `app/static/vendor/osm-vector/` ichida. Internetdan faqat ko‘rinayotgan xarita qismi olinadi; bekor qilingan tile so‘rovlari to‘xtatiladi, muvaffaqiyatsiz yuklanish uchun qayta urinish tugmasi ishlaydi. Manbalar `app/static/data/OSM-SOURCES.md` da yangilangan. Avvalgi fayllar `.backups/map-readability-20260914/` ichida.

Tekshirildi: uchta JS faylining sintaksisi; odatiy oynada 602 × 423 va 390 px telefon ekranida 350 × 423 xarita ichida barcha 14 ta nom to‘liq ko‘rinishi, o‘zaro to‘qnashuv va chetdan chiqish yo‘qligi; oq va tungi palitralar. Joylashtirish algoritmi 135 xil kenglik, masshtab va surish kombinatsiyasida to‘qnashuvsiz sinovdan o‘tdi.

Yaqinlashtirish va surishdan keyingi HTMX yangilanishida xarita transformi, mamlakat klipi va masshtab o‘zgarmadi; bitta xarita, bitta klip va 14 belgi saqlandi. Navoiy nomini sichqoncha bilan bosish hamda Enter orqali tanlash `/hudud/13` sahifasini ochdi. Tekshiruvdan keyin asosiy sahifa odatiy oyna o‘lchamida, lotin yozuvi va tungi rejimda qoldirildi. Brauzer xatolari qayd etilmadi.

## Yandex Maps xaritasi — 14.09.2026 (amaldagi variant)

Yandex Konstruktorida O‘zbekiston chegarasi to‘q ko‘k chiziq va shaffof oltin rang bilan ajratildi. Foydalanuvchi akkauntga kirib, dastlabki saqlash tugmasini o‘zi bosdi. Saqlangan xarita admin panelga rasmiy iframe orqali API kalitisiz ulandi.

Keng va ixcham ko‘rinishlar bir xil mamlakat geometriyasidan foydalanadi. Iframe kengligi 480 px dan kichik bo‘lsa ixcham ko‘rinish ochiladi. Har ikkala manzil Konstruktordan olindi va o‘zgartirilmaydi. “O‘zbekistonni to‘liq ko‘rsatish” tugmasi joriy kenglikka mos ko‘rinishga qaytaradi. Manzillar, manba va cheklovlar `app/static/data/YANDEX-SOURCES.md` da qayd etilgan.

Chegara OSM geometriyasidan tayyorlangan KML orqali import qilindi; paneldagi obyektlar yoki operativ ma’lumotlar Yandex’ga yuborilmadi. Yandex importda uzun konturlarni soddalashtirishini bildirgan; dastlabki KML `docs/admin-panel/yandex-constructor/` papkasida saqlanadi. Panelga qo‘shilgan ortiqcha Yandex yozuvlari olib tashlangan. Vidjetning rasmiy logotipi va manba yozuvlari, shuningdek xarita ostidagi OSM chegara atributsiyasi saqlanadi.

Qo‘shni davlatlar ham ko‘rinadi, O‘zbekiston rang va kontur bilan ajratiladi. Panelning oq va tungi rejimlari saqlanadi, xaritaning o‘zi Yandex’ning och ranglarida qoladi. Joriy variant xaritada jonli hudud belgilari yoki maxsus mamlakat tashqi niqobini bermaydi.

`executive-overview` `hx-swap="none"` ishlatadi. `/partials/executive` javobidagi beshta OOB qism — `executive-heading`, `executive-region-nav`, `executive-attention`, `executive-kpis`, `executive-status` — ma’lumotlarni yangilaydi; iframe bu qismlardan tashqarida turadi. Tanlangan hudud `situation-yandex.js` orqali tiklanadi. “Tafsilotlar” server taqdim etgan `/hudud/{id}` manziliga olib boradi.

Tekshirildi: JS sintaksisi; faol brauzer tabidagi admin panelda O‘zbekistonning to‘liq konturi; oq va tungi rejimlar; 350 × 380 px alohida komponentda ixcham manzilning avtomatik tanlanishi va mamlakatning to‘liq ko‘rinishi. Shu komponentda kattalashtirish va boshlang‘ich ko‘rinishga qaytarish ishladi. Jonli yangilanishdan keyin bitta iframe, beshta OOB qismning har biri bittadan va 14 hudud saqlandi; Navoiy tanlovi saqlandi, “Tafsilotlar” `/hudud/13` sahifasini ochdi. Brauzer xatolari qayd etilmadi.

Tekshiruv vositasi to‘liq mobil viewport o‘zgarishini qo‘llamadi, shuning uchun bu safar butun sahifaning mobil sinovi o‘rniga aniq 350 px kenglikdagi xarita komponenti tekshirildi. Fon tabidagi iframe tekshiruvda bo‘sh ko‘rindi; faol foydalanuvchi tabida haqiqiy yuklanishi tasdiqlandi. Yakunda asosiy panel odatiy o‘lchamda va tungi rejimda qoldirildi. Vaqtinchalik tekshiruv sahifalari olib tashlandi.

# Yandex Konstruktor uchun O‘zbekiston chegarasi

`uzbekistan-boundary.kml` — O‘zbekiston chegarasini Yandex xaritasida ajratib ko‘rsatish uchun import fayli. Faqat ochiq mamlakat geografiyasi mavjud; paneldagi obyektlar, xodimlar yoki operativ ma’lumotlar kiritilmagan.

Manba: `admin-panel/app/static/data/uzbekistan-osm.geojson`, OSM relation 196240. © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright). Besh poligon, olti yopiq kontur va 1 493 koordinata saqlangan. Bu umumiy ko‘rinish uchun soddalashtirilgan chegara.

KML uslubi: to‘q ko‘k chegara, eni 3 px; shaffof oltin rangli ichki maydon. Konstruktor import vaqtida ranglarni o‘z palitrasiga yaqinlashtirishi mumkin. Importdan keyin ko‘rinishni tekshirish kerak.

## Ulanish tartibi

1. [Yandex Konstruktor](https://yandex.ru/map-constructor/) sahifasida Yandex ID bilan kiring.
2. Yangi xarita ochib, **Импорт** orqali `uzbekistan-boundary.kml` faylini tanlang.
3. Chegara va xarita markazini tekshirib, O‘zbekistonni to‘liq sig‘diring. Xarita tavsifidagi OSM manba yozuvini saqlang.
4. Xaritani saqlab, interaktiv xaritaning saytga qo‘yish kodini oling.
5. Tasdiqlangan konstruktor vidjetini `app/templates/partials/executive.html` ichidagi mavjud iframe o‘rniga ulang. `situation-yandex.js` dagi markaz/masshtab boshqaruvini yangi vidjet parametrlari bilan tekshiring.

14.09.2026 holati: KML import qilindi, foydalanuvchi xaritani saqladi va uning shartlarini qabul qildi. Keng ko‘rinish va “O‘zbekiston Respublikasi — ixcham ko‘rinish” nusxasi tayyorlandi; ikkalasi admin panelda ekran kengligiga qarab ulanadi. Chegara ko‘rinishi, kattalashtirish va qaytarish tekshirildi. Yandex 1 000 nuqtadan uzun obyektlarni soddalashtirishini bildirdi; dastlabki KML o‘zgarmagan holda saqlanadi. Joriy iframe manzillari `admin-panel/app/static/data/YANDEX-SOURCES.md` da yozilgan.

Rasmiy qo‘llanmalar: [Konstruktor](https://yandex.com/maps-api/docs/constructor/index.html), [KML importi](https://yandex.ru/maps-api/docs/constructor/concept/markers_5.html). Konstruktor o‘z obyektlari bilan joylashtiriladigan xaritani API kalitisiz tayyorlash yo‘lini beradi; maxsus jonli qatlamlar va dasturiy mavzu boshqaruvi esa alohida JS API integratsiyasi hisoblanadi. Rasmiy Yandex manba yozuvlari saqlanadi.

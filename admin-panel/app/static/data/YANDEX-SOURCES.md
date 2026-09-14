# Yandex Maps — bosh sahifadagi amaldagi xarita

Integratsiya: 14.09.2026. Yandex Konstruktor orqali saqlangan interaktiv xarita API kalitisiz ulanadi. O‘zbekiston to‘q ko‘k kontur va shaffof oltin rang bilan ajratilgan.

## Saqlangan xaritalar

- Keng ko‘rinish: `48305d5482e468637379b710e7eac8f0e120aac596272fb16b5f9b987d9f6bdd` — O‘zbekiston Respublikasi.
- Ixcham ko‘rinish: `735c3ac36df3895848e156bb42f7dbb4db0900caa9f04a816eee78962398b205` — O‘zbekiston Respublikasi — ixcham ko‘rinish.

Konstruktordan olingan iframe manzillari:

```text
https://yandex.ru/map-widget/v1/?um=constructor%3A48305d5482e468637379b710e7eac8f0e120aac596272fb16b5f9b987d9f6bdd&source=constructor
https://yandex.ru/map-widget/v1/?um=constructor%3A735c3ac36df3895848e156bb42f7dbb4db0900caa9f04a816eee78962398b205&source=constructor
```

Har ikkala xarita bir xil chegara geometriyasiga ega. Farqi saqlangan masshtabda: keng ko‘rinish 5, ixcham ko‘rinish 4. `situation-yandex.js` iframe kengligi 480 px dan kichik bo‘lsa ixcham manzilni tanlaydi. Vidjetning o‘z parametrlari o‘zgartirilmaydi; faqat ikki rasmiy manzil orasida almashadi. Takroriy o‘lchovda manzil bir xil bo‘lsa iframe qayta yuklanmaydi. Qaytarish tugmasi tanlangan ko‘rinishni qayta ochadi.

## Chegara manbasi

Chegara `docs/admin-panel/yandex-constructor/uzbekistan-boundary.kml` orqali import qilindi. Uning manbasi `uzbekistan-osm.geojson`, OSM relation 196240: © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright). KML 5 poligon, 6 kontur va 1 493 koordinatani saqlaydi. Yandex 1 000 nuqtadan uzun obyektlarni soddalashtirishini bildirdi; boshlang‘ich fayl o‘zgartirilmadi. Bu umumiy ko‘rinish uchun soddalashtirilgan geografiya.

Yandex’ga faqat ochiq mamlakat chegarasi va uning manba tavsifi yuklandi. Paneldagi obyektlar, xodimlar, signallar yoki hisoblar xaritaga yuborilmaydi. Hududlar holati serverdagi vakolat doirasidagi tanlov orqali ochiladi.

## Ko‘rinish va cheklovlar

- Qo‘shni davlatlar ko‘rinadi; O‘zbekiston alohida rang va kontur bilan ajratilgan.
- Panelning kunduzgi va tungi rejimlari saqlanadi. Xarita Yandex’ning tabiiy och palitrasida qoladi.
- Panel qo‘shgan ortiqcha Yandex sarlavhasi olib tashlangan. Vidjetning rasmiy logotipi va manba yozuvlari saqlanadi; chegara manbasi xarita ostida ko‘rsatilgan.
- Iframe jonli HTMX yangilanishlarida almashtirilmaydi. Beshta OOB bo‘lim ma’lumotlarni yangilaydi, hudud tanlovi saqlanadi.
- Xarita internetga bog‘liq. Yandex rasm yoki tile fayllari yuklab olinmagan; proksi va begona API kaliti ishlatilmaydi.

Rasmiy hujjatlar: [Konstruktor](https://yandex.com/maps-api/docs/constructor/index.html), [iframe kodini olish](https://yandex.com/maps-api/docs/constructor/concept/markers_2.html), [Konstruktor parametrlari](https://yandex.com/maps-api/docs/constructor/api.html), [Yandex foydalanish shartlari](https://yandex.com/dev/commercial/doc/en/).

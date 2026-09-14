# O‘zbekiston xaritasi — interaktiv maket 02

Asosiy admin paneldan alohida ko‘rinish: http://127.0.0.1:8092/.
Asosiy panel shablonlari, Yandex xaritasi, autentifikatsiya va ma’lumotlar bazasi o‘zgartirilmagan.

## Bajarilgan yetti tuzatish

1. Muhim ogohlantirishlar yuqoridagi “Birinchi navbatda” blokida. 1200 px dan tor oynalarda tafsilotlar xaritadan oldin chiqadi. Kichik hudud tugmasi bosilganda tafsilot ekrandan tashqarida bo‘lsa, ko‘rinadigan joyga olib kelinadi.
2. Respublika xulosasi jiddiy signalli hududni, oflayn obyektlarni, ma’lumotsiz hududni va qo‘shimcha ogohlantirishlarni ko‘rsatadi. Xulosadagi tugmalar tegishli tafsilotlarni ochadi.
3. Xaritada va legendada bir xil rang tokenlari ishlatiladi. Tanlov holat rangini o‘zgartirmaydi; oltin kontur va yozuv ramkasi bilan ko‘rsatiladi. Ma’lumot yo‘q bo‘lsa kulrang chiziqli naqsh qo‘llanadi.
4. SVG yozuvlari atrofida kattaroq bosish maydoni; Toshkent shahri, Namangan, Andijon, Farg‘ona uchun kamida 44 px balandlikdagi tugmalar. Tanlangan hududni kattalashtirish, masshtabni qaytarish va umumiy holatga qaytish ishlaydi. Kattalashtirilganda signal doirasi hududni berkitmaydi.
5. “Faol signallar” faqat jiddiy + ogohlantirish signallarini qo‘shadi. “Aloqa holati” onlayn/oflayn obyektlarni alohida hisoblaydi. Masalan, Toshkent shahri: 4 signal, 1 oflayn obyekt; respublika: 7 signal, 2 oflayn obyekt.
6. Namunaviy holat vaqti, hududning oxirgi xabari, eskirish chegarasi va oldingi kun bilan farq ko‘rsatiladi. Yetishmayotgan ma’lumot nolga aylantirilmaydi.
7. Menyu ikonkalari asosiy paneldagi SVG to‘plamidan olingan. Matn, legendalar va boshqaruvlar kattalashtirilgan; kunduzgi va tungi rejim moslashtirilgan.

## Ma’lumot va vaqtlar

Faol skript: app-v2.js. Raqamlar va vaqtlar ochiq namunaviy qiymatlardir, jonli API chaqiruvi yo‘q.
Holat vaqti: 14.09.2026 10:00 UTC+5; oldingi davr: 13.09.2026 10:00 UTC+5.
Eskirish mezoni: xabar namuna vaqtidan kamida 15 daqiqa oldin kelgan bo‘lsa. Brauzerni ochish vaqti bilan hisoblanmaydi: bu muzlatilgan namuna.
Buxoro: 09:30, 30 daqiqa, eskirgan. Namangan: qiymatlar va xabar vaqti yo‘q. Boshqa 12 hudud: yangi.
Yig‘indilar ma’lumot mavjud 13 hududdan olinadi, eskirgan Buxoro qiymatlari ham alohida belgilangan holda kiradi. Kunlik farq aynan bir xil 13 hududni taqqoslaydi. Namangan ikki davrda ham hisobga kiritilmagan.
Namuna natijasi: 22 qurolxona, 775 qurol, 4 jiddiy signal, 3 ogohlantirish, 2 oflayn obyekt. Oldingi kunga nisbatan: jiddiy +2, ogohlantirish −1, oflayn +1.

## Manbalar va ishga tushirish

Geometriya: admin-panel/app/static/data/uz_regions.json. Loyihaning dizayn/README.md hujjatida geoBoundaries ADM1 / ODbL 1.0 deb ko‘rsatilgan. Soddalashtirilgan konturlar huquqiy aniqlikdagi chegara emas.
Ikonkalar: admin-panel/app/icons.py dan icons.js ga olingan; quyosh, oy va shimol belgisi shu 24 px chiziqli uslubda qo‘shilgan.
index.html bevosita ochiladi yoki shu papkada:
python -m http.server 8092 --bind 127.0.0.1
Oldingi holat revision-01/ ichida saqlangan. Eski app.js endi index.html tomonidan yuklanmaydi.

## Tekshiruv

- JavaScript sintaksisi; brauzerda error/warn yozuvlari yo‘q.
- Toshkent: signal jami 4 = 4 + 0; oflayn 1; kunlik o‘zgarishlar +2 va +1.
- Buxoro: 09:30, 30 daqiqa, Eskirgan; signal 1, oflayn 0.
- Namangan: qiymatlar “—”, xabar yo‘q, taqqoslash mumkin emas.
- Navoiy klaviaturada Enter bilan tanlandi; 0 signal saqlandi.
- Filtr barqaror 10 hududni xiralashtiradi; noma’lum va eskirgan holatlar xiralashtirilmaydi.
- Kunduzgi rejimda barqaror hudud va legenda rangi bir xil rgb(173, 191, 204). Tanlangan hudud shu rangni saqlab, konturi ajraladi. Jiddiy holatning ranglari ham mos.
- Kichik hudud tugmalari 44 px; Toshkentni kattalashtirish va Farg‘onaga almashtirish tekshirildi. Tanlangan hudud to‘liq sig‘di, yozuv ko‘rindi. Umumiy ko‘rinishga qaytish ishladi.
- 1265×900 kontent maydonida xulosa va faol signallar birinchi ekranda, xarita va tafsilotlar yonma-yon.
- 375×844 kontent maydonida ustuvor signal y=185–241, faol signallar y=647–785; ikkisi birinchi ekranda. Gorizontal chiqish yo‘q, tafsilotlar xaritadan oldin.
- Tekshiruvdan keyin vaqtinchalik viewport o‘lchami tiklandi, umumiy respublika ko‘rinishi va tungi rejim qoldirildi.

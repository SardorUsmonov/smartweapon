# O‘zbekiston xaritasi — vizual maket 01

Rahbariyat uchun taklif etilgan ko‘rinishning alohida interaktiv maketi. Asosiy admin panelning shablonlari, xaritasi, autentifikatsiyasi va bazasi o‘zgartirilmagan.

- Faqat O‘zbekiston; 14 hududning mavjud SVG shakllari.
- Chegara ostida yengil hajm, barqaror hududlarda neytral rang, signallarda cheklangan urg‘u.
- Hudud tanlash (xarita, ro‘yxat yoki pastki tugmalar), tafsilot, umumiy holatga qaytish va kunduzgi/tungi rejim ishlaydi.
- Barcha ko‘rsatkichlar `app.js` dagi ochiq namunaviy ma’lumotlardir. Jonli tizimga ulanish yo‘q; noma’lum holat alohida beriladi.
- Geometriya `admin-panel/app/static/data/uz_regions.json` dan olingan. Loyihaning `dizayn/README.md` hujjatida geoBoundaries ADM1 / ODbL 1.0 deb ko‘rsatilgan; soddalashtirilgan konturlar huquqiy aniqlikdagi chegara emas.

`index.html` faylini bevosita brauzerda ochish mumkin. Yoki shu papkada `python -m http.server 8092 --bind 127.0.0.1` ishga tushirib, http://127.0.0.1:8092/ manzilini oching. Tashqi xarita, tile xizmati yoki API kaliti kerak emas.

Tekshirildi: JavaScript sintaksisi; 14 hudud shakli; Navoiy tanlanganda tafsilotlar; Namanganda ma’lumot yo‘qligi; ogohlantirish filtri; umumiy holatga qaytish; kunduzgi/tungi ko‘rinish. 375 px sahifa kengligida xarita va tafsilotlar ketma-ket joylashdi, gorizontal chiqish yo‘q. Brauzerda JavaScript xato/ogohlantirishlari qayd etilmadi. Tekshiruvdan keyin vaqtinchalik ekran o‘lchami tiklandi.

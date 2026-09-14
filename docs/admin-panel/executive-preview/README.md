# Rahbariyat ma’lumotnomasi

2026-09-12. Smart Weapon uchun rahbarning umumiy holat va muhim ogohlantirishlarni ko‘rishiga mo‘ljallangan interaktiv dizayn konsepsiyasi. Foydalanuvchi asosiy auditoriyani «Rahbar: umumiy holat va muhim ogohlantirishlar» deb belgiladi.

## Art yo‘nalish

Tartibli davlat boshqaruvi ma’lumotnomasi: to‘q ko‘k navigatsiya, och ish maydoni, o‘qiladigan Segoe UI, aniq sarlavhalar, bitta hisob qatori, hududiy xarita va alohida signal ro‘yxati. Obyektlarga doir kundalik amallar mavjud operator paneliga olib boruvchi havolalarda qoladi. Rang va tipografika mahsulot ichida bitta tizimda ishlatiladi; bezakdan ko‘ra ma’lumotning ustuvorligi asosiy mezon.

O‘qilish, ranglarning vazifasi va jadvallar bo‘yicha ko‘rib chiqilgan manbalar:

- [Carbon — data table](https://carbondesignsystem.com/components/data-table/style/)
- [Carbon — typography](https://carbondesignsystem.com/elements/typography/type-sets/)
- [GOV.UK — functional colour and contrast](https://design-system.service.gov.uk/styles/colour/)

Bu manbalardan dizayn tamoyillari olindi; hech biriga muvofiqlik yoki rasmiy tasdiq da’vo qilinmaydi. IIV ramzi va O‘zbekiston xaritasi shu loyihada mavjud fayllardan olindi. Tashqi shrift, CDN yoki kuzatuv skripti yo‘q.

## Nima ishlaydi

- Xarita, signal ro‘yxati va jadvaldan hudud tanlash.
- Ro‘yxatdan tanlanganda hudud tafsilotiga fokus va ko‘rinishni olib o‘tish.
- Hudud nomini qidirish, signal/aloqa filtri, jadval ustunlarini saralash.
- Klaviatura orqali xarita hududlarini tanlash, ko‘rinadigan fokus.
- Kompyuter va telefon maketi; keng jadval o‘z hududida gorizontal suriladi.
- Mavjud paneldagi hudud, inventar, jurnal, signal va hisobot sahifalariga havolalar.
- Brauzerning chop etish oynasini ochuvchi tugma va alohida print CSS. Chop etilgan natija bu bosqichda alohida tasdiqlanmagan.

## Ma’lumotlarning ma’nosi

`data.json` — mahalliy demo bazasining saqlangan, vaqt belgisi bor nusxasi. Bu jonli ulanish emas. Yangi konsepsiya asosiy 8080 panelga integratsiya qilinmagan.

- 14 hudud, 18 qurolxona, 321 yacheyka, 590 ta qurol hisobda.
- 9 faol signal = 4 jiddiy + 5 ogohlantirish.
- Signal yoki aloqa uzilishi qayd etilgan 6 hudud. Bu filtr muddati o‘tgan barcha qaytarishlarni qamramaydi.
- 182 ta takrorlanmagan berilgan qurol; nusxa vaqtida 182 tasining qaytarish muddati o‘tgan. Buni bosh xulosa va alohida ko‘rsatkich ochiq aytadi.
- 183 ochiq berish qaydi ichida bitta takroriy qayd mavjud. Tarix o‘zgartirilmagan.
- 15/18 aloqada — bazada qayd etilgan holat. Eng so‘nggi qurolxona sinxronlashuvi 10 sentabrga tegishli; sana ko‘rsatkich yonida ko‘rinadi.
- Haftalik grafik faqat bazadagi berish/qaytarish qaydlarini ko‘rsatadi. Nol qayd operatsiya bazada qayd etilmaganini bildiradi.

`build_snapshot.py` SQLite `mode=ro` orqali SELECT so‘rovlari bilan izchil nusxa yaratadi va hududiy yig‘indilarni tekshiradi. Ilova startup jarayonini chaqirmaydi. Snapshotda shaxsiy xodim ma’lumotlari yoki hisobga kirish rekvizitlari yo‘q.

## Ishga tushirish

Shu papkada:

```powershell
python -B -X utf8 build_snapshot.py
python -B -X utf8 -m http.server 8091 --bind 127.0.0.1
```

Manzil: [Rahbariyat ma’lumotnomasi](http://127.0.0.1:8091/).

## Tekshiruv

2026-09-12 kuni brauzerda tekshirildi:

- Nusxa yig‘indilari tekshiruvdan o‘tdi.
- 14 hudud yuklandi; signal/aloqa filtrida 6 hudud.
- Samarqand qidiruvi 1 qator; topilmaydigan so‘zda aniq bo‘sh holat; tozalanganda 14 qator qaytdi.
- Yacheyka soni bo‘yicha kamayish tartibi 55, 36, 34 bilan boshlandi.
- Navoiy klaviatura Enter orqali tanlandi va 1 qurolxona, 24 yacheyka, 11 berilgan qurol ko‘rsatildi.
- Telefonda ro‘yxatdan Toshkent shahri tanlanganda tafsilot ko‘rindi va klaviatura fokusi unga o‘tdi.
- 390×844 o‘lchamda sahifa kengligi chiqib ketmadi; jadvalning o‘zida surish saqlangan.
- O‘lchamni vaqtincha o‘zgartirish tekshiruvdan keyin bekor qilindi.

Bu vizual konsepsiya tekshiruvi; xavfsizlik auditi yoki production tayyorgarligi tasdig‘i emas.

# Bosh sahifa uchun dizayn namunasi

2026-09-12. Mavjud panelning shablon taassurotini kamaytirish uchun alohida vizual taklif.

- Och va to‘q ko‘rinish; guruhlangan menyu, yagona hisob qatori, xarita, qaydlar va hududlar jadvali.
- Ko‘rinishni almashtirish, hududni qidirish, xarita/jadvaldan tanlash va tanlovni bekor qilish brauzerda tekshirildi.
- 390×844 va odatiy kompyuter ko‘rinishi tekshirildi; konsolda xato kuzatilmadi.
- `regions.json` — mahalliy demo bazasidan faqat o‘qish orqali olingan hududiy agregatlar. Bu jonli ma’lumot emas. Xarita mavjud loyiha geometriyasidan olingan.
- Boshqa bo‘limlarga havolalar amaldagi 8080 panelni yangi tabda ochadi. Amaldagi panelga bu dizayn hali integratsiya qilinmagan.

Ushbu papkada ishga tushirish:

```powershell
python -m http.server 8090 --bind 127.0.0.1
```

Ko‘rish: http://127.0.0.1:8090/

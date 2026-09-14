# Dizayn tizimi: "Nazorat markazi" (tanlangan dizayn)

Manba: foydalanuvchi 2026-09-10 kuni yuborgan dashboard rasmi ("NAZORAT MARKAZI · Qurol saqlash tizimi", 1672 × 941). Rasm faylini `docs/admin-panel/dizayn/malumot-dashboard.png` nomi bilan saqlash tavsiya etiladi (chatdan rasmni faylga yozib bo'lmaydi). Quyidagi qiymatlar rasmdan ko'z bilan olingan, aniq hex qiymatlari birinchi ekran yig'ilganda rasm bilan yonma-yon solishtirib tuzatiladi.

## 1. Ranglar

| Rol | Qiymat (taxminiy) | Qayerda |
|---|---|---|
| Sahifa foni | #0a1220 | butun fon |
| Panel (card) foni | #0f1a2e | KPI plitkalar, xarita, jadval, lentalar |
| Menyu foni | #0c1526 | chap sidebar, yuqori bar |
| Chegara | #1c2a45 | kartochka va jadval chiziqlari |
| Asosiy matn | #e6edf7 | sarlavha, raqamlar |
| Ikkilamchi matn | #8ea0bd | izohlar, ustun nomlari |
| Aksent (ko'k) | #2f7ff5 | faol menyu, grafik ustunlari, havolalar, AXBOROT belgisi |
| Yashil | #22c55e | onlayn, me'yorda, "Tizim faol" |
| Sariq | #f5b400 | ogohlantirish, kechikish, nosoz/bloklangan |
| Qizil | #ef3b3b | signal, trevoga, oflayn, favqulodda |
| Kulrang-ko'k | #3a4a66 | ma'lumot yo'q, xaritada me'yordagi hudud |
| Xarita hudud (me'yor) | #1d2b45, chegara #2a3c5e | xaritadagi oddiy hududlar |

Holat ranglari faqat holat uchun, doim belgi va matn bilan birga (rangning o'zi ma'no bermaydi).

## 2. Tipografika

| Element | Uslub |
|---|---|
| Shrift | Bitta geometrik sans (rasmdagi ko'rinishga eng yaqin Google shrift: Exo 2; zaxira: Segoe UI, sans-serif) |
| Tizim nomi | 24 px, 700, katta harflar, harf oralig'i .06em ("NAZORAT MARKAZI"), ostida 12 px kichik harflar bilan "QUROL SAQLASH TIZIMI" |
| Kartochka sarlavhasi | 14 px, 700, katta harflar, harf oralig'i .08em, chapida 3 px yashil vertikal chiziq |
| KPI qiymati | 30 px, 700, raqamlar tabular; holatga qarab rang (oq, sariq, qizil) |
| KPI yorlig'i | 12 px, ikkilamchi rang, 2 qatorgacha; osti 11 px izoh |
| Jadval | 12.5 px, ustun nomlari 11 px katta harflar; raqamlar o'ngga tekislangan |
| Menyu | 13.5 px, 600; faol element ko'k fonda oq |

## 3. Joylashuv (1440 × 900 va undan katta, ekran kengligiga cho'ziladi)

| Zona | O'lcham | Mazmun |
|---|---|---|
| Yuqori bar | 64 px | chapda logotip (ko'k qalqon) + tizim nomi; markazda rejim banneri (qizil chegara, qo'ng'iroq belgisi, matn, o'ng strelka); o'ngda soat va sana, "Tizim faol" yashil nuqta |
| Chap menyu | 136 px | 12 band: Respublika, Hududlar, Qurolxonalar, Yacheykalar, Xodimlar, Inventar, Jurnal, Signallar (qizil nuqta), Rejimlar, Hisobotlar, Qurilmalar, Sozlamalar; pastda "O'ZBEKISTON ICHKI ISHLAR VAZIRLIGI" |
| KPI qatori | 9 ta plitka, balandligi 108 px | belgi (rangli), yorliq, qiymat, izoh |
| Xarita kartasi | kenglik ≈ 975 px, balandlik ≈ 500 px | sarlavha, o'ngda "212 qurolxona · 209 onlayn · 3 oflayn · sinxron 09:42:10"; xarita; chapda + − va joylashuv tugmalari; o'ng-pastda legenda (Onlayn, Ogohlantirish, Muammo, Ma'lumot yo'q) |
| Grafik kartasi | xarita ostida, balandlik ≈ 205 px | "Sutkalik olish-qaytarish · 7 kun", y o'qi 0–6 000, ko'k ustunlar, joriy kun yorqinroq, ustun tepasida qiymat |
| Signal lentasi | o'ng ustun, kenglik ≈ 510 px, balandlik ≈ 320 px | "Barchasini ko'rish →" tugmasi; qatorlar: vaqt, belgi, sarlavha, izoh, o'ngda belgi-chip (TREVOGA qizil to'ldirilgan, OFLAYN qizil kontur, OGOHLANTIRISH sariq kontur, AXBOROT ko'k kontur); qator chap chegarasi daraja rangida |
| Hududlar jadvali | o'ng ustun, qolgan balandlik | "Batafsil tahlil →"; ustunlar: #, Hudud, Yacheyka, Berilgan, Kechikish, Signal, Oflayn; 14 qator; kechikish sariq, signal qizil |

Drill-down: xaritadagi hudud yoki jadval qatori bosilsa hudud sahifasi; breadcrumb yuqori barda rejim bannerining chap tomonida (Respublika › Hudud › Qurolxona › Yacheyka).

## 4. Xarita

14 hudud (`docs/admin-panel/dizayn/xarita/uz_regions.json`, geoBoundaries ADM1). Hudud rangi eng yomon faol holat bo'yicha: qizil = faol signal yoki oflayn qurolxona, sariq = kechikish, kulrang-ko'k = me'yor, och kulrang = ma'lumot yo'q. Har hududda dumaloq raqamli belgi (kechikish + signal + oflayn soni), Toshkent shahri uchun chiziqli callout. Ustiga kelganda hudud KPI kartochkasi, bosilganda drill-down. Zoom, pan va "respublikaga qaytish" tugmalari.

## 5. Komponentlar ro'yxati

Yuqori bar, rejim banneri, chap menyu, KPI plitka, kartochka (sarlavha chizig'i bilan), xarita, legenda, ustunli grafik, signal qatori va daraja chiplari (4 daraja), jadval (saralash, rangli raqamlar, holat chiplari), tugma (asosiy ko'k, kontur), qidiruv maydoni, breadcrumb, holat nuqtasi, badge (menyuda), modal (tasdiq, ikkinchi tasdiq), forma maydonlari, tab, vaqt chizig'i (hodisalar), 2D yacheyka sxemasi (raqamli egizak), terminal ko'zgusi vidjeti, toast va ovozli signal.

## 6. Bo'limlar va funksiyalar (chap menyu bo'yicha)

| Bo'lim | Funksiyalar | Manba |
|---|---|---|
| Respublika | rasmdagi dashboard: xarita, 9 KPI, signal lentasi, hududlar jadvali, 7 kunlik grafik, rejim banneri, sinxron holati, jonli yangilanish (WebSocket), drill-down | 02 §5; 02 §1.1 |
| Hududlar | 14 hudud ro'yxati KPI bilan, hudud sahifasi: hudud xaritasi yoki bo'linmalar jadvali, signal lentasi, taqqoslash | 02 §1.1, §5 |
| Qurolxonalar | bo'linma bo'yicha ro'yxat; qurolxona sahifasi: yacheykalar rejasi (devor/qator), qurilmalar holati, smena holati; smena ochish vizardi (o'z-tekshiruv, solishtiruv, ruxsat ro'yxati) va smena yopish (qaytarilmaganlar, tasdiq, hisobot) | 02 §5; TZ §7 |
| Yacheykalar | ro'yxat va filtrlar (holat, hudud, qurolxona); yacheyka kartasi: 2D raqamli egizak (5 zona, uyalar, qulflar, datchiklar), terminal ko'zgusi, hodisalar vaqt chizig'i, biriktirish, bloklash/blokdan chiqarish, xizmat rejimi, 3D tab | 02 §5; 01-artifact |
| Xodimlar | ro'yxat (F.I.Sh., tabel, bo'linma, holat, yacheyka, qurollangan/yo'q); karta: 5 yaroqlilik yozuvi, kredensiallar, ruxsatlar (AVTOMAT, TO'PPONCHA), navbat, custody tarixi, rad etishlar; yacheyka biriktirish | 02 §3.2, §5; TZ §6.1 |
| Inventar | qurol, magazin, o'q-dori, jihoz ro'yxatlari; jihoz kartasi va chain of custody; ko'rik/ta'mir holati, ushlab turish; inventarizatsiya sessiyasi, farqlar, akt (PDF) | 02 §3.4, §5 |
| Jurnal | append-only hodisalar, filtrlar (sana, tugun, xodim, tur, usul, smena), "Yaxlitlikni tekshirish", eksport; alohida favqulodda ochilishlar jurnali | 02 §5, §6 |
| Signallar | signal markazi: 4 daraja (INFO, WARNING, CRITICAL, SECURITY), rang va ovoz, majburiy tasdiq kartochkasi, tasdiqlash va yechish, qorovul postiga yo'naltirish, foto/video havola (simulyatsiya) | 02 §5; TZ §6.4, Ilova B |
| Rejimlar | Yig'ilish va Trevoga: boshlash/tugatish, qamrov, tasdiqlovchilar, jonli jarayon (olganlar soni, navbat, qaytarilmagan, o'rtacha vaqt), har yacheyka tasdig'i | 02 §5; TZ §6.6 |
| Hisobotlar | 7 hisobot (berish-qaytarish, joriy qurollanganlik, insidentlar, administrator harakatlari, texnik holat, kechikishlar, inventar farqlari); filtrlar; eksport PDF/XLSX/CSV raqam, maqsad, muddat, hash bilan; eksportlar jurnali | 02 §5; TZ §6.5, §12 |
| Qurilmalar | 5 daraja daraxti + obyekt qurilmalari (kamera, kommutator, UPS, NAS, server, terminal, kontroller); ko'rsatkichlar (CPU, RAM, disk, oqim, batareya, NTP, tarmoq); harakatlar (self-test, vaqt sinxroni, proshivka, xizmat rejimi); zaxira nusxalash holati | 02 §5; TZ §5.2, §11, §10.3 |
| Sozlamalar | foydalanuvchilar va rollar (ikkinchi tasdiq bilan), MFA, autentifikatsiya siyosati, chegaralar, saqlash muddatlari, integratsiyalar holati, sozlamalar auditi, til almashtirgich (lotin/kirill) | 02 §2, §5, §6 |
| Qo'shimcha | kirish sahifasi (login, parol, MFA), simulyator sahifasi (yacheyka va qurolxona hodisalarini qo'lda chaqirish), terminal ko'zgusi | 03 §7 |

## 7. Texnik asos (03-hujjat bo'yicha)

FastAPI (Python) bitta kod bazasi ikki rolda (qurolxona va markaz), SQLite (prototip) → PostgreSQL (pilot), Jinja2 shablonlar + HTMX + kichik JS modullar (SVG xarita, grafiklar, WebSocket jonli yangilanish), MQTT/HTTP hodisa oqimi, simulyator. Dizayn tokenlari bitta CSS faylida (`tokens.css`), komponentlar Jinja makrolarida.

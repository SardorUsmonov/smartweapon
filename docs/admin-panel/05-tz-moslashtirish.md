# "Aqlli qurolxona" TZ bilan moslashtirish

Manba: `docs/manbalar/Aqlli_qurolxona_TZ_v1.0.md` (kirill, "Келишиш учун лойиҳа", v1.0, fayl sanasi 2026-08-21). Bu yerda "TZ §" deb TZ bo'limlariga, "[01 §]" deb tadqiqot hujjatiga, "02/03/04" deb bizning admin panel hujjatlariga havola qilinadi.

## 1. TZ nima haqida

TZ bitta obyekt (qurolxona) uchun to'liq apparat-dasturiy kompleksni tavsiflaydi: shaxsiy yacheykalar, shkaf kontrollerlari, Face ID + Touch ID terminali, IP-kameralar va VMS, lokal server, operator ish joyi, PoE kommutator, Online UPS, zaxira NAS, tarmoq segmentatsiyasi, kiberxavfsizlik, saqlash muddatlari, ishonchlilik, qabul sinovlari, o'qitish va kafolat. Buyurtmachi, ijrochi va obyekt manzili bo'sh qoldirilgan, ya'ni bu umumiy shablon.

Bizning admin panel uchun TZ ikki narsani beradi:

| TZ darajasi | Bizning arxitekturada | Manba |
|---|---|---|
| Obyekt: lokal server, operator ish joyi, smena tartibi, VMS | Qurolxona kontrolleri (role=armory) va operator konsoli | TZ §5.1, §7; 03 §2 |
| "Raҳbariyat hisobot tizimiga agregat, shaxssizlantirilgan ma'lumot" | Respublika markaziy serveri va respublika dashboardi (role=central) | TZ §16; 02 §1.1 |

Demak TZ bizning ikki qatlamli arxitekturaga zid emas, faqat obyekt qatlamini ancha batafsil belgilaydi.

## 2. Mos keladigan joylar

| Mavzu | TZ | Bizda | Holat |
|---|---|---|---|
| Rollar | 5 rol: harbiy xizmatchi/xodim, qurolxona mas'uli, navbatchi/operator, tizim administratori, auditor/rahbar (TZ §4.2) | 5 rol [01 §2.4] + respublika va hudud rollari (02 §2) | Mos, "Navbatchi yoki komandir" = "Navbatchi/operator" |
| Bir xodim, bir yacheyka | Boshqa variantlar faqat tasdiqlangan ssenariyda (TZ §6.1) | Bir xodim, bir shkaf [01] | Mos |
| Fail-secure | Quvvat yoki aloqa yo'qolganda yacheyka yopiq qoladi (TZ §1.5, §14) | 02 §6, 04 №8 | Mos |
| Offline ishlash | Internet bo'lmasa aniqlash, ruxsat, ochish, jurnal, keyin sinxron (TZ §5.1); bufer 10 000 hodisa yoki 72 soat (TZ §11) | Offline-first, ruxsatlar keshi, hodisalar navbati (03 §2) | Mos, raqamlar qo'shiladi |
| Jurnal o'zgarmasligi | append-only/WORM yoki hash zanjiri; administrator o'chira olmaydi (TZ §9) | append-only, hash zanjiri, kontroller imzosi (02 §6) | Mos |
| Panel qulf ochmaydi | Tashqi tizimga qulfni to'g'ridan-to'g'ri ochish huquqi berilmaydi (TZ §16); avariya ochilishi faqat plombalangan kalit, ikki shaxs, kamera, akt (TZ §7.3) | 02 §1, §6; 04 №2 | Mos |
| Ikki datchik | Eshik ochiq va qulflangan holati alohida, faqat bitta gerkonga tayanilmaydi (TZ §14) | door_open va door_locked alohida (01-artifact §4) | Mos |
| Yig'ilish va trevoga | Har yacheyka faqat identifikatsiyadan keyin; guruh ochish odatda o'chirilgan, kerak bo'lsa ikki shaxs va idoraviy tartib (TZ §6.6) | Yig'ilish = navbat oynasi, Trevoga = 01 §2.6 (04 №18) | Mos |
| Eksport formatlari | PDF, XLSX, CSV (TZ §6.5, §12) | 02 §5 | Mos |
| Tarmoq | Ethernet yoki RS-485, alohida VLAN (TZ §5.1, §8) | MQTT/HTTP, RS-485 sinovda (04 №24) | Mos |

## 3. TZ dan qo'shiladigan yangi talablar

| № | Talab | TZ | Qayerga kiradi |
|---|---|---|---|
| 1 | Interfeys tili: o'zbek (kirill) va rus | §12 | 02 §6 "Til": i18n uchta til (kirill, lotin, rus); standart til: ochiq savol |
| 2 | Smena boshlanishi tartibi: operator sessiyasi (login, parol, ikkinchi omil), tizim o'z-o'zini tekshirishi (server, baza, kamera, terminal, kontroller, UPS, disk), yacheykalar va inventarni dashboard bilan solishtirish, smena ruxsat ro'yxatini tasdiqlash | §7.1, Ilova A | 02 §5: yangi ekran "Smena ochish" (chek-list vizardi) |
| 3 | Smena yakunlanishi: qaytarilmagan qurollar va ochiq insidentlar ro'yxati avtomatik, mas'ulning elektron tasdig'i, smena hisoboti, ochiq sessiyalarni avtomatik yopish, zaxira nusxa va UPS ogohlantirishlarini tekshirish | §7.4 | 02 §5: yangi ekran "Smena yopish" va "Smena hisoboti" |
| 4 | Terminalda operatsiya tanlovi: "Olish" yoki "Qaytarish"; qaytarishda aynan shu xodimga berilgan inventar ko'rsatiladi | §6.3 | 03 §7 simulyator; 01-artifact holatlar mashinasiga "operatsiya tanlash" holati |
| 5 | Ekranda ochiladigan yacheyka raqami ko'rsatiladi; qulf qisqa vaqtga ochiladi | §6.2 | Terminal ko'zgusi vidjeti; 04 №8 (15 s) mos |
| 6 | Monitoring holatlari: yacheyka (yopiq-qulflangan, ochishga ruxsat, ochiq, qulf xatosi, datchik xatosi, tamper); xodim (qurol olmagan, olgan, qaytarish kutilmoqda, bloklangan); qurilma (onlayn/oflayn, quvvat, UPS batareyasi, disk bo'sh joyi, kamera oqimi, vaqt sinxroni) | §6.4 | 02 §4 hodisalar, 02 §5 shkaf va qurilmalar ekranlari: "qulf xatosi", "datchik xatosi", "disk", "kamera oqimi", "vaqt sinxroni" qo'shiladi |
| 7 | Muhim hodisalar rang, ovoz va tasdiq talab qiluvchi kartochka ko'rinishida | §6.4 | 02 §5 signal markazi: ovozli signal va majburiy tasdiq |
| 8 | Hodisa darajalari INFO, WARNING, CRITICAL, SECURITY va ularning minimal ro'yxati | Ilova B | 02 §3.5 "Signal" va "Hodisa" obyektlariga "daraja" enum shu 4 qiymat bilan |
| 9 | Hisobotlar: berish-qaytarish jurnali, joriy qurollanganlik, insidentlar, administrator harakatlari, texnik holat (maydonlar, filtrlar, formatlar bilan) | §6.5 | 02 §5 hisobotlar: 01 §2.4 dagi 5 tur bilan birlashtiriladi, jami 7 hisobot |
| 10 | Har eksportga raqam, vaqt va bajargan shaxs; eksport vakolat, maqsad va muddat bilan cheklanadi va jurnalga yoziladi | §9, §12 | 02 §5 hisobotlar: eksport dialogida "maqsad" va "amal qilish muddati", eksport raqami |
| 11 | Foydalanuvchi kartochkasi maydonlari: F.I.Sh., tabel/xizmat raqami, bo'linma, lavozim, smena, amal qilish muddati, yacheyka raqami, ruxsat holati | §6.1 | 02 §3.2 Xodim: "amal qilish muddati" va "yacheyka raqami" aniq maydon |
| 12 | Xizmatdan bo'shatish, ta'til, kasallik, vaqtincha chetlatishda avtomatik yoki vakolatli shaxs tomonidan bloklash | §6.1 | 04 №1 xizmat holati enum: "kasallik" qo'shiladi |
| 13 | Ma'muriy huquq berish va bekor qilish kamida ikki shaxs nazorati yoki elektron tasdig'i bilan | §6.1 | 02 §2: rol berish uchun ikkinchi tasdiq oqimi |
| 14 | Administrator va auditor uchun ko'p omilli autentifikatsiya; parol siyosati, xato urinishlar bloki, sessiya taym-auti, bo'shagan xodim huquqini darhol bekor qilish | §9 | 02 §6 "Panel kirishi": MFA barcha vakolatli rollar uchun |
| 15 | Saqlash muddatlari: audit kamida 5 yil, video kamida 90 kun, foto kamida 1 yil, biometrik shablon xizmat davri + qonuniy muddat, konfiguratsiya joriy + 12 oylik versiyalar | §10.1 | 02 §6 saqlash sinflari jadvali TZ qiymatlari bilan almashtiriladi (bizning 30 kun va 90 kun taxminlari bekor) |
| 16 | Zaxira nusxalash: kunlik inkremental, haftalik to'liq, kamida 3 nusxa, shifrlangan, oylik tiklash sinovi, choraklik DR mashqi, natijalar auditda | §10.3 | 02 §5: yangi ekran "Zaxira nusxalash" (holat, oxirgi muvaffaqiyat, tiklash sinovi jurnali); 03 §2 markaz va qurolxona |
| 17 | Ishonchlilik: 24×7, mavjudlik kamida 99,5 %, ruxsat tekshiruvi va ekran javobi 2 s dan, yacheyka ochilishi 3 s dan oshmaydi, UPS kamida 30 daqiqa, monitoring ro'yxati (CPU, RAM, disk, baza, kamera, kontroller, UPS, NTP, tarmoq) | §11 | 02 §6 nofunksional talablar jadvaliga qo'shiladi |
| 18 | Vaqt: barcha qurilmalar yagona ishonchli NTP manbasi bilan | §9 | 04 №25 mos, NTP manbasi qurolxona kontrolleri yoki obyekt NTP serveri |
| 19 | Qurilmalar daraxtiga yangi turlar: IP-kamera (ONVIF), PoE kommutator (SNMPv3), Online UPS (SNMP/USB), zaxira NAS, lokal server (disk, RAID) | §5.2, §13 | 02 §5 "Qurilmalar" ekrani; simulyatorda kamera va UPS holati |
| 20 | Video va foto: kamera yozuvi hodisa belgisi bilan bog'lanadi, identifikatsiya paytida foto kadr, rad etishda foto qayd | §6.2, §7.3, §10.1 | 02 §4 hodisalar: media_ref majburiy maydonga yaqinlashadi; prototipda simulyatsiya (ochiq savol) |
| 21 | Qurilmalarni mustahkamlash: zavod parollari, keraksiz portlar, imzolangan yangilanishlar, USB cheklovi, EDR, markazlashgan jurnal va ogohlantirish | §9 | 03 §6 xavfsizlik jadvali; Bosqich 3 |
| 22 | Integratsiyalar: kadrlar tizimi, qo'riqlash va tashvish signalizatsiyasi (quruq kontakt yoki API), SIEM ga syslog/API, yagona vaqt serveri va katalog xizmati, rahbariyat hisobot tizimi (agregat, shaxssizlantirilgan) | §16 | 03 §5 API: syslog eksporti, tashvish paneli I/O; 02 §6 "Vazifalarni ajratish" |
| 23 | Yong'in xavfsizligi: evakuatsiya eshiklari ochilishi yacheykalarni avtomatik ochmaydi | §7.3 | 02 §6 nofunksional: "evakuatsiya signali qulflarga ta'sir qilmaydi" |
| 24 | Server ishlamaganda kontrollerlar cheklangan rejimda buferga yozadi yoki operatsiyani bloklaydi | §7.3 | 04: yangi taxmin "server yo'q: keshdagi ruxsatlar bilan ishlash, kesh bo'lmasa blok" (obyekt bo'yicha sozlama) |
| 25 | Yacheyka raqami va shtrix/RFID yorlig'i dasturdagi identifikatorga mos | §14 | 02 §3.3 Shkaf: "yorliq kodi" maydoni |
| 26 | Qabul sinovlari F-01..U-01 va qabul varaqasi | §18, Ilova V | 6-bo'lim: demo qamrovi |
| 27 | Konfiguratsiya, foydalanuvchi huquqlari va dastur versiyasi o'zgarishlari versiyalanadi; yashirin administrator hisoblari bo'lmaydi; API, baza sxemasi, protokol hujjatlashtiriladi | §12 | 03 §6; hujjatlashtirish rejasi |
| 28 | Yig'ilish rejimida ekranda: qurol olganlar soni, kutayotganlar navbati, qaytarilmagan inventar, o'rtacha operatsiya vaqti | §6.6 | 02 §5 "Rejimlar" ekrani: navbat va o'rtacha vaqt vidjetlari |

## 4. Ziddiyatlar va taklif qilingan yechim

| № | Mavzu | TZ | Tadqiqot hujjati / bizning hujjatlar | Taklif | Savol |
|---|---|---|---|---|---|
| 1 | Identifikatsiya omillari | Face ID va/yoki Touch ID (yuz va/yoki barmoq izi), liveness; karta va PIN tilga olinmagan (TZ §5.2, §6.2) | Asosiy: xizmat kartasi + barmoq izi yoki PIN; Face ID qo'shimcha [01 §4.2] | Ikkalasini ham qo'llab-quvvatlash, obyekt bo'yicha autentifikatsiya siyosati sozlanadi; demoda TZ tartibi (yuz + barmoq) | Ha, 1-savol |
| 2 | Interfeys tili | O'zbek kirill va rus (TZ §12) | O'zbek lotin (02 §6, 04 №18 javobi) | i18n uchta til; hujjatlar lotinda qoladi | Ha, 2-savol |
| 3 | Respublika darajasida shaxsiy ma'lumot | Rahbariyat tizimiga agregat, shaxssizlantirilgan ma'lumot (TZ §16) | Respublika tekshiruvchisi jurnalni to'liq ko'radi (04 №30) | Respublika va hudud darajasida standart holatda faqat agregat; F.I.Sh. obyekt doirasida yoki alohida "shaxsiy ma'lumot" huquqi bilan, har ko'rish auditda | Ha, 3-savol |
| 4 | Video va foto | Kameralar va VMS tizimning bir qismi, hodisaga video havola, foto kadr (TZ §5.2, §6.2, §10.1) | Prototipda ichki kamera yo'q, video tashqi CCTV (04 №34) | Prototipda kamera holati va foto kadr simulyatsiya qilinadi, ONVIF integratsiyasi Bosqich 3 | Ha, 4-savol |
| 5 | Saqlash muddatlari | Audit 5 yil, video 90 kun, foto 1 yil (TZ §10.1) | Video 30 kun, biometrika +90 kun (04 №15) | TZ qiymatlari qabul qilinadi | Yo'q, hal qilindi |
| 6 | Atama: yacheyka | "Ячейка" = bir shaxsga biriktirilgan, alohida qulf va datchikli shkaf bo'limi (TZ §3) | "Shkaf" = bir xodimning butun shkafi, ichida pastki qulflar [01] | Yacheyka = bizning shkaf; ichki qulflar "bo'lim" | Ha, 6-savol (faqat atama) |
| 7 | Obyekt konsoli va respublika paneli | TZ operator konsolini (smena, monitoring, VMS) batafsil beradi | Foydalanuvchi: panel respublika bo'yicha | Bitta veb-ilova, rol doirasi bilan ikkala daraja; Demo 1 da ikkalasi | Ha, 5-savol |
| 8 | Navbatchi roli | Navbatchi/operator (TZ §4.2) | Navbatchi yoki komandir [01 §2.4] | Nomi "Navbatchi/operator", vakolatlari 01 bo'yicha | Yo'q |
| 9 | Ma'muriy huquq berish | Ikki shaxs nazorati tavsiya etiladi (TZ §6.1) | Administrator bir o'zi (02 §2) | Ikkinchi tasdiq oqimi qo'shiladi | Yo'q |

## 5. Atamalar mosligi

| TZ (kirill) | Bizning hujjatlar (lotin) | Izoh |
|---|---|---|
| АҚТ, Тизим | Tizim, admin panel + qurolxona konsoli | |
| Ячейка | Shkaf (bir xodimniki) | Ichki qulflar: bo'lim |
| Шкаф контроллери | Shkaf kontrolleri (ESP32) | |
| Face ID + Touch ID терминали | Terminal (Face ID, barmoq izi) | Karta va PIN qo'shimcha |
| Локал сервер | Qurolxona kontrolleri (role=armory) | TZ da VMS ham shu serverda |
| Оператор иш жойи | Operator konsoli (veb) | |
| Навбатчи/оператор | Navbatchi yoki komandir | |
| Қуролхона масъули | Qurolxona mas'uli | |
| Аудитор/раҳбар | Tekshiruvchi/rahbariyat | |
| Смена | Navbat (xizmat navbati) | |
| Инцидент | Signal (hodisa) | Darajalari: INFO, WARNING, CRITICAL, SECURITY |
| Йиғин ва ташвиш режими | Yig'ilish va Trevoga rejimlari | |
| Аудит журнали | Jurnal (append-only) | |
| Раҳбарият ҳисобот тизими | Respublika dashboardi (role=central) | |

## 6. Qabul sinovlari va demo qamrovi

| Kod | Sinov (TZ §18) | Demo 1 simulyatorda | Real stend (Bosqich 3) |
|---|---|---|---|
| F-01 | Ruxsatli shaxs, faqat o'z yacheykasi ochiladi | Ha | Ha |
| F-02 | Ruxsatsiz shaxs, foto va ogohlantirish | Ha (foto simulyatsiya) | Ha |
| F-03 | Olish-qaytarish datchiklar bilan | Ha | Ha |
| F-04 | Eshik ochiq qoldi | Ha | Ha |
| F-05 | Tamper | Ha | Ha |
| R-01 | Tarmoq uzilishi, offline va sinxron | Ha (WAN uzish tugmasi) | Ha |
| R-02 | Elektr uzilishi, UPS, yacheykalar yopiq | Simulyatsiya | Ha |
| R-03 | Zaxiradan tiklash | Ha (SQLite nusxa) | Ha |
| S-01 | Rol cheklovi | Ha | Ha |
| S-02 | Jurnal butunligi | Ha ("Yaxlitlikni tekshirish") | Ha |
| P-01 | Yuklama | Sintetik flot bilan | Ha |
| U-01 | Hisobot va eksport | Ha | Ha |

## 7. Ochiq savollar (foydalanuvchiga)

1. Manba ustuvorligi: TZ va tadqiqot hujjati farq qilganda qaysi ustun? Taklif: TZ, chunki u buyurtmachi bilan kelishiladigan hujjat; tadqiqot hujjati konstruksiya uchun qoladi.
2. Interfeys tili: TZ kirill va rus deydi. Uchta til (kirill, lotin, rus) qilamiz; demo qaysi tilda ochilsin? Taklif: kirill.
3. Respublika va hudud darajasida F.I.Sh. ko'rinsinmi yoki faqat agregat (TZ §16 "shaxssizlantirilgan")? Taklif: standart holatda agregat, F.I.Sh. faqat obyekt doirasida yoki alohida huquq bilan.
4. Prototipda video va foto: simulyatsiya (kamera holati, foto kadr o'rnida belgi) yetarlimi, ONVIF integratsiyasi keyingi bosqichdami? Taklif: ha.
5. Demo 1 da nimaga urg'u: respublika xaritasi va dashboard, yoki obyekt operator konsoli (smena tartibi, monitoring)? Taklif: ikkalasi bitta ilovada, demo respublikadan boshlanib bitta qurolxonaga kirib boradi.
6. Atama: interfeysda "yacheyka" (TZ) ishlatamizmi yoki "shkaf"? Taklif: TZ atamasi "yacheyka".

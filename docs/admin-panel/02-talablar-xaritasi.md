# Admin panel: talablar xaritasi

Hujjat maqsadi: "Smart qurol-aslaha shkafi" tizimining markaziy admin paneli uchun talablar. Manba ustuvorligi (foydalanuvchi qarori, 2026-09-09): TZ ("Aqlli qurolxona", v1.0), keyin 01 (tadqiqot hujjati, konstruksiya uchun asos), keyin 02, 03, 06. TZ bilan solishtirish: 05-tz-moslashtirish.md. Bosqich: prototip, laboratoriyada 1-2 shkaf, apparat hali yo'q [01 §3.2].

Qabul qilingan qarorlar (2026-09-09): interfeys o'zbek tilida (lotin asosiy, kirill almashtirgich), rus tili keyingi bosqichda; respublika va hudud dashboardlarida ham F.I.Sh. ko'rinadi; video va foto prototipda simulyatsiya; obyekt operator konsoli va respublika dashboardi bitta ilovada; interfeys atamasi "yacheyka" (TZ) = bir xodimning shkafi.

## 1. Maqsad va foydalanuvchilar

Admin panel "Tashkilot serveri" darajasi: markaziy ma'lumotlar bazasi, ruxsatlar, audit va dashboard [01 §4.7]. U barcha shkaflarni kuzatadi va boshqaradi. U qulf ochmaydi. Qulf ochilishi faqat terminalda, xodimning o'z omillari bilan bo'ladi [01 §2.5, §2.6, §4.2].

### 1.1 Qamrov: respublika darajasi

Foydalanuvchi qarori (2026-09-09): dashboard va admin panel butun respublika bo'yicha ishlaydi. Bu 01 §4.7 dagi "Hudud/respublika" darajasini asosiy kirish ekraniga aylantiradi.

| Talab | Mazmuni | Manba |
|---|---|---|
| Ierarxiya | Respublika → Hudud (14 ta: Qoraqalpog'iston Respublikasi, Toshkent shahri, 12 viloyat) → Tuman/shahar IIB yoki funksional bo'linma → Qurolxona → Terminal guruhi → Shkaf | [01 §4.7, §2.1; foydalanuvchi] |
| Kirish ekrani | Respublika dashboardi: O'zbekiston xaritasi (14 hudud, holat rangi bilan), respublika KPI lari, hududlar jadvali, jonli signal lentasi, faol rejimlar | [01 §3.5 "hudud va bo'linmalar bo'yicha holat"; foydalanuvchi] |
| Kirib borish (drill-down) | Xaritadagi hudud yoki jadval qatori bosilsa hudud sahifasi ochiladi, undan bo'linma, qurolxona va shkafgacha. Breadcrumb har sahifada | [01 §4.7] |
| Yig'ma ko'rsatkichlar (rollup) | 9 ta KPI har darajada bir xil ma'noda, faqat qamrov farq qiladi: respublika, hudud, bo'linma, qurolxona | [01 §3.5] |
| Vakolat doirasi | Foydalanuvchi bitta tugunga bog'lanadi va faqat shu shoxni ko'radi. Respublika darajasi: IIV markaziy apparati rahbariyati va tekshiruvchisi (faqat o'qish), respublika administratori. Hudud darajasi: viloyat IIB rahbariyati, hudud administratori. Bo'linma va qurolxona darajasi: 01 §2.4 rollari | [01 §2.4, §4.7] |
| Shaxsiy ma'lumotlar | Respublika va hudud dashboardlarida ham F.I.Sh. va tabel raqami ko'rinadi, chunki bu davlat bo'yicha yagona asosiy dashboard (foydalanuvchi qarori). TZ §16 dagi shaxssizlantirish faqat tashqi rahbariyat tizimlariga eksportga tegishli. Har bir shaxsiy ma'lumot ko'rish va eksport auditga yoziladi | [TZ §9, §16; foydalanuvchi] |
| Ikki daraja, bitta ilova | Obyekt operator konsoli (TZ §7 smena tartibi, monitoring, VMS holati) va respublika dashboardi bitta veb-ilovada, rol doirasi bilan ajratiladi | [TZ §5, §7; foydalanuvchi] |
| Taqqoslash | Hududlar va bo'linmalarni KPI bo'yicha saralash va taqqoslash (kechikish, rad etish, favqulodda ochish, inventar farqi) | [01 §3.5] |
| Ko'lam | Birinchi respublika bosqichi 5 500 shkaf, katta milliy tizim 27 500 shkaf; kuniga 22 000 dan 110 000 gacha hodisa | [01 §3.1, §3.6] |
| Ma'lumot joyi | Respublika markaziy serveri IIV da, O'zbekiston hududida; bulut yo'q | [01 §3.6, §4.6] |

Respublika xaritasi 14 hududning soddalashtirilgan SVG konturlaridan quriladi, hudud kodlari ma'lumotlar bazasidagi "Hudud" jadvaliga mos keladi.

Beshta tamoyil panelning asosi [01 'Loyiha konsepsiyasi']:

| Tamoyil | Panel uchun ma'nosi |
|---|---|
| Bir xodim - bir shkaf | shkaf faqat bitta xodim profiliga biriktiriladi |
| Individual hisob | qurol, magazin, o'q-dori va jihoz inventar yoki seriya raqami bilan |
| Ikki bosqichli tasdiqlash | xizmat kartasi va biometrika/PIN; panel usulni qayd etadi |
| Offline ishlash | markaziy tarmoq uzilganda mahalliy ruxsatlar va jurnal ishlaydi |
| To'liq audit | har bir ochish, olish, qaytarish, rad etish va favqulodda operatsiya qayd etiladi |

Foydalanuvchilar [01 §2.4; 06 'Сравнение возможностей по ролям']:

| Rol (01 atamasi) | 06 muvofiqligi | Paneldagi asosiy ishi |
|---|---|---|
| Respublika rahbariyati / tekshiruvchisi (IIV markaziy apparati) | yo'q | respublika dashboardi, barcha hududlar bo'yicha KPI, taqqoslash, hisobotlar, jurnal (faqat o'qish) |
| Hudud rahbariyati / tekshiruvchisi (viloyat IIB) | yo'q | o'z hududi bo'yicha dashboard, bo'linmalar taqqoslashi, hisobotlar (faqat o'qish) |
| Oddiy xodim | Сотрудник | panelga kirmaydi; terminal bilan ishlaydi. Keyin ixtiyoriy "Mening shkafim" (faqat o'qish) |
| Qurolxona mas'uli | Оператор (qisman) | qurolni qabul qiladi/beradi, inventarni ro'yxatdan o'tkazadi, shkafni biriktiradi va bloklaydi; inventarizatsiya |
| Navbatchi yoki komandir (TZ: Navbatchi/operator) | Оператор (qisman) | xizmat ruxsatini tasdiqlaydi, vaqtinchalik vakolat, favqulodda ochish so'rovi, rejimlar; smena ochish va yopish, o'z-tekshiruv natijalarini ko'rish, tasdiq talab qiluvchi hodisalarga javob [TZ §4.2, §7.1, §7.4] |
| Administrator | Администратор | foydalanuvchi, tizim va elektronika sozlamalari; qurol olish vakolati avtomatik berilmaydi. Darajalari: respublika administratori (butun ierarxiya, siyosatlar), hudud administratori (o'z hududi), bo'linma administratori (o'z qurolxonalari). MFA majburiy; rol berish va bekor qilish ikkinchi vakolatli shaxs tasdig'i bilan [TZ §6.1, §9] |
| Tekshiruvchi/rahbariyat | yo'q | jurnal, statistika, kechikish, favqulodda ochish va inventar farqlarini ko'radi (faqat o'qish) |

Qonuniy tamoyil: panel vakolat yaratmaydi, faqat mavjud vakolatni texnik tekshiradi va qayd etadi [01 §2.2]. Qurolxona bo'yicha mas'ul shaxs tayinlanadi [01 §1.3].

## 2. Rollar va vakolatlar

Belgilar: B = bajaradi, K = ko'radi, - = yo'q. Vakolat doirasi: har bir foydalanuvchi ierarxiyadagi bitta tugunga (qurolxona, bo'linma, viloyat, respublika) bog'lanadi va faqat shu shoxni ko'radi [01 §4.7].

| Harakat | Oddiy xodim | Qurolxona mas'uli | Navbatchi yoki komandir | Administrator | Tekshiruvchi/rahbariyat | Manba |
|---|---|---|---|---|---|---|
| Dashboardni ko'rish | - | K | K | K | K | [01 §3.5] |
| Jurnalni ko'rish | - | K | K | K | K | [01 §2.4] |
| Xodim profilini yaratish, tahrirlash | - | B (biriktirish maydonlari) | - | B (akkaunt, karta) | - | [01 §2.4] |
| Yaroqlilik hujjatlarini kiritish (5 shart) | - | B | - | - | K | [01 §2.2] |
| Shkafni biriktirish, ajratish | - | B | - | - | K | [01 §2.4] |
| Shkafni bloklash, blokdan chiqarish | - | B | - | - | K | [01 §2.4] |
| Inventarni ro'yxatdan o'tkazish | - | B | - | - | K | [01 §2.4] |
| Qurolga ko'rik/ta'mir holati qo'yish | - | B | - | - | K | [01 §4.4] |
| Inventarizatsiya sessiyasi va akt | - | B | K | - | K | [01 §4.3, §3.5] |
| Xizmat ruxsatini tasdiqlash (navbat oynasi) | - | - | B | - | K | [01 §2.4, §2.5] |
| Vaqtinchalik vakolat berish | - | - | B | - | K | [01 §2.4] |
| Favqulodda ochish so'rovi (bajarilishi terminalda) | - | B | B | - | K | [01 §2.6] |
| Rejim: Yig'ilish, Trevoga | - | - | B | - | K | [06; 01 §2.6] |
| Signalni tasdiqlash (ack) | - | B | B | - | K | [01 §3.4] |
| Foydalanuvchi va rollar | - | - | - | B | - | [01 §2.4] |
| Qurilma va elektronika sozlamalari | - | - | - | B | - | [01 §2.4] |
| Autentifikatsiya siyosati, chegaralar, saqlash muddatlari | - | - | - | B | K | [01 §4.2, §3.6] |
| Sozlamalar auditi | - | - | - | K | K | [06 'Аудит системных правок'] |
| Hisobot eksporti (PDF, XLSX, CSV) | - | B | B | B | B | [01 §2.4] |
| Qurol olish | terminalda | - | - | - | - | [01 §2.5] |

Qoidalar:
- Tizim roli va qurol ruxsati ikki alohida narsa. Administratorga qurol olish vakolati avtomatik berilmaydi [01 §2.4].
- Hech bir rol jurnal yozuvini o'zgartira yoki o'chira olmaydi [01 §4.5, §2.6].
- Barcha sozlama o'zgarishlari jurnalga yoziladi: kim, qachon, eski va yangi qiymat [06; TZ §6.5].
- Ma'muriy huquq berish va bekor qilish ikkinchi vakolatli shaxsning elektron tasdig'i bilan bajariladi [TZ §6.1].
- Administrator, Tekshiruvchi va boshqa vakolatli rollar uchun ko'p omilli autentifikatsiya; parol siyosati, xato urinishlar bloki, sessiya taym-auti; bo'shagan xodim huquqi darhol bekor qilinadi [TZ §9].
- Har eksportga raqam, vaqt, bajargan shaxs, maqsad va amal qilish muddati yoziladi; eksport fakti jurnalga tushadi [TZ §9, §12].

## 3. Ma'lumotlar modeli

### 3.1 Tashkiliy ierarxiya

| Obyekt | Atributlar | Manba |
|---|---|---|
| Hudud | nomi (viloyat, respublika), ota tugun | [01 §4.7, §3.5] |
| Tashkilot/bo'linma | nomi, turi (tuman va shahar IIB; patrul-post xizmati; qo'riqlash va tezkor bo'linmalar; maxsus operatsion bo'linmalar; navbatchilik qismlari; o'quv markazlari), hudud | [01 §2.1] |
| Qurolxona | nomi, manzil, mas'ul shaxs (xodim), ruxsatnoma raqami, qo'riqlash-yong'in signalizatsiyasi mavjudligi, qorovul posti kontakti, muhit (o'lcham, elektr, tarmoq, harorat, namlik), tasdiqlovchilar soni (1 yoki 2) | [01 §1.3, §5.1, §2.6] |
| Terminal guruhi | qurolxona, xizmat ko'rsatiladigan shkaflar (10-20), o'quvchi imkoniyatlari (karta, barmoq izi, Face ID, PIN, displey) | [01 §3.3, §4.7] |

### 3.2 Xodim va vakolat

| Obyekt | Atributlar | Manba |
|---|---|---|
| Xodim | F.I.Sh., tabel raqami (tabiiy kalit), bo'linma, lavozim, xizmat holati (faol, ta'tilda, kasallik, vaqtincha chetlashtirilgan, ishdan bo'shagan), smena, amal qilish muddati, yacheyka raqami, ruxsat holati, tashqi identifikator (HR) | [01 §3.4, §2.5, §4.5; TZ §6.1] |
| Yaroqlilik (5 yozuv) | xizmat quroli rasmiy biriktirilgan (buyruq); saqlash va olib yurish vakolati; maxsus tayyorgarlik (sana); davriy professional yaroqlilik tekshiruvi (sana, amal qilish muddati); rahbar buyrug'i (raqam, sana) | [01 §2.2] |
| Kredensial | xizmat kartasi UID (holat: faol, bloklangan, yo'qolgan), shaxsiy PIN (hash), maxsus PIN (hash, faqat vakolatli rollar), biometrik shablon holati (Face ID, barmoq izi: ro'yxatdan o'tgan/yo'q, sana, qurilma); shablonning o'zi terminalda shifrlangan | [01 §2.3, §4.2, §2.6, §3.6] |
| Qurol ruxsati | sinf: AVTOMAT, TO'PPONCHA; shkaf; amal qilish boshi va oxiri; kim berdi; vaqtinchalik belgisi; sabab | [03 aside 'Beshik va qisqich'; 01 §2.4, §4.1] |
| Xizmat navbati | bo'linma, xodim, boshlanish, tugash, tasdiqlagan Navbatchi | [01 §2.5, §2.4] |
| Panel foydalanuvchisi | xodim, tizim roli, vakolat doirasi tuguni, login, parol hash, ikkinchi omil (karta + maxsus PIN) | [01 §2.4, §2.6] |

### 3.3 Shkaf va qurilmalar

| Obyekt | Atributlar | Manba |
|---|---|---|
| Shkaf (TZ atamasi: yacheyka) | yorliq kodi (shtrix yoki RFID, dasturdagi identifikatorga mos) [TZ §14], seriya raqami (tizim beradi), inventar raqami (buyurtmachi, ixtiyoriy), manzil (ierarxiya + devor/qator + o'rin), texnik holati, hayot holati: zaxira, biriktirilgan, bloklangan, nosoz, xizmatda; model (2000 × 400 × 600; modul bilan 2000 × 600 × 600), o'rnatish (2 × M12 pol, M8-M10 devor), sertifikat sinfi | [01 §3.4, §2.4, §3.1, §1.1, §1.4, §1.5] |
| Biriktirish tarixi | shkaf, xodim, boshlanish, tugash, kim bajardi | [01 §2.3, §2.4] |
| Shkaf kontrolleri | qurilma ID, ESP32/STM32, proshivka, oxirgi heartbeat, online/offline, terminal guruhi, kalit/juftlash holati | [01 §4.7; 03 aside 'Xavfsizlik'] |
| Qurolxona kontrolleri | qurolxona, UPS holati, hodisalar keshi hajmi (kamida 10 000 hodisa yoki 72 soat), oxirgi sinxronlash, WAN holati (LTE zaxira) | [01 §4.7; TZ §11] |
| Obyekt qurilmalari | turi: IP-kamera (ONVIF Profile T), PoE kommutator (SNMPv3), Online UPS (SNMP/USB), zaxira NAS, lokal server, terminal; holat: onlayn/oflayn, quvvat, batareya, disk bo'sh joyi, kamera oqimi, vaqt sinxroni; prototipda simulyatsiya | [TZ §5.2, §6.4, §13] |
| Qulf | turi: eshik, stvol qulfi, PM qutisi, o'q-dori kamari, magazin uyasi; holat; qaysi ruxsat ochadi; fail_mode = secure | [03 aside; 06] |
| Datchik | turi: eshik, urilish (akselerometr), buzish, lyuk tamper, qisqich holati, qo'ndoq bosimi, RFID, vazn, quvvat, harorat; oxirgi qiymat; oxirgi vaqt; sog'lomlik | [01 §1.4, §4.3; 03] |
| Uya (slot) | shkaf, zona (0-1150, 1150-1450, 1450-1700, 1700-1950, 1950-2000), kutilayotgan jihoz turi, datchiklar, saqlash sharti (AK: magazinsiz, bo'sh, saqlagichda) | [01 §1.2; 03 aside 'AK-74 uyasi'] |

### 3.4 Inventar

| Obyekt | Atributlar | Holat enum | Manba |
|---|---|---|---|
| Qurol | turi (avtomat, to'pponcha), modeli (AK-74, AK-74M, PM), seriya raqami, RFID, biriktirilgan xodim/shkaf/uya, ko'rik holati (yaroqli, ko'rik kutilmoqda, ko'rikda, ta'mirda), oxirgi va keyingi ko'rik | mavjud, yo'q, nosoz, xizmatda | [01 §3.4, §2.3, §4.4] |
| Magazin | inventar raqami, RFID, turi (5,45×39 30 o'q; PM), miqdori, uya o'rni | mavjud, yo'q, nosoz, xizmatda | [01 §2.3, §4.3] |
| O'q-dori (muhrlangan birlik) | turi, kalibri (5,45×39; 9×18 taxmin), partiyasi, soni, plomba raqami, quti/pachka | mavjud, yo'q, nosoz, xizmatda | [01 §2.3, §3.4; 03] |
| Jihoz | kategoriya (dubulg'a, bronjilet, gaz niqobi, kishan, taktik sumka, kamar to'plami, kichik jihozlar qutisi, body-kamera), inventar raqami yoki qurilma seriya raqami, RFID (ixtiyoriy) | mavjud, yo'q, nosoz, xizmatda | [01 §2.3, §4.6; 03] |
| Jihozlar shabloni (kit) | lavozim bo'yicha jihozlar ro'yxati; tahrirlanadigan katalog | | [01 §1.2, §5.1] |

### 3.5 Hodisalar va jurnallar

| Obyekt | Atributlar | Manba |
|---|---|---|
| Hodisa (append-only) | id, shkaf, terminal, qurolxona, kontroller tartib raqami, qurilma vaqti, server vaqti, turi, xodim, jihoz/seriya, kirish usuli (karta, PIN, biometrika, favqulodda, mexanik kalit), natija, sabab, urinishlar soni, tasdiqlovchi 1 va 2, offline belgisi, oldingi hash, hash, kontroller imzosi, foto kadr va video havolasi (identifikatsiya va operatsiya kadri; prototipda simulyatsiya) [TZ §6.2, §10.1], daraja (INFO, WARNING, CRITICAL, SECURITY) [TZ Ilova B], simulyatsiya belgisi | [01 §3.4, §2.5, §4.5; 06; TZ] |
| Olish/qaytarish (custody) | jihoz, xodim, shkaf, olingan vaqt, qaytarish muddati, qaytarilgan vaqt, davomiylik, tekshiruv natijasi (mos/mos emas) | [01 §3.4, §2.5, §4.4] |
| Favqulodda jurnali (alohida, o'chirilmaydi) | shkaflar, boshlovchi, usul (karta + maxsus PIN), ikkinchi tasdiqlovchi, mexanik kalit belgisi, sabab, vaqt | [01 §2.6, §1.4] |
| Signal | turi (urilish, buzish, eshik ochiq qolishi, quvvat uzilishi, kechikish, takroriy rad etish, lyuk tamper, qaytarish nomuvofiqligi; TZ §6.4 bo'yicha qo'shimcha: qulf xatosi, datchik xatosi, disk to'lgan, kamera oqimi yo'q, vaqt sinxroni buzilgan, server yo'q), darajasi (INFO, WARNING, CRITICAL, SECURITY [TZ Ilova B]), ovozli signal va majburiy tasdiq bayrog'i [TZ §6.4], shkaf/terminal, boshlangan, tasdiqlagan, yechilgan, yo'naltirilgan (qorovul posti) | [01 §3.4; 03 aside 'Xavfsizlik'; 02 §6] |
| Rejim | turi (yig'ilish, trevoga), qurolxona/bo'linma, boshlovchi, tasdiqlovchilar, boshlanish, tugash, qamrov | [06; 01 §2.6] |
| Inventarizatsiya | sessiya (qurolxona, kim, boshlanish, tugash), qator (jihoz, kutilgan, aniqlangan, tasdiqlangan), farq (turi: yo'q, begona RFID, datchik noaniq; yechilgan), akt (muzlatilgan, imzolovchilar) | [01 §3.5, §4.3, §2.4] |
| Sozlamalar auditi | kim, qachon, kalit, eski qiymat, yangi qiymat, obyekt | [06] |
| Sinxronlash | qurolxona, so'nggi qabul qilingan tartib raqami, ruxsatlar snapshoti versiyasi, kutilayotgan hodisalar soni | [01 §4.7, §4.5] |
| Smena (obyekt) | qurolxona, ochgan operator, boshlanish, o'z-tekshiruv natijasi (server, baza, kamera, terminal, kontroller, UPS, disk), yacheyka va inventar solishtiruvi, ruxsat ro'yxati tasdig'i, yopilish, qaytarilmagan qurollar va ochiq insidentlar ro'yxati, mas'ul tasdig'i, smena hisoboti | [TZ §7.1, §7.4, Ilova A] |
| Zaxira nusxa | tur (kunlik inkremental, haftalik to'liq), vaqt, hajm, natija, joy (lokal, ajratilgan), tiklash sinovi (oylik) va DR mashqi (choraklik) natijalari | [TZ §10.3] |
| Eksport jurnali | eksport raqami, kim, qachon, hisobot turi, filtrlar, maqsad, amal qilish muddati, fayl hash | [TZ §9, §12] |

### 3.6 Siyosatlar

| Obyekt | Atributlar | Manba |
|---|---|---|
| Autentifikatsiya siyosati (qurolxona bo'yicha) | asosiy: karta + barmoq izi yoki PIN; qo'shimcha: Face ID; favqulodda: vakolatli karta + maxsus PIN + mexanik kalit; tasdiqlovchilar soni | [01 §4.2, §2.6, §5.1] |
| Saqlash muddati (ma'lumot sinfi bo'yicha) | jurnal (uzoq muddat), biometrik shablon (himoyalangan), oddiy kirish videosi (cheklangan), buzish videosi (alohida arxiv); qiymatlar buyurtmachidan | [01 §3.6, §5.1] |
| Chegaralar | eshik ochiq qolishi, qaytarish muddati, rad etish limiti, batareya pasti, urilish g, ochilmagan qulf taymeri | taxminlar (4-hujjat) |

## 4. Hodisalar katalogi

| Hodisa | Kim / manba | Qachon | Qayd qilinadigan ma'lumot | Panelda ko'rinishi |
|---|---|---|---|---|
| auth_boshlandi | terminal | xodim o'quvchiga yaqinlashdi | terminal, vaqt | terminal ko'zgusi: kutish |
| karta_o'qildi | terminal | karta tutilganda | karta UID, xodim (topilsa) | terminal ko'zgusi: karta |
| yuz_natijasi | terminal | Face ID urinishi | ok/yo'q, ball | terminal ko'zgusi: face |
| barmoq_natijasi | terminal | barmoq izi urinishi | ok/yo'q | terminal ko'zgusi: finger |
| pin_natijasi | terminal | PIN kiritilganda | ok/yo'q | terminal ko'zgusi: pin |
| ruxsat_berildi | qurolxona kontrolleri | 3-qadam tekshiruvi o'tdi [01 §2.5] | xodim, shkaf, kirish usuli, ruxsat sinflari (AVTOMAT, TO'PPONCHA), navbat | jurnal; shkaf holati "ruxsat" |
| rad_etildi | qurolxona kontrolleri | tekshiruv o'tmadi | kim, qachon, sababi, urinishlar soni [01 §3.4] | jurnal; KPI "rad etilgan kirish urinishlari"; N dan keyin signal |
| qulf_ochildi | shkaf kontrolleri | ruxsatdan keyin | shkaf, qulf ID | shkaf holati |
| eshik_ochildi | eshik datchigi | qo'lda ochilganda | vaqt | shkaf holati "ochiq" |
| eshik_yopildi | eshik datchigi | yopilganda | vaqt, ochiq turgan davomiylik | shkaf holati |
| avtomatik_qulflandi | shkaf kontrolleri | eshik yopilgach [01 §2.5] | rigel tasdig'i | shkaf holati "qulflangan" |
| ochilmagan_qulf | shkaf kontrolleri | qulf ochildi, eshik ochilmadi (taymer) | qayta qulflash vaqti | jurnal, ogohlantirish |
| eshik_ochiq_qoldi | shkaf kontrolleri | chegara oshganda | davomiylik | signal markazi [01 §3.4] |
| stvol_qulfi_ochildi/yopildi | shkaf kontrolleri | AVTOMAT ruxsati | holat | egizak: pastki qulflar |
| avtomat_olindi/qaytarildi | datchiklar (bosim, qisqich, RFID) | kamida 2 signal mos kelganda [01 §4.3] | qurol seriya raqami, RFID, signallar, ishonch | jurnal; custody ochildi/yopildi; readiness |
| pm_olindi/qaytarildi | RFID, quti qulfi | TO'PPONCHA ruxsati | seriya raqami | jurnal; custody |
| o'q_dori_olindi/qaytarildi | vazn, kamar holati, RFID | | partiya, quti, vazn (taxminiy) | jurnal; inventar |
| magazin_soni_o'zgardi | vazn, RFID | | band uyalar 0-4, vazn | inventar |
| jihoz_olindi/qaytarildi | RFID (bo'lsa) | | kategoriya, inventar raqami | inventar |
| qaytarish_nomuvofiq | qurolxona kontrolleri | biriktirilgan jihoz emas [01 §2.5] | kutilgan va aniqlangan | signal; inventar farqi |
| kechikish | server va qurolxona kontrolleri | qaytarish muddati o'tdi [01 §3.4] | jihoz, xodim, muddat, kechikish davomiyligi | KPI "vaqtida qaytarilmagan qurollar"; xabar mas'ul shaxsga [01 §4.4] |
| mexanik_kalit | kalit datchigi yoki qulf buyrug'isiz ochilish | | vaqt, keyin kiritilgan sabab | favqulodda jurnali; signal [01 §1.4] |
| favqulodda_ochish | terminal (karta + maxsus PIN) | rejim yoki bitta shkaf | boshlovchi, ikkinchi tasdiqlovchi, qamrov, sabab, har shkaf tasdig'i | alohida jurnal; KPI "favqulodda ochilishlar" [01 §2.6] |
| rejim_boshlandi/tugadi | panel (Navbatchi yoki komandir) | | rejim turi, qamrov, boshlovchi, tasdiqlovchilar, oyna | dashboard banneri; readiness |
| urilish | akselerometr | g chegarasi oshganda | g, o'q | signal; qorovul postiga [01 §3.4] |
| buzish_urinishi | tamper, akselerometr | | turi | signal, video arxiv belgisi [01 §3.6] |
| lyuk_ochildi | lyuk tamper | xizmat eshigi yoki yuqori lyuk | qaysi lyuk, xizmat rejimidami | signal yoki xizmat yozuvi [03] |
| quvvat_uzildi/tiklandi | quvvat datchigi | | mains, batareya %, taxminiy vaqt | signal; shkaf "batareyada" [01 §3.4] |
| batareya_past | kontroller | chegara | % | signal |
| aloqa_uzildi/tiklandi | qurolxona kontrolleri, server | heartbeat yo'q | qaysi daraja, davomiylik | qurilmalar daraxti; sinxron vidjeti |
| shkaf_bloklandi/blokdan_chiqdi | panel (Qurolxona mas'uli) | | sabab, izoh | KPI "nosoz yoki bloklangan shkaflar" [01 §2.4] |
| biriktirildi/ajratildi | panel (Qurolxona mas'uli) | | xodim, shkaf, jihozlar | xodim va shkaf kartasi |
| jihoz_ushlab_turildi | panel (Qurolxona mas'uli) | ko'rik/ta'mir [01 §4.4] | jihoz, sabab | inventar; berish bloklanadi |
| inventarizatsiya_ochildi/yopildi | panel | | sessiya, farqlar soni, akt | KPI "inventarizatsiyadagi farqlar" |
| sozlama_o'zgardi | panel (Administrator) | | kalit, eski, yangi, kim | sozlamalar auditi [06] |
| kirish/chiqish (panel) | panel | | foydalanuvchi, rol, natija, urinishlar | audit |
| sinxronlandi | qurolxona kontrolleri | ulanish tiklanganda | qabul qilingan tartib raqami, kech kelgan hodisalar soni | sinxron vidjeti; "offline yozilgan" belgisi |
| operatsiya_tanlandi | terminal | xodim "Olish" yoki "Qaytarish" ni tanlaganda [TZ §6.3] | operatsiya turi, xodim | terminal ko'zgusi |
| smena_ochildi / smena_yopildi | panel (Navbatchi/operator) | smena boshida va oxirida [TZ §7.1, §7.4] | operator, o'z-tekshiruv natijasi, solishtiruv, tasdiqlar, hisobot | smena ekranlari; dashboard banneri |
| oz_tekshiruv_xato | qurolxona kontrolleri | smena ochilishida kritik xato [TZ §7.1] | qaysi komponent | operatsiyalar cheklanadi; signal CRITICAL |
| qulf_xatosi / datchik_xatosi | shkaf kontrolleri | qulf qaytar aloqasi yoki datchik nosoz [TZ §6.4, §14] | yacheyka, element | signal CRITICAL; yacheyka "xizmatda" |
| disk_toldi | qurolxona kontrolleri, server | disk 80 % [TZ Ilova B] | foiz, qurilma | signal WARNING |
| kamera_oqimi_uzildi / tiklandi | VMS (simulyatsiya) | oqim yo'qolganda [TZ §6.4] | kamera | signal CRITICAL; qurilmalar |
| vaqt_sinxroni_buzildi | qurilma | NTP og'ishi [TZ §9] | og'ish, qurilma | signal CRITICAL |
| server_yoq_rejimi | shkaf kontrolleri | server javob bermaganda [TZ §7.3] | rejim (kesh bilan ishlash yoki blok) | signal; keyin sinxron |
| huquq_berish_tasdiqlandi | panel (ikkinchi vakolatli shaxs) | rol berish yoki bekor qilish [TZ §6.1] | kim so'radi, kim tasdiqladi, rol | sozlamalar auditi (SECURITY) |
| eksport_qilindi | panel | har hisobot eksportida [TZ §9, §12] | raqam, kim, maqsad, muddat, hash | eksport jurnali (SECURITY) |
| zaxira_nusxa_bajarildi / xato; tiklash_sinovi | server | jadval bo'yicha [TZ §10.3] | tur, hajm, natija | zaxira nusxalash ekrani; xato bo'lsa signal |

## 5. Ekranlar va vidjetlar

| Ekran | Vidjetlar | Kerakli ma'lumot | Kim ko'radi |
|---|---|---|---|
| Respublika dashboardi (kirish ekrani) | O'zbekiston xaritasi: 14 hudud, rang = eng yomon faol holat (signal, kechikish, oflayn qurolxona), ustiga kelganda KPI; respublika bo'yicha 9 KPI; hududlar jadvali (shkaflar, berilgan qurollar, kechikish, rad etish, favqulodda, signal, oflayn) saralash bilan; jonli signal lentasi; faol rejimlar (Yig'ilish, Trevoga) banneri; sinxron holati (qancha qurolxona oflayn) | hudud bo'yicha yig'ma KPI, signallar, rejimlar, sinxron | respublika darajasidagi rollar; boshqalar o'z tugunidan boshlaydi |
| Hudud sahifasi (viloyat) | hudud xaritasi yoki bo'linmalar ro'yxati; bo'linmalar jadvali KPI bilan; hudud signal lentasi; hudud bo'yicha hisobotga o'tish | bo'linma bo'yicha yig'ma KPI | hudud va respublika rollari |
| Bo'linma / qurolxona dashboardi (Rahbariyat dashboardi) | 9 KPI: jami va mavjud qurollar; ayni paytda xodimlarga berilgan qurollar; vaqtida qaytarilmagan qurollar; nosoz yoki bloklangan shkaflar; sutkalik olish-qaytarishlar; rad etilgan kirish urinishlari; favqulodda ochilishlar; inventarizatsiyadagi farqlar; hudud va bo'linmalar bo'yicha holat [01 §3.5]. Qo'shimcha: "kim qurollangan, kim yo'q" doskasi [06]; faol rejim banneri; signal lentasi; sinxron va quvvat holati | qurol holati, ochiq custody, shkaf holati, hodisalar, signallar, inventarizatsiya, ierarxiya | barcha panel rollari, vakolat doirasida |
| Xodimlar | ro'yxat (F.I.Sh., tabel raqami, bo'linma, xizmat holati, shkaf, qurollangan/yo'q); karta: yaroqlilik (5 shart), kredensial holati, ruxsatlar (AVTOMAT/TO'PPONCHA), navbat, jurnal, kechikishlar, rad etishlar | xodim, yaroqlilik, kredensial, ruxsat, custody | Qurolxona mas'uli, Navbatchi, Administrator, Tekshiruvchi |
| Shkaflar | ro'yxat va qurolxona xaritasi (devor, qator, terminal guruhi); holat chiplari; bloklash dialogi (sabab) | shkaf, biriktirish, kontroller sog'lomligi | barcha |
| Shkaf raqamli egizagi | 2D old ko'rinish: 5 zona [01 §1.2] va sozlangan uyalar; har uyada holat (mavjud, yo'q, nosoz, xizmatda) va qulf; eshik/qulf/signal chizig'i; pastki qulflar (stvol, PM qutisi, o'q-dori kamari, magazin uyasi); terminal ko'zgusi (LED, displey matni, holat); quvvat, harorat, aloqa chizig'i; biriktirish sarlavhasi; hodisalar vaqt chizig'i; harakatlar paneli (rolga qarab); alohida "3D" tabi (03 viewer, metall eshik, gabarit izohi 2000 × 400 × 600) | telemetriya snapshoti, hodisalar, biriktirish | barcha; harakatlar rolga qarab |
| Inventar | qurol, magazin, o'q-dori, jihoz ro'yxatlari; jihoz kartasi va custody vaqt chizig'i (chain of custody) [01 §4]; ko'rik/ta'mir holati; ushlab turish; biriktirish oynasi | inventar obyektlari, custody | Qurolxona mas'uli, Tekshiruvchi |
| Inventarizatsiya | sessiyani boshlash; RFID sweep natijasi; qator bo'yicha tasdiqlash; farqlar ro'yxati; akt (PDF, imzo qatorlari) | sessiya, qatorlar, farqlar | Qurolxona mas'uli; Tekshiruvchi ko'radi |
| Jurnal | ustunlar: vaqt, hodisa turi, shkaf, xodim (tabel raqami), jihoz/seriya, kirish usuli, natija, sabab, tasdiqlovchi, manba (online/offline), video havola; filtrlar: sana, ierarxiya tuguni, xodim, qurol turi, hodisa turi, kirish usuli, smena; "Yaxlitlikni tekshirish"; eksport | hodisalar | barcha |
| Favqulodda ochilishlar jurnali | alohida tab; tahrirlash va o'chirish tugmalari yo'q | favqulodda jurnali | barcha |
| Signal markazi | jonli ro'yxat: turi, darajasi (INFO, WARNING, CRITICAL, SECURITY), yacheyka, vaqt; rang va ovoz; CRITICAL va SECURITY uchun tasdiq talab qiluvchi kartochka; tasdiqlash va yechish; qorovul postiga yo'naltirish holati; foto kadr va video havolasi (simulyatsiya) | signallar | Qurolxona mas'uli, Navbatchi, Tekshiruvchi |
| Navbatchilik va ruxsatlar | navbat jadvali (bo'linma, xodimlar, boshlanish, tugash); xizmat ruxsatini tasdiqlash navbati; vaqtinchalik vakolat (xodim, shkaf, boshlanish, tugash, sabab) | navbat, ruxsat | Navbatchi yoki komandir |
| Rejimlar | Yig'ilish va Trevoga: qamrov, oyna, tasdiqlovchilar; jonli qurollanish jarayoni; har yacheyka tasdig'i; ekranda qurol olganlar soni, kutayotganlar navbati, qaytarilmagan inventar, o'rtacha operatsiya vaqti [TZ §6.6]; guruh ochish odatda o'chirilgan, faqat ikki shaxs tasdig'i bilan | rejim, custody, eshik holati | Navbatchi yoki komandir |
| Smena ochish (vizard) | operator sessiyasi (login, parol, MFA); tizim o'z-tekshiruvi natijalari (server, baza, kamera, terminal, kontroller, UPS, disk) yashil/qizil; yacheykalar holati va inventar solishtiruvi, nomuvofiqlik insidentga; smena ruxsat ro'yxati va vaqtinchalik cheklovlarni tasdiqlash; Ilova A chek-listi | qurilma holati, yacheyka holati, inventar, ruxsatlar | Navbatchi/operator, Qurolxona mas'uli |
| Smena yopish va smena hisoboti | qaytarilmagan qurollar va ochiq insidentlar avtomatik ro'yxati; Qurolxona mas'ulining elektron tasdig'i; smena hisoboti (PDF); keyingi smenaga topshiriladigan holatlar; zaxira nusxa va UPS ogohlantirishlari tekshiruvi; ochiq sessiyalarni yopish | custody, signallar, zaxira nusxa holati | Navbatchi/operator, Qurolxona mas'uli |
| Zaxira nusxalash | oxirgi kunlik va haftalik nusxa holati, hajm, joy; tiklash sinovi va DR mashqi jurnali; xatolar; "tiklash sinovini boshlash" (Administrator) | zaxira_nusxa | Administrator; Navbatchi ko'radi |
| Eksportlar jurnali | barcha eksportlar: raqam, kim, qachon, hisobot, maqsad, muddat, hash; qidiruv | eksport_jurnali | Administrator, Tekshiruvchi |
| Hisobotlar | 7 tur: berish-qaytarish jurnali; joriy qurollanganlik (olgan, olmagan, qaytarmagan); insidentlar (toifa, ustuvorlik); administrator harakatlari (kim, sozlama, eski va yangi qiymat); texnik holat (qurilma, ish vaqti, uzilish, disk, UPS, tarmoq); kechikishlar; inventar farqlari [TZ §6.5; 01 §2.4]; guruhlash: kun, smena, bo'linma, hudud; eksport PDF/XLSX/CSV, har eksportga raqam, vaqt, shaxs, maqsad, muddat, hash | hodisalar agregati | Tekshiruvchi va boshqalar |
| Qurilmalar | 5 daraja daraxti: yacheyka, terminal guruhi (10-20), qurolxona, tashkilot serveri, hudud [01 §4.7]; obyekt qurilmalari: kamera, PoE kommutator, UPS, NAS, lokal server [TZ §5.2]; ko'rsatkichlar: CPU, RAM, disk, baza, kamera oqimi, kontroller, UPS batareyasi, NTP, tarmoq [TZ §11]; sog'lomlik, heartbeat, proshivka, kutilayotgan hodisalar, WAN; harakatlar: self-test, vaqt sinxroni, proshivka, xizmat rejimi | qurilma telemetriyasi | Administrator |
| Sozlamalar | foydalanuvchilar va rollar; autentifikatsiya siyosati; chegaralar; saqlash muddatlari (buyurtmachi bilan kelishiladi); integratsiyalar (HR, navbatchilik, kirish nazorati, videokuzatuv: adapter holati); sozlamalar tarixi | siyosatlar | Administrator |
| Simulyator | 1-2 jonli yacheyka + sintetik respublika floti; tugmalar: yuz, barmoq izi, karta, PIN, operatsiya tanlash (olish/qaytarish), eshik ochish/yopish, jihoz olish/qaytarish, urilish, buzish, quvvat uzilishi, UPS batareyasi past, kamera oqimi uzish/ulash, qulf xatosi, datchik xatosi, disk to'lishi, WAN uzish/ulash, kechikish, favqulodda ochish; foto kadr o'rnida belgi; "SIMULYATSIYA" belgisi | simulyator | taqdimotchi |

## 6. Nofunksional talablar

| Talab | Mazmuni | Manba |
|---|---|---|
| Offline-first | qurolxona kontrolleri mahalliy ruxsatlar keshi va hodisalar keshi bilan markaziy tarmoqsiz ishlaydi; kesh muddati cheksiz; qayta ulanganda bekor qilishlar birinchi qo'llanadi; oraliqdagi hodisalar bayroqlanadi | [01 'Offline ishlash', §4.5, §4.7] |
| Audit o'chirilmasligi | append-only jadvallar; UPDATE/DELETE huquqi hech bir rolga yo'q; shkaf oqimi bo'yicha hash zanjiri; kontroller imzosi; "Yaxlitlikni tekshirish"; favqulodda jurnali alohida | [01 §4.5, §2.6, §4.4; 06] |
| Buyruq xavfsizligi | server va kontroller buyruqlari imzolangan, nonce va muddat bilan; qulf yuritmasi shkaf ichida; takrorlash rad etiladi | [03 aside 'Xavfsizlik'; 02 §5.4] |
| Biometrika | shablonlar terminal/qurolxona kontrollerida shifrlangan; markazda faqat holat va shifrlangan escrow; panel hech qachon shablon yoki yuz tasvirini ko'rsatmaydi; o'chirish audit qilinadi | [01 §3.6, §5] |
| Ma'lumot rezidentligi | O'zbekiston hududidagi mahalliy server; bulut, tashqi CDN, tashqi shrift yo'q; paket offline o'rnatiladi | [01 §3.6, §4.6] |
| Vazifalarni ajratish | Administrator qurol vakolatiga ega emas; Tekshiruvchi faqat o'qiydi; vakolat doirasi bo'yicha filtr | [01 §2.4, §4.7] |
| Fail-secure | quvvat yo'qolganda qulflangan; masofadan ochish yo'li yo'q; mexanik kalit alohida qayd | [06; 01 §1.4] |
| Panel qulf ochmaydi | favqulodda ochish ham terminalda: vakolatli karta + maxsus PIN; tashqi tizimga qulf ochish huquqi berilmaydi; mexanik avariya ochilishi plombalangan kalit, ikki shaxs, kamera va akt bilan | [01 §2.6, §4.2; TZ §7.3, §16] |
| Ishonchlilik | 24×7; yillik mavjudlik kamida 99,5 %; ruxsat tekshiruvi va ekran javobi 2 s dan, yacheyka ochilishi 3 s dan oshmaydi; oflayn bufer kamida 10 000 hodisa yoki 72 soat; UPS kamida 30 daqiqa; monitoring: CPU, RAM, disk, baza, kamera, kontroller, UPS, NTP, tarmoq | [TZ §11] |
| Panel kirishi | shaxsiy hisob yozuvlari, umumiy login yo'q; Administrator, Tekshiruvchi va vakolatli rollar uchun MFA; parol siyosati, xato urinishlar bloki, sessiya taym-auti, ochiq sessiyalarni avtomatik yopish | [TZ §9, §7.4] |
| Eksport nazorati | eksport vakolat, maqsad va muddat bilan cheklanadi; har eksportga raqam, vaqt, shaxs va hash; fakti jurnalda | [TZ §9, §12] |
| Video va foto | hodisaga video havola va foto kadr (identifikatsiya, rad etish, operatsiya); prototipda simulyatsiya, ONVIF Profile T integratsiyasi Bosqich 3; kamera oqimi holati monitoringda | [TZ §5.2, §6.2, §7.3; foydalanuvchi] |
| Evakuatsiya | yong'in va evakuatsiya signallari yacheykalarni avtomatik ochmaydi; avariya ochilishi faqat idoraviy tartibda | [TZ §7.3] |
| Server yo'q rejimi | kontrollerlar keshdagi ruxsatlar bilan cheklangan rejimda ishlaydi yoki operatsiyani bloklaydi (obyekt bo'yicha sozlama); tiklangach solishtiriladi | [TZ §7.3] |
| Versiyalash va hujjatlashtirish | konfiguratsiya, foydalanuvchi huquqlari va dastur versiyasi o'zgarishlari versiyalanadi (kamida 12 oy); API, baza sxemasi, protokol hujjatlashtiriladi; yashirin administrator hisoblari yo'q; litsenziya ko'lamni cheklamaydi | [TZ §10.1, §12] |
| Zaxira nusxalash | kunlik inkremental, haftalik to'liq, kamida 3 nusxa, shifrlangan, oddiy operatorda o'chirish huquqi yo'q; oylik tiklash sinovi, choraklik DR mashqi; natijalar auditda | [TZ §10.3] |
| Til | o'zbek: lotin asosiy, kirill almashtirgich (avtomatik transliteratsiya + istisnolar lug'ati); rus tili keyingi bosqichda; yagona i18n jadval; apostrof bitta kod nuqtasi | [TZ §12; foydalanuvchi 2026-09-09] |
| Vaqt | UTC saqlanadi, Asia/Tashkent ko'rsatiladi; qurolxona kontrolleri NTP manbasi | taxmin |
| Media | video va tasvirlar bazadan tashqarida, havola bilan; hodisa vaqt belgisi CCTV bilan bog'lash uchun | [01 §3.6; 06] |
| Respublika ko'lami | 27 500 shkafgacha, kuniga 110 000 hodisagacha; hodisa jadvali sana bo'yicha bo'linadi; hudud, bo'linma va qurolxona bo'yicha soatlik va kunlik agregat jadvallar; respublika dashboardi faqat agregatlardan o'qiydi (2 soniyadan tez); jonli oqim WebSocket orqali faqat signal va holat o'zgarishlari | [01 §3.1, §3.6; foydalanuvchi] |
| Ko'lam | quyidagi jadval | [01 §3.1, §3.2, §3.6] |
| Saqlash muddatlari | sinf bo'yicha sozlanadi; qiymatlar buyurtmachidan | [01 §3.6, §5.1] |
| Hisobot | PDF/XLSX/CSV, hash, vaqt, kim yaratdi, qatorlar oralig'i; E-IMZO keyingi integratsiya | [01 §4.5, §5.1] |

Ko'lam raqamlari:

| Ko'rsatkich | Qiymat | Manba |
|---|---|---|
| Prototip | 1-2 shkaf, korxona laboratoriyasi | [01 §3.2] |
| Sinov | 10-20 shkaf, bitta qurolxona | [01 §3.2] |
| Pilot | 30-50 shkaf, bitta IIB | [01 §3.2] |
| Hududiy pilot | 300-500 shkaf, bitta viloyat | [01 §3.2] |
| Respublika | 5 000+ | [01 §3.2] |
| Bitta kichik IIB | 22 (20 + 2) | [01 §3.1] |
| O'rtacha IIB | 55 (50 + 5) | [01 §3.1] |
| Katta bo'linma | 110 | [01 §3.1] |
| Bitta viloyat piloti | 550 | [01 §3.1] |
| Birinchi respublika bosqichi | 5 500 | [01 §3.1] |
| Kengaytirilgan bosqich | 11 000 | [01 §3.1] |
| Katta milliy tizim | 27 500 | [01 §3.1] |
| Zaxira shkaflar | 5-10 % | [01 §3.1] |
| Hududlar | 14 (Qoraqalpog'iston Respublikasi, Toshkent shahri, 12 viloyat) | ma'muriy bo'linish |
| Birinchi respublika bosqichi: kuniga | 22 000 hodisa (5 500 × 4) | [01 §3.1, §3.6] |
| Katta milliy tizim: kuniga | 110 000 hodisa (27 500 × 4) | [01 §3.1, §3.6] |
| Hodisa har shkafga kuniga | 4 | [01 §3.6] |
| 5 000 shkaf: kuniga | 20 000 hodisa | [01 §3.6] |
| 5 000 shkaf: yiliga | ≈7 300 000 hodisa | [01 §3.6] |
| Terminal guruhi | 10-20 shkaf | [01 §3.3] |
| Modul batareyasi | 12,8 V 20 Ah, ≈5 soat | [03 aside 'Ichki joy'] |

Saqlash sinflari:

| Sinf | 01 talabi | TZ §10.1 qiymati (qabul qilindi) |
|---|---|---|
| Audit hodisalari | uzoq muddat | kamida 5 yil yoki idoraviy talab; o'zgartirishdan himoyalangan arxiv |
| Videoyozuv | cheklangan muddat | kamida 90 kun; muhim hodisa akt muddatigacha |
| Foto kadr | | kamida 1 yil yoki idoraviy talab |
| Face ID va barmoq izi shabloni | himoyalangan shaklda | xizmat davri + qonuniy/idoraviy muddat; bekor qilinganda tasdiqlangan yo'q qilish |
| Buzishga urinish videosi | alohida arxiv | akt muddatigacha, alohida arxiv |
| Konfiguratsiya | | amaldagi + kamida 12 oylik versiyalar |

Manba: [TZ §10.1; 01 §3.6]. Yakuniy muddatlar buyurtmachining idoraviy tartibi va xotira hajmi bilan tasdiqlanadi [TZ §10.1; 01 §5.1].

## 7. Prototip doirasi

| Birinchi demoda bor | Simulyatsiya qilinadi | Keyingi bosqichga qoldiriladi |
|---|---|---|
| Qurolxona mas'uli: xodim kartasi, yaroqlilik, biriktirish, bloklash, inventar ro'yxati, inventarizatsiya; Navbatchi/operator: smena ochish va yopish vizardi [TZ §7.1, §7.4] | shkaf kontrolleri (ESP32) va terminal: yuz, barmoq izi, karta, PIN, operatsiya tanlash, eshik, jihoz datchiklari, urilish, quvvat; kamera holati va foto kadr o'rnida belgi; UPS, NAS, kommutator holati | jismoniy stend (Prototip bosqichi, 01 §3.2); ONVIF, SNMPv3, syslog integratsiyalari |
| Jurnal (append-only, hash zanjiri) va favqulodda jurnali | offline: WAN uzish/ulash tugmasi, hodisalar keshi, sinxron | HR, navbatchilik, kirish nazorati, videokuzatuv API adapterlari (Hududiy pilot) |
| Respublika dashboardi: xarita (14 hudud), 9 KPI, hududlar jadvali, drill-down ierarxiya; readiness doskasi | sintetik flot butun respublika bo'yicha: 14 hudud, har hududda 3-6 tuman IIB, jami ≈5 500 shkaf (birinchi respublika bosqichi), 30 kun tarix, 4 hodisa/kun, "SIMULYATSIYA" belgisi; kichik rejim (14 × 22 = 308 shkaf) tez demo uchun | PostgreSQL (Pilot) |
| Ikki qatlam: qurolxona roli (SQLite) va markaz roli (SQLite) bitta kod bazasida | terminal ro'yxatga olish (enroll) buyrug'i | O'zDSt kriptografiyasi (sertifikatlash) |
| Demo 2: Navbatchi (navbat, vaqtinchalik vakolat, favqulodda so'rov, rejimlar), Administrator (foydalanuvchilar, sozlamalar, audit), signal markazi, hisobot eksporti, 2D egizak, 3D tab metall eshik bilan, hududlar taqqoslash hisoboti | qorovul posti relesi (log) | E-IMZO eksport imzosi; ixtiyoriy viloyat serverlari (role=region) |
| Til: o'zbek (lotin, kirill almashtirgich) | | Rus tili; Rasmiy IIV jurnal shakli (buyurtmachidan) |

TZ qabul sinovlari (F-01 … U-01) va demo qamrovi: 05-tz-moslashtirish.md, 6-bo'lim.

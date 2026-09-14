# Interaktiv prototip (artifact) tahlili

Manbalar: 03 (chop etilgan interaktiv 3D viewer), 02 (2026-09-07 hisoboti), 05 (build_viewer.py), 06 (infografika). Ziddiyat bo'lsa 01 (tadqiqot hujjati) ustun turadi. Foydalanuvchi qarorlari (2026-09-09): viewer shkafning vizual modeli; eshik metall; har bir konstruktiv qaror 01 bo'yicha.

## 1. Artifact admin panel uchun nima beradi

| Nima | Qayerda | Admin panelga foydasi |
|---|---|---|
| Terminal holatlar mashinasi: idle, face, finger, ok, open, lock | [03 JS authenticate(), tick()] | Shkafning jonli holati va "terminal ko'zgusi" vidjeti |
| Displey matnlari (o'zbek lotin) | [03 JS drawScreen()] | Holat nomlari va simulyator matnlari |
| LED rang kodi (4 rang) | [03 aside 'Holat LED'] | Holat chiplari palitrasi |
| Ikkita alohida ruxsat: avtomat / to'pponcha | [03 aside 'Beshik va qisqich'; 02 §5.4] | Ruxsat modeli va pastki qulflar |
| Datchik, qulf, yuritma ro'yxati | [03 aside 'Ichki joy', 'Xavfsizlik'] | Telemetriya maydonlari |
| Jihozlar va tokcha koordinatalari | [03 JS addCab(); 02 §5.3] | 2D uya sxemasi uchun joylashuv |
| Interloklar (eshik 90° dan ortiq, avtomat tashqarida) | [03 JS toggleDrawer(), requestDoors()] | Holat tekshiruv qoidalari |
| Modul quvvat va aloqa tarkibi | [03 aside 'Ichki joy', 'Aloqa va EMC'] | Quvvat va aloqa telemetriyasi |
| BOM jadvali va ko'rinishlar: Izometriya, Old, Yon, Ust, Ichki | [03 header .views; aside 'Spetsifikatsiya'] | Shkaf kartasidagi 3D tab |
| META konfiguratsiyasi: WINDOWS, GLASS, CLIP_Y | [05 build_viewer.py] | Metall eshikka o'tkazish: WINDOWS={} |

## 2. Autentifikatsiya ssenariysi va holatlar

03 dagi ssenariy: "yuzni tanish, barmoq izi, qulf ochiladi, eshiklar ochiladi; eshiklar yopilganda avtomatik qulflanadi" [03 aside eslatma; 02 §3].

| Holat | Displey (1-qator / 2-qator) | LED | Davomiylik | Keyingi holat | O'tish sharti |
|---|---|---|---|---|---|
| idle | "Yuzingizni kameraga" / "qarating" | ko'k #2f9bff | cheksiz | face | "Kirish" tugmasi yoki o'quvchiga bosish |
| face | "Yuz tanilmoqda…" / "NN %" | ko'k, pulsatsiya | 1300 ms | finger | progress 100 % |
| finger | "Barmoq izini" / "beshikka qo'ying" | sariq #ffb547, pulsatsiya | 1400 ms | ok | progress 100 % |
| ok | "Ruxsat · Xodim #01" / "Chapga qadam qo'ying, eshikni oching" | yashil #3ddc84 | 700 ms | open | viewerda eshik 100° ga ochiladi |
| open | "Eshiklar ochiq" / "Yopilganda avtomatik qulflanadi" | yashil #3ddc84 | eshik yopilguncha | lock | barcha eshiklar 0° (eshik datchigi) |
| lock | "Qulflandi" / (bo'sh) | qizil #ff5252 | 1500 ms | idle | taymer |

Manba: [03 JS tick(), drawScreen(), setLeds()].

Boshqa matnlar (aynan qayta ishlatiladi):

| Element | Matn | Manba |
|---|---|---|
| Ekran sarlavhasi (chap) | SMART SHKAF | [03 JS drawScreen()] |
| Ekran sarlavhasi (o'ng) | OCHIQ (open holatida) yoki QULF | [03 JS drawScreen()] |
| Tugma | Kirish / … / Yopish va qulflash | [03 JS authenticate(), tick()] |
| Maslahat 1 | Avval eshikni 90° dan ortiq oching | [03 JS toggleDrawer()] |
| Maslahat 2 | Avval avtomatlar joyiga qo'yiladi… | [03 JS requestDoors()] |
| Ko'rsatma (displey) | chapga qadam qo'ying, eshikni oching | [03 aside 'Displey'] |

Ssenariy qoidalari:
- authenticate() faqat idle holatda ishlaydi. Jarayon o'rtasida qayta kirish yo'q [03 JS authenticate()].
- open dan lock ga o'tish ikkinchi bosish bilan emas, eshik yopilish datchigi bilan boshlanadi [03 JS animateDoors() izohi; 01 §2.5 8-qadam].
- 03 da eshik animatsiya bilan o'zi ochiladi. Real eshik qo'lda ochiladi, elektr yuritma yo'q [03 aside eslatma; 02 §5.4]. Shuning uchun "qulf ochildi" va "eshik ochildi" ikki alohida hodisa.
- Ekranda xodim "Xodim #01" deb ko'rsatiladi. Real kalit tabel raqami [01 §3.4].

Admin panel uchun kengaytirilgan holatlar (01 talab qiladi, 03 da yo'q):

| Holat | Sabab | Manba |
|---|---|---|
| karta | Asosiy omil: xizmat kartasi | [01 §4.2, §2.5] |
| pin | Barmoq izi o'rniga PIN; qo'lqop holati | [01 §4.2; 03 aside 'Barmoq izi'] |
| rad_etildi | Kim, qachon, sababi, urinishlar soni | [01 §3.4] |
| bloklangan | Qurolxona mas'uli bloklaydi | [01 §2.4] |
| signal | Urilish, buzish, eshik ochiq qolishi, quvvat uzilishi | [01 §3.4] |
| offline | Mahalliy ruxsatlar bilan ishlash | [01 'Loyiha konsepsiyasi' Offline ishlash] |
| favqulodda | Favqulodda ommaviy ochish | [01 §2.6] |
| yig'ilish / trevoga | Rejimlar | [06 'Режим «Сбор» и «Тревога»'; 01 §2.6] |
| kechikish | Belgilangan vaqtda qaytarilmagan jihoz | [01 §3.4] |
| jihoz ushlab turilgan | Ko'rik yoki ta'mirdan o'tmagan qurol berilmaydi | [01 §4.4] |
| mexanik kalit | Alohida qayd qilinadi | [01 §1.4] |

## 3. LED va displey konvensiyalari

| Rang | 03 ma'nosi | Hex | Admin paneldagi qaror |
|---|---|---|---|
| ko'k | kutish (idle, face) | #2f9bff | kutish |
| sariq | barmoq (finger) | #ffb547 | tasdiqlash jarayoni |
| yashil | ruxsat (ok, open) | #3ddc84 | ruxsat, eshik ochiq |
| qizil | qulf (lock) | #ff5252 | faqat "terminal ko'zgusi" vidjetida qulf; dashboardda qizil faqat signal, kechikish, bloklangan uchun |

Manba: [03 aside 'Holat LED'; 03 JS setLeds()]. 03 da rad etish va signal uchun rang yo'q. Taxmin: rad etish va signal uchun qizil miltillash (sozlanadi).

| Displey | Qiymat | Manba |
|---|---|---|
| O'lcham | 3,5 dyuym, 74 × 56 mm | [03 aside 'Displey'] |
| Balandlik | ≈1390 mm | [03 aside 'Displey'] |
| Mazmuni | holat, ko'rsatmalar, xodim ID | [03 aside 'Displey'] |
| Canvas | 296 × 224 px, ikon + 2 qator matn + progress bar | [03 JS drawScreen()] |

## 4. Datchiklar, qulflar va yuritmalar

| Element | 03/02 tavsifi | 01 talabi | Telemetriya maydoni |
|---|---|---|---|
| Eshik datchigi | qulflash eshik yopilganda avtomatik (eshik sensori) [03 aside 'O'quvchi'] | eshik holati datchigi [01 §1.4] | door_open |
| Eshik qulfi | motorli ilgak/qulf qutisi x -317…-254, z 980…1120; eshik qo'lda ochiladi [03 aside 'Oynali eshik'] | elektron qulf + favqulodda mexanik qulf [01 §1.4] | door_locked |
| Mexanik kalit | 03 da yo'q | ishlatilishi alohida qayd qilinadi [01 §1.4] | mechanical_key_used |
| Stvol qisqichi | U-o'yiqli 22 × 30 mm, z 965…995 [03 aside 'Beshik va qisqich'] | stvol qisqichidagi holat datchigi [01 §4.3] | barrel_in_clamp |
| Stvol qulfi | solenoidli planka y -118…-108, z 970…990, 10 mm rigel, C-qalpoq ostida [03 JS addCab 'Stvol qulfi'] | qurol holati mustaqil nazorat [01 §1.4] | ak_clamp_locked |
| Qo'ndoq bosim datchigi | rezina beshik z 180…215, datchik ko'rsatilmagan [03 aside 'Beshik va qisqich'] | qo'ndoq ostidagi bosim datchigi [01 §4.3] | butt_pressure |
| RFID antennalar | 03 da yo'q | qurol, magazin, muhim jihoz [01 §4.3] | rfid_seen {tag, slot} |
| Vazn datchigi | 03 da yo'q | magazin va o'q-dori bo'limlarida [01 §4.3] | mag_rack_weight_g, ammo_box_weight_g |
| PM qutisi qulfi | 200 × 160 × 60, alohida elektron qulf [03 JS addCab] | o'q-dori holati mustaqil [01 §1.4] | pm_box_locked, pm_present |
| O'q-dori kamari solenoidi | 3 × 30 kamar, +x oyoqda solenoid, PM qutisi ruxsati [03 JS addCab] | [01 §1.4] | ammo_strap_locked, ammo_present |
| Magazin uyasi qopqog'i | 4 joy, 30 mm qadam, qulflanadigan [03 JS addCab] | vazn nazorati [01 §4.5] | mag_rack_locked, mag_slots_occupied |
| 3 o'qli akselerometr | shisha sinishi + akselerometr, modul, qorovul posti [03 aside 'Oynali eshik'; 02 §6] | urilish, buzishga urinish [01 §1.4, §3.4] | impact_g, tamper_attempt |
| Shisha sinishi datchigi | bor [03] | metall eshik: olib tashlanadi [01 §1.5] | yo'q |
| Lyuk tamper datchiklari | xizmat eshigi 155 × 1150, yuqori lyuk 155 × 200 [03 aside 'Xizmat kirishi'] | buzishga urinish [01 §1.4] | tamper_service_door, tamper_upper_hatch |
| Quvvat | 24 V/150 W, DIN DC-UPS, LiFePO4 12,8 V 20 Ah, ≈5 soat [03 aside 'Ichki joy'] | zaxira quvvat; quvvat uzilishi signali [01 §1.4, §3.4] | mains_ok, on_battery, battery_pct |
| Harorat va isitgich | 30-50 W termostat, 5 °C dan past [03 aside 'Muhit'] | IP darajasi IEC 60529 [01 §1.5] | module_temp_c, heater_on |
| Ichki LED chiziqlar | 2 × 12 V, z 2140 va z 1281, Face ID yoki eshik datchigi bilan [03 JS addCab] | ichki holatni ekranda ko'rsatish [01 §1.5] | interior_light_on |
| Holat LED chizig'i | 60 × 3 mm [03 aside 'Holat LED'] | | reader_led |
| Face ID kameralar | IR Ø10, RGB Ø8, IR yoritgich Ø6; 1466 mm; 11° yuqoriga [03 aside 'Face ID moduli'] | Qo'shimcha omil [01 §4.2] | face_result |
| Barmoq izi | sig'imli Ø24 mm, 35° beshik, ≈1290 mm [03 aside 'Barmoq izi'] | Asosiy omil [01 §4.2] | finger_result |
| Karta o'quvchi va PIN | 03 da yo'q | Asosiy: xizmat kartasi + PIN [01 §4.2] | card_read, pin_result |

## 5. Modul tarkibi va 01 bo'yicha joylashuvi

| Komponent | 03/02 qiymati | 01 bo'yicha qayerda turadi |
|---|---|---|
| Modul korpusi | 200 × 623 × 2056 mm, 3 mm po'lat, IP54, 110-150 kg [03 aside 'Modul korpusi', 'Mahkamlash'] | 10-20 shkafga bitta umumiy terminal [01 §3.3, §4.7] |
| Kontroller | SBC + yuz tanish protsessori, z ≈ 1400 [03 aside 'Ichki joy'] | terminal (10-20 shkaf); shkafda ESP32/STM32 [01 §4.7] |
| Quvvat | 24 V/150 W, DIN DC-UPS, LiFePO4 12,8 V 20 Ah, ≈5 soat [03 aside 'Ichki joy'] | UPS qurolxona darajasida; shkafda zaxira quvvat [01 §4.7, §1.4] |
| Rele | qulf yuritmasi relelari, TVS himoyasi [03 aside 'Ichki joy'] | shkafning himoyalangan hajmi ichida [03 aside 'Xavfsizlik'] |
| LTE router | yuqori lyukda, SMA tashqi antenna [03 aside 'Xizmat kirishi', 'Aloqa va EMC'] | tarmoq shlyuzi qurolxona darajasida [01 §4.7, §4.6] |
| O'quvchi | 120 × 260 × 14 mm, x -519…-399, z 1340…1600 [03 aside 'O'quvchi'] | Face ID terminali va ekran [01 §4.7] |
| Xizmat kirishi | old eshik 155 × 1150 (kalit), yuqori lyuk 155 × 200 [03 aside 'Xizmat kirishi'] | xizmat rejimi va tamper hodisalari |
| Kabel | ekranlangan, qulf kabelidan ≥ 50 mm ajratilgan [03 aside 'Aloqa va EMC'] | lokal tarmoq TZ bo'limi [01 §5] |
| Isitgich | 30-50 W, 5 °C dan past [03 aside 'Muhit'] | Muhit ma'lumotlari buyurtmachidan [01 §5.1] |

Xulosa: 03 dagi modul laboratoriya prototipi (1-2 dona) uchun. Tizim modelida Terminal, Shkaf kontrolleri va Qurolxona kontrolleri alohida obyektlar [01 §3.3, §4.7]. Telemetriya maydonlari saqlanadi, lekin terminal va qurolxona darajasiga o'tadi.

## 6. Jihozlar va uyalar

03 koordinatalari: pol z = 104 mm. Tokcha balandliklari poldan: 1293 - 104 = 1189; 1553 - 104 = 1449; 1812 - 104 = 1708 mm [03 aside 'Shkaf o'zgarishi'; 02 §5].

| Jihoz | 03 joyi | O'lcham, mm | 01 zonasi | Identifikator [01 §2.3] | Mavjudlik datchigi |
|---|---|---|---|---|---|
| AK-74 | tik uya, x -273, z 180…1158 | 943 (AK-74M 705) | Pastki 0-1150 | seriya raqami + RFID | bosim + qisqich + RFID (kamida 2) [01 §4.3] |
| Taktik sumka | polda, x -200…-5 | 450 × 300 × 195 | Pastki 0-1150 | inventar raqami (taxmin) | RFID ixtiyoriy |
| Kamar + PM koburasi + kishan | ilgak plastinasi x 13,6, z 880…1270 | kishan 230 × 90 × 28 | Pastki/O'rta | inventar raqami (taxmin) | yo'q |
| Bronjilet | shtanga Ø20, z 1230 | | O'rta 1150-1450 | inventar raqami | RFID ixtiyoriy |
| O'q-dori qutisi | 1293 tokchasi, kamar ostida | 240 × 200 × 130 | O'rta 1150-1450 | turi, kalibri, partiyasi, soni | vazn + kamar holati |
| O'q pachkasi 5,45×39 | 1293 tokchasi | 2 dona | O'rta 1150-1450 | partiya | vazn |
| PM + 2 magazin | 1553 tokchasi, qulfli quti | PM 161 × 127 × 30; quti 200 × 160 × 60 | Yuqori-o'rta 1450-1700 | seriya raqami + RFID | RFID + quti qulfi |
| AK magazinlari | 1553 tokchasi, uya | 4 dona, 30 mm qadam, 30 o'q, bo'sh | Yuqori-o'rta 1450-1700 | inventar raqami va miqdori | vazn + RFID |
| Kichik jihozlar qutisi | 1553 tokchasi | 160 × 120 × 60 | Yuqori-o'rta 1450-1700 | inventar raqami (taxmin) | yo'q |
| Dubulg'a 6B47 | 1812 tokchasi, halqa beshik Ø200 | 305 × 260 × 175 | Yuqori 1700-1950 | inventar raqami | RFID ixtiyoriy |
| Gaz niqobi sumkasi | 1812 tokchasi, orqada | 280 × 120 × 190 | Yuqori 1700-1950 | inventar raqami (taxmin) | RFID ixtiyoriy |
| Body-kamera | 03 da yo'q | | Yuqori-o'rta (taxmin) | qurilma seriya raqami [01 §2.3] | RFID (taxmin) |
| Kabel, LED, datchiklar | z 1950-2000 | | Texnik bo'shliq | | |

Manba: [03 aside 'Jihozlar (1 askar)'; 03 JS addCab(); 02 §5.3; 01 §1.2, §2.3]. 01 §1.2: tokchalar yechiladigan yoki balandligi o'zgartiriladigan. Shuning uchun uya joylashuvi shkaf bo'yicha sozlanadigan shablon, qattiq kod emas.

## 7. Ikkita alohida ruxsat

| Qulf | Qaysi ruxsat ochadi | Manba |
|---|---|---|
| Tashqi eshik qulfi | asosiy kirish (karta + barmoq izi yoki PIN) | [01 §4.2, §2.5] |
| Stvol qulfi (AK) | AVTOMAT | [03 aside 'Beshik va qisqich'] |
| AK magazin uyasi qopqog'i | AVTOMAT (taxmin) | [03 JS addCab] |
| PM qutisi qulfi | TO'PPONCHA | [03 aside 'Beshik va qisqich'; 02 §5.4] |
| O'q-dori kamari solenoidi | TO'PPONCHA (PM qutisi ruxsati) | [03 JS addCab 'O'q-dori qutisi qulf kamari'] |

Xulosa: xodim ruxsati kamida ikki sinfdan iborat: AVTOMAT va TO'PPONCHA. Har biri alohida beriladi, bekor qilinadi va jurnalga yoziladi. Displeyning ok holati qaysi qulflar ochilganini ko'rsatishi kerak (03 da faqat umumiy "Ruxsat").

## 8. Interloklar

| Qoida | 03 manbasi | Elektron talqin |
|---|---|---|
| Avtomat faqat eshik 90° dan ortiq ochiq bo'lganda olinadi (to'xtatgich 100°, 86° dan past eshik yo'lni kesadi) | [03 aside 'Olish harakati'; JS toggleDrawer()] | stvol qulfi faqat door_open = true bo'lganda ochiladi |
| Olish harakati: 15 mm ko'tarish, 30 mm tortish, 25° dan ortiq qiyalik | [03 aside 'Olish harakati'; JS animateDrawers()] | egizakda "olish" animatsiyasi uchun |
| Avtomat tashqarida turganda eshik yopilmaydi | [03 JS requestDoors(), pendingDoor] | uyada qisman turgan avtomat: qulf ulanmasin, ogohlantirish. To'liq olingan avtomat: eshik yopiladi, bu olish hodisasi [01 §2.5] |
| Eshik yopilganda avtomatik qulflanadi | [03 aside 'O'quvchi'; 01 §2.5] | door_closed hodisasi lock buyrug'ini beradi |
| Ochiq eshik o'quvchini to'smaydi | [03 aside 'Eshik klirensi'] | elektron interlok kerak emas |
| Eshik va modul klirensi 0-100° da ≥ 3 mm devorga, ≥ 24 mm modulga | [03 JS izohlar NEW_WALL/MOD_BODY] | ma'lumot uchun |

## 9. Aloqa va quvvat

| Ko'rsatkich | 03/02 | 01 | Panel uchun |
|---|---|---|---|
| WAN | LTE router har modulda, SMA antenna [03 aside 'Aloqa va EMC'] | tarmoq shlyuzi qurolxonada [01 §4.7] | wan_up, lte_rssi qurolxona kontrollerida |
| Shkaf va terminal aloqasi | ekranlangan simli kabel [03 aside 'Aloqa va EMC'] | umumiy aloqa/boshqaruv moduli [01 §4.7] | transport aniqlanmagan, taxmin: MQTT/TLS |
| Signal yo'li | datchik, modul, qorovul posti (signal, jurnal, LTE) [03 aside 'Oynali eshik'; 02 §6] | qo'riqlash-yong'in signalizatsiyasi almashtirilmaydi [01 §1.3] | signal qorovul postiga ham yo'naltiriladi |
| Quvvat | 24 V/150 W + DC-UPS + LiFePO4 20 Ah ≈5 soat [03 aside 'Ichki joy'] | zaxira quvvat; UPS qurolxonada [01 §1.4, §4.7] | ikki qatlam: qurolxona UPS va shkaf zaxirasi |
| Fail-secure | | fail-safe/fail-secure siyosati TZ bo'limi [01 §5] | quvvat yo'q: qulflangan holat, mexanik kalit alohida qayd [06; 01 §1.4] |
| Buyruq xavfsizligi | modul faqat autentifikatsiyalangan (shifrlangan) signal yuboradi [03 aside 'Xavfsizlik'] | | server va kontroller buyruqlari imzolangan, nonce va muddat bilan |

## 10. Ziddiyatlar va qarorlar

| № | Mavzu | 02/03/06 aytadi | 01 aytadi | Qaror | Admin panelga ta'siri |
|---|---|---|---|---|---|
| 1 | Eshik materiali | oynali eshik, 2 ta ko'rish oynasi 260 × 695 va 260 × 910, 44.4 P4A laminat, shisha sinishi datchigi [03 aside 'Oynali eshik'; 02 §5.5] | metall tashqi eshik, ichki holat kamera/ekranda [01 §1.5] | metall eshik (01 + foydalanuvchi) | shisha sinishi hodisasi yo'q; urilish va buzish qoladi; ichki holat uya sxemasida |
| 2 | Gabarit | 400 × 646 × 2056 mm [03 aside 'Gabarit'; 02 §5.1] | 2000 × 400 × 600 mm; modul bilan 2000 × 600 × 600 [01 §1.1] | 01 | shkaf modeli kartasida 01 raqamlari; 03 faqat vizual |
| 3 | Elektronika topologiyasi | to'liq balandlikdagi modul har shkafda: SBC, UPS, LTE [03 aside 'Modul korpusi'; 02 §5.4] | 10-20 shkafga bitta terminal; shkafda arzon kontroller; qurolxonada lokal kontroller [01 §3.3, §4.7] | 01 | Terminal, Shkaf kontrolleri, Qurolxona kontrolleri alohida obyektlar |
| 4 | Autentifikatsiya tartibi | yuz asosiy omil; yuz, barmoq izi, qulf [03 aside 'Face ID moduli'; 02 §5.4] | asosiy: karta + barmoq izi yoki PIN; Face ID qo'shimcha [01 §4.2] | 01 | karta va PIN holatlari qo'shiladi; usul har hodisada yoziladi |
| 5 | Karta o'quvchi va PIN | o'quvchida yo'q, faqat zaxira sifatida eslatilgan [03 aside 'Barmoq izi'] | xizmat kartasi asosiy [01 §2.3, §4.2] | 01 | terminalga karta antennasi va PIN kiritish qo'shiladi (simulyatorda ham) |
| 6 | Mexanik kalit | faqat motorli qulf qutisi [03 aside 'Oynali eshik'] | elektron + favqulodda mexanik qulf, alohida qayd [01 §1.4] | 01 | mexanik kalit hodisasi va kalit datchigi |
| 7 | LTE | har shkaf modulida [03 aside 'Xizmat kirishi'] | tarmoq shlyuzi qurolxonada; lokal server [01 §4.6, §4.7] | 01 | WAN holati qurolxona darajasida |
| 8 | Body-kamera | jihozlar ro'yxatida yo'q [03 aside 'Jihozlar (1 askar)'] | qurilma seriya raqami bilan biriktiriladi [01 §2.3] | 01 | inventarga body-kamera kategoriyasi |
| 9 | Rollar | 3 rol: Сотрудник, Оператор, Администратор [06] | 5 rol [01 §2.4] | 01 | Оператор = Qurolxona mas'uli + Navbatchi; 06 dagi "аудит системных правок" saqlanadi |
| 10 | Saqlash birligi | ko'p yacheykali blok, "персональная ячейка" [06] | Bir xodim - bir shkaf [01 konsepsiya, §4.6] | 01 | yacheyka = butun shkaf; pastki qutilar = shkaf ichidagi uyalar va qulflar |
| 11 | Xodim identifikatori | "Xodim #01" [03 JS drawScreen()] | tabel raqami [01 §2.3, §3.4] | 01 | displeyda tabel raqami; "#01" faqat maket |
| 12 | Qizil rang | qizil = oddiy qulf holati [03 aside 'Holat LED'] | rad etish va signal alohida qayd [01 §3.4] | muhandislik qarori | dashboardda qizil faqat signal uchun; terminal ko'zgusida 03 palitrasi |
| 13 | Eshik ochilishi | ok dan keyin eshik animatsiya bilan 100° ga ochiladi [03 JS tick()] | eshik qo'lda ochiladi [02 §5.4; 03 eslatma] | 03 animatsiya faqat qulaylik | unlock va door_open alohida; ochilmasa qayta qulf (taxmin: 15 s) |
| 14 | Interlok o'qilishi | "Avtomat tashqarida turganda eshik yopilmaydi" [03 aside 'Olish harakati'] | avtomat olinadi, eshik yopiladi, shkaf qulflanadi [01 §2.5] | ziddiyat emas | qoida uyada qisman turgan avtomatga tegishli |
| 15 | Tokcha zonalari | o'q-dori 1293, PM 1553, dubulg'a 1812 [02 §5.3] | zonalar 0-1150, 1150-1450, 1450-1700, 1700-1950, 1950-2000 [01 §1.2] | mos, 01 zonalari asos | uya shabloni 01 zonalari bo'yicha; 03 joylashuvi standart namuna |
| 16 | UPS joyi | DC-UPS har modulda [03 aside 'Ichki joy'] | UPS qurolxonada; shkafda zaxira quvvat [01 §4.7, §1.4] | ikki qatlam, ziddiyat emas | telemetriya "qurolxona UPS da" va "shkaf batareyada" ni ajratadi |
| 17 | Sertifikatlash yo'li | "tekshiruv shkafi" sifatida hujjatlashtirish [02 §6; 03] | EN 14450 S1/S2, O'RQ-550 "metall shkaf" [01 §1.3, §1.5] | 01 | shkaf modelida sertifikat sinfi maydoni |
| 18 | Rejimlar | Сбор va Тревога [06] | faqat favqulodda ommaviy ochish [01 §2.6] | 01 asos, 06 nomlari | Yig'ilish = vaqtinchalik vakolat oynasi; Trevoga = 01 §2.6 |
| 19 | Favqulodda usuli | | "karta + maxsus PIN, zarur holatda ikki mas'ul shaxs" [01 §2.6] va "karta + maxsus PIN + mexanik kalit" [01 §4.2] | ziddiyat emas | approver_2 va mech_key_used maydonlari favqulodda hodisasida |

## 11. Artifactdan qayta ishlatiladigan narsalar

| Narsa | Qanday ishlatiladi |
|---|---|
| Displey matnlari (6 holat) | simulyator va "terminal ko'zgusi" satrlari, i18n jadvalida |
| LED palitrasi (4 hex) | terminal ko'zgusi chiplari |
| Uya koordinatalari (x, z) | 2D old ko'rinish sxemasi uchun nisbiy joylashuv; 01 zonalariga qayta bog'lanadi |
| BOM jadvali uslubi (qator tanlash, katakcha) | inventar ro'yxatlari |
| Ko'rinishlar va eshik slayderi (setDoors, toggleDrawer) | 3D tabda eshik ochiq/yopiq va avtomat olindi holatini telemetriyadan berish (ixtiyoriy) |
| 05 konfiguratsiyasi | WINDOWS={} va GLASS, CLIP_Y ni olib tashlash: yaxlit eshik 11-3 qayta hosil bo'ladi; header va 'Oynali eshik' qatori matni tuzatiladi |
| Eskirgan qoldiqlar | RACK 5 uya / 95 mm izohi, eshik 11-2, META.removed ['11-2','3-6','5-6','9-7','9-8'], shisha halqalari: e'tiborga olinmaydi |

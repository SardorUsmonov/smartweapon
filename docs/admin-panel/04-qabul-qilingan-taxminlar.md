# Qabul qilingan taxminlar

(D) ro'yxati bo'sh: tahlil bosqichida manbalar javob bermagan har bir savol yo manbada topildi (2-bo'lim), yo quyidagi muhandislik taxminlari bilan yopildi (1-bo'lim). Foydalanuvchiga savol qolmadi.

Yangilanish (2026-09-09): foydalanuvchi qarori bilan panel qamrovi respublika darajasi deb belgilandi; 29, 30, 35, 36-taxminlar shunga moslandi.

Yangilanish 2 (2026-09-09, TZ va foydalanuvchi javoblari): manba ustuvorligi TZ; til o'zbek (lotin asosiy, kirill almashtirgich), rus keyin; F.I.Sh. barcha darajalarda ko'rinadi; video va foto prototipda simulyatsiya; ikkala daraja bitta ilovada; atama "yacheyka". 1, 15, 30, 34-taxminlar va 2-bo'limdagi 11, 12, 18-javoblar o'zgardi; 37-41 qo'shildi.

## 1. Muhandislik taxminlari (manbalarda raqam yoki qoida yo'q)

Har biri sozlama sifatida saqlanadi. Formati: taxmin, nima uchun xavfsiz, keyin o'zgartirish mumkin.

| № | Taxmin | Nima uchun xavfsiz | Keyin o'zgartirish mumkin |
|---|---|---|---|
| 1 | "xizmat holati" qiymatlari: faol, ta'tilda, kasallik, vaqtincha chetlashtirilgan, ishdan bo'shagan [TZ §6.1]; faqat "faol" kirishga ruxsat beradi | 01 §2.3 holatni kirish huquqi qismi deydi, ro'yxat bermaydi | enum kengaytiriladi, HR adapteridan keladi |
| 2 | Identifikatorlar (tabel raqami, seriya raqami, inventar raqami, karta UID, RFID EPC) erkin matn, tashkilot ichida noyob; nazorat raqami yo'q | 01 formatlarni bermaydi; buyurtmachi bazalari bilan integratsiya §4.6 | validatsiya qoidasi qo'shiladi |
| 3 | Shkaf raqami = ishlab chiqaruvchi seriya raqami (tizim beradi); inventar raqami ixtiyoriy; manzil = qurolxona + devor/qator + o'rin | 01 §3.4 raqam va manzilni alohida maydon deydi | format o'zgarsa jurnalga ta'sir yo'q (ichki ID) |
| 4 | Qaytarish muddati = tasdiqlangan navbat oxiri + 30 daqiqa; Navbatchi har berishda o'zgartira oladi | 01 §3.4 "belgilangan vaqt" deydi, qoidani bermaydi | grace vaqti sozlama |
| 5 | Rad etish sabablari: no_permit, outside_shift, status_inactive, unknown_card, biometric_mismatch, wrong_pin, cabinet_blocked, weapon_not_inspected, lockout, offline_no_cached_permit | 01 §2.5, §2.4, §4.4 tekshiruvlaridan kelib chiqadi | enum kengaytiriladi |
| 6 | Blokirovka: 3 muvaffaqiyatsiz urinish, 15 daqiqa, Navbatchiga xabar | 01 §3.4 urinishlar sonini qayd qiladi, chegara bermaydi | sozlama |
| 7 | Eshik ochiq qolishi: 60 s ogohlantirish, 180 s signal | 01 §3.4 signal turini beradi, raqam bermaydi | qurolxona bo'yicha sozlama |
| 8 | Qulf ochildi, eshik ochilmadi: 15 s dan keyin qayta qulf, hodisa | eshik qo'lda ochiladi [02 §5.4]; fail-secure | sozlama |
| 9 | Batareya past: 20 %; urilish chegarasi: 2 g; vazn og'ishi: 10 % | 03 batareya sig'imini beradi, chegara yo'q | sozlama |
| 10 | Vazn hech qachon o'q soni sifatida ko'rsatilmaydi, faqat "taxminiy" | 01 §4.3 vazn yuridik dalil emas | o'zgarmaydi |
| 11 | O'q-dori katalogiga 9×18 (PM) qo'shiladi | 03 da faqat 5,45×39; PM bor | tarkib buyurtmachidan [01 §5.1] |
| 12 | Body-kamera: 1450-1700 zonasida RFID belgili joy, zaryadlashsiz | 01 §2.3 seriya raqami bilan biriktiradi, joy yo'q | kit shablonida o'zgartiriladi |
| 13 | RFID: qurol, magazin, body-kamera; dubulg'a, bronjilet, gaz niqobi, kishan, sumka: inventar raqami + ixtiyoriy RFID | 01 §4.3 "muhim jihoz" deydi | jihoz bo'yicha bayroq |
| 14 | Ierarxiya: respublika, viloyat, tuman/shahar IIB yoki funksional bo'linma, qurolxona, terminal guruhi, shkaf | 01 §4.7 va §2.1 | tugun turlari qo'shiladi |
| 15 | Saqlash muddatlari TZ §10.1 bo'yicha: audit kamida 5 yil, video kamida 90 kun, foto kamida 1 yil, biometrik shablon xizmat davri + qonuniy muddat, konfiguratsiya 12 oylik versiyalar | TZ qiymatlari; yakuniy tasdiq buyurtmachidan [TZ §10.1] | sozlamalar ekranida |
| 16 | Favqulodda tasdiqlovchilar: 2 (ommaviy), 1 (bitta shkaf) | 01 §2.6 "zarur holatda ikki mas'ul shaxs"; soni buyurtmachidan [01 §5.1] | qurolxona bo'yicha sozlama |
| 17 | Karta UID shaffof satr; o'quvchi turi sozlama | karta texnologiyasi buyurtmachidan [01 §5.1] | adapter |
| 18 | Yig'ilish rejimi faqat navbat tekshiruvini yumshatadi; omillar saqlanadi; Trevoga = 01 §2.6 ommaviy ochish | 01 §4.2 da uchinchi profil yo'q; 06 faqat yuz yoki barmoq izidan keyin kirish deydi | tasdiqlovchilar va qamrov sozlama |
| 19 | Ko'rik/ta'mir holatini Qurolxona mas'uli qo'yadi va yechadi; davriy ko'rik intervali sozlama | 01 §4.4 blokni beradi, egasini bermaydi | ish jarayoni kengaytiriladi |
| 20 | Mexanik kalit: ochish buyrug'isiz eshik ochilishi = mexanik kalit; sabab kiritiladi; kalit egasi qurolxona atributi | 01 §1.4 alohida qayd talab qiladi, datchik turi yo'q | kalit datchigi qo'shilsa aniqroq |
| 21 | Offline: ruxsatlar keshi muddatsiz; qayta ulanganda bekor qilishlar birinchi; oraliq hodisalar bayroqlanadi | 01 "Offline ishlash" muddat bermaydi | TTL sozlama |
| 22 | Noto'g'ri jihoz qaytarilganda: nomuvofiqlik hodisasi, signal, inventar farqi; eshik baribir qulflanadi | 01 §2.5 "tekshiriladi" deydi | ish jarayoni |
| 23 | PIN kiritish: terminalda 12 tugmali muhrlangan klaviatura (simulyatorda virtual) | 03 displey sensorli emas, klaviatura yo'q | terminal dizayni |
| 24 | Transport: MQTT over TLS (mTLS), qurilma kaliti, tartib raqami, offline navbat; HTTP zaxira | 01 §4.7 faqat "aloqa moduli" va "shlyuz" deydi | RS-485 yoki Ethernet Sinovda |
| 25 | Vaqt: qurolxona kontrolleri NTP manbasi; UTC saqlanadi, Asia/Tashkent ko'rsatiladi; drift bayrog'i | 01 vaqt sinxronini bermaydi | sozlama |
| 26 | Kripto: SHA-256 + Ed25519, almashtiriladigan modul | O'zDSt talabi sertifikatlashda [01 §5.1] | algoritm almashtiriladi |
| 27 | LED: rad etish va signal uchun qizil miltillash; dashboardda qizil faqat signal | 03 da rad etish rangi yo'q | palitra sozlama |
| 28 | Umumiy terminal arxitekturasida har shkafda faqat RGB holat LED; matnlar terminalda | 01 §4.7 ekranni terminalga beradi | shkafga displey qo'shilsa |
| 29 | Sintetik flot butun respublika: 14 hudud, ≈5 500 shkaf, 30 kun, 4 hodisa/kun; kichik rejim 308 shkaf | 01 §3.1, §3.6 raqamlari; foydalanuvchi: panel respublika bo'yicha | seed parametrlari |
| 30 | Respublika va hudud dashboardlarida ham F.I.Sh. va tabel raqami ko'rinadi (davlat bo'yicha yagona asosiy dashboard); har ko'rish va eksport auditda; TZ §16 shaxssizlantirish faqat tashqi rahbariyat tizimlariga eksport uchun | foydalanuvchi qarori 2026-09-09; TZ §9 | eksportda shaxssizlantirish rejimi |
| 35 | Hududlar ro'yxati: Qoraqalpog'iston Respublikasi, Toshkent shahri va 12 viloyat (jami 14); xarita konturlari ochiq ma'lumotlardan soddalashtirilgan SVG | ma'muriy bo'linish; 01 xarita talab qilmaydi, faqat "hudud bo'yicha holat" | hudud ro'yxati sozlama, kontur almashtiriladi |
| 36 | Prototipda bitta respublika markaziy serveri; viloyat oraliq serverlari keyin (role=region) | 01 §4.7 "hudud/respublika" darajasini alohida server deb aytmaydi | Bosqich 3 da qo'shiladi |
| 37 | Server yo'q rejimi: kontroller keshdagi ruxsatlar bilan cheklangan rejimda ishlaydi; kesh bo'lmasa operatsiya bloklanadi; obyekt bo'yicha sozlama | TZ §7.3 ikkala variantni beradi | sozlama |
| 38 | Autentifikatsiya tartibi standart holatda TZ bo'yicha: yuz va/yoki barmoq izi (liveness); karta va PIN obyekt siyosatida qo'shimcha omil sifatida yoqiladi | TZ §6.2 ustun; 01 §4.2 karta | siyosat sozlamasi |
| 39 | Smena ochilishida o'z-tekshiruvda kritik xato bo'lsa operatsiyalar cheklanadi: faqat qaytarish va favqulodda tartib | TZ §7.1 "operatsiyalar chekLanadi" deydi, ro'yxat bermaydi | sozlama |
| 40 | Rol berish va bekor qilish ikkinchi tasdiq bilan: so'rov Administratordan, tasdiq boshqa Administrator yoki Qurolxona mas'ulidan; 24 soat ichida tasdiqlanmasa bekor | TZ §6.1 "kamida ikki shaxs" | rol va muddat sozlama |
| 41 | Kirill almashtirgich avtomatik transliteratsiya (lotin → kirill) va istisnolar lug'ati bilan; rus tili alohida i18n fayli sifatida keyin qo'shiladi | TZ §12; foydalanuvchi | tarjima jadvali |
| 31 | Oddiy xodim uchun web login yo'q | 01 §2.4 faqat o'z shkafi | "Mening shkafim" keyin |
| 32 | Inventarizatsiya: talab bo'yicha + sozlanadigan jadval | 01 §4.3 faqat "tez inventarizatsiya" | jadval sozlama |
| 33 | KPI "jami va mavjud qurollar" qurol turi bo'yicha (AK-74, PM) va jami | 01 §3.5 granularlikni bermaydi | vidjet sozlama |
| 34 | Kameralar va VMS TZ bo'yicha tizimning qismi; prototipda kamera holati va foto kadr simulyatsiya (o'rnida belgi), media_ref to'ldiriladi; ONVIF Profile T integratsiyasi Bosqich 3 | TZ §5.2, §6.2, §10.1; foydalanuvchi | real VMS ulanadi |

## 2. Manbada javobi bor (qayta so'ralmadi)

| № | Savol (qisqacha) | Javob (bir qator) | Manba |
|---|---|---|---|
| 1 | Simulyator va sintetik flot kerakmi, qaysi ko'lamda? | Ha: seed + simulyator; O'rtacha IIB 55 va Bitta kichik IIB 22 shkaf, 30 kun, 4 hodisa/kun, "SIMULYATSIYA" belgisi, is_simulated | [01 §3.1, §3.2, §3.6, §3.4] |
| 2 | Panel qulf ocha oladimi (bitta shkaf, Trevoga, ikkinchi tasdiq)? | Yo'q, hech biri. Panel bloklaydi, rejim yoqadi, oldindan ruxsat beradi, kuzatadi. Ochish terminalda: vakolatli karta + maxsus PIN | [01 §2.6, §4.2, §2.4, §4] |
| 3 | Birinchi demo uchun jismoniy stend shartmi? | Yo'q. Dasturiy simulyator yetarli. Stend Prototip bosqichida: fail-secure qulf, eshik/urilish/buzish datchiklari, zaxira quvvat, RFID + qisqich datchigi | [01 §3.2, §5, §1.4, §4.3; 02 §10] |
| 4 | Prototip ikki qatlam bo'lishi kerakmi? | Ha. Bitta kod, ikki rol (armory, central), WAN uzilishi va sinxron demosi | [01 'Offline ishlash', §4.5, §4.6, §4.7] |
| 5 | Qaysi rol ekranlari birinchi, mock kerakmi? | Ishlaydigan prototip, mock yo'q. Tartib: Qurolxona mas'uli, Jurnal, Dashboard (Demo 1); Navbatchi, Administrator (Demo 2) | [01 §2.3, §2.4, §3.2, §4, §5; 02 §3; 03] |
| 6 | 3D jonli egizakmi yoki 2D sxema? | 2D uya sxemasi jonli (5 zona); 3D alohida tab, metall eshik (05: WINDOWS={}), gabarit izohi 2000 × 400 × 600 | [01 §1.2, §1.5, §3.3, §3.4; 05] |
| 7 | Terminal sotib olinadimi, qurilinadimi; shablonlar qayerda? | Quriladi (mahalliy modul). Shablonlar terminal/qurolxona kontrollerida shifrlangan; markazda holat + shifrlangan escrow; ro'yxatga olish faqat terminalda | [01 §4.6, §4.7, §3.6, §2.4, §3.3] |
| 8 | Rasmiy IIV jurnal shakli va E-IMZO kerakmi? | Prototipda yo'q. Umumiy A4 PDF/XLSX, imzo qatorlari, hash. Rasmiy shakl va E-IMZO buyurtmachi bilan TZda | [01 §5.1, §3.4, §2.6, §4.5, §4.6] |
| 9 | Сбор va Тревога qanday ishlaydi? | Yig'ilish = vaqtinchalik vakolat oynasi, omillar o'zgarmaydi. Trevoga = 01 §2.6 ommaviy ochish, terminaldan, alohida jurnal. Tasdiqlovchilar soni sozlama | [01 §2.4, §2.5, §2.6, §4.2; 06] |
| 10 | Xodim va navbat ma'lumotlarini tizim o'zi saqlaydimi? | Ha. Navbat = Navbatchi tasdiqlagan vaqt oynasi; qaytarish muddati = oyna oxiri; kechikish signali Qurolxona mas'uliga; HR/navbatchilik API keyin | [01 §2.3, §2.4, §2.5, §3.4, §4.4, §4.5, §3.2] |
| 11 | Ichki kamera va yuz surati kerakmi? | TZ bo'yicha ha: kameralar va VMS tizimning qismi, hodisaga video havola va foto kadr; prototipda simulyatsiya, ONVIF Bosqich 3 | [TZ §5.2, §6.2, §10.1; foydalanuvchi] |
| 12 | Panelga kirish: lokal akkaunt, ikkinchi omil, AD/LDAP? | Lokal akkauntlar; Administrator, Tekshiruvchi va vakolatli rollar uchun MFA (karta + maxsus PIN yoki TOTP) [TZ §9]; katalog xizmati (AD/LDAP) keyingi adapter [TZ §16] | [01 §2.4, §2.6, §4.2, §4.6, §5.1, §3.2] |
| 13 | Offline ishlash muddati va HR o'zgarishi? | Cheksiz. HR o'zgarishi lokal blok bilan bajariladi (Qurolxona mas'uli, Navbatchi). Quvvat yo'qolsa fail-secure | [01 'Offline ishlash', §2.4, §4.6, §4.7, §1.4; 06] |
| 14 | Jurnal yaxlitligi: server hash zanjiri yetarlimi, O'zDSt kerakmi? | Ikkalasi: server hash zanjiri + kontroller imzosi. Administratorga ham yozish huquqi yo'q. O'zDSt sertifikatlashda, kripto moduli almashtiriladigan | [01 §4.5, §2.4, §2.6, §5.1; 03 aside 'Xavfsizlik'; 06] |
| 15 | "Inventarizatsiyadagi farqlar" nima? | Ikkalasi: jonli farqlar (datchik va profil) + Qurolxona mas'uli sessiyasi va imzolanadigan akt; KPI = yechilmagan farqlar | [01 §2.4, §3.4, §3.5, §4.3, §1.3] |
| 16 | O'q-dori hisobi darajasi? | Quti va pachka (muhrlangan birlik) darajasida; soni faqat qayta ro'yxat bilan o'zgaradi; vazn taxminiy | [01 §2.3, §3.4, §4.3, §3.6; 02 §5.3; 03] |
| 17 | Laboratoriyada Wi-Fi mumkinmi? | Ha. Qurolxona tarmog'i buyurtmachi savoli; shlyuz transport-agnostik | [01 §3.2, §5.1, §4.7; 03 aside 'Aloqa va EMC'] |
| 18 | UI tili? | O'zbek: lotin asosiy, kirill almashtirgich; rus tili keyingi bosqichda (TZ §12 kirill va rus talab qiladi) | [TZ §12; foydalanuvchi 2026-09-09] |
| 19 | Mobil ogohlantirish kerakmi? | Yo'q. Desktop panel va sahifa ichi signal; qorovul posti relesi; push/SMS yo'q | [01 §3.2, §3.4, §3.5, §4.7, §1.3, §5.1; 02 §6] |
| 20 | Shkaf raqami tizimdan yoki qo'lda? | Seriya raqami tizimdan; inventar raqami qo'lda, ixtiyoriy; manzil alohida | [01 §3.4, §2.3, §3.1, §4.5, §4.6] |

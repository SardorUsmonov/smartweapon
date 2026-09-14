# Admin panel arxitekturasi (taklif)

Qabul qilingan standart qarorlar: Python FastAPI; SQLite prototipda, PostgreSQL pilotda; web dashboard o'zbek tilida; offline-first lokal server qurolxonada; har shkafda ESP32; qurolxonada Raspberry Pi; fail-secure qulf va mexanik kalit. Arxitektura 01 §4.7 dagi 5 darajaga mos.

## 1. Tamoyillar

| Tamoyil | Amalga oshirish | Manba |
|---|---|---|
| 5 daraja | shkaf, terminal guruhi (10-20), qurolxona, tashkilot serveri, hudud/respublika | [01 §4.7] |
| Offline-first | qurolxona kontrolleri ruxsatlar snapshoti va hodisalar keshini saqlaydi; markaz keyin sinxronlanadi | [01 'Offline ishlash', §4.5] |
| Panel qulf ochmaydi | server buyruqlari faqat cheklash va sozlash; ochish terminalda | [01 §2.6, §4.2] |
| Audit o'chirilmaydi | append-only, hash zanjiri, kontroller imzosi | [01 §4.5; 06] |
| Mahalliy server | bulut yo'q, tashqi resurs yo'q | [01 §3.6, §4.6] |
| Bitta kod, ikki rol | FastAPI ilovasi role=armory va role=central sifatida ishga tushadi | (C) javobi, ikki qatlam |
| Respublika qamrovi | role=central = IIV dagi respublika markaziy serveri; ierarxiya (respublika, 14 hudud, bo'linma, qurolxona, terminal guruhi, yacheyka) ma'lumotlar bazasida; hudud = vakolat doirasi filtri va yig'ma; keyin ixtiyoriy viloyat tugunlari (role=region) sinxron zanjirida | [01 §4.7; foydalanuvchi 2026-09-09] |
| TZ ustuvor | "Aqlli qurolxona" TZ v1.0 talablari 01 dan ustun; role=armory TZ dagi lokal server va operator konsoli vazifasini bajaradi (smena tartibi, monitoring, VMS holati, zaxira nusxa) | [TZ §5, §7, §10; foydalanuvchi] |
| Atama | interfeysda "yacheyka" = bir xodimning shkafi; ichki qulflar "bo'lim" | [TZ §3; foydalanuvchi] |
| Til | o'zbek lotin asosiy, kirill almashtirgich; rus keyin | [TZ §12; foydalanuvchi] |

## 2. Komponent diagrammasi (matn)

```
[Web UI, o'zbek lotin]  (brauzer, IIV tarmog'i: markaziy apparat, viloyat IIB, tuman IIB)
        |  HTTPS + WebSocket /ws/live
        v
[Respublika markaziy serveri, IIV Toshkent]  FastAPI role=central
   - markaziy MB (SQLite -> PostgreSQL), ierarxiya: respublika, 14 hudud, bo'linma, qurolxona, terminal guruhi, shkaf
   - ruxsatlar, biriktirish, inventar, custody
   - jurnal (append-only, hash zanjiri), favqulodda jurnali
   - dashboard agregatlari (soatlik, kunlik; hudud, bo'linma, qurolxona bo'yicha), xarita KPI, hisobotlar, saqlash siyosati
   - vakolat doirasi = ierarxiya tuguni bo'yicha filtr (respublika, hudud, bo'linma, qurolxona)
        ^  /sync (idempotent, tartib raqami bilan)      |  ruxsatlar snapshoti (versiya)
        |  WAN: IIV tarmog'i, LTE zaxira; uziladigan     v
        |  (Bosqich 3+: ixtiyoriy viloyat tuguni role=region shu yerda oraliq bo'lishi mumkin)
[Qurolxona kontrolleri] x M (respublika bo'ylab yuzlab)  Raspberry Pi, FastAPI role=armory
   - SQLite: ruxsatlar keshi (TTL yo'q), hodisalar keshi (chiquvchi navbat)
   - avtorizatsiya qarori: karta/Face ID + barmoq/PIN + navbat + ruxsat + xizmat holati
   - MQTT broker (TLS) yoki HTTP; NTP manbasi; UPS (SNMP) holati; qorovul posti relesi
   - obyekt qurilmalari monitoringi: kameralar (ONVIF, prototipda simulyatsiya), PoE kommutator (SNMPv3), NAS
   - smena tartibi (ochish: o'z-tekshiruv va solishtiruv; yopish: hisobot), zaxira nusxalash jadvali
   - imzolangan buyruqlar: bloklash, ushlab turish, rejim, self-test, vaqt, displey matni
        |  MQTT: shkaf/{id}/event, shkaf/{id}/state, shkaf/{id}/cmd
        v                                   v
[Terminal, 10-20 shkafga]           [Shkaf kontrolleri, ESP32] x N
   - Face ID, barmoq izi, karta,       - eshik qulfi, stvol qulfi, PM qutisi,
     PIN, 3,5" displey, LED               o'q-dori kamari, magazin uyasi
   - biometrik shablonlar (shifrlangan)  - eshik, akselerometr, tamper, qisqich,
   - faqat autentifikatsiyalangan signal   bosim, RFID, vazn, quvvat datchiklari
                                         - mahalliy hodisa buferi, tartib raqami
[Simulyator]  (prototipda terminal va ESP32 o'rnida, xuddi shu protokol)
```

Manba: [01 §4.7, §3.3; 03 aside 'Xavfsizlik']. Prototipda ikkala rol laboratoriya kompyuterida ikki jarayon sifatida ishlaydi. WAN "uzildi/ulandi" tugmasi qurolxona rolida.

## 3. Ma'lumotlar bazasi

| Guruh | Jadvallar | Qayerda |
|---|---|---|
| Ierarxiya | hudud (14 ta, kod, xarita konturi identifikatori), tashkilot, qurolxona, terminal_guruhi | markaz; qurolxonaga snapshot |
| Agregatlar | kpi_soatlik, kpi_kunlik (tugun, davr, 9 KPI); respublika va hudud dashboardlari faqat shulardan o'qiydi; hodisa kelganda inkremental yangilanadi | markaz |
| Xodim | xodim, yaroqlilik, kredensial, qurol_ruxsati, navbat, panel_foydalanuvchi, rol_biriktirish | markaz; qurolxonaga snapshot |
| Shkaf | shkaf, biriktirish_tarixi, kontroller, qulf, datchik, uya, uya_shabloni | markaz; qurolxonaga snapshot |
| Inventar | qurol, magazin, oq_dori, jihoz, kit_shabloni | markaz; qurolxonaga snapshot |
| Hodisalar | hodisa (append-only, daraja INFO/WARNING/CRITICAL/SECURITY, foto va video havola), custody, favqulodda_jurnali, signal, rejim, sinxron_holati | qurolxonada yaratiladi, markazga ko'chadi |
| Smena va eksport | smena (ochilish, o'z-tekshiruv natijasi, solishtiruv, ruxsat ro'yxati tasdig'i, yopilish, hisobot), eksport_jurnali (raqam, kim, qachon, hisobot, maqsad, muddat, hash) | qurolxona; markazga ko'chadi |
| Qurilmalar | qurilma (turi: yacheyka kontrolleri, terminal, kamera, kommutator, UPS, NAS, server), qurilma_holati (CPU, RAM, disk, oqim, batareya, NTP), zaxira_nusxa (tur, vaqt, hajm, natija, tiklash sinovi) | ikkalasi |
| Inventarizatsiya | sessiya, qator, farq, akt | markaz |
| Siyosat | auth_siyosati, saqlash_muddati, chegaralar, sozlama_auditi | markaz |
| Simulyatsiya | is_simulated bayrog'i barcha jadvallarda; purge buyrug'i | ikkalasi |

SQLite dan PostgreSQL ga o'tish: SQLAlchemy modellari va Alembic migratsiyalari; hodisa jadvali sana bo'yicha bo'linadi; kunlik agregat jadval dashboard uchun (7 300 000 hodisa/yil, 01 §3.6).

## 4. Hodisa sxemasi (JSON namuna)

```json
{
  "event_id": "9f0c1e2a-6b3d-4a1e-9c47-2d3f5e6a7b8c",
  "schema": "1.0",
  "type": "AVTOMAT_OLINDI",
  "hudud": "Toshkent shahri",
  "tashkilot": "Yunusobod tuman IIB",
  "qurolxona_id": "QX-YUN-01",
  "terminal_id": "T-01",
  "shkaf_id": "SHK-2026-0007",
  "kontroller_seq": 4711,
  "qurilma_vaqti": "2026-09-09T08:12:31+05:00",
  "server_vaqti": null,
  "sessiya_id": "S-20260909-0007-03",
  "xodim": {"tabel_raqami": "12345", "kirish_usuli": "KARTA+BARMOQ"},
  "ruxsatlar": ["AVTOMAT", "TO'PPONCHA"],
  "jihoz": {"turi": "qurol", "modeli": "AK-74", "seriya_raqami": "1234567", "rfid": "E2000017221101441890A1B2", "uya": "AK_UYASI"},
  "signallar": {"rfid_bor": false, "qisqich": "ochiq", "qondoq_bosimi": false, "ishonch": 3},
  "holat_snapshot": {"eshik": "ochiq", "eshik_qulfi": "ochiq", "stvol_qulfi": "ochiq", "pm_qutisi": "qulf", "oq_dori_kamari": "qulf", "magazin_uyasi": "qulf", "mains": true, "batareya_pct": 100, "harorat_c": 21.5},
  "custody": {"olingan": "2026-09-09T08:12:31+05:00", "qaytarish_muddati": "2026-09-09T20:30:00+05:00"},
  "offline": false,
  "rejim_id": null,
  "media_ref": null,
  "prev_hash": "sha256:5b7c…",
  "hash": "sha256:a91e…",
  "kontroller_imzosi": "ed25519:MEUCIQ…",
  "is_simulated": true
}
```

Hodisa turlari 4-bo'lim katalogidan (talablar hujjati). Rad etish namunasi uchun maydonlar: `kim`, `sabab` (no_permit, outside_shift, status_inactive, unknown_card, biometric_mismatch, wrong_pin, cabinet_blocked, weapon_not_inspected, lockout, offline_no_cached_permit), `urinishlar_soni` [01 §3.4].

Buyruq sxemasi (server dan qurolxona kontrolleriga, imzolangan):

```json
{
  "command_id": "c-20260909-0012",
  "type": "SHKAF_BLOKLASH",
  "shkaf_id": "SHK-2026-0007",
  "berdi": {"tabel_raqami": "20001", "rol": "QUROLXONA_MASULI"},
  "sabab": "nosozlik",
  "nonce": "b2f1…",
  "muddat": "2026-09-09T08:20:00+05:00",
  "server_imzosi": "ed25519:…"
}
```

Buyruq turlari: SHKAF_BLOKLASH, BLOKDAN_CHIQARISH, RUXSAT_SNAPSHOT, JIHOZ_USHLAB_TURISH, REJIM (yig'ilish, trevoga, normal), FAVQULODDA_SO'ROV (terminalda bajariladi), VAQT_SINXRON, SELF_TEST, INVENTAR_SKAN, DISPLEY_XABAR, PROSHIVKA, ENROLL (terminalga). Qulf ochish buyrug'i yo'q [01 §2.6, §4.2].

## 5. API ro'yxati

| Usul va yo'l | Vazifasi | Rol |
|---|---|---|
| POST /api/auth/login, /logout | login + parol, keyin karta + maxsus PIN (vakolatli rollar) | barcha |
| GET /api/dashboard/kpi?scope= | 9 KPI; scope = respublika, hudud, bo'linma, qurolxona tuguni | barcha |
| GET /api/dashboard/map?scope= | xarita uchun: har hudud (yoki bo'linma) bo'yicha KPI, holat rangi, oflayn qurolxonalar soni | barcha |
| GET /api/hierarchy/tree; GET /api/hierarchy/{id}/children | respublika, hudud, bo'linma, qurolxona daraxti; drill-down va breadcrumb | barcha |
| GET /api/dashboard/compare?scope=&metric= | hududlar yoki bo'linmalarni KPI bo'yicha taqqoslash va saralash | rahbariyat, tekshiruvchi |
| GET /api/dashboard/readiness?scope= | kim qurollangan, kim yo'q | barcha |
| GET, POST /api/officers; GET, PUT /api/officers/{id} | xodimlar | Qurolxona mas'uli, Administrator |
| PUT /api/officers/{id}/eligibility | 5 shart | Qurolxona mas'uli |
| POST /api/officers/{id}/credentials | karta, PIN, enroll so'rovi | Administrator |
| GET, POST /api/permissions; POST /api/permissions/temporary | AVTOMAT, TO'PPONCHA; vaqtinchalik vakolat | Navbatchi yoki komandir |
| GET, POST /api/shifts; POST /api/shifts/{id}/confirm | navbat, xizmat ruxsati tasdig'i | Navbatchi yoki komandir |
| POST /api/armory/{id}/shift/open (o'z-tekshiruv + solishtiruv + ruxsat ro'yxati); POST /api/armory/{id}/shift/close (qaytarilmaganlar, tasdiq, smena hisoboti) | smena tartibi [TZ §7.1, §7.4] | Navbatchi/operator, Qurolxona mas'uli |
| GET /api/backups; POST /api/backups/run; POST /api/backups/restore-test | zaxira nusxalash [TZ §10.3] | Administrator |
| GET /api/exports; har hisobot eksporti maqsad va muddat bilan | eksport jurnali [TZ §9, §12] | Administrator, Tekshiruvchi |
| POST /api/roles/grant-requests; POST .../{id}/approve | rol berishga ikkinchi tasdiq [TZ §6.1] | Administrator (so'rov), ikkinchi vakolatli shaxs |
| GET, POST /api/cabinets; GET /api/cabinets/{id}; GET /api/cabinets/{id}/state | shkaflar, jonli holat | barcha |
| POST /api/cabinets/{id}/assign, /unassign, /block, /unblock | biriktirish, bloklash | Qurolxona mas'uli |
| GET, PUT /api/cabinets/{id}/slots | uya shabloni | Qurolxona mas'uli |
| GET, POST /api/items; PUT /api/items/{id}; POST /api/items/{id}/hold, /release | inventar, ushlab turish | Qurolxona mas'uli |
| GET /api/items/{id}/custody | chain of custody | barcha |
| GET /api/custody/open; GET /api/custody/overdue | berilgan, kechikkan | barcha |
| GET /api/events?filters; GET /api/events/{id}; GET /api/events/verify?from&to | jurnal, yaxlitlik | barcha |
| GET /api/emergency-journal | favqulodda jurnali | barcha |
| GET /api/alarms; POST /api/alarms/{id}/ack, /resolve | signal markazi | Qurolxona mas'uli, Navbatchi |
| POST /api/modes; POST /api/modes/{id}/stop; GET /api/modes/active | Yig'ilish, Trevoga | Navbatchi yoki komandir |
| POST /api/emergency/requests; GET /api/emergency/requests/{id} | so'rov, tasdiqlovchilar, jarayon | Navbatchi, Qurolxona mas'uli |
| POST /api/inventory/sessions; POST .../{id}/lines; POST .../{id}/close; GET /api/inventory/discrepancies | inventarizatsiya | Qurolxona mas'uli |
| GET /api/reports/{jurnal, statistika, kechikish, favqulodda, inventar_farqlari}?format=pdf,xlsx,csv | hisobotlar | barcha |
| GET, PUT /api/settings/{auth-policy, thresholds, retention, integrations}; GET /api/settings/audit | sozlamalar va audit | Administrator |
| GET, POST /api/users; GET, PUT /api/roles | foydalanuvchilar | Administrator |
| GET /api/devices/tree; GET /api/devices/{id}/health; POST /api/devices/{id}/{self-test, time-sync, firmware, maintenance} | qurilmalar | Administrator |
| POST /sync/events (batch, idempotent: shkaf_id + seq); GET /sync/permissions?since=version; POST /sync/ack | qurolxona va markaz | tizim |
| MQTT shkaf/{id}/event, shkaf/{id}/state, shkaf/{id}/cmd; HTTP zaxira POST /device/events | shkaf va qurolxona | tizim |
| POST /sim/cabinets/{id}/{face, finger, card, pin, select_take, select_return, door_open, door_close, take, return, impact, tamper, lock_fault, sensor_fault, power_loss, power_restore}; POST /sim/armory/{id}/{camera_down, camera_up, ups_low, disk_full, ntp_drift, server_down, server_up}; POST /sim/wan/{cut, restore}; POST /sim/seed; POST /sim/purge | simulyator | taqdimotchi |
| WS /ws/live | jonli yangilanishlar | barcha |

## 6. Xavfsizlik

| Chora | Mazmuni | Manba |
|---|---|---|
| Transport | mTLS; har qurilmaga alohida kalit, ishga tushirishda beriladi | taxmin; [03 aside 'Xavfsizlik'] |
| Buyruq | imzo, nonce, muddat; kontroller takrorlashni rad etadi | [03 aside 'Xavfsizlik'; 02 §5.4] |
| Jurnal | shkaf oqimi bo'yicha hash zanjiri; kontroller imzolagan paketlar; kunlik server imzosi; hech bir rolga UPDATE/DELETE yo'q | [01 §4.5, §2.6; 06] |
| RBAC | 5 rol; vakolat doirasi; Administrator qurol vakolatisiz | [01 §2.4, §4.7] |
| Biometrika | shablon terminalda shifrlangan; markazda holat + escrow; panelda ko'rinmaydi | [01 §3.6, §5] |
| Panel kirishi | shaxsiy lokal akkauntlar; Administrator, Tekshiruvchi va vakolatli rollar uchun MFA (karta + maxsus PIN yoki TOTP); parol siyosati, xato urinishlar bloki, sessiya taym-auti, bo'shagan xodimni darhol bekor qilish; harakat oldidan qayta tasdiqlash | [TZ §9; 01 §2.6, §4.2] |
| Eksport nazorati | maqsad va muddat majburiy; raqam, vaqt, shaxs, hash; eksport jurnali; SECURITY darajali hodisa | [TZ §9, §12] |
| Qurilmalarni mustahkamlash (Bosqich 3) | zavod parollari, keraksiz portlar, imzolangan yangilanishlar, USB cheklovi, syslog SIEM ga | [TZ §9, §16] |
| Kripto | SHA-256 + Ed25519 bitta modulda; O'zDSt algoritmlari sertifikatlashda almashtiriladi | [01 §5, §5.1] |
| Sintetik ma'lumot | is_simulated bayrog'i, "SIMULYATSIYA" belgisi, rasmiy hisobotdan chiqariladi, purge | [01 §3.1; 06] |

## 7. Simulyator

| Xususiyat | Mazmuni |
|---|---|
| Protokol | real ESP32 va terminal protokoli (MQTT/HTTP), xuddi shu hodisa sxemasi |
| Ssenariy | 01 §2.5 qadamlari: karta, barmoq izi yoki PIN, navbat va ruxsat tekshiruvi, shkaf ochildi, AK/PM olindi (datchik), qaytarish tekshiruvi, avtomatik qulf |
| Holatlar | 03 dagi idle, face, finger, ok, open, lock; qo'shimcha: operatsiya tanlash (olish/qaytarish) [TZ §6.3], karta, pin, rad_etildi (foto kadr belgisi bilan), bloklangan, signal, offline, server_yoq, favqulodda |
| Nosozliklar | rad etish, kechikish, eshik ochiq qoldi, urilish, buzish, quvvat uzilishi, UPS batareyasi past, WAN uzilishi, server yo'q, noto'g'ri jihoz, qulf xatosi, datchik xatosi, kamera oqimi uzilishi, disk to'lishi, vaqt sinxroni buzilishi [TZ §6.4, §7.3, Ilova B] |
| Seed | 1 real "Laboratoriya" qurolxonasi (1-2 shkaf, Toshkent shahri) + sintetik respublika: 14 hudud, har hududda 3-6 tuman/shahar IIB va 1-2 funksional bo'linma, har birida 1 qurolxona 22-55 shkaf bilan, jami ≈5 500 shkaf (birinchi respublika bosqichi), 30 kun tarix, 4 hodisa/kun; kichik rejim 14 × 22 = 308 shkaf [01 §3.1, §3.6; foydalanuvchi] |
| Hududlar | Qoraqalpog'iston Respublikasi, Andijon, Buxoro, Farg'ona, Jizzax, Namangan, Navoiy, Qashqadaryo, Samarqand, Sirdaryo, Surxondaryo, Toshkent viloyati, Xorazm, Toshkent shahri |

## 8. Bosqichma-bosqich reja

| Bosqich | Nima quriladi | Demo nimani ko'rsatadi |
|---|---|---|
| Bosqich 1: Demo 1 (ichki) | FastAPI ikki rol (armory, central), SQLite ikkalasida; ma'lumotlar modeli ierarxiya bilan (respublika, 14 hudud, bo'linma, qurolxona); simulyator: 1-2 jonli shkaf + sintetik respublika floti; Respublika dashboardi (O'zbekiston xaritasi, 9 KPI, hududlar jadvali, drill-down hudud → bo'linma → qurolxona → shkaf); Qurolxona mas'uli ekranlari (xodim, yaroqlilik, biriktirish, bloklash, inventar); jurnal (append-only, hash) va favqulodda jurnali; readiness; rol almashtirgich (respublika, hudud, qurolxona darajalari); WAN uzish tugmasi; smena ochish va yopish vizardi [TZ §7.1, §7.4]; signal markazi 4 daraja bilan (INFO, WARNING, CRITICAL, SECURITY); zaxira nusxa holati; interfeys o'zbek lotin, kirill almashtirgich; atama "yacheyka" | respublika xaritasida jonli holat; hududga kirib qurolxona va shkafgacha borish; to'liq 01 §2.5 ssenariysi jonli shkafda; rad etish va kechikish; WAN uzilganda ishlash va keyin sinxron; KPI jonli yangilanishi |
| Bosqich 2: Demo 2 (ichki, TZ uchun material) | Navbatchi ekranlari (navbat, vaqtinchalik vakolat, favqulodda so'rov, Yig'ilish/Trevoga); Administrator (foydalanuvchilar, sozlamalar, audit); signal markazi va ack; inventarizatsiya sessiyasi va akt; hisobot eksporti PDF/XLSX/CSV hash bilan; hududlar va bo'linmalar taqqoslash hisoboti; 2D raqamli egizak; 3D tab metall eshik bilan (05: WINDOWS={}); "Yaxlitlikni tekshirish"; ekran katalogi eksporti | 9 KPI to'liq; Trevoga rejimi va shkaf tasdiqlari; inventar farqlari; hisobot chop etish; hudud bo'yicha holat |
| Bosqich 3: Sinov tayyorgarligi | PostgreSQL markazda; armory roli Raspberry Pi da; ESP32 stend (fail-secure eshik qulfi + rid datchik + stvol qisqichi + 1 RFID jihoz); terminal adapteri (enroll, natija); mTLS va kalit berish; integratsiya adapterlari: ONVIF Profile T kameralar (VMS), SNMPv3 kommutator va UPS, syslog SIEM ga, HR, navbatchilik, kirish nazorati, tashvish paneli quruq kontakt [TZ §8, §16]; rus tili; saqlash muddatlari va tasdiqlovchilar soni sozlamalari buyurtmachi qiymatlari uchun | real stendda bitta shkaf: karta + barmoq izi, eshik ochildi, avtomat olindi (2 signal), qaytarildi, avtomatik qulf; qolgani simulyatorda |

Bosqich 3 dan keyin Sinov bosqichi: bitta qurolxona, 10-20 shkaf, real jarayon [01 §3.2].

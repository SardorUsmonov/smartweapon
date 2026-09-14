# TZ bilan moslik tekshiruvi (kod bo'yicha)

Sana: 2026-09-14. Manba: `docs/manbalar/Aqlli_qurolxona_TZ_v1.0.md` (v1.0, kelishish uchun loyiha). Tekshirilgan kod: `admin-panel/app/` (2026-09-14 15:44 holati). Usul: har bir TZ bandi kodda fayl va qator bilan tasdiqlandi; README, DEV_GUIDE va 05–12 hujjatlardagi da'volar dalil sifatida olinmadi. Uch parallel tekshiruv agenti + asosiy agentning tanlab tekshiruvi.

Holat belgilari: **MOS** — ilovada haqiqiy mantiq ishlaydi; **QISMAN** — bir qismi bor; **SIMULYATSIYA** — apparat o'rnida dasturiy stub, real tekshiruv yo'q; **YO'Q** — kodda yo'q; **APPARAT** — TZ bandi dasturga tegishli emas (montaj, kabel, sertifikat va h.k.).

## 1. Umumiy xulosa

Panel TZ ning **tuzilmasi** bo'yicha ko'tarilgan: 5 rol, 4 hodisa darajasi (INFO/WARNING/CRITICAL/SECURITY), 7 hisobot va 3 eksport formati, smena ochish/yopish vizardi, append-only hash zanjirli jurnal, eksport raqami/maqsadi/muddati, haqiqiy SQLite zaxira va alohida faylga tiklash, ikkinchi administrator tasdig'i, sozlamalar auditi. Bu qism TZ ga mos.

Lekin TZ ning **xatti-harakat** talablarining katta qismi yoki simulyatsiya, yoki "e'lon qilingan, ammo ishlamaydigan" holatda:

- sozlamalar bazada saqlanadi, lekin hech qaysi kod ularni o'qimaydi (`qulf_qayta_s`, `eshik_ochiq_*_s`, `rad_blok_urinish`, `batareya_past_pct`, saqlash muddatlari);
- holatlar e'lon qilingan, lekin hech qachon o'rnatilmaydi (`terminal_state` = `face`, `finger`, `ok`; tamper holati);
- hodisa turi bor, lekin hech qayerda yozilmaydi (`favqulodda_ochish`, `Event.offline=True`, `media_ref`);
- MFA demo konstantasi (`123456`), TLS yo'q, shifrlash yo'q, parol almashtirish yo'li yo'q.

TZ §5, §8, §13, §14, §15, §17, §19, §20 (apparat, montaj, kabel, o'qitish, kafolat) dasturga tegishli emas va prototipda bo'lishi kutilmaydi.

Qisqa javob: **prototip TZ ning "nima bo'lishi kerak" ro'yxatini ekranlar va jadvallar sifatida qamrab olgan, lekin TZ ning "qanday ishlashi kerak" talablarining taxminan yarmi hali dasturda amalga oshirilmagan.**

## 2. TZ bo'limlari bo'yicha jadval

| TZ | Mavzu | Holat | Izoh |
|---|---|---|---|
| §4.2 | Rollar | QISMAN | 5 rol bor (`app/deps.py:14-17`); harbiy xizmatchi panel foydalanuvchisi emas (TZ ga mos, u terminalda). Qurolxona mas'uli "shtat hisobini yuritishi" kerak — xodim yaratish/tahrirlash yo'li yo'q. Shaxsiy ma'lumotni ko'rish auditga yozilmaydi. |
| §5.1 | Lokal, offline-first arxitektura | SIMULYATSIYA | `AQ_ROLE=armory` faqat baza fayl nomini o'zgartiradi (`app/config.py:13-14`). Kontrollerdan hodisa qabul qiladigan kanal (MQTT/HTTP) yo'q. Offline bufer: `pending_events` simulyatorda 0 ga tenglashtiriladi (`app/services/sim.py:185,189`). |
| §6.1 | Ro'yxatga olish va huquq | QISMAN | Xodim kartasi maydonlari to'liq (`app/models.py:88-100`). Bloklash (ta'til, kasallik) qo'lda ishlaydi va olishni rad etadi (`sim.py:41-42`). Navbat oynasi tekshirilmaydi (`Shift` sim.py da so'ralmaydi). Bir xodim = bir katak faqat ilova darajasida, bazada unique yo'q (`models.py:64`). Ikki shaxs tasdig'i — MOS (`settings_svc.py:140-206`). |
| §6.2 | Qurolni olish | SIMULYATSIYA | Ruxsat tekshiruvlari haqiqiy (holat, muddat, permit, 5 yaroqlilik sharti — `sim.py:38-57`). Biometrika stub (`method="YUZ+BARMOQ"` matn). Qulf qisqa vaqtga ochilishi — taymer yo'q, butun ssenariy bitta so'rovda. Datchiklar tasdig'i — simulyator yozadi, o'qimaydi. Kamera havolasi (`media_ref`) hech qachon yozilmaydi. |
| §6.3 | Qurolni qaytarish | QISMAN | Qaytarishda hech qanday cheklov tekshirilmaydi (`sim.py:96-102`). "Eshik yopilmasa operatsiya ochiq qoladi" — yo'q, doim yopiq deb yoziladi (`sim.py:120-122`). Nomuvofiqlik CRITICAL signal — MOS; kechikish WARNING — MOS (12 s 30 daq demo qiymati). |
| §6.4 | Real vaqt monitoringi | QISMAN | Katak: qulf xatosi/datchik xatosi bitta `nosoz` holatiga yig'iladi; tamper holati yo'q (faqat hodisa). Xodim holatlari — MOS/QISMAN (kechikish faqat kartada). Qurilmalar: CPU/RAM/disk/UPS/kamera — MOS; NTP seed qilinmagan. Rang + ovoz (CRITICAL/SECURITY) + tasdiq kartasi — MOS (`app.js:41-51`). |
| §6.5 | Hisobotlar | QISMAN | 7 hisobot, 3 format — MOS. Filtrlar faqat sana + hudud + bo'linma (`hisobot_svc.py:161-209`); TZ dagi shaxs, holat, smena, toifa, ustuvorlik, administrator, obyekt, davr, qurilma filtrlari yo'q. "Qurol olmaganlar" ro'yxati yo'q. Hududiy foydalanuvchi uchun admin harakatlari hisoboti `SettingsAudit` ni tashlab ketadi (`:400`). |
| §6.6 | Yig'ilish/trevoga | QISMAN | Ikkinchi tasdiqlovchi + sabab — MOS; boshlanish/tugash SECURITY/INFO — MOS; guruh ochish yo'q (TZ ga mos). O'rtacha vaqt tasodifiy son (`sim.py:233`); qaytarilmagan inventar rejim ekranida yo'q. `Armory.approvers_required=2` hech qayerda tekshirilmaydi. |
| §7.1 | Smena boshlanishi | QISMAN | 7 bandli o'z-tekshiruv — MOS (`smena_svc.py:97-141`). Kritik xato operatsiyalarni cheklamaydi: sabab yozib smena ochiladi (`qurolxonalar.py:174-175`). Inventar nomuvofiqligi akt/signal yaratmaydi (faqat checkbox + JSON). Vaqtinchalik cheklovlar vizardda tahrirlanmaydi. |
| §7.3 | Nostandart holatlar | SIMULYATSIYA | Barcha holatlar simulyator tugmalari orqali. Biometrik rad — WARNING, signal yo'q, foto yo'q. Tarmoq uzilishi — `offline` belgili hodisa yozilmaydi. Mexanik kalit — ikki shaxs, plomba, akt maydonlari yo'q. `favqulodda_ochish` hech qayerda yozilmaydi (4 modul uni so'raydi). |
| §7.4 | Smena yakunlanishi | QISMAN | Qaytarilmaganlar va ochiq signallar avtomatik — MOS; hisobot raqami — MOS. Elektron tasdiq — matn maydoni (≥3 belgi). Sessiya smena yopilganda yopilmaydi. Zaxira holati va UPS ogohlantirishlari yopish vizardida ko'rsatilmaydi. |
| §9 | Kirish | QISMAN | Shaxsiy hisoblar, PBKDF2, xato urinish bloki, sessiya muddati, rol o'zgarganda sessiyani bekor qilish — MOS. MFA — SIMULYATSIYA (`auth_svc.py:160`, `AQ_DEMO=0` da kirish umuman rad). Parol siyosati faqat uzunlik; parolni almashtirish yo'li yo'q. 7 demo hisob parol `demo`. |
| §9 | Ma'lumot himoyasi | YO'Q | TLS yo'q (`run.py:7`), baza va zaxira shifrlanmagan, biometrik shablon yo'q (faqat bool). Eksport vakolat/maqsad/muddat/hash bilan — MOS; qayta yuklab olish auditga yozilmaydi. |
| §9 | Audit yaxlitligi | MOS (ilova) | Hash zanjiri, `verify_chain`, o'chirish/tahrirlash yo'li yo'q. Cheklov: fayl darajasida WORM yo'q; oxirgi yozuvlarni kesib tashlash aniqlanmaydi; buzilish topilsa signal yaratilmaydi. NTP — simulyatsiya. |
| §10.1 | Saqlash muddatlari | QISMAN | `audit_saqlash_yil=5`, `video=90`, `foto=365` saqlanadi; avtomatik o'chirish/arxivlash yo'q (UI o'zi shuni yozadi). Biometrik shablon va konfiguratsiya versiyasi muddatlari yo'q. Audit chegarasi 1 yilgacha tushirish mumkin. |
| §10.3 | Zaxira | QISMAN | Haqiqiy SQLite backup API + manifest + SHA-256 + alohida tiklash — MOS. Jadval, shifrlash, 3 nusxa/NAS, inkremental (kunlik = haftalik = to'liq), choraklik DR — YO'Q. Zaxira xatosi signal yaratmaydi (`make_alarm=False`). |
| §11 | Ishonchlilik | YO'Q | 99,5 %, 2 s, 3 s, 10 000 hodisa/72 soat, UPS 30 daqiqa — sozlama, metrika yoki tekshiruv yo'q. Chegaralar signal yaratmaydi (disk/batareya WARNING faqat simulyatordan). Disk chegarasi 85 % (TZ 80 %). |
| §12 | Dasturiy talablar | QISMAN | Kirill — transliteratsiya; rus tili yo'q. Qidiruv 7 mezondan 5 tasi (natija va insident toifasi yo'q). Jurnal eksporti faqat CSV. Dastur versiyasi raqami yo'q. `/api/docs` va `/openapi.json` autentifikatsiyasiz ochiq. Demo hisoblar `AQ_DEMO=0` da ham qoladi. |
| §16 | Integratsiya | YO'Q | HR, SIEM, qo'riqlash paneli, NTP/katalog — statik "Ulanmagan" yozuvi. Syslog kodi yo'q. Tashqi API yo'q (3 ta o'qish endpointi faqat brauzer sessiyasi bilan). "Tashqi tizim qulf ochmaydi" — MOS (qulf faqat `sim.py:77,103` da ochiladi). |
| §18 | Qabul sinovlari | QISMAN | Quyidagi 4-bo'limga qarang. |
| Ilova B | Hodisalar ro'yxati | QISMAN | 16 hodisadan 12 tasi mos. Farqlar: ruxsatsiz urinish WARNING (TZ CRITICAL); kamera/datchik qisqa uzilishi CRITICAL (TZ WARNING); server ishlamaydi WARNING (TZ CRITICAL); "zaxirani o'chirishga urinish" hodisasi yo'q. |

## 3. Eng muhim kamchiliklar (ustuvorlik bo'yicha)

Dasturda hozir tuzatish mumkin bo'lganlar:

1. **Ruxsatsiz urinish signal yaratmaydi.** `rad_etildi` WARNING, `make_alarm=False` (`events.py:16`). TZ Ilova B: CRITICAL. Operator hech narsa ko'rmaydi.
2. **Panelning o'z rad javoblari auditga yozilmaydi.** 12 ta `HTTPException(403)` routerlarda, `record_event` yo'q, global handler yo'q. TZ §18 S-01 "rad etiladi VA auditga yoziladi" — ikkinchi yarmi yo'q.
3. **Taymerlar yo'q.** Qulf ochiq vaqti, eshik ochiq qolishi (60/180 s), 3 urinish bloki — sozlamalar bor, o'qilmaydi. F-04 sinovini qayta ishlab bo'lmaydi.
4. **Qaytarishda tekshiruv yo'q**, eshik yopilmagan holat modellashtirilmagan (`sim.py:96-123`).
5. **Navbat (smena) oynasi olishda tekshirilmaydi**; `Shift` jadvali bor, ishlatilmaydi.
6. **Smena ochishda kritik xato cheklamaydi**, inventar farqi akt/signal yaratmaydi.
7. **Hisobot filtrlari** TZ §6.5 ga mos emas; hududiy auditor admin harakatlarining bir qismini ko'rmaydi.
8. **Parol almashtirish yo'li yo'q; demo hisoblar doimiy**; `/api/docs` ochiq; jurnal eksporti faqat CSV; `favqulodda_ochish` va `offline` belgisi hech qachon yozilmaydi.
9. **Chegaralar signal yaratmaydi** (disk, batareya, NTP); `batareya_past_pct` o'qilmaydi.
10. **Saqlash muddatlari** hech narsa qilmaydi; zaxira jadvali va xato signali yo'q.

Apparat yoki keyingi bosqichga bog'liq (prototipda kutilmaydi, lekin TZ ga mos deb aytib bo'lmaydi):

11. Haqiqiy MFA adapteri, TLS, baza/zaxira shifrlash, biometrik shablonlar.
12. Kontrollerdan hodisa qabul qilish kanali va obyekt darajasidagi lokal server (offline bufer 10 000/72 soat).
13. Kamera/foto (`media_ref`), ONVIF, HR/SIEM/syslog, NTP klienti, NAS.
14. Rus tili (i18n), 99,5 % / 2 s / 3 s ko'rsatkichlarini o'lchash.

## 4. Qabul sinovlari (TZ §18) — demo simulyatorda holat

| Kod | Sinov | Holat | Izoh |
|---|---|---|---|
| F-01 | Ruxsatli shaxs faqat o'z katagini ochadi | QISMAN | Bog'lanish tekshiriladi; "boshqa shaxs" ssenariysi ifodalanmaydi (xodim doim `cab.officer_id` dan olinadi). |
| F-02 | Ruxsatsiz shaxs: foto, vaqt, ogohlantirish | QISMAN | Rad + vaqt bor; foto yo'q; signal yo'q. |
| F-03 | Olish-qaytarish datchiklar bilan | SIMULYATSIYA | Datchik qiymatlarini simulyator o'zi yozadi. |
| F-04 | Eshik uzoq ochiq | QISMAN | Faqat qo'lda tugma; vaqt hisoblanmaydi; `door_open` ham o'rnatilmaydi. |
| F-05 | Tamper | QISMAN | CRITICAL + tasdiq — bor; kamera markeri bezak. |
| R-01 | Tarmoq uzilishi, offline, sinxron | QISMAN | Holat almashadi; buferlangan/offline hodisa yo'q. |
| R-02 | Elektr uzilishi, UPS, kataklar yopiq | QISMAN | Hodisa + UPS maydonlari bor; "yopiq" tekshirilmaydi. |
| R-03 | Zaxiradan tiklash | MOS | Haqiqiy nusxa va alohida faylga tiklash, hash va yaxlitlik. |
| S-01 | Rol cheklovi rad + audit | QISMAN | Rad — bor; audit — yo'q. |
| S-02 | Jurnal yaxlitligi | QISMAN | Buzilish aniqlanadi (`/jurnal/yaxlitlik`); signal yaratilmaydi. |
| P-01 | Yuklama | YO'Q | Sintetik flot bor, javob vaqti o'lchanmaydi. |
| U-01 | Hisobot va eksport | MOS | 7 hisobot, 3 format, raqam/hash/muddat. |

## 5. Yaxshi bajarilgan joylar

- Hash zanjirli append-only jurnal va yaxlitlik tekshiruvi (`events.py:70-145`, `jurnal.py:307-363`).
- Eksport nazorati: raqam, kim, maqsad, muddat, SHA-256, muddati o'tgan/o'zgartirilgan faylni rad etish, SECURITY hodisa.
- Ikkinchi administrator tasdig'i, o'z so'rovini tasdiqlash taqiqi, rol o'zgarganda sessiyalarni bekor qilish (`settings_svc.py:140-206`).
- Haqiqiy SQLite zaxira (backup API, manifest, hash, integrity_check, zanjir tekshiruvi) va alohida faylga tiklash.
- Smena ochish o'z-tekshiruvi (7 band) va inventar solishtiruvi; yopishda qaytarilmaganlar va ochiq signallar avtomatik.
- Olish oldidan 5 yaroqlilik sharti, xizmat holati, muddat, permit, hold tekshiruvi.
- Vakolat doirasi (respublika/hudud/bo'linma/qurolxona) barcha ro'yxat, partial, API va eksportda.
- Panel hech qachon qulf ochmaydi (TZ §16 chegarasi).

## 6. Tavsiya etilgan tartib

1. Avval 1–6 bandlarni tuzatish (signal darajasi, 403 auditi, taymerlar, qaytarish tekshiruvi, navbat oynasi, smena bloklash) — bular TZ ning "ishlash mantig'i" va qabul sinovlari F-02, F-04, S-01, S-02 ga bevosita ta'sir qiladi.
2. Keyin 7–10 (hisobot filtrlari, parol/hisoblar, chegaralar → signal, saqlash/zaxira jadvali).
3. 11–14 real stend (Bosqich 3) bilan birga: MFA provayder, TLS, kontroller kanali, kamera, integratsiyalar.

Ushbu hujjat `08-yakuniy-tekshiruv.md` dagi "demo qabul qilindi" xulosasini bekor qilmaydi: u mahalliy demo doirasida to'g'ri. Bu hujjat esa TZ ga nisbatan farqni ko'rsatadi.

"""Sintetik respublika ma'lumotlari (NAMUNAVIY). Hajmi: small | medium | full (AQ_SEED)."""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta

from sqlalchemy import insert, select, text, update

from .config import BASE_DIR, SEED_DAYS, SEED_SIZE
from .db import Base, engine, session_scope
from .models import (Alarm, Armory, ArmoryShift, Backup, Cabinet, Custody, Device, Eligibility, Event, Item, Mode,
                     Officer, Region, Setting, Shift, Unit, User)

R = random.Random(42)

# ---- hudud tartibi va sintetik bo'linmalar ----
REGION_ORDER = ["UZ-TK", "UZ-TO", "UZ-SA", "UZ-FA", "UZ-AN", "UZ-NG", "UZ-QA", "UZ-SU", "UZ-BU", "UZ-QR", "UZ-XO", "UZ-JI", "UZ-NW", "UZ-SI"]
TASHKENT_DISTRICTS = ["Yunusobod", "Chilonzor", "Mirzo Ulug'bek", "Yakkasaroy", "Shayxontohur", "Olmazor", "Uchtepa", "Sergeli",
                      "Bektemir", "Yashnobod", "Mirobod", "Yangihayot"]
REGION_CENTER = {"UZ-TO": "Nurafshon", "UZ-SA": "Samarqand", "UZ-FA": "Farg'ona", "UZ-AN": "Andijon", "UZ-NG": "Namangan",
                 "UZ-QA": "Qarshi", "UZ-SU": "Termiz", "UZ-BU": "Buxoro", "UZ-QR": "Nukus", "UZ-XO": "Urganch",
                 "UZ-JI": "Jizzax", "UZ-NW": "Navoiy", "UZ-SI": "Guliston"}
REGION_SECOND = {"UZ-FA": "Marg'ilon", "UZ-FA2": "Qo'qon", "UZ-SA": "Kattaqo'rg'on", "UZ-AN": "Asaka", "UZ-NG": "Chust",
                 "UZ-QA": "Shahrisabz", "UZ-SU": "Denov", "UZ-BU": "Kogon", "UZ-QR": "Xo'jayli", "UZ-XO": "Xiva",
                 "UZ-JI": "Zomin", "UZ-NW": "Zarafshon", "UZ-SI": "Yangiyer", "UZ-TO": "Angren"}
FUNCTIONAL = ["Patrul-post xizmati", "Tezkor bo'linma", "Qo'riqlash bo'linmasi", "O'quv markazi"]

FIRST = ["Aziz", "Bobur", "Doston", "Eldor", "Farrux", "G'ayrat", "Husan", "Islom", "Jasur", "Kamol", "Lochin", "Murod",
         "Nodir", "Otabek", "Rustam", "Sardor", "Temur", "Ulug'bek", "Vohid", "Yodgor", "Zafar", "Sherzod", "Shuhrat",
         "Dilshod", "Abror", "Alisher", "Bekzod", "Davron", "Firdavs", "Jahongir", "Nigora", "Dilnoza", "Madina", "Zilola"]
SURNAME = ["Karimov", "Rahimov", "Tursunov", "Yusupov", "Abdullayev", "Ismoilov", "Qodirov", "Saidov", "Xolmatov", "Ergashev",
           "Mirzayev", "Umarov", "Nazarov", "Sobirov", "Jo'rayev", "Toshmatov", "Hamidov", "Norov", "Rasulov", "Sultonov",
           "Bekmurodov", "Xudoyberdiyev", "Egamberdiyev", "Mahmudov", "Olimov", "Sharipov", "Boboyev", "Ismatov"]
PATRO = ["Bahodirovich", "Akmalovich", "Rustamovich", "Anvarovich", "Shavkatovich", "Ulug'bekovich", "Alisherovich", "Kamolovich"]
POSITIONS = ["Inspektor", "Katta inspektor", "Tezkor xodim", "Patrul inspektori", "Uchastka inspektori", "Navbatchi", "Qo'riqlash xodimi"]
RANKS = ["Serjant", "Katta serjant", "Leytenant", "Katta leytenant", "Kapitan", "Mayor"]

SIZES = {  # bo'linmalar soni har hududda (markaz shahar + tumanlar + funksional), yacheyka oralig'i
    "small": {"units": (1, 2), "cab": (14, 24), "tk_units": 3},
    "medium": {"units": (3, 4), "cab": (18, 32), "tk_units": 6},
    "full": {"units": (5, 7), "cab": (22, 55), "tk_units": 12},
}


def _name(i: int) -> str:
    return "%s %s %s" % (R.choice(SURNAME), R.choice(FIRST), R.choice(PATRO))


def _h(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + "|" + json.dumps(body, sort_keys=True, ensure_ascii=False, default=str)).encode("utf-8")).hexdigest()


def _link_seed_events(events: list[dict]) -> None:
    """Link new fixture rows before insertion; never rewrite the stored audit log.

    Scripted rows must hash their actual payload and continue the same cabinet
    stream as the generated history. Insertion order is the verification order.
    """
    streams: dict[int | None, tuple[str, int]] = {}
    for row in events:
        key = row.get("cabinet_id")
        prev, seq = streams.get(key, ("", 0))
        body = {"type": row["type"], "ts": row["ts_device"].isoformat(),
                "cab": key, "arm": row.get("armory_id"), "off": row.get("officer_id"),
                "item": row.get("item_id"), "method": row.get("method", ""),
                "result": row.get("result", "ok"), "reason": row.get("reason", ""),
                "payload": row.get("payload") or {}}
        row.update(seq=seq + 1, prev_hash=prev, hash=_h(prev, body))
        streams[key] = (row["hash"], seq + 1)


def reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed(size: str = SEED_SIZE, days: int = SEED_DAYS, now: datetime | None = None) -> dict:
    now = (now or datetime.now()).replace(microsecond=0)
    cfg = SIZES.get(size, SIZES["small"])
    regions_json = json.load(open(BASE_DIR / "static" / "data" / "uz_regions.json", encoding="utf-8"))["regions"]
    stats = {"size": size}
    with session_scope() as db:
        # ---- hududlar ----
        regions: dict[str, Region] = {}
        for i, code in enumerate(REGION_ORDER):
            r = regions_json[code]
            reg = Region(code=code, name=r["name"], short=r["short"], order=i)
            db.add(reg); regions[code] = reg
        db.flush()
        # ---- bo'linmalar va qurolxonalar ----
        units: list[Unit] = []
        for code, reg in regions.items():
            names = []
            if code == "UZ-TK":
                names = [d + " tumani IIB" for d in TASHKENT_DISTRICTS[:cfg["tk_units"]]]
                if size != "small":
                    names += ["Patrul-post xizmati boshqarmasi", "Tezkor bo'linma"]
            else:
                n_units = R.randint(*cfg["units"])
                names = [REGION_CENTER[code] + " shahar IIB"]
                second = REGION_SECOND.get(code)
                if n_units >= 2 and second:
                    names.append(second + " shahar IIB")
                k = 1
                while len(names) < n_units:
                    names.append("%d-tuman IIB" % k); k += 1
                if size == "full":
                    names.append(R.choice(FUNCTIONAL))
            for nm in names:
                kind = "funksional" if ("xizmati" in nm or "bo'linma" in nm or "markazi" in nm) else ("shahar_iib" if "shahar" in nm or "tumani" in nm else "tuman_iib")
                u = Unit(region=reg, name=nm, kind=kind)
                db.add(u); units.append(u)
        db.flush()
        armories: list[Armory] = []
        for u in units:
            a = Armory(unit=u, name=u.name + " qurolxonasi", address=u.region.short + ", " + u.name, online=True,
                       last_sync=now - timedelta(seconds=R.randint(5, 90)))
            db.add(a); armories.append(a)
        db.flush()
        # oflayn qurolxonalar: Nukus (QR), Marg'ilon (FA), Qashqadaryo 1-tuman
        offline_names = {"Nukus shahar IIB qurolxonasi", "Marg'ilon shahar IIB qurolxonasi"}
        qa_units = [a for a in armories if a.unit.region.code == "UZ-QA"]
        offline = [a for a in armories if a.name in offline_names] + qa_units[-1:]
        for a in offline:
            a.online = False; a.wan_ok = False; a.pending_events = R.randint(20, 140)
            a.last_sync = now - timedelta(minutes=R.randint(12, 70))
        # ---- yacheykalar, xodimlar, inventar ----
        cabinets: list[Cabinet] = []; officers: list[Officer] = []
        serial_no = 1; tabel_no = 10001
        item_rows: list[dict] = []
        for a in armories:
            n_cab = R.randint(*cfg["cab"])
            for i in range(1, n_cab + 1):
                cab = Cabinet(armory=a, serial="SHK-2026-%06d" % serial_no, label="Y-%03d" % i, wall="A" if i <= n_cab / 2 else "B",
                              position=i, status="zaxira", last_seen=now - timedelta(seconds=R.randint(1, 120)),
                              controller_online=a.online, battery_pct=R.randint(92, 100), temp_c=round(R.uniform(19, 24), 1))
                serial_no += 1
                db.add(cab); cabinets.append(cab)
            db.flush()
            # 90 % yacheykaga xodim biriktirilgan
            assigned = [c for c in a.cabinets if R.random() < 0.9]
            for cab in assigned:
                off = Officer(unit_id=a.unit_id, armory_id=a.id, full_name=_name(tabel_no), tabel=str(tabel_no),
                              position=R.choice(POSITIONS), rank=R.choice(RANKS), service_status="faol",
                              valid_until=now + timedelta(days=R.randint(60, 700)), card_uid="%08X" % R.getrandbits(32))
                tabel_no += 1
                db.add(off); db.flush()
                cab.officer_id = off.id; cab.status = "biriktirilgan"
                officers.append(off)
                for kind in ("qurol_biriktirilgan", "saqlash_vakolati", "maxsus_tayyorgarlik", "yaroqlilik_tekshiruvi", "rahbar_buyrugi"):
                    db.add(Eligibility(officer_id=off.id, kind=kind, doc_ref="B-%d/%d" % (R.randint(1, 400), 2026),
                                       issued=now - timedelta(days=R.randint(30, 400)), valid_until=now + timedelta(days=R.randint(30, 400)), ok=True))
                ak_serial = "%07d" % R.randint(1000000, 9999999); pm_serial = "%s%06d" % (R.choice("АБВГ"), R.randint(100000, 999999))
                item_rows += [
                    {"kind": "qurol", "category": "avtomat", "model": "AK-74", "serial": ak_serial, "rfid": "E200%020X" % R.getrandbits(80), "cabinet_id": cab.id, "officer_id": off.id, "slot": "AK_UYASI", "qty": 1, "state": "mavjud", "inspection_state": "yaroqli", "next_inspection": now + timedelta(days=R.randint(10, 180)), "hold": False},
                    {"kind": "qurol", "category": "to'pponcha", "model": "PM", "serial": pm_serial, "rfid": "E200%020X" % R.getrandbits(80), "cabinet_id": cab.id, "officer_id": off.id, "slot": "PM_QUTISI", "qty": 1, "state": "mavjud", "inspection_state": "yaroqli", "next_inspection": now + timedelta(days=R.randint(10, 180)), "hold": False},
                    {"kind": "magazin", "category": "AK magazini", "model": "5,45x39 30 o'q", "serial": "M-%06d" % R.randint(1, 999999), "rfid": None, "cabinet_id": cab.id, "officer_id": off.id, "slot": "MAGAZIN_UYASI", "qty": 4, "state": "mavjud", "inspection_state": "yaroqli", "next_inspection": None, "hold": False},
                    {"kind": "oq_dori", "category": "o'q-dori qutisi", "model": "5,45x39 · partiya %d-%d" % (R.randint(1, 60), 2025), "serial": "P-%05d" % R.randint(1, 99999), "rfid": None, "cabinet_id": cab.id, "officer_id": off.id, "slot": "OQ_DORI", "qty": 120, "state": "mavjud", "inspection_state": "yaroqli", "next_inspection": None, "hold": False},
                    {"kind": "jihoz", "category": "dubulg'a", "model": "6B47", "serial": "D-%06d" % R.randint(1, 999999), "rfid": None, "cabinet_id": cab.id, "officer_id": off.id, "slot": "YUQORI", "qty": 1, "state": "mavjud", "inspection_state": "yaroqli", "next_inspection": None, "hold": False},
                    {"kind": "jihoz", "category": "bronjilet", "model": "6B45", "serial": "B-%06d" % R.randint(1, 999999), "rfid": None, "cabinet_id": cab.id, "officer_id": off.id, "slot": "ORTA", "qty": 1, "state": "mavjud", "inspection_state": "yaroqli", "next_inspection": None, "hold": False},
                    {"kind": "jihoz", "category": "body-kamera", "model": "BK-2", "serial": "BK-%06d" % R.randint(1, 999999), "rfid": None, "cabinet_id": cab.id, "officer_id": off.id, "slot": "YUQORI_ORTA", "qty": 1, "state": "mavjud", "inspection_state": "yaroqli", "next_inspection": None, "hold": False},
                ]
            # nosoz/bloklangan: ~0.4 %
            for cab in a.cabinets:
                if R.random() < 0.004:
                    cab.status = R.choice(["bloklangan", "nosoz"])
            # qurilmalar
            for kind, name, metrics in (("server", "Lokal server", {"cpu": R.randint(5, 40), "ram": R.randint(20, 60), "disk": R.randint(30, 78)}),
                                        ("kommutator", "PoE kommutator", {"portlar": 24, "band": R.randint(8, 20)}),
                                        ("ups", "Online UPS", {"batareya": R.randint(90, 100), "yuklama": R.randint(20, 55)}),
                                        ("nas", "Zaxira NAS", {"disk": R.randint(20, 70)}),
                                        ("kamera", "Kamera 1 (umumiy)", {"oqim": True}), ("kamera", "Kamera 2 (yaqin plan)", {"oqim": True}),
                                        ("terminal", "Face ID terminali", {"kesh": True})):
                st = "onlayn" if a.online else "oflayn"
                db.add(Device(armory_id=a.id, kind=kind, name=name, status=st, metrics=metrics, last_seen=a.last_sync))
        db.flush()
        if item_rows:
            for i in range(0, len(item_rows), 2000):
                db.execute(insert(Item), item_rows[i:i + 2000])
        db.flush()
        stats.update(regions=len(regions), units=len(units), armories=len(armories), cabinets=len(cabinets), officers=len(officers))

        # ---- ruxsat va navbatlar (hozirgi smena) ----
        for off in officers:
            if R.random() < 0.6:
                db.add(Shift(unit_id=off.unit_id, officer_id=off.id, start=now.replace(hour=8, minute=0, second=0), end=now.replace(hour=20, minute=0, second=0), confirmed_by="Navbatchi"))

        # ---- tarixiy hodisalar (hash zanjiri bilan) ----
        cab_by_id = {c.id: c for c in cabinets}
        assigned_cabs = [c for c in cabinets if c.officer_id]
        arm_by_id = {a.id: a for a in armories}
        ak_by_cab = {r[0]: r[1] for r in db.execute(select(Item.cabinet_id, Item.id).where(Item.category == "avtomat"))}
        events: list[dict] = []
        custody_rows: list[dict] = []
        alarm_rows: list[dict] = []
        start_day = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0)
        for cab in assigned_cabs:
            a = arm_by_id[cab.armory_id]; unit = a.unit
            prev = ""; seq = 0
            def push(type_, ts, level="INFO", method="YUZ+BARMOQ", result="ok", reason="", title="", detail="", item_id=None, payload=None):
                nonlocal prev, seq
                seq += 1
                body = {"type": type_, "ts": ts.isoformat(), "cab": cab.id, "arm": a.id, "off": cab.officer_id, "item": item_id,
                        "method": method, "result": result, "reason": reason, "payload": payload or {}}
                h = _h(prev, body)
                events.append({"seq": seq, "ts_device": ts, "ts_server": ts, "type": type_, "level": level, "region_id": unit.region_id,
                               "unit_id": unit.id, "armory_id": a.id, "cabinet_id": cab.id, "officer_id": cab.officer_id, "item_id": item_id,
                               "method": method, "result": result, "reason": reason, "attempts": 0, "approver1": "", "approver2": "",
                               "offline": False, "simulated": True, "title": title or type_, "detail": detail, "payload": payload or {},
                               "prev_hash": prev, "hash": h, "media_ref": ""})
                prev = h
            for d in range(days):
                day = start_day + timedelta(days=d)
                is_today = d == days - 1
                # xodimning ish kuni: ~70 % ehtimol bilan olish-qaytarish
                if R.random() < 0.7:
                    t_take = day + timedelta(hours=R.randint(7, 9), minutes=R.randint(0, 59))
                    if t_take > now:
                        continue
                    push("auth_ok", t_take - timedelta(seconds=20), title="Kirish tasdiqlandi", detail="Yuz + barmoq izi")
                    push("avtomat_olindi", t_take, title="Avtomat olindi", detail="AK-74, datchiklar 3/3", item_id=ak_by_cab.get(cab.id))
                    t_ret = t_take + timedelta(hours=R.randint(8, 11), minutes=R.randint(0, 59))
                    if is_today and t_ret > now:
                        # hozir xodimda: ~2 % kechikkan
                        overdue = R.random() < 0.013
                        due = t_take + timedelta(hours=12, minutes=30)
                        if overdue:
                            due = now - timedelta(hours=R.randint(1, 6))
                        custody_rows.append({"item_id": ak_by_cab.get(cab.id), "officer_id": cab.officer_id, "cabinet_id": cab.id,
                                             "taken_at": t_take, "due_at": due, "returned_at": None, "match_ok": True})
                        cab.ak_present = False
                        if overdue:
                            push("kechikish", due + timedelta(minutes=1), level="WARNING", title="Qaytarish muddati o'tdi", detail="AK-74 belgilangan vaqtda qaytarilmadi")
                            alarm_rows.append({"level": "WARNING", "type": "kechikish", "region_id": unit.region_id, "unit_id": unit.id, "armory_id": a.id,
                                               "cabinet_id": cab.id, "title": "Qaytarish muddati o'tdi", "detail": "%s · %s · %s" % (unit.region.short, unit.name, cab.label),
                                               "opened_at": due, "requires_ack": False, "forwarded": False})
                    else:
                        ok = R.random() > 0.004
                        push("auth_ok", t_ret - timedelta(seconds=20), title="Kirish tasdiqlandi", detail="Yuz + barmoq izi")
                        push("avtomat_qaytarildi", t_ret, title="Avtomat qaytarildi", detail="AK-74 uyaga qo'yildi" if ok else "Nomuvofiqlik: RFID mos emas", result="ok" if ok else "nomuvofiq", item_id=ak_by_cab.get(cab.id))
                        custody_rows.append({"item_id": ak_by_cab.get(cab.id), "officer_id": cab.officer_id, "cabinet_id": cab.id,
                                             "taken_at": t_take, "due_at": t_take + timedelta(hours=12, minutes=30), "returned_at": t_ret, "match_ok": ok})
                        if not ok:
                            push("qaytarish_nomuvofiq", t_ret + timedelta(seconds=5), level="CRITICAL", title="Qaytarish nomuvofiq", detail="Biriktirilgan qurol emas")
                # kamdan-kam hodisalar
                r = R.random()
                if r < 0.006:
                    push("rad_etildi", day + timedelta(hours=R.randint(6, 22)), level="WARNING", result="rad", reason=R.choice(["outside_shift", "no_permit", "biometric_mismatch", "wrong_pin"]), title="Kirish rad etildi", detail="Navbat oynasidan tashqarida")
                elif r < 0.008:
                    push("eshik_ochiq_qoldi", day + timedelta(hours=R.randint(6, 22)), level="WARNING", title="Eshik ochiq qoldi", detail="3 daqiqadan ortiq")
                elif r < 0.0085:
                    push("urilish", day + timedelta(hours=R.randint(0, 23)), level="CRITICAL", title="Urilish aniqlandi", detail="Akselerometr 2,4 g")
            db.flush()
        # ---- ssenariy: rasmdagi jonli holat (bugun) ----
        def find_arm(region_code: str, contains: str) -> Armory | None:
            for a in armories:
                if a.unit.region.code == region_code and contains in a.name:
                    return a
            return next((a for a in armories if a.unit.region.code == region_code), None)
        scripted = [
            ("UZ-TK", "Yunusobod", "buzish_urinishi", "CRITICAL", "Buzishga urinish (tamper)", "Kamera belgisi bor, qorovul postiga yuborildi", now - timedelta(minutes=1)),
            ("UZ-QR", "Nukus", "aloqa_uzildi", "CRITICAL", "Qurolxona oflayn", "12 daqiqa aloqa yo'q, hodisalar keshda", now - timedelta(minutes=4)),
            ("UZ-FA", "Marg'ilon", "eshik_ochiq_qoldi", "WARNING", "Eshik ochiq qoldi", "3 daqiqadan ortiq ochiq", now - timedelta(minutes=12)),
            ("UZ-SA", "Samarqand shahar", "kechikish", "WARNING", "Qaytarish muddati o'tdi", "2 ta qurol muddatida qaytarilmadi", now - timedelta(minutes=30)),
            ("UZ-AN", "Andijon shahar", "texnik_xizmat", "INFO", "Texnik xizmat yakunlandi", "Rejalashtirilgan profilaktika", now - timedelta(minutes=45)),
            ("UZ-SU", "Termiz", "smena_ochildi", "INFO", "Smena ochildi", "O'z-tekshiruv o'tdi", now - timedelta(minutes=62)),
        ]
        for code, contains, typ, lvl, title, detail, ts in scripted:
            a = find_arm(code, contains)
            if a is None:
                continue
            cab = next((c for c in a.cabinets if c.officer_id), a.cabinets[0] if a.cabinets else None)
            unit = a.unit
            body = {"type": typ, "ts": ts.isoformat(), "cab": cab.id if cab else None, "arm": a.id, "off": cab.officer_id if cab else None,
                    "item": None, "method": "", "result": "ok", "reason": "", "payload": {}}
            events.append({"seq": 999999, "ts_device": ts, "ts_server": ts, "type": typ, "level": lvl, "region_id": unit.region_id,
                           "unit_id": unit.id, "armory_id": a.id, "cabinet_id": cab.id if cab else None, "officer_id": cab.officer_id if cab else None,
                           "item_id": None, "method": "", "result": "ok", "reason": "", "attempts": 0, "approver1": "", "approver2": "",
                           "offline": False, "simulated": True, "title": title, "detail": detail, "payload": {"scripted": True},
                           "prev_hash": "", "hash": _h("", body), "media_ref": ""})
            if lvl in ("CRITICAL", "WARNING"):
                alarm_rows.append({"level": lvl, "type": {"buzish_urinishi": "tamper", "aloqa_uzildi": "oflayn", "eshik_ochiq_qoldi": "eshik_ochiq", "kechikish": "kechikish"}[typ],
                                   "region_id": unit.region_id, "unit_id": unit.id, "armory_id": a.id, "cabinet_id": cab.id if cab else None,
                                   "title": title, "detail": "%s · %s%s" % (unit.region.short, unit.name, (" · " + cab.label) if cab and typ in ("buzish_urinishi", "eshik_ochiq_qoldi") else ""),
                                   "opened_at": ts, "requires_ack": lvl == "CRITICAL", "forwarded": lvl == "CRITICAL"})
        # security hodisa (respublika darajasi)
        events.append({"seq": 1, "ts_device": now - timedelta(minutes=47), "ts_server": now - timedelta(minutes=47), "type": "huquq_berish_tasdiqlandi",
                       "level": "SECURITY", "region_id": None, "unit_id": None, "armory_id": None, "cabinet_id": None, "officer_id": None, "item_id": None,
                       "method": "", "result": "kutilmoqda", "reason": "", "attempts": 0, "approver1": "admin", "approver2": "", "offline": False,
                       "simulated": True, "title": "Administrator huquqi berildi", "detail": "Ikkinchi tasdiq kutilmoqda", "payload": {},
                       "prev_hash": "", "hash": _h("", {"type": "huquq"}), "media_ref": ""})
        # Hash the exact fixture data, including scripted rows, before insertion.
        _link_seed_events(events)
        # bulk insert
        for i in range(0, len(events), 2000):
            db.execute(insert(Event), events[i:i + 2000])
        for i in range(0, len(custody_rows), 2000):
            db.execute(insert(Custody), custody_rows[i:i + 2000])
        # Match only newly generated items to their newly generated open records.
        # Existing databases are never reconciled or rewritten by this fixture builder.
        issued_item_ids = {row["item_id"] for row in custody_rows if row["returned_at"] is None}
        if issued_item_ids:
            db.execute(update(Item).where(Item.id.in_(issued_item_ids)).values(state="yo'q"))
        db.flush()
        # eski signallarni yechilgan qilib qo'yamiz, faqat so'nggi 24 soatdagilar faol
        for al in alarm_rows:
            if al["opened_at"] < now - timedelta(hours=24):
                al["resolved_at"] = al["opened_at"] + timedelta(minutes=R.randint(10, 240)); al["resolved_by"] = "Navbatchi"
        if alarm_rows:
            db.execute(insert(Alarm), alarm_rows)
        stats.update(events=len(events), custody=len(custody_rows), alarms=len(alarm_rows))

        # ---- faol Trevoga rejimi: Toshkent sh., Yunusobod ----
        a = find_arm("UZ-TK", "Yunusobod")
        if a:
            db.add(Mode(kind="trevoga", unit_id=a.unit_id, armory_id=a.id, started_by="Navbatchi", approver2="Komandir",
                        started_at=now - timedelta(minutes=52), target_count=min(48, len(a.cabinets)), issued_count=min(41, len(a.cabinets) - 7),
                        queue_count=7, avg_seconds=38, reason="O'quv trevoga"))
            db.add(ArmoryShift(armory_id=a.id, opened_by="Navbatchi", opened_at=now.replace(hour=8, minute=2, second=0),
                               selfcheck={"server": True, "baza": True, "kamera": True, "terminal": True, "kontroller": True, "ups": True, "disk": True},
                               reconcile={"mos": len(a.cabinets), "nomuvofiq": 0}, permits_confirmed=True))
        # ---- foydalanuvchilar, zaxira nusxa, sozlamalar ----
        tk_region = regions["UZ-TK"]
        db.add_all([
            User(username="admin", full_name="Respublika administratori", role="administrator", scope_kind="respublika"),
            User(username="tekshiruvchi", full_name="IIV markaziy apparati tekshiruvchisi", role="tekshiruvchi", scope_kind="respublika"),
            User(username="rahbar", full_name="Rahbariyat (respublika)", role="rahbariyat", scope_kind="respublika"),
            User(username="hudud_tk", full_name="Toshkent sh. IIB rahbariyati", role="rahbariyat", scope_kind="hudud", scope_id=tk_region.id),
            User(username="navbatchi", full_name="Navbatchi (Yunusobod)", role="navbatchi", scope_kind="qurolxona", scope_id=a.id if a else None),
            User(username="masul", full_name="Qurolxona mas'uli (Yunusobod)", role="qurolxona_masuli", scope_kind="qurolxona", scope_id=a.id if a else None),
        ])
        db.add_all([
            Backup(scope="markaz", kind="kunlik", ts=now.replace(hour=2, minute=0, second=0), size_mb=R.randint(400, 900), ok=True),
            Backup(scope="markaz", kind="haftalik", ts=(now - timedelta(days=now.weekday())).replace(hour=3, minute=0, second=0), size_mb=R.randint(2000, 4000), ok=True),
            Backup(scope="markaz", kind="tiklash_sinovi", ts=now - timedelta(days=9), size_mb=0, ok=True, note="Oylik tiklash sinovi muvaffaqiyatli"),
        ])
        db.add_all([Setting(key=k, value=v) for k, v in {
            "eshik_ochiq_ogohlantirish_s": "60", "eshik_ochiq_signal_s": "180", "qulf_qayta_s": "15", "rad_blok_urinish": "3",
            "rad_blok_daqiqa": "15", "batareya_past_pct": "20", "urilish_g": "2.0", "qaytarish_grace_min": "30",
            "favqulodda_tasdiqlovchilar": "2", "video_saqlash_kun": "90", "foto_saqlash_kun": "365", "audit_saqlash_yil": "5",
        }.items()])
        db.flush()
        # signallar soni menyu belgisi uchun
        stats["active_alarms"] = db.scalar(select(text("count(*)")).select_from(Alarm).where(Alarm.resolved_at.is_(None))) or 0
    return stats


if __name__ == "__main__":
    reset_db()
    print(seed())

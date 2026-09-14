"""Yacheyka raqamli egizagi (2D old ko'rinish): 5 zona [01 §1.2], uyalar, qulflar, terminal holati.

SVG geometriyasi (piksel) shu yerda hisoblanadi, shablon (`yacheykalar/_twin.html`) faqat chizadi.
Shkaf: 2000 × 400 × 600 mm, metall eshik; o'ngda 200 mm elektronika moduli.
"""
from __future__ import annotations

from ..models import Cabinet, Item

# ---- mm -> px (old ko'rinish; kenglik va balandlik masshtabi sxema o'qilishi uchun har xil) ----
TOP_PX, BOTTOM_PX = 30.0, 550.0
K = (BOTTOM_PX - TOP_PX) / 2000.0
BODY_X, BODY_W = 40, 160


def y_mm(mm: float) -> float:
    return round(BOTTOM_PX - mm * K, 1)


# (kalit, y0 mm, y1 mm, nomi, mazmuni)
ZONES = [
    ("pastki", 0, 1150, "Pastki zona", "AK-74 va taktik sumka"),
    ("orta", 1150, 1450, "O'rta zona", "O'q-dori qutisi yoki bronjilet"),
    ("yuqori_orta", 1450, 1700, "Yuqori-o'rta zona", "PM, magazinlar, kishan va kichik jihozlar"),
    ("yuqori", 1700, 1950, "Yuqori zona", "Dubulg'a va gaz niqobi"),
    ("texnik", 1950, 2000, "Texnik bo'shliq", "Kabel, LED va datchiklar"),
]

# jihoz holati -> (rang, yorliq)
STATE = {
    "mavjud": ("green", "uyada"), "yo'q": ("yellow", "xodimda"), "nosoz": ("red", "nosoz"),
    "xizmatda": ("blue", "xizmatda"), "bo'sh": ("gray", "biriktirilmagan"),
}

# uya shabloni: kalit, zona, nomi, qisqa nomi, kategoriyalar, tur, x, y, w, h, shakl, qulf atributi, mavjudlik atributi, datchik, qulf nomi
SLOTS = [
    ("ak", "pastki", "AK-74 uyasi", "AK-74", ("avtomat",), "qurol", 52, 262, 44, 280, "rifle", "ak_clamp_locked", "ak_present", "bosim + qisqich + RFID", "stvol qisqichi"),
    ("sumka", "pastki", "Taktik sumka", "Sumka", ("taktik sumka", "sumka"), "jihoz", 104, 468, 88, 74, "bag", None, None, "RFID (ixtiyoriy)", ""),
    ("oq_dori", "orta", "O'q-dori qutisi", "O'q-dori", ("o'q-dori qutisi",), "oq_dori", 48, 196, 70, 48, "box", None, None, "vazn + kamar", ""),
    ("bronjilet", "orta", "Bronjilet", "Bronjilet", ("bronjilet",), "jihoz", 126, 180, 66, 64, "vest", None, None, "RFID (ixtiyoriy)", ""),
    ("pm", "yuqori_orta", "PM + 2 magazin (qulfli quti)", "PM", ("to'pponcha",), "qurol", 48, 118, 62, 48, "pistol", "pm_box_locked", "pm_present", "RFID + quti qulfi", "PM qutisi"),
    ("magazin", "yuqori_orta", "AK magazinlari (4 uya)", "Magazin", ("ak magazini",), "magazin", 116, 118, 36, 48, "mags", None, None, "vazn + RFID", ""),
    ("kishan", "yuqori_orta", "Kishan", "Kishan", ("kishan",), "jihoz", 158, 118, 34, 21, "cuffs", None, None, "", ""),
    ("bodycam", "yuqori_orta", "Body-kamera", "Kamera", ("body-kamera",), "jihoz", 158, 145, 34, 21, "cam", None, None, "RFID", ""),
    ("dubulga", "yuqori", "Dubulg'a 6B47", "Dubulg'a", ("dubulg'a",), "jihoz", 48, 54, 68, 46, "helmet", None, None, "RFID (ixtiyoriy)", ""),
    ("gaz", "yuqori", "Gaz niqobi", "Gaz niqobi", ("gaz niqobi",), "jihoz", 124, 54, 68, 46, "mask", None, None, "RFID (ixtiyoriy)", ""),
]

OUTLINE = {"biriktirilgan": "green", "zaxira": "gray", "bloklangan": "red", "nosoz": "red", "xizmatda": "yellow"}

# terminal holati -> (LED rangi, yorliq)
TERMINAL_META = {
    "idle": ("blue", "Kutish"), "face": ("yellow", "Yuz tanilmoqda"), "finger": ("yellow", "Barmoq izi"),
    "ok": ("green", "Ruxsat berildi"), "open": ("green", "Eshik ochiq"), "lock": ("blue", "Qulflandi"),
    "denied": ("red", "Rad etildi"), "blocked": ("red", "Bloklangan"),
}


def _f(v: float) -> str:
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _shape(shape: str, x: float, y: float, w: float, h: float) -> str:
    """Uya ichidagi jihozning chiziqli silueti (stroke=currentColor, shablon CSS rang beradi)."""
    cx, cy = x + w / 2, y + h / 2
    f = _f
    if shape == "rifle":  # tik turgan AK-74: stvol yuqorida, qo'ndoq pastda
        top, rb = y + 10, y + 130
        return (f'<line x1="{f(cx)}" y1="{f(top)}" x2="{f(cx)}" y2="{f(rb)}"/>'
                f'<line x1="{f(cx + 4)}" y1="{f(top + 34)}" x2="{f(cx + 4)}" y2="{f(rb - 6)}"/>'
                f'<rect x="{f(cx - 7)}" y="{f(rb)}" width="14" height="62" rx="2"/>'
                f'<rect x="{f(cx + 7)}" y="{f(rb + 22)}" width="7" height="28" rx="2"/>'
                f'<path d="M{f(cx - 5)} {f(rb + 62)}L{f(cx + 5)} {f(rb + 62)}L{f(cx + 8)} {f(y + h - 14)}L{f(cx - 8)} {f(y + h - 14)}Z"/>')
    if shape == "bag":
        return (f'<rect x="{f(x + 10)}" y="{f(y + 24)}" width="{f(w - 20)}" height="{f(h - 36)}" rx="3"/>'
                f'<path d="M{f(cx - 14)} {f(y + 24)}a14 10 0 0 1 28 0"/>'
                f'<line x1="{f(x + 10)}" y1="{f(y + 40)}" x2="{f(x + w - 10)}" y2="{f(y + 40)}"/>')
    if shape == "box":
        return (f'<rect x="{f(x + 8)}" y="{f(y + 12)}" width="{f(w - 16)}" height="{f(h - 24)}" rx="2"/>'
                f'<line x1="{f(x + 8)}" y1="{f(y + 21)}" x2="{f(x + w - 8)}" y2="{f(y + 21)}"/>'
                f'<line x1="{f(cx - 6)}" y1="{f(y + 16)}" x2="{f(cx + 6)}" y2="{f(y + 16)}"/>')
    if shape == "vest":
        return (f'<path d="M{f(x + 10)} {f(y + 8)}L{f(x + 22)} {f(y + 8)}L{f(x + 22)} {f(y + 18)}L{f(x + w - 22)} {f(y + 18)}'
                f'L{f(x + w - 22)} {f(y + 8)}L{f(x + w - 10)} {f(y + 8)}L{f(x + w - 10)} {f(y + h - 12)}L{f(x + 10)} {f(y + h - 12)}Z"/>'
                f'<line x1="{f(x + 18)}" y1="{f(y + 30)}" x2="{f(x + w - 18)}" y2="{f(y + 30)}"/>')
    if shape == "pistol":
        return (f'<rect x="{f(x + 8)}" y="{f(y + 10)}" width="{f(w - 24)}" height="9" rx="2"/>'
                f'<path d="M{f(x + w - 28)} {f(y + 19)}L{f(x + w - 16)} {f(y + 19)}L{f(x + w - 12)} {f(y + h - 14)}L{f(x + w - 24)} {f(y + h - 14)}Z"/>'
                f'<path d="M{f(x + w - 32)} {f(y + 19)}v5h4"/>'
                f'<rect x="{f(x + 8)}" y="{f(y + 24)}" width="5" height="11" rx="1"/><rect x="{f(x + 15)}" y="{f(y + 24)}" width="5" height="11" rx="1"/>')
    if shape == "mags":
        return "".join(f'<rect x="{f(x + 6 + i * 7)}" y="{f(y + 8)}" width="5" height="{f(h - 20)}" rx="1.5"/>' for i in range(4))
    if shape == "cuffs":
        return (f'<circle cx="{f(x + 10)}" cy="{f(cy - 2)}" r="4.5"/><circle cx="{f(x + w - 10)}" cy="{f(cy - 2)}" r="4.5"/>'
                f'<line x1="{f(x + 14.5)}" y1="{f(cy - 2)}" x2="{f(x + w - 14.5)}" y2="{f(cy - 2)}"/>')
    if shape == "cam":
        return f'<rect x="{f(x + 7)}" y="{f(y + 4)}" width="{f(w - 14)}" height="{f(h - 10)}" rx="2"/><circle cx="{f(cx)}" cy="{f(cy - 1)}" r="2.5"/>'
    if shape == "helmet":
        return (f'<path d="M{f(x + 10)} {f(y + h - 14)}a{f((w - 20) / 2)} {f(h - 24)} 0 0 1 {f(w - 20)} 0Z"/>'
                f'<line x1="{f(x + 6)}" y1="{f(y + h - 14)}" x2="{f(x + w - 6)}" y2="{f(y + h - 14)}"/>')
    if shape == "mask":
        return (f'<ellipse cx="{f(cx)}" cy="{f(cy - 4)}" rx="{f(w / 2 - 12)}" ry="{f(h / 2 - 10)}"/>'
                f'<circle cx="{f(cx - 8)}" cy="{f(cy - 7)}" r="3.5"/><circle cx="{f(cx + 8)}" cy="{f(cy - 7)}" r="3.5"/>'
                f'<rect x="{f(cx - 5)}" y="{f(cy + 1)}" width="10" height="6" rx="2"/>')
    return ""


def terminal(cab: Cabinet) -> dict:
    from .sim import TERMINAL_TEXT
    state = cab.terminal_state if cab.terminal_state in TERMINAL_META else "idle"
    tone, label = TERMINAL_META[state]
    l1, l2 = TERMINAL_TEXT.get(state, TERMINAL_TEXT["idle"])
    return {"state": state, "tone": tone, "label": label, "line1": l1, "line2": l2,
            "short1": l1[:14], "short2": l2[:16]}


def build(cab: Cabinet, items: list[Item]) -> dict:
    """Egizak ma'lumoti: zonalar, uyalar (holat, qulf, jihoz), eshik, terminal, korpus rangi."""
    by_cat: dict[str, Item] = {}
    by_kind: dict[str, Item] = {}
    for it in items:
        by_cat.setdefault((it.category or "").lower(), it)
        by_kind.setdefault(it.kind, it)
    zones = {z[0]: {"key": z[0], "y0": z[1], "y1": z[2], "py0": y_mm(z[1]), "py1": y_mm(z[2]), "label": z[3], "desc": z[4], "slots": []}
             for z in ZONES}
    flat = []
    for key, zone, label, short, cats, kind, x, y, w, h, shape, lock_attr, present_attr, sensor, lock_label in SLOTS:
        item = next((by_cat[c] for c in cats if c in by_cat), None)
        if item is None and kind in ("magazin", "oq_dori"):
            item = by_kind.get(kind)
        if item is None:
            state = "bo'sh"
        elif item.state in ("nosoz", "xizmatda"):
            state = item.state
        elif present_attr is not None:
            state = "mavjud" if getattr(cab, present_attr) else "yo'q"
        else:
            state = item.state if item.state in STATE else "mavjud"
        tone, state_label = STATE[state]
        lock = bool(getattr(cab, lock_attr)) if lock_attr else None
        s = {"key": key, "zone": zone, "label": label, "short": short, "state": state, "state_label": state_label, "tone": tone,
             "lock": lock, "lock_label": lock_label, "sensor": sensor, "item": item, "x": x, "y": y, "w": w, "h": h,
             "lx": x + w - 8, "ly": y + 7, "shape_svg": _shape(shape, x, y, w, h), "hold": bool(item.hold) if item else False}
        zones[zone]["slots"].append(s)
        flat.append(s)
    counts = {k: sum(1 for s in flat if s["state"] == k) for k in STATE}
    return {
        "zones": list(zones.values()), "slots": flat, "counts": counts,
        "outline": OUTLINE.get(cab.status, "gray"), "term": terminal(cab),
        "door": {"open": cab.door_open, "locked": cab.door_locked},
        "dims": "2000 × 400 × 600 mm",
    }

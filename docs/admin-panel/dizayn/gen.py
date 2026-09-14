# Generates four direction artboards for the republic dashboard (.dc.html) + canvas.json
import json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, "map", "uz_regions.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "canvas")
os.makedirs(OUT, exist_ok=True)

# ---------------- shared sample data (namunaviy) ----------------
KPI = [
    ("Jami yacheykalar", "5 512", "212 qurolxona", "neutral"),
    ("Berilgan qurollar", "1 284", "hozir xodimlarda", "neutral"),
    ("Vaqtida qaytarilmagan", "17", "muddat o'tgan", "critical"),
    ("Nosoz yoki bloklangan", "23", "yacheyka", "warning"),
    ("Sutkalik olish-qaytarish", "3 941", "bugun, 09:42 gacha", "neutral"),
    ("Rad etilgan urinishlar", "12", "bugun", "warning"),
    ("Favqulodda ochilishlar", "2", "30 kun", "critical"),
    ("Inventar farqlari", "5", "yechilmagan", "warning"),
    ("Oflayn qurolxonalar", "3", "212 dan", "critical"),
]
# region rows: iso, yacheyka, berilgan, kechikish, rad, signal, oflayn, status
ROWS = [
    ("UZ-TK", 1180, 296, 4, 3, 2, 0, "critical"),
    ("UZ-TO", 520, 121, 2, 1, 1, 0, "warning"),
    ("UZ-SA", 480, 112, 2, 1, 1, 0, "warning"),
    ("UZ-FA", 460, 104, 2, 2, 1, 1, "critical"),
    ("UZ-AN", 410, 98, 1, 1, 0, 0, "good"),
    ("UZ-NG", 390, 87, 1, 0, 0, 0, "good"),
    ("UZ-QA", 360, 81, 1, 1, 0, 1, "warning"),
    ("UZ-SU", 330, 79, 2, 1, 1, 0, "warning"),
    ("UZ-BU", 300, 66, 0, 0, 0, 0, "good"),
    ("UZ-QR", 282, 68, 1, 1, 1, 1, "critical"),
    ("UZ-XO", 240, 52, 1, 1, 0, 0, "good"),
    ("UZ-JI", 210, 44, 0, 0, 0, 0, "good"),
    ("UZ-NW", 190, 41, 0, 0, 0, 0, "good"),
    ("UZ-SI", 160, 35, 0, 0, 0, 0, "good"),
]
STATUS_OF = {r[0]: r[7] for r in ROWS}
ALERTS = [
    ("CRITICAL", "09:41", "Toshkent sh. · Yunusobod IIB · Y-017", "Buzishga urinish (tamper), kamera belgisi bor"),
    ("CRITICAL", "09:38", "Qoraqalpog'iston · Nukus sh. IIB", "Qurolxona 12 daqiqa oflayn, hodisalar keshda"),
    ("WARNING", "09:30", "Farg'ona · Marg'ilon IIB · Y-042", "Eshik 3 daqiqa ochiq qoldi"),
    ("WARNING", "09:12", "Samarqand · Samarqand sh. IIB", "2 ta qurol qaytarish muddati o'tdi"),
    ("SECURITY", "08:55", "Respublika · Sozlamalar", "Administrator huquqi berildi, ikkinchi tasdiq kutilmoqda"),
    ("INFO", "08:40", "Surxondaryo · Termiz IIB", "Smena ochildi, o'z-tekshiruv o'tdi"),
]
NAV = ["Dashboard", "Hududlar", "Qurolxonalar", "Yacheykalar", "Xodimlar", "Inventar", "Jurnal", "Signal markazi", "Rejimlar", "Hisobotlar", "Qurilmalar", "Sozlamalar"]
DAYS = [("Du", 3120), ("Se", 3480), ("Ch", 3905), ("Pa", 3610), ("Ju", 3941), ("Sh", 2210), ("Ya", 1980)]

STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
LEVEL = {"CRITICAL": ("critical", "#d03b3b"), "WARNING": ("warning", "#fab219"), "SECURITY": ("security", None), "INFO": ("info", None)}

# ---------------- icons (stroke, 24 grid) ----------------
ICON = {
    "dashboard": '<rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="11" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/>',
    "map": '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14M15 6v14"/>',
    "building": '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M8 7h2M14 7h2M8 11h2M14 11h2M8 15h2M14 15h2M10 21v-3h4v3"/>',
    "lock": '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17" cy="9" r="2.5"/><path d="M21.5 19a5 5 0 0 0-6-4.5"/>',
    "box": '<path d="M3 8l9-4 9 4-9 4z"/><path d="M3 8v9l9 4 9-4V8M12 12v9"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
    "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 21a2 2 0 0 0 4 0"/>',
    "flag": '<path d="M5 21V4"/><path d="M5 4h12l-2 4 2 4H5"/>',
    "file": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="10" y="10" width="4" height="4"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    "wifi-off": '<path d="M2 9a15 15 0 0 1 20 0M5.5 12.5a10 10 0 0 1 13 0M9 16a5 5 0 0 1 6 0M12 19.5h.01M3 3l18 18"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "download": '<path d="M12 4v11M7 10l5 5 5-5M4 19h16"/>',
    "chev": '<path d="M9 6l6 6-6 6"/>',
    "sync": '<path d="M20 12a8 8 0 0 1-14 5.3M4 12a8 8 0 0 1 14-5.3M18 3v4h-4M6 21v-4h4"/>',
}
NAV_ICON = ["dashboard", "map", "building", "lock", "users", "box", "list", "bell", "flag", "file", "cpu", "settings"]

def icon(name, size=18, color="currentColor", sw=1.7):
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0">%s</svg>'
            % (size, size, color, sw, ICON[name]))

def esc(s):
    return html.escape(s, quote=True)

# ---------------- building blocks ----------------
def map_svg(t, width, height, label_size=11, show_labels=True, callouts=True, badges=True):
    W, H = MAP["w"], MAP["h"]
    parts = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" style="display: block; max-width: 100%%" role="img" aria-label="O\'zbekiston xaritasi, hududlar holati">' % (W, H, width, height)]
    parts.append('<defs><pattern id="hatch-%s" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="%s"/><line x1="0" y1="0" x2="0" y2="6" stroke="%s" stroke-width="1.6"/></pattern></defs>' % (t["id"], STATUS["critical"], t["page"]))
    for iso, r in MAP["regions"].items():
        st = STATUS_OF[iso]
        if st == "good":
            fill = t["mapBase"]; op = "1"
        elif st == "warning":
            fill = STATUS["warning"]; op = t["mapOpacity"]
        else:
            fill = ("url(#hatch-%s)" % t["id"]) if t.get("hatch") else STATUS["critical"]; op = t["mapOpacity"] if not t.get("hatch") else "1"
        parts.append('<path d="%s" fill="%s" fill-opacity="%s" stroke="%s" stroke-width="1.2" stroke-linejoin="round"/>' % (r["d"], fill, op, t["mapStroke"]))
    if show_labels:
        for iso, r in MAP["regions"].items():
            if iso == "UZ-TK":
                continue
            parts.append('<text x="%s" y="%s" font-size="%d" font-family="%s" font-weight="600" fill="%s" text-anchor="middle" paint-order="stroke" stroke="%s" stroke-width="3" stroke-linejoin="round">%s</text>'
                         % (r["cx"], r["cy"] + 4, label_size, t["fontBody"], t["mapLabel"], t["mapLabelHalo"], esc(r["short"])))
        if callouts:
            tk = MAP["regions"]["UZ-TK"]
            parts.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1"/>' % (tk["cx"], tk["cy"], tk["cx"] + 40, tk["cy"] - 46, t["mapLabel"]))
            parts.append('<text x="%s" y="%s" font-size="%d" font-family="%s" font-weight="600" fill="%s" paint-order="stroke" stroke="%s" stroke-width="3">Toshkent sh.</text>' % (tk["cx"] + 44, tk["cy"] - 48, label_size, t["fontBody"], t["mapLabel"], t["mapLabelHalo"]))
    if badges:
        for iso, ya, be, ke, ra, si, of, st in ROWS:
            if ke + si + of == 0:
                continue
            r = MAP["regions"][iso]
            x, y = r["cx"], r["cy"] - 16
            if iso == "UZ-TK":
                x, y = r["cx"] + 96, r["cy"] - 52
            col = STATUS["critical"] if st == "critical" else STATUS["warning"]
            n = ke + si + of
            parts.append('<g><circle cx="%s" cy="%s" r="9" fill="%s" stroke="%s" stroke-width="2"/><text x="%s" y="%s" font-size="10" font-weight="700" font-family="%s" fill="#111" text-anchor="middle">%d</text></g>' % (x, y, col, t["page"], x, y + 3.5, t["fontBody"], n))
    parts.append("</svg>")
    return "".join(parts)

def legend(t, dark):
    items = [("Faol signal yoki oflayn", STATUS["critical"], "alert"), ("Kechikish bor", STATUS["warning"], "clock"), ("Me'yorda", t["mapBase"], "check")]
    out = ['<div style="display: flex; gap: 16px; align-items: center; flex-wrap: wrap">']
    for label, col, ic in items:
        out.append('<div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: %s"><span style="width: 12px; height: 12px; border-radius: 3px; background: %s; border: 1px solid %s; display: inline-block"></span>%s</div>' % (t["muted"], col, t["border"], esc(label)))
    out.append('<div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: %s"><span style="width: 16px; height: 16px; border-radius: 50%%; background: %s; display: inline-flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 700; color: #111">3</span>kechikish + signal + oflayn soni</div>' % (t["muted"], STATUS["warning"]))
    out.append("</div>")
    return "".join(out)

def level_chip(t, level, compact=False):
    kind, col = LEVEL[level]
    if level == "SECURITY":
        col = t["security"]
    if level == "INFO":
        col = t["muted"]
    ic = {"CRITICAL": "alert", "WARNING": "clock", "SECURITY": "shield", "INFO": "info"}[level]
    txt = "" if compact else level
    return ('<span style="display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; border-radius: %s; font-size: 10.5px; font-weight: 700; letter-spacing: .06em; color: %s; background: %s; border: 1px solid %s">%s%s</span>'
            % (t["chipRadius"], col, t["chipBg"], col, icon(ic, 12, col, 2.2), txt))

def alerts_block(t, height, dense=False, limit=6):
    out = ['<div style="display: flex; flex-direction: column; gap: %dpx; height: %dpx; overflow: hidden">' % (6 if dense else 10, height)]
    for level, tm, where, what in ALERTS[:limit]:
        out.append('<div style="display: flex; gap: 10px; align-items: flex-start; padding: %s; border-bottom: 1px solid %s">' % ("6px 0" if dense else "8px 0", t["border"]))
        out.append('<span style="font-family: %s; font-size: 12px; color: %s; width: 40px; flex-shrink: 0; padding-top: 3px">%s</span>' % (t["fontMono"], t["muted"], tm))
        out.append('<div style="display: flex; flex-direction: column; gap: 3px; min-width: 0; flex-grow: 1"><div style="display: flex; align-items: center; gap: 8px">%s<span style="font-size: 12.5px; font-weight: 600; color: %s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">%s</span></div><div style="font-size: 12.5px; color: %s">%s</div></div>' % (level_chip(t, level, compact=dense), t["text"], esc(where), t["muted"], esc(what)))
        out.append("</div>")
    out.append("</div>")
    return "".join(out)

def status_chip(t, st):
    label = {"good": "Me'yorda", "warning": "Kechikish", "critical": "Signal"}[st]
    ic = {"good": "check", "warning": "clock", "critical": "alert"}[st]
    col = STATUS["good"] if st == "good" else STATUS[st]
    if st == "good" and not t["dark"]:
        col = "#006300"
    return '<span style="display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: %s">%s%s</span>' % (col, icon(ic, 13, col, 2.2), label)

def region_table(t, row_h=24, font=12.5, rows=None, show_status=True, columns="full", cols=("ya", "be", "ke", "ra", "si", "of")):
    rows = rows or ROWS
    th = 'style="text-align: right; font-weight: 600; font-size: 11px; letter-spacing: .05em; text-transform: uppercase; color: %s; padding: 0 8px 6px 8px; border-bottom: 1px solid %s; white-space: nowrap"' % (t["muted"], t["border"])
    thl = th.replace("text-align: right", "text-align: left")
    out = ['<table style="width: 100%%; border-collapse: collapse; font-size: %spx; color: %s; font-variant-numeric: tabular-nums">' % (font, t["text"])]
    HEAD = {"ya": "Yacheyka", "be": "Berilgan", "ke": "Kechikish", "ra": "Rad etish", "si": "Signal", "of": "Oflayn"}
    heads = [("Hudud", thl)] + [(HEAD[c], th) for c in cols]
    if show_status:
        heads.append(("Holat", thl))
    out.append("<thead><tr>" + "".join("<th %s>%s</th>" % (s, h) for h, s in heads) + "</tr></thead><tbody>")
    for iso, ya, be, ke, ra, si, of, st in rows:
        name = MAP["regions"][iso]["name"] if columns == "full" else MAP["regions"][iso]["short"]
        td = 'style="padding: 0 8px; height: %dpx; text-align: right; border-bottom: 1px solid %s; white-space: nowrap"' % (row_h, t["border"])
        tdl = td.replace("text-align: right", "text-align: left")
        def num(v, bad):
            if v and bad:
                return '<span style="color: %s; font-weight: 700">%d</span>' % (STATUS["critical"] if bad == "critical" else STATUS["warning"] if t["dark"] else "#8a5a00", v)
            return "%d" % v if v else '<span style="color: %s">0</span>' % t["muted"]
        VAL = {"ya": "{:,}".format(ya).replace(",", " "), "be": "%d" % be, "ke": num(ke, "warning"), "ra": num(ra, "warning"), "si": num(si, "critical"), "of": num(of, "critical")}
        cells = ['<td %s><span style="font-weight: 600">%s</span></td>' % (tdl, esc(name))] + ['<td %s>%s</td>' % (td, VAL[c]) for c in cols]
        if show_status:
            cells.append('<td %s>%s</td>' % (tdl, status_chip(t, st)))
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)

def bars(t, width, height, color=None):
    color = color or t["series"]
    mx = max(v for _, v in DAYS)
    n = len(DAYS); slot = width / n; bw = slot * 0.5
    parts = ['<svg width="%d" height="%d" viewBox="0 0 %d %d" style="display: block">' % (width, height, width, height)]
    base = height - 18
    for i, (d, v) in enumerate(DAYS):
        h = (base - 14) * v / mx
        x = i * slot + (slot - bw) / 2
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" ry="4" fill="%s"/><rect x="%.1f" y="%.1f" width="%.1f" height="4" fill="%s"/>' % (x, base - h, bw, h, color, x, base - 4, bw, color))
        parts.append('<text x="%.1f" y="%d" font-size="11" font-family="%s" fill="%s" text-anchor="middle">%s</text>' % (x + bw / 2, height - 3, t["fontBody"], t["muted"], d))
        if i == 4:
            parts.append('<text x="%.1f" y="%.1f" font-size="11.5" font-weight="700" font-family="%s" fill="%s" text-anchor="middle">%s</text>' % (x + bw / 2, base - h - 5, t["fontBody"], t["text"], "{:,}".format(v).replace(",", " ")))
    parts.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (base, width, base, t["border"]))
    parts.append("</svg>")
    return "".join(parts)

def kpi_tile(t, label, value, sub, st, w=None, h=84, big=False, radius=None, border=True):
    col = t["text"]
    if st == "critical":
        col = STATUS["critical"]
    elif st == "warning":
        col = STATUS["warning"] if t["dark"] else "#8a5a00"
    style = "display: flex; flex-direction: column; justify-content: space-between; padding: %s; background: %s; border-radius: %s; %s %s min-width: 0;" % (
        "14px 16px" if big else "10px 12px", t["surface"], radius or t["radius"], ("border: 1px solid %s;" % t["border"]) if border else "", t.get("shadow", ""))
    if w:
        style += " width: %dpx; flex-shrink: 0;" % w
    else:
        style += " flex: 1 1 0;"
    style += " height: %dpx; box-sizing: border-box;" % h
    return ('<div style="%s"><div style="font-size: %spx; color: %s; letter-spacing: .02em; line-height: 1.15; height: %spx; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical">%s</div><div style="display: flex; flex-direction: column; gap: 3px"><span style="font-family: %s; font-size: %spx; font-weight: 700; color: %s; line-height: 1; white-space: nowrap">%s</span><span style="font-size: 10.5px; color: %s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">%s</span></div></div>'
            % (style, "12" if big else "11", t["muted"], "28" if big else "26", esc(label), t["fontNum"], "30" if big else "22", col, esc(value), t["muted"], esc(sub)))

def nav_vertical(t, width, active=0, brand=True, compact=False, radius="8px", pill=False):
    out = ['<div style="width: %dpx; flex-shrink: 0; display: flex; flex-direction: column; background: %s; border-right: 1px solid %s; height: 100%%; box-sizing: border-box">' % (width, t["nav"], t["border"])]
    if brand:
        out.append('<div style="display: flex; align-items: center; gap: 10px; padding: 18px 18px 14px 18px"><span style="width: 32px; height: 32px; border-radius: 8px; background: %s; display: inline-flex; align-items: center; justify-content: center">%s</span><div style="display: flex; flex-direction: column"><span style="font-family: %s; font-weight: 700; font-size: 15px; color: %s; line-height: 1.1">Aqlli qurolxona</span><span style="font-size: 11px; color: %s">Respublika · IIV</span></div></div>' % (t["accent"], icon("shield", 18, "#fff", 2), t["fontHead"], t["text"], t["muted"]))
    out.append('<div style="display: flex; flex-direction: column; gap: 2px; padding: 6px 10px">')
    for i, (label, ic) in enumerate(zip(NAV, NAV_ICON)):
        act = i == active
        bg = (t["accentSoft"] if act else "transparent")
        col = t["accentText"] if act else t["navText"]
        out.append('<div style="display: flex; align-items: center; gap: 10px; padding: %s; border-radius: %s; background: %s; color: %s; font-size: 13.5px; font-weight: %s">%s<span>%s</span>%s</div>' % ("9px 10px" if not compact else "7px 10px", "999px" if pill else radius, bg, col, "600" if act else "500", icon(ic, 17, col, 1.8), esc(label), ('<span style="margin-left: auto; font-size: 11px; font-weight: 700; color: #fff; background: %s; border-radius: 999px; padding: 1px 7px">7</span>' % STATUS["critical"]) if label == "Signal markazi" else ""))
    out.append("</div>")
    out.append('<div style="margin-top: auto; padding: 14px 18px; border-top: 1px solid %s; display: flex; flex-direction: column; gap: 3px"><span style="font-size: 12.5px; font-weight: 600; color: %s">Tekshiruvchi</span><span style="font-size: 11px; color: %s">IIV markaziy apparati · respublika</span></div>' % (t["border"], t["text"], t["muted"]))
    out.append("</div>")
    return "".join(out)

def rail(t, active=0):
    out = ['<div style="width: 72px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; background: %s; border-right: 1px solid %s; height: 100%%; box-sizing: border-box; padding: 14px 0; gap: 4px">' % (t["nav"], t["border"])]
    out.append('<span style="width: 36px; height: 36px; border-radius: 10px; background: %s; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 10px">%s</span>' % (t["accent"], icon("shield", 20, "#fff", 2)))
    for i, (label, ic) in enumerate(zip(NAV, NAV_ICON)):
        act = i == active
        col = t["accentText"] if act else t["navText"]
        out.append('<div style="display: flex; flex-direction: column; align-items: center; gap: 3px; width: 60px; padding: 6px 0; border-radius: 8px; background: %s; color: %s; position: relative">%s<span style="font-size: 9px; letter-spacing: .02em; text-align: center; line-height: 1.1">%s</span>%s</div>' % (t["accentSoft"] if act else "transparent", col, icon(ic, 18, col, 1.8), esc(label if len(label) < 12 else label.split()[0]), ('<span style="position: absolute; top: 4px; right: 8px; width: 8px; height: 8px; border-radius: 50%%; background: %s"></span>' % STATUS["critical"]) if label == "Signal markazi" else ""))
    out.append("</div>")
    return "".join(out)

def topbar(t, height=56, title=None, breadcrumb=True, search=True, mode=True, actions=None, tabs=None):
    out = ['<div style="height: %dpx; flex-shrink: 0; display: flex; align-items: center; gap: 16px; padding: 0 20px; background: %s; border-bottom: 1px solid %s; box-sizing: border-box">' % (height, t["surface"], t["border"])]
    if title:
        out.append('<span style="font-family: %s; font-size: 18px; font-weight: 700; color: %s; white-space: nowrap">%s</span>' % (t["fontHead"], t["text"], esc(title)))
    if breadcrumb:
        out.append('<div style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: %s"><span style="font-weight: 600; color: %s">Respublika</span>%s<span>Hudud</span>%s<span>Qurolxona</span>%s<span>Yacheyka</span></div>' % (t["muted"], t["text"], icon("chev", 14, t["muted"]), icon("chev", 14, t["muted"]), icon("chev", 14, t["muted"])))
    if tabs:
        out.append('<div style="display: flex; align-items: center; gap: 2px; margin-left: 8px">')
        for i, lab in enumerate(tabs):
            act = i == 0
            out.append('<span style="padding: 8px 12px; font-size: 13px; font-weight: %s; color: %s; border-bottom: 2px solid %s; letter-spacing: .04em; text-transform: uppercase; font-family: %s">%s</span>' % ("700" if act else "500", t["text"] if act else t["navText"], t["accent"] if act else "transparent", t["fontHead"], esc(lab)))
        out.append("</div>")
    out.append('<div style="flex-grow: 1"></div>')
    if mode:
        out.append('<div style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: %s; background: %s; border: 1px solid %s; color: %s; font-size: 12.5px; font-weight: 700">%s TREVOGA · Toshkent sh., Yunusobod IIB · 41/48 berildi</div>' % (t["chipRadius"], t["chipBg"], STATUS["critical"], STATUS["critical"], icon("flag", 14, STATUS["critical"], 2.2)))
    if search:
        out.append('<div style="display: flex; align-items: center; gap: 8px; width: 260px; height: 34px; padding: 0 10px; border-radius: %s; background: %s; border: 1px solid %s; color: %s; font-size: 12.5px; box-sizing: border-box">%s Xodim, yacheyka, seriya raqami…</div>' % (t["radius"], t["page"], t["border"], t["muted"], icon("search", 15, t["muted"])))
    if actions:
        out.append(actions)
    out.append('<div style="display: flex; align-items: center; gap: 8px; font-family: %s; font-size: 12.5px; color: %s">%s 09:42 · 09.09.2026</div>' % (t["fontMono"], t["muted"], icon("clock", 15, t["muted"])))
    out.append("</div>")
    return "".join(out)

def card(t, body, title=None, right=None, pad=14, style_extra="", radius=None):
    head = ""
    if title:
        head = '<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px"><span style="font-family: %s; font-size: %s; font-weight: 700; color: %s; letter-spacing: %s; %s">%s</span>%s</div>' % (
            t["fontHead"], t["cardTitleSize"], t["text"], t["cardTitleSpacing"], t["cardTitleCase"], esc(title), right or "")
    return '<div style="background: %s; border: 1px solid %s; border-radius: %s; padding: %dpx; box-sizing: border-box; min-width: 0; %s %s">%s%s</div>' % (t["surface"], t["border"], radius or t["radius"], pad, t.get("shadow", ""), style_extra, head, body)

def sample_note(t):
    return '<div style="position: absolute; right: 16px; bottom: 8px; font-size: 10.5px; color: %s; letter-spacing: .04em">NAMUNAVIY MA\'LUMOT · 2026-09-09 09:42</div>' % t["muted"]

def page(t, body, fonts_link):
    return '''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <link rel="stylesheet" href="%s">
  <style>
    body { margin: 0; background: %s; }
    a { color: %s; } a:hover { color: %s; }
    table { border-spacing: 0; }
  </style>
</helmet>
<div style="width: 1440px; height: 900px; overflow: hidden; position: relative; display: flex; background: %s; color: %s; font-family: %s; font-size: 13px; line-height: 1.35; -webkit-font-smoothing: antialiased">
%s
%s
</div>
</x-dc>
</body>
</html>
''' % (fonts_link, t["page"], t["accentText"], t["accent"], t["page"], t["text"], t["fontBody"], body, sample_note(t))

# ---------------- themes ----------------
A = dict(id="a", dark=True, page="#0b1118", surface="#121a24", nav="#0e151d", border="rgba(255,255,255,0.08)", text="#e6edf3", muted="#8b9bab",
         accent="#3987e5", accentSoft="rgba(57,135,229,0.16)", accentText="#7fb2f0", navText="#9fb0c0", series="#3987e5", security="#9085e9",
         mapBase="#1f2c3a", mapStroke="#0b1118", mapOpacity="0.85", mapLabel="#e6edf3", mapLabelHalo="rgba(11,17,24,0.85)",
         fontHead="'IBM Plex Sans', 'Segoe UI', sans-serif", fontBody="'IBM Plex Sans', 'Segoe UI', sans-serif", fontNum="'IBM Plex Mono', Consolas, monospace", fontMono="'IBM Plex Mono', Consolas, monospace",
         radius="6px", chipRadius="4px", chipBg="rgba(255,255,255,0.04)", cardTitleSize="12px", cardTitleSpacing=".08em", cardTitleCase="text-transform: uppercase;")
B = dict(id="b", dark=False, page="#f3f2ee", surface="#ffffff", nav="#1f3a5f", border="#d9d6cf", text="#1a1a1a", muted="#5f6368",
         accent="#1f3a5f", accentSoft="rgba(255,255,255,0.14)", accentText="#ffffff", navText="#c9d3e0", series="#2a78d6", security="#4a3aa7",
         mapBase="#dfe6ee", mapStroke="#ffffff", mapOpacity="0.8", mapLabel="#1a1a1a", mapLabelHalo="rgba(255,255,255,0.85)",
         fontHead="'Source Serif 4', Georgia, serif", fontBody="'Source Sans 3', 'Segoe UI', sans-serif", fontNum="'Source Serif 4', Georgia, serif", fontMono="Consolas, 'Courier New', monospace",
         radius="4px", chipRadius="3px", chipBg="#ffffff", cardTitleSize="15px", cardTitleSpacing="0", cardTitleCase="")
C = dict(id="c", dark=True, page="#12160f", surface="#1a2017", nav="#161c13", border="rgba(255,255,255,0.10)", text="#e8eadf", muted="#9aa38f",
         accent="#c8a94a", accentSoft="rgba(200,169,74,0.16)", accentText="#e2c76a", navText="#aab39f", series="#c8a94a", security="#9085e9",
         mapBase="#2b3526", mapStroke="#12160f", mapOpacity="0.85", mapLabel="#e8eadf", mapLabelHalo="rgba(18,22,15,0.85)", hatch=True,
         fontHead="'Barlow Condensed', 'Arial Narrow', sans-serif", fontBody="'Barlow', 'Segoe UI', sans-serif", fontNum="'Barlow Condensed', 'Arial Narrow', sans-serif", fontMono="'Barlow', 'Segoe UI', sans-serif",
         radius="2px", chipRadius="2px", chipBg="rgba(0,0,0,0.25)", cardTitleSize="14px", cardTitleSpacing=".1em", cardTitleCase="text-transform: uppercase;")
D = dict(id="d", dark=False, page="#f4f5f7", surface="#ffffff", nav="#ffffff", border="#e5e7eb", text="#111827", muted="#6b7280",
         accent="#2a78d6", accentSoft="#e8f0fb", accentText="#1c5cab", navText="#4b5563", series="#2a78d6", security="#4a3aa7",
         mapBase="#e5e9f0", mapStroke="#ffffff", mapOpacity="0.8", mapLabel="#111827", mapLabelHalo="rgba(255,255,255,0.85)",
         fontHead="'Manrope', 'Segoe UI', sans-serif", fontBody="'Manrope', 'Segoe UI', sans-serif", fontNum="'Manrope', 'Segoe UI', sans-serif", fontMono="'Manrope', 'Segoe UI', sans-serif",
         radius="14px", chipRadius="999px", chipBg="#ffffff", cardTitleSize="14px", cardTitleSpacing="0", cardTitleCase="", shadow="box-shadow: 0 1px 2px rgba(17,24,39,0.04), 0 6px 20px rgba(17,24,39,0.05);")

FONTS = {
    "a": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;700&display=swap",
    "b": "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=Source+Sans+3:wght@400;600;700&display=swap",
    "c": "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600&display=swap",
    "d": "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap",
}

# ---------------- A: Nazorat markazi ----------------
def build_A():
    t = A
    kpis = '<div style="display: flex; gap: 10px">' + "".join(kpi_tile(t, *k, h=90) for k in KPI) + "</div>"
    sync = '<div style="display: flex; align-items: center; gap: 10px; font-size: 12px; color: %s">%s 212 qurolxona · <span style="color: %s; font-weight: 600">209 onlayn</span> · <span style="color: %s; font-weight: 600">3 oflayn</span> · sinxron 09:42:10</div>' % (t["muted"], icon("sync", 14, t["muted"]), STATUS["good"], STATUS["critical"])
    map_card = card(t, '<div style="display: flex; flex-direction: column; gap: 8px">%s%s</div>' % (map_svg(t, 868, 560), legend(t, True)), title="Respublika xaritasi · hududlar holati", right=sync, pad=12, style_extra="width: 892px; flex-shrink: 0;")
    right = '<div style="display: flex; flex-direction: column; gap: 12px; flex-grow: 1; min-width: 0">%s%s</div>' % (
        card(t, alerts_block(t, 236, dense=True, limit=5), title="Signal lentasi · jonli", right='<span style="font-size: 11px; color: %s">7 faol · 2 tasdiq kutmoqda</span>' % t["muted"], pad=12),
        card(t, region_table(t, row_h=21, font=11.5, show_status=False, columns="short", cols=("ya", "be", "ke", "si", "of")), title="Hududlar · KPI", right='<span style="font-size: 11px; color: %s">saralash: kechikish</span>' % t["muted"], pad=12))
    chart = card(t, bars(t, 860, 100), title="Sutkalik olish-qaytarish · 7 kun", right='<span style="font-size: 11px; color: %s">jami operatsiyalar, respublika</span>' % t["muted"], pad=12, style_extra="width: 892px; flex-shrink: 0;")
    body = rail(t) + '<div style="display: flex; flex-direction: column; flex-grow: 1; min-width: 0">' + topbar(t) + \
        '<div style="display: flex; flex-direction: column; gap: 12px; padding: 12px 16px; flex-grow: 1; min-height: 0">%s<div style="display: flex; gap: 12px; flex-grow: 1; min-height: 0">%s%s</div>%s</div></div>' % (kpis, map_card, right, chart)
    return page(t, body, FONTS["a"])

# ---------------- B: Rasmiy ----------------
def build_B():
    t = B
    actions = '<div style="display: flex; align-items: center; gap: 8px"><span style="display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 12px; border: 1px solid %s; border-radius: 4px; font-size: 12.5px; color: %s; background: #fff">%s 09.09.2026</span><span style="display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 12px; border-radius: 4px; font-size: 12.5px; font-weight: 600; color: #fff; background: %s">%s Hisobot</span></div>' % (t["border"], t["text"], icon("clock", 14, t["muted"]), t["accent"], icon("download", 14, "#fff", 2))
    kpis = '<div style="display: flex; gap: 10px">' + "".join(kpi_tile(t, *k, h=90) for k in KPI) + "</div>"
    sync = '<span style="font-size: 12px; color: %s">209 / 212 qurolxona onlayn · sinxron 09:42</span>' % t["muted"]
    map_card = card(t, '<div style="display: flex; flex-direction: column; gap: 8px">%s%s</div>' % (map_svg(t, 572, 378, label_size=12), legend(t, False)), title="Hududlar bo'yicha holat", right=sync, pad=14, style_extra="width: 602px; flex-shrink: 0;")
    table_card = card(t, region_table(t, row_h=25, font=12.5, show_status=True, columns="short", cols=("ya", "be", "ke", "si", "of")), title="Hududlar jadvali", right='<span style="font-size: 12px; color: %s">14 hudud · saralash: yacheyka</span>' % t["muted"], pad=14, style_extra="flex-grow: 1; min-width: 0;")
    alerts_inner = alerts_block(t, 112, dense=True, limit=4).replace("flex-direction: column", "flex-direction: row; flex-wrap: wrap").replace("gap: 6px; height: 112px", "gap: 0 24px; height: 112px")
    alerts_inner = alerts_inner.replace('<div style="display: flex; gap: 10px; align-items: flex-start; padding: 6px 0;', '<div style="display: flex; gap: 10px; align-items: flex-start; padding: 6px 0; width: calc(50% - 12px); box-sizing: border-box;')
    alerts = card(t, alerts_inner, title="So'nggi signallar", right='<span style="font-size: 12px; color: %s">Signal markaziga o\'tish</span>' % t["accentText"], pad=14)
    body = nav_vertical(t, 240, radius="4px") + '<div style="display: flex; flex-direction: column; flex-grow: 1; min-width: 0">' + topbar(t, height=64, title="Respublika bo'yicha holat", breadcrumb=False, search=True, mode=True, actions=actions) + \
        '<div style="display: flex; flex-direction: column; gap: 14px; padding: 16px 20px; flex-grow: 1; min-height: 0">%s<div style="display: flex; gap: 14px; flex-grow: 1; min-height: 0">%s%s</div>%s</div></div>' % (kpis, map_card, table_card, alerts)
    return page(t, body, FONTS["b"])

# ---------------- C: Harbiy ----------------
def build_C():
    t = C
    banner = '<div style="height: 40px; flex-shrink: 0; display: flex; align-items: center; gap: 14px; padding: 0 20px; background: repeating-linear-gradient(135deg, rgba(208,59,59,0.22) 0 10px, rgba(208,59,59,0.08) 10px 20px); border-bottom: 1px solid %s; color: %s; font-family: %s; font-size: 15px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase">%s TREVOGA rejimi faol · Toshkent sh., Yunusobod IIB · 08:50 dan · 41 / 48 qurol berildi · navbatda 7 · o\'rtacha 38 s<span style="margin-left: auto; font-size: 12px; letter-spacing: .06em; color: %s">boshlagan: Navbatchi · tasdiq: Komandir</span></div>' % (STATUS["critical"], "#ffd9d9", t["fontHead"], icon("flag", 16, "#ffd9d9", 2.2), t["muted"])
    kpi_grid = '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; width: 420px; flex-shrink: 0; align-content: start">' + "".join(kpi_tile(t, *k, h=118, big=True) for k in KPI) + "</div>"
    map_card = card(t, '<div style="display: flex; flex-direction: column; gap: 8px">%s%s</div>' % (map_svg(t, 596, 393, label_size=12), legend(t, True)), title="Operatsion xarita", right='<span style="font-size: 12px; color: %s; letter-spacing: .06em">209 / 212 ONLAYN</span>' % t["muted"], pad=12, style_extra="width: 622px; flex-shrink: 0;")
    alerts = card(t, alerts_block(t, 420, dense=False), title="Signallar", right=level_chip(t, "CRITICAL"), pad=12, style_extra="flex-grow: 1; min-width: 0;")
    left_rows, right_rows = ROWS[:7], ROWS[7:]
    tbl = '<div style="display: flex; gap: 24px"><div style="flex: 1 1 0; min-width: 0">%s</div><div style="flex: 1 1 0; min-width: 0">%s</div></div>' % (
        region_table(t, row_h=26, font=13, rows=left_rows, show_status=False, columns="full"), region_table(t, row_h=26, font=13, rows=right_rows, show_status=False, columns="full"))
    table_card = card(t, tbl, title="Hududlar · 14", right='<span style="font-size: 12px; color: %s; letter-spacing: .06em">JAMI 5 512 YACHEYKA · 1 284 BERILGAN · 17 KECHIKISH</span>' % t["muted"], pad=12)
    body = '<div style="display: flex; flex-direction: column; flex-grow: 1; min-width: 0">' + topbar(t, height=56, title="AQLLI QUROLXONA", breadcrumb=False, search=True, mode=False, tabs=NAV[:8]) + banner + \
        '<div style="display: flex; flex-direction: column; gap: 12px; padding: 12px 20px; flex-grow: 1; min-height: 0"><div style="display: flex; gap: 12px">%s%s%s</div>%s</div></div>' % (kpi_grid, map_card, alerts, table_card)
    return page(t, body, FONTS["c"])

# ---------------- D: Yengil ----------------
def build_D():
    t = D
    actions = '<div style="display: flex; align-items: center; gap: 8px"><span style="display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 14px; border: 1px solid %s; border-radius: 999px; font-size: 12.5px; font-weight: 600; color: %s; background: #fff">%s Bugun</span><span style="display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 14px; border-radius: 999px; font-size: 12.5px; font-weight: 700; color: #fff; background: %s">%s Eksport</span></div>' % (t["border"], t["text"], icon("clock", 14, t["muted"]), t["accent"], icon("download", 14, "#fff", 2))
    kpi_grid = '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; width: 372px; flex-shrink: 0; align-content: start">' + "".join(kpi_tile(t, *k, h=106, big=True, border=False) for k in KPI) + "</div>"
    map_card = card(t, '<div style="display: flex; flex-direction: column; gap: 10px">%s%s</div>' % (map_svg(t, 408, 269, label_size=10, badges=True), legend(t, False)), title="Respublika xaritasi", right='<span style="font-size: 12px; color: %s">209 / 212 onlayn</span>' % t["muted"], pad=16, style_extra="width: 440px; flex-shrink: 0; border: 0;")
    alerts = card(t, alerts_block(t, 292, dense=False, limit=5), title="Signal lentasi", right='<span style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700; color: #fff; background: %s; border-radius: 999px; padding: 3px 10px">7 faol</span>' % STATUS["critical"], pad=16, style_extra="flex-grow: 1; min-width: 0; border: 0;")
    chart = card(t, bars(t, 372 - 32, 200), title="Olish-qaytarish · 7 kun", right='<span style="font-size: 12px; color: %s">respublika</span>' % t["muted"], pad=16, style_extra="width: 372px; flex-shrink: 0; border: 0;")
    table_card = card(t, region_table(t, row_h=20, font=11.5, show_status=True, columns="short"), title="Hududlar", right='<span style="font-size: 12px; color: %s; font-weight: 600">Barchasini ko\'rish</span>' % t["accentText"], pad=16, style_extra="flex-grow: 1; min-width: 0; border: 0;")
    body = nav_vertical(t, 232, radius="10px", pill=True) + '<div style="display: flex; flex-direction: column; flex-grow: 1; min-width: 0">' + topbar(t, height=72, title="Respublika holati", breadcrumb=False, search=True, mode=True, actions=actions) + \
        '<div style="display: flex; flex-direction: column; gap: 14px; padding: 16px 20px; flex-grow: 1; min-height: 0"><div style="display: flex; gap: 14px">%s%s%s</div><div style="display: flex; gap: 14px; flex-grow: 1; min-height: 0">%s%s</div></div></div>' % (kpi_grid, map_card, alerts, chart, table_card)
    return page(t, body, FONTS["d"])

files = {"Main.dc.html": build_A(), "Rasmiy.dc.html": build_B(), "Harbiy.dc.html": build_C(), "Yengil.dc.html": build_D()}
for name, src in files.items():
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(src)
    print(name, len(src), "bytes")

canvas = {
    "artboards": [
        {"file": "Main.dc.html", "title": "A · Nazorat markazi", "x": 0, "y": 0, "w": 1440, "h": 900},
        {"file": "Rasmiy.dc.html", "title": "B · Rasmiy", "x": 1560, "y": 0, "w": 1440, "h": 900},
        {"file": "Harbiy.dc.html", "title": "C · Harbiy", "x": 0, "y": 1120, "w": 1440, "h": 900},
        {"file": "Yengil.dc.html", "title": "D · Yengil", "x": 1560, "y": 1120, "w": 1440, "h": 900},
    ],
    "annotations": [
        {"id": "brief", "x": 0, "y": -300, "w": 1440, "text": "Respublika dashboardi: kirish ekrani uchun 4 ta yo'nalish. Bir xil namunaviy ma'lumot: 14 hudud, 5 512 yacheyka, 9 KPI, signal lentasi, faol Trevoga rejimi. Tanlangan yo'nalishda butun admin panel (yacheyka, xodim, jurnal, smena ekranlari) quriladi.\nBittasini tanlang: A, B, C yoki D. Aralashtirish ham mumkin, masalan \"A ning ranglari, B ning jadvali\"."},
        {"id": "note-a", "x": 0, "y": -150, "w": 700, "text": "A · Nazorat markazi. Qorong'i fon, xarita ekranning katta qismini egallaydi, tor ikonkali menyu, monoshirift raqamlar. Kimga: sutka bo'yi ekranga qaraydigan navbatchi va nazorat markazi. Kamchiligi: yorug' xonada va chop etishda kontrast pasayadi, matn zich."},
        {"id": "note-b", "x": 1560, "y": -150, "w": 700, "text": "B · Rasmiy. Yorug' fon, to'q ko'k menyu, serif sarlavhalar, jadval ustuvor. Kimga: rahbariyat, tekshiruvchi, rasmiy hisobotlar, chop etish. Kamchiligi: jonli signal lentasi kichikroq, \"tezkor\" his kamroq."},
        {"id": "note-c", "x": 0, "y": 970, "w": 700, "text": "C · Harbiy. Olive-qora fon, kondensat harflar, yuqori menyu, Trevoga banneri butun eni bo'ylab, signalli hududlar shtrixlangan (rangsiz chop etganda ham ko'rinadi). Kimga: harbiy va tezkor bo'linmalar, rejim davomida ishlash. Kamchiligi: fuqarolik ko'rinishdan uzoq, uzoq o'qish uchun og'irroq."},
        {"id": "note-d", "x": 1560, "y": 970, "w": 700, "text": "D · Yengil. Yorug' kulrang fon, yumaloq oq kartochkalar, yumshoq soya, dumaloq tugmalar. Kimga: keng foydalanuvchi doirasi, o'rganish oson, zamonaviy SaaS ko'rinishi. Kamchiligi: davlat tizimi uchun \"yengil\" ko'rinishi mumkin, zichlik past, katta jadvallar ko'proq joy oladi."},
    ],
    "launch": {"view": "canvas"},
}
json.dump(canvas, open(os.path.join(OUT, "canvas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("canvas.json written")

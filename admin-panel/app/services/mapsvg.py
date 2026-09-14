"""O'zbekiston xaritasi (14 hudud) SVG generatori."""
from __future__ import annotations

import json
from functools import lru_cache
from html import escape

from ..config import BASE_DIR

STATUS_FILL = {"critical": "var(--red)", "warning": "var(--yellow)", "good": "var(--map-base)", "nodata": "var(--gray)"}


@lru_cache(maxsize=1)
def regions_geo() -> dict:
    return json.load(open(BASE_DIR / "static" / "data" / "uz_regions.json", encoding="utf-8"))


def region_paths(rows: list[dict], link_base: str = "/hudud/", labels: bool = True, badges: bool = True, label_size: int = 12, *, executive: bool = False) -> str:
    """rows: kpi.region_rows() natijasi. executive — vaziyat markazi uslubi."""
    if executive:
        return _executive_region_paths(rows, link_base, labels, badges, label_size)
    geo = regions_geo()
    by_code = {r["code"]: r for r in rows}
    W, H = geo["w"], geo["h"]
    out = [f'<svg class="uzmap" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="O\'zbekiston xaritasi">',
           '<g class="uzmap-regions">']
    for code, r in geo["regions"].items():
        row = by_code.get(code)
        st = row["status"] if row else "nodata"
        rid = row["id"] if row else 0
        title = f'{r["name"]}: qurol katagi {row["yacheyka"]}, berilgan {row["berilgan"]}, kechikish {row["kechikish"]}, signal {row["signal"]}, oflayn {row["oflayn"]}' if row else r["name"]
        out.append(f'<a href="{link_base}{rid}" class="uzmap-region st-{st}" data-code="{code}" data-id="{rid}" data-name="{escape(r["name"])}">'
                   f'<path d="{r["d"]}" fill="{STATUS_FILL[st]}" fill-opacity="{"0.92" if st in ("critical", "warning") else "1"}" stroke="var(--map-stroke)" stroke-width="1.2" stroke-linejoin="round"><title>{escape(title)}</title></path></a>')
    out.append("</g>")
    if labels:
        out.append('<g class="uzmap-labels" pointer-events="none">')
        for code, r in geo["regions"].items():
            if code == "UZ-TK":
                continue
            out.append(f'<text x="{r["cx"]}" y="{r["cy"] + 4}" font-size="{label_size}" font-weight="600" text-anchor="middle" fill="var(--text)" '
                       f'paint-order="stroke" stroke="var(--bg)" stroke-width="3" stroke-linejoin="round">{escape(r["short"])}</text>')
        tk = geo["regions"]["UZ-TK"]
        out.append(f'<line x1="{tk["cx"]}" y1="{tk["cy"]}" x2="{tk["cx"] + 40}" y2="{tk["cy"] - 46}" stroke="var(--text)" stroke-width="1"/>'
                   f'<text x="{tk["cx"] + 44}" y="{tk["cy"] - 48}" font-size="{label_size}" font-weight="600" fill="var(--text)" paint-order="stroke" stroke="var(--bg)" stroke-width="3">Toshkent sh.</text>')
        out.append("</g>")
    if badges:
        out.append('<g class="uzmap-badges" pointer-events="none">')
        for code, r in geo["regions"].items():
            row = by_code.get(code)
            if not row or not row["badge"]:
                continue
            x, y = (r["cx"], r["cy"] - 16) if code != "UZ-TK" else (r["cx"] + 96, r["cy"] - 52)
            col = "var(--red)" if row["status"] == "critical" else "var(--yellow)"
            out.append(f'<g class="uzmap-badge"><circle cx="{x}" cy="{y}" r="10" fill="{col}" stroke="var(--bg)" stroke-width="2"/>'
                       f'<text x="{x}" y="{y + 4}" font-size="11" font-weight="700" text-anchor="middle" fill="#0a1220">{row["badge"]}</text></g>')
        out.append("</g>")
    out.append("</svg>")
    return "".join(out)


def _executive_region_paths(rows: list[dict], link_base: str, labels: bool, badges: bool, label_size: int) -> str:
    """Geographic overview: quiet region faces and small, data-backed status marks."""
    geo = regions_geo()
    by_code = {row["code"]: row for row in rows}
    width, height = geo["w"], geo["h"]
    out = [
        f'<svg class="uzmap uzmap--executive" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg" role="group" aria-label="O‘zbekiston hududlari holati">',
        '<defs>'
        '<linearGradient id="situation-map-face" x1="0" y1="0" x2="0.35" y2="1">'
        '<stop offset="0" stop-color="#234a70"/><stop offset="0.52" stop-color="#163554"/>'
        '<stop offset="1" stop-color="#102a46"/></linearGradient>'
        '<linearGradient id="situation-map-empty" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#192e43"/><stop offset="1" stop-color="#112135"/></linearGradient>'
        '<filter id="situation-map-depth" x="-20%" y="-20%" width="140%" height="150%" '
        'color-interpolation-filters="sRGB">'
        '<feDropShadow dx="0" dy="9" stdDeviation="10" flood-color="#010916" flood-opacity="0.8"/>'
        '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#2475ad" flood-opacity="0.28"/>'
        '</filter></defs>',
        '<g class="uzmap-depth" aria-hidden="true" pointer-events="none" '
        'transform="translate(0 7)" filter="url(#situation-map-depth)">',
    ]
    for region in geo["regions"].values():
        out.append(f'<path d="{region["d"]}" fill="#103c60" stroke="#28597a" '
                   'stroke-width="1.3" stroke-linejoin="round"/>')
    out.append('</g><g class="uzmap-regions">')
    for code, region in geo["regions"].items():
        row = by_code.get(code)
        status = row.get("status", "nodata") if row else "nodata"
        if status not in STATUS_FILL:
            status = "nodata"
        region_id = row["id"] if row else 0
        title = (
            f'{region["name"]}: qurol katagi {row["yacheyka"]}, berilgan {row["berilgan"]}, '
            f'kechikish {row["kechikish"]}, signal {row["signal"]}, oflayn {row["oflayn"]}'
            if row else f'{region["name"]}: ma’lumot mavjud emas'
        )
        attributes = (
            f'class="uzmap-region st-{status}" data-code="{escape(code, quote=True)}" '
            f'data-id="{escape(str(region_id), quote=True)}" '
            f'data-name="{escape(region["name"], quote=True)}"'
        )
        # Only regions inside the user's scope receive a navigation link.
        if row:
            out.append(f'<a href="{escape(f"{link_base}{region_id}", quote=True)}" {attributes} '
                       f'tabindex="0" role="link" aria-label="{escape(title, quote=True)}">')
        else:
            out.append(f'<g {attributes}>')
        fill = "situation-map-empty" if status == "nodata" else "situation-map-face"
        out.append(f'<path class="uzmap-face" d="{region["d"]}" fill="url(#{fill})" '
                   'stroke="#b5a276" stroke-opacity="0.76" stroke-width="0.9" '
                   f'stroke-linejoin="round"><title>{escape(title)}</title></path>')
        out.append('</a>' if row else '</g>')
    out.append('</g>')
    if labels:
        out.append('<g class="uzmap-labels" aria-hidden="true" pointer-events="none">')
        for code, region in geo["regions"].items():
            if code == "UZ-TK":
                continue
            out.append(f'<text x="{region["cx"]}" y="{region["cy"] + 5}" '
                       f'font-size="{label_size}" font-weight="500" text-anchor="middle" '
                       'fill="#e7e4d9" paint-order="stroke" stroke="#112943" '
                       f'stroke-width="3" stroke-linejoin="round">{escape(region["short"])}</text>')
        tashkent = geo["regions"]["UZ-TK"]
        tx, ty = tashkent["cx"], tashkent["cy"]
        out.append(f'<path d="M{tx} {ty} L{tx + 13} {ty - 39} L{tx + 65} {ty - 39}" '
                   'fill="none" stroke="#c6b589" stroke-width="0.9" stroke-opacity="0.8"/>'
                   f'<text x="{tx + 19}" y="{ty - 46}" font-size="{label_size}" font-weight="600" '
                   'fill="#f0e5c9" paint-order="stroke" stroke="#112943" stroke-width="3">Toshkent sh.</text>')
        out.append('</g>')
    if badges:
        # A marker represents a region's status, not the sum of unlike event counts.
        out.append('<g class="uzmap-badges uzmap-status-markers" aria-hidden="true" pointer-events="none">')
        colors = {"critical": "#ee7977", "warning": "#dfb961", "good": "#72b4ad"}
        for code, region in geo["regions"].items():
            row = by_code.get(code)
            if not row or row.get("status") not in colors:
                continue
            status = row["status"]
            x, y = region["cx"], region["cy"] - 14
            if code == "UZ-TK":
                x, y = region["cx"], region["cy"]
            color = colors[status]
            out.append(f'<g class="uzmap-badge uzmap-status-marker st-{status}">'
                       f'<circle cx="{x}" cy="{y}" r="8" fill="{color}" fill-opacity="0.12" '
                       f'stroke="{color}" stroke-opacity="0.3" stroke-width="0.8"/>'
                       f'<circle cx="{x}" cy="{y}" r="3.2" fill="{color}" '
                       'stroke="#10243b" stroke-width="1.1"/></g>')
        out.append('</g>')
    out.append('</svg>')
    return ''.join(out)

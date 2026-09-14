# Dashboard dizayn yo'nalishlari

Dizayn kanvasi (4 ta yo'nalish, tanlov uchun): https://claude.ai/code/artifact/871ea894-232a-4e1d-978d-70c654f64022

| Papka | Mazmuni |
|---|---|
| gen.py | Artboardlarni yaratuvchi skript (namunaviy ma'lumot, mavzular A/B/C/D, komponentlar). `python gen.py` `artboards/` ni qayta yozadi. |
| artboards/ | Main (A · Nazorat markazi), Rasmiy (B), Harbiy (C), Yengil (D) `.dc.html` fayllari va `canvas.json` |
| xarita/uz_regions.json | O'zbekiston 14 hududi SVG konturlari (viewBox 800×528), qisqa va to'liq nomlar, markazlar. Manba: geoBoundaries ADM1, ODbL 1.0 |
| xarita/geo2svg.py | GeoJSON dan SVG path yasovchi skript (proyeksiya, soddalashtirish) |

Barcha raqamlar namunaviy (5 512 yacheyka, 14 hudud), TZ va talablar hujjatidagi 9 KPI, signal darajalari (INFO, WARNING, CRITICAL, SECURITY) va Trevoga rejimi banneri aks ettirilgan.

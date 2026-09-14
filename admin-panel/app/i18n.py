"""O'zbek lotin asosiy matn; kirill almashtirgich transliteratsiya bilan. Rus tili keyingi bosqich."""
from __future__ import annotations

import re

# Presentation terminology also covers older event descriptions without changing
# stored audit text, route names or data keys. Uzbek case endings are explicit.
_CABINET_TERMS = {
    "yacheyka": "qurol katagi", "yacheykalar": "qurol kataklari",
    "yacheykaga": "qurol katagiga", "yacheykada": "qurol katagida",
    "yacheykadan": "qurol katagidan", "yacheykani": "qurol katagini",
    "yacheykaning": "qurol katagining", "yacheykalari": "qurol kataklari",
    "yacheykalardan": "qurol kataklaridan", "yacheykasida": "qurol katagida",
    "yacheykasiga": "qurol katagiga", "yacheykasiz": "qurol katagisiz",
}
_CABINET_WORD = re.compile(r"(?<![\w/])(" + "|".join(_CABINET_TERMS) + r")(?![\w/])", re.IGNORECASE)


def display_terms(text: str) -> str:
    """Apply the current product vocabulary to human-readable text only."""
    if not isinstance(text, str):
        return text

    def replace(match):
        source = match.group()
        value = _CABINET_TERMS[source.lower()]
        if source.isupper():
            return value.upper()
        return value[0].upper() + value[1:] if source[0].isupper() else value

    return _CABINET_WORD.sub(replace, text)

# Lotin -> kirill: avval ko'p harfli birikmalar, keyin bittalik harflar.
_MULTI = [
    ("o'", "ў"), ("O'", "Ў"), ("o‘", "ў"), ("O‘", "Ў"), ("oʻ", "ў"), ("Oʻ", "Ў"),
    ("g'", "ғ"), ("G'", "Ғ"), ("g‘", "ғ"), ("G‘", "Ғ"), ("gʻ", "ғ"), ("Gʻ", "Ғ"),
    ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
    ("ch", "ч"), ("Ch", "Ч"), ("CH", "Ч"),
    ("ng", "нг"), ("Ng", "Нг"), ("NG", "НГ"),
    ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"),
    ("yu", "ю"), ("Yu", "Ю"), ("YU", "Ю"),
    ("ya", "я"), ("Ya", "Я"), ("YA", "Я"),
    ("ye", "е"), ("Ye", "Е"), ("YE", "Е"),
    ("ts", "ц"), ("Ts", "Ц"), ("TS", "Ц"),
]
_SINGLE = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж", "k": "к", "l": "л",
    "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "x": "х",
    "y": "й", "z": "з", "'": "ъ", "ʼ": "ъ", "’": "ъ",
}
_SINGLE.update({k.upper(): v.upper() for k, v in list(_SINGLE.items()) if k.isalpha()})

# Istisnolar lug'ati: transliteratsiya noto'g'ri beradigan so'zlar
_EXCEPTIONS = {
    "Toshkent": "Тошкент", "Yacheyka": "Ячейка", "yacheyka": "ячейка", "Yacheykalar": "Ячейкалар",
    "Respublika": "Республика", "Hisobotlar": "Ҳисоботлар", "Sozlamalar": "Созламалар", "Yig'ilish": "Йиғилиш",
    "Trevoga": "Тревога", "TREVOGA": "ТРЕВОГА", "AK-74": "АК-74", "PM": "ПМ", "IIB": "ИИБ", "IIV": "ИИВ",
    "KPI": "KPI", "UPS": "UPS", "NTP": "NTP", "RFID": "RFID", "PIN": "PIN", "ID": "ID", "Y-": "Y-",
    "QUROL": "ҚУРОЛ", "KATAGI": "КАТАГИ",
}

_TOKEN = re.compile(r"[A-Za-z'‘’ʻʼ\-]+|[^A-Za-z'‘’ʻʼ\-]+")


def to_cyrillic(text: str) -> str:
    if not text:
        return text
    out = []
    for tok in _TOKEN.findall(text):
        if tok in _EXCEPTIONS:
            out.append(_EXCEPTIONS[tok]); continue
        if not re.search(r"[A-Za-z]", tok):
            out.append(tok); continue
        # raqam-harf kodlari (Y-017, UZ-TK) o'zgarmaydi
        if re.fullmatch(r"[A-Z]{1,3}-?\d*[A-Z]*", tok) and len(tok) <= 6:
            out.append(tok); continue
        s = tok
        for a, b in _MULTI:
            s = s.replace(a, b)
        s = "".join(_SINGLE.get(ch, ch) for ch in s)
        out.append(s)
    return "".join(out)


def t(text: str, lang: str = "lat") -> str:
    text = display_terms(text)
    return to_cyrillic(text) if lang == "cyr" else text

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Keyword dictionaries
# ---------------------------------------------------------------------------

BRANDS: dict[str, list[str]] = {
    "Nike": ["nike"],
    "Adidas": ["adidas"],
    "Puma": ["puma"],
    "Reebok": ["reebok"],
    "New Balance": ["new balance", "newbalance"],
    "Converse": ["converse"],
    "Vans": ["vans"],
    "Under Armour": ["under armour", "underarmour"],
    "Champion": ["champion"],
    "Fila": ["fila"],
    "Zara": ["zara"],
    "H&M": ["h&m", "h and m", "hm"],
    "Uniqlo": ["uniqlo"],
    "Levis": ["levi's", "levis", "levi"],
    "Tommy Hilfiger": ["tommy hilfiger", "tommy"],
    "Ralph Lauren": ["ralph lauren", "polo ralph"],
    "Calvin Klein": ["calvin klein", "ck"],
    "Guess": ["guess"],
    "Hacoo": ["hacoo"],
    "Jacquemus": ["jacquemus"],
    "Lacoste": ["lacoste"],
    "Hugo Boss": ["hugo boss", "boss"],
    "Mango": ["mango"],
    "Stradivarius": ["stradivarius"],
    "Pull&Bear": ["pull&bear", "pull & bear", "pull and bear"],
    "Bershka": ["bershka"],
    "Massimo Dutti": ["massimo dutti"],
    "Stone Island": ["stone island"],
    "The North Face": ["the north face", "north face", "tnf"],
    "Carhartt": ["carhartt"],
    "Dickies": ["dickies"],
    "Tommy Jeans": ["tommy jeans"],
    "Guess": ["guess"],
    "Versace": ["versace"],
    "Armani": ["armani", "emporio armani", "ea7"],
    "Balenciaga": ["balenciaga"],
    "Other": [],
}

CATEGORIES: dict[str, list[str]] = {
    "Hoodies": ["hoodie", "hoody", "sweatshirt", "sudadera"],
    "T-Shirts": ["t-shirt", "tshirt", "tee", "camiseta"],
    "Shoes": ["shoe", "shoes", "sneaker", "sneakers", "trainer", "trainers", "zapatilla", "zapatillas"],
    "Pants": ["pant", "pants", "trouser", "trousers", "jeans", "jogger", "joggers", "pantalon"],
    "Jackets": ["jacket", "coat", "parka", "chaqueta", "abrigo"],
    "Shorts": ["short", "shorts"],
    "Dresses": ["dress", "dresses", "vestido"],
    "Accessories": ["cap", "hat", "bag", "backpack", "socks", "belt", "gorra", "mochila"],
    "Other": [],
}

COLORS: dict[str, list[str]] = {
    "Black": ["black", "negro", "negra"],
    "White": ["white", "blanco", "blanca"],
    "Red": ["red", "rojo", "roja"],
    "Blue": ["blue", "azul"],
    "Navy": ["navy", "navy blue", "marino"],
    "Green": ["green", "verde"],
    "Grey": ["grey", "gray", "gris"],
    "Pink": ["pink", "rosa"],
    "Yellow": ["yellow", "amarillo", "amarilla"],
    "Orange": ["orange", "naranja"],
    "Purple": ["purple", "morado", "lila"],
    "Brown": ["brown", "marron", "marrón"],
    "Beige": ["beige", "cream", "crema"],
    "Other": [],
}

# Pre-compile URL pattern
_URL_RE = re.compile(r"https?://[^\s]+")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParsedPost:
    brand: str = "Other"
    category: str = "Other"
    color: str = "Other"
    title: str = ""
    description: str = ""
    external_link: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_keyword_dict(text_lower: str, mapping: dict[str, list[str]]) -> str:
    """Return the first key whose keywords appear in text_lower, else 'Other'."""
    for canonical, keywords in mapping.items():
        if canonical == "Other":
            continue
        for kw in keywords:
            if kw in text_lower:
                return canonical
    return "Other"


def _extract_external_link(text: str) -> str | None:
    """Return the first non-Telegram URL found in text, or None."""
    for url in _URL_RE.findall(text):
        if "t.me" not in url and "telegram" not in url.lower():
            return url
    return None


def _build_title(text: str) -> str:
    """Use the first non-empty non-URL line as title, truncated to 255 chars."""
    for line in text.splitlines():
        line = line.strip()
        if line and not _URL_RE.match(line):
            return line[:255]
    return text[:255]


def _build_description(text: str) -> str:
    """Return up to 500 chars of the full text as a short description."""
    return text.strip()[:500]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_post(text: str) -> ParsedPost:
    """Extract brand, category, color, title, description, and external link from post text."""
    text_lower = text.lower()

    brand = _match_keyword_dict(text_lower, BRANDS)
    category = _match_keyword_dict(text_lower, CATEGORIES)
    color = _match_keyword_dict(text_lower, COLORS)
    title = _build_title(text)
    description = _build_description(text)
    external_link = _extract_external_link(text)

    return ParsedPost(
        brand=brand,
        category=category,
        color=color,
        title=title,
        description=description,
        external_link=external_link,
    )

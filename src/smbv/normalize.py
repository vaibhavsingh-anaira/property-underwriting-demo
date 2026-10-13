"""Name and address normalisation shared by every matcher."""
from __future__ import annotations
import math
import re

ABBR = {"AVENUE": "AVE", "AV": "AVE", "STREET": "ST", "STR": "ST", "ROAD": "RD", "PLACE": "PL", "BOULEVARD": "BLVD",
        "PARKWAY": "PKWY", "EAST": "E", "WEST": "W", "NORTH": "N", "SOUTH": "S", "LANE": "LN", "DRIVE": "DR",
        "SQUARE": "SQ", "TERRACE": "TER", "COURT": "CT", "HIGHWAY": "HWY", "FIRST": "1", "SECOND": "2", "THIRD": "3",
        "FOURTH": "4", "FIFTH": "5", "SIXTH": "6", "SEVENTH": "7", "EIGHTH": "8", "NINTH": "9", "TENTH": "10",
        "ELEVENTH": "11", "TWELFTH": "12", "SAINT": "ST"}
STOP = {"INC", "LLC", "CORP", "CORPORATION", "CO", "LTD", "THE", "RESTAURANT", "REST", "BAR", "CAFE", "GRILL",
        "KITCHEN", "NYC", "NY", "OF", "AND", "DBA", "L", "P", "LP"}


def _s(x) -> str:
    return x if isinstance(x, str) else ""


def street(s) -> str:
    s = re.sub(r"[^A-Z0-9 ]", " ", _s(s).upper())
    s = re.sub(r"\b(\d+)(ST|ND|RD|TH)\b", r"\1", s)
    return " ".join(ABBR.get(w, w) for w in s.split())


def house(s) -> str:
    m = re.match(r"\s*(\d+)", _s(s))
    return m.group(1) if m else ""


def split_address(a) -> tuple[str, str]:
    """'175 179 W 4TH STREET' and '54-56 GANSEVOORT ST' are ranges -> first number; '45 1 AVENUE' is 45 First Avenue."""
    m = re.match(r"\s*(\d+[-\d]*)\s+(.*)", _s(a).upper())
    if not m:
        return "", street(a)
    num, rest = house(m.group(1)), m.group(2)
    r = re.match(r"(\d+)\s+(\S.*)", rest)
    if r and num and int(r.group(1)) > int(num) and len(r.group(2).split()) >= 2:
        rest = r.group(2)
    return num, street(rest)


GENERIC = {"BAKERY", "PIZZA", "PIZZERIA", "DELI", "GOURMET", "DINER", "FOOD", "FOODS", "HOUSE", "EXPRESS", "CHINESE", "THAI",
           "JAPANESE", "SUSHI", "MEXICAN", "ITALIAN", "INDIAN", "KOREAN", "TACO", "TACOS", "COFFEE", "TEA", "SHOP", "MARKET",
           "BURGER", "BURGERS", "CHICKEN", "BAGEL", "BAGELS", "NEW", "YORK", "MANHATTAN", "HOTEL", "TAVERN", "LOUNGE", "PUB",
           "WINE", "CUCINA", "TRATTORIA", "BISTRO", "EATERY", "CANTINA", "STEAKHOUSE", "RAMEN", "NOODLE", "NOODLES", "HALAL",
           "CATERING", "SERVICES", "HOSPITALITY", "GROUP", "HOLDINGS", "ENTERPRISES", "MANAGEMENT", "VENTURES", "1", "2", "3", "I", "II",
           # NYC place words: they locate a business, they don't identify it ('WELLS FARGO 30 HUDSON YARDS' vs 'QUEENSYARD')
           "HUDSON", "YARDS", "TIMES", "SQUARE", "BROADWAY", "PARK", "AVE", "AVENUE", "CENTRAL", "CHELSEA", "SOHO", "TRIBECA",
           "HARLEM", "VILLAGE", "MIDTOWN", "DOWNTOWN", "UPTOWN", "E", "W", "EAST", "WEST", "WALL", "PLAZA", "CENTER",
           "ROCKEFELLER", "GRAND", "STATION", "PIER", "MADISON", "LEXINGTON", "BOWERY", "UNION", "WASHINGTON", "HEIGHTS"}


def distinctive(normalized: str) -> set[str]:
    return {w for w in normalized.split() if w not in GENERIC and len(w) > 1}


def name(s) -> str:
    s = re.sub(r"[^A-Z0-9 ]", " ", _s(s).upper().replace("'", "").replace("&", " AND "))
    return " ".join(w for w in s.split() if w not in STOP)


def meters(la1, lo1, la2, lo2) -> float:
    p = math.pi / 180
    a = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 12742000 * math.asin(math.sqrt(a))


def grid(lat: float, lon: float) -> tuple[int, int]:
    """Grid cells of 0.001 degree (~111 m x ~84 m in NYC) for neighbour search."""
    return round(lat * 1000), round(lon * 1000)


_TIME = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")


def closes_after_midnight(opening_hours: str | None) -> bool | None:
    """True if any OSM opening_hours range ends between 00:00 and 05:00 (or at 24:00+). None if unparseable."""
    if not isinstance(opening_hours, str) or not opening_hours:
        return None
    if "24/7" in opening_hours:
        return True
    ranges = _TIME.findall(opening_hours)
    if not ranges:
        return None
    for h1, _, h2, m2 in ranges:
        start, end = int(h1), int(h2) + int(m2) / 60
        if end >= 24 or (end < start and end > 0) or (end <= 5 and end > 0 and start >= 12):
            return True
    return False


_LONLAT = re.compile(r"POINT \(([-\d.]+) ([-\d.]+)\)|\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]")


def lon_lat(geo) -> tuple[float, float] | tuple[None, None]:
    """Socrata point as WKT 'POINT (lon lat)' or GeoJSON {'coordinates': [lon, lat]}."""
    m = _LONLAT.search(_s(geo))
    if not m:
        return None, None
    lon, lat = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    return float(lon), float(lat)


def bbl(x) -> str | None:
    """10-digit borough-block-lot; PLUTO publishes '1020660059.00000000'."""
    d = _s(x).split(".")[0].strip()
    return d.zfill(10) if d.isdigit() and int(d) > 0 else None

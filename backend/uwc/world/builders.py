"""Helpers for building truth objects."""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

from uwc.refdata import CITIES, STREETS
from uwc.world.truth import Building, Location, Values

ZIPS = {"FL": "336", "TX": "750", "LA": "708", "SC": "294", "NC": "284", "CA": "926", "NV": "895", "CO": "802", "VA": "201",
        "OH": "454", "PA": "152", "IL": "606", "GA": "303", "TN": "372", "AZ": "850", "MN": "554", "MA": "021", "WA": "981",
        "MI": "482", "NJ": "071"}


def d(s: str) -> date:
    return date.fromisoformat(s)


def iso(x: date) -> str:
    return x.isoformat()


def add_days(s: str, n: int) -> str:
    return iso(d(s) + timedelta(days=n))


def offset_latlon(lat: float, lon: float, dx_km: float, dy_km: float) -> tuple[float, float]:
    return lat + dy_km / 111.0, lon + dx_km / (111.0 * math.cos(math.radians(lat)))


def loc(rng: random.Random, key: str, name: str, city: str, occupancy: str, occupancy_raw: str, construction: int,
        construction_raw: str, year_built: int, stories: int, sqft: int, roof_year: int, values_prior: Values,
        values_current: Values | None = None, *, ppc: int = 3, sprinkler_pct: float = 1.0, roof_type: str = "TPO membrane",
        street_no: int | None = None, street: str | None = None, dx_km: float | None = None, dy_km: float | None = None,
        model_rc_per_sqft: float | None = None, **kw) -> Location:
    lat, lon, st, zone, tier, fz, eqz, wf = CITIES[city]
    if construction_raw in ("__CONS__", "Masonry", "Reinforced concrete", "Brick") or construction_raw == "Joisted masonry" and construction != 2:
        construction_raw = {1: "Frame", 2: "Joisted masonry", 3: "Non-combustible", 4: "Masonry non-combustible", 5: "Modified fire resistive", 6: "Fire resistive"}[construction]
    if dx_km is None:
        dx_km = rng.uniform(-9, 9)
    if dy_km is None:
        dy_km = rng.uniform(-9, 9)
    la, lo = offset_latlon(lat, lon, dx_km, dy_km)
    vc = values_current or values_prior
    # modelled RC defaults to the reported building value / 0.93 (slightly under-insured is normal)
    model_rc = (model_rc_per_sqft * sqft) if model_rc_per_sqft else vc.building / rng.uniform(0.9, 1.02)
    l = Location(
        key=key, name=name, street_no=street_no or rng.randint(100, 9800), street=street or rng.choice(STREETS),
        city=city, state=st, zip=ZIPS.get(st, "100") + f"{rng.randint(1, 99):02d}", lat=round(la, 6), lon=round(lo, 6),
        occupancy=occupancy, occupancy_raw=occupancy_raw, construction=construction, construction_raw=construction_raw,
        year_built=year_built, stories=stories, sqft=sqft, roof_year=roof_year, roof_type=roof_type, ppc=ppc,
        sprinkler_pct=sprinkler_pct, values_prior=values_prior, values_current=values_current, model_rc=round(model_rc, -3),
        zone=zone, wind_tier=tier, flood_zone=fz, eq_zone=eqz, wildfire=wf, burglary_score=rng.randint(20, 70),
    )
    for k, v in kw.items():
        setattr(l, k, v)
    if not l.buildings:
        l.buildings = [default_building(l)]
    return l


def default_building(l: Location, key: str = "B-1") -> Building:
    footprint_m2 = l.sqft * 0.0929 / max(1, l.stories)
    ratio = 1.6 if l.occupancy in ("warehouse", "li_storage", "manufacturing", "plastics", "cold_storage", "scrap") else 1.2
    w = math.sqrt(footprint_m2 * ratio)
    dp = footprint_m2 / w
    kind = "warehouse" if l.occupancy in ("warehouse", "li_storage", "cold_storage") else "datahall" if l.occupancy == "data_center" else "tower" if l.stories >= 6 else "box"
    return Building(key=key, label=l.name, width_m=round(w, 1), depth_m=round(dp, 1), stories=l.stories,
                    story_h_m=9.0 if kind == "warehouse" and l.stories == 1 else 4.0,
                    roof="flat", kind=kind)


def split_values(tiv: float, occupancy: str, rng: random.Random) -> Values:
    """Split a TIV into building / contents / stock / BI shares typical for the occupancy."""
    shares = {
        "office": (0.72, 0.16, 0.0, 0.12), "retail": (0.45, 0.20, 0.25, 0.10), "jewelry": (0.20, 0.12, 0.60, 0.08),
        "restaurant": (0.55, 0.22, 0.05, 0.18), "hotel": (0.74, 0.10, 0.01, 0.15), "manufacturing": (0.62, 0.25, 0.06, 0.07),
        "plastics": (0.50, 0.30, 0.10, 0.10), "warehouse": (0.55, 0.08, 0.30, 0.07), "li_storage": (0.45, 0.05, 0.45, 0.05),
        "shopping_ctr": (0.80, 0.04, 0.0, 0.16), "hospital": (0.70, 0.18, 0.02, 0.10), "university": (0.82, 0.12, 0.0, 0.06),
        "data_center": (0.35, 0.55, 0.0, 0.10), "scrap": (0.30, 0.25, 0.35, 0.10), "multifamily": (0.85, 0.03, 0.0, 0.12),
        "cold_storage": (0.50, 0.12, 0.30, 0.08),
    }[occupancy]
    j = [s * rng.uniform(0.93, 1.07) for s in shares]
    t = sum(j)
    b, c, s, bi = (x / t * tiv for x in j)
    return Values(round(b, -3), round(c, -3), round(s, -3), round(tiv - round(b, -3) - round(c, -3) - round(s, -3), -3))


def grow(v: Values, f: float, rng: random.Random | None = None, jitter: float = 0.0) -> Values:
    g = lambda x: round(x * (f + (rng.uniform(-jitter, jitter) if rng and jitter else 0)), -3)
    return Values(g(v.building), g(v.contents), g(v.stock), g(v.bi))

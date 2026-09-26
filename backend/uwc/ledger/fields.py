"""Field catalogue + evidence-resolution policies (blueprint §9)."""
from __future__ import annotations

from typing import Any, Callable

from uwc.refdata import CONSTRUCTION, OCCUPANCY

# field_code -> (label, kind, policy_id)
# kind: money | int | year | pct | text | bool | ratio | ft | score | class | construction | latlon
FIELDS: dict[str, tuple[str, str, str]] = {
    "address": ("Address", "text", "latest"),
    "location_name": ("Location name", "text", "latest"),
    "occupancy_raw": ("Occupancy (as reported)", "text", "latest"),
    "occupancy_class": ("Occupancy class", "class", "occupancy.v2"),
    "construction_raw": ("Construction (as reported)", "text", "latest"),
    "construction_class": ("Construction class", "construction", "construction.v3"),
    "year_built": ("Year built", "year", "engineering_first.v1"),
    "stories": ("Stories", "int", "engineering_first.v1"),
    "sqft": ("Floor area", "sqft", "latest"),
    "roof_year": ("Roof year", "year", "roof_year.v3"),
    "roof_type": ("Roof covering", "text", "engineering_first.v1"),
    "roof_condition": ("Roof condition", "text", "latest"),
    "sprinkler_pct": ("Sprinkler protection", "pct", "engineering_first.v1"),
    "sprinkler_design_ft": ("Sprinkler design storage height", "ft", "engineering_only.v1"),
    "storage_height_ft": ("Max storage height", "ft", "latest"),
    "commodity": ("Commodity", "text", "latest"),
    "fire_alarm": ("Fire alarm", "text", "engineering_first.v1"),
    "ppc": ("Public protection class", "int", "vendor.v1"),
    "building_value": ("Building value", "money", "term_value.v1"),
    "contents_value": ("Contents / BPP", "money", "term_value.v1"),
    "stock_value": ("Stock / inventory", "money", "term_value.v1"),
    "bi_value": ("Business income", "money", "term_value.v1"),
    "tiv_reported": ("TIV (as reported)", "money", "term_value.v1"),
    "lat": ("Latitude", "latlon", "vendor.v1"),
    "lon": ("Longitude", "latlon", "vendor.v1"),
    "geocode_level": ("Geocode resolution", "text", "vendor.v1"),
    "cat_zone": ("CAT zone", "text", "vendor.v1"),
    "wind_tier": ("Wind tier", "text", "vendor.v1"),
    "flood_zone": ("Flood zone", "text", "vendor.v1"),
    "eq_zone": ("Earthquake zone", "text", "vendor.v1"),
    "wildfire_score": ("Wildfire score", "score", "vendor.v1"),
    "burglary_score": ("Burglary score", "score", "vendor.v1"),
    "model_rc": ("Modelled replacement cost", "money", "vendor.v1"),
    "rc_per_sqft_model": ("Modelled RC / sq ft", "money2", "vendor.v1"),
    "burglar_monitored": ("Burglar alarm central-station monitored", "bool", "verified_first.v1"),
    "burglar_alarm": ("Burglar alarm", "bool", "verified_first.v1"),
    "cooking_suppression_verified": ("Cooking suppression (UL 300) verified", "bool", "verified_first.v1"),
    "hood_cleaning_ok": ("Hood cleaning certificate", "bool", "verified_first.v1"),
    "vacancy_pct": ("Vacant share of floor area", "pct", "latest"),
    "vacancy_since": ("Vacant since", "date", "latest"),
    "vacancy_indicator": ("Vacancy indicated by imagery", "bool", "latest"),
    "sprinkler_impaired": ("Sprinkler system impaired", "bool", "latest"),
    "yard_change": ("Site change detected by imagery", "bool", "latest"),
    "cat_input_construction": ("CAT model input construction", "construction", "latest"),
    "carrier_loc_id": ("Carrier location ID", "text", "latest"),
    "appraisal_date": ("Last appraisal date", "date", "latest"),
    # account-level
    "target_premium": ("Broker target premium", "money", "latest"),
    "requested_ns_ded_pct": ("Requested named storm deductible", "pct", "latest"),
    "cash_on_premises": ("Cash on premises", "money", "latest"),
    "burglar_alarm_all": ("Burglar alarms (broker statement)", "bool", "latest"),
    "stated_change": ("Stated change (broker narrative)", "text", "latest"),
    "missing_document": ("Document to follow (broker narrative)", "text", "latest"),
}

POLICY_EXPLAINER = {
    "construction.v3": "Engineering (V) > inspection data (S) > carrier prior-resolved > SOV mapping (N) > model (M)",
    "roof_year.v3": "Engineering (V) > roofing permit (S) > SOV (C); imagery informs condition only",
    "occupancy.v2": "Explicit disclosure (broker narrative, engineering V) beats a carried-forward SOV template description; newer engineering beats older disclosure; conflicts are raised",
    "engineering_first.v1": "Engineering (V) > carrier systems (S) > broker-reported (C/N)",
    "engineering_only.v1": "Engineering (V) only — design basis is never taken from broker data",
    "verified_first.v1": "Verified certificate / inspection (V) > broker statement (C)",
    "vendor.v1": "Latest vendor / model value (M)",
    "term_value.v1": "Values for the term: renewal SOV (C) for current; issued schedule (S) > SOV (C) for prior",
    "latest": "Most recently recorded observation",
}

TYPE_RANK = {"V": 6, "S": 5, "R": 4, "N": 3, "C": 3, "M": 2, "D": 1}


def resolve(obs: list, policy: str):
    """Pick the winning observation per policy. Returns (winner, conflict: bool)."""
    if not obs:
        return None, False
    obs = sorted(obs, key=lambda o: o.recorded_at)
    winner = None
    if policy in ("construction.v3", "roof_year.v3", "engineering_first.v1", "verified_first.v1"):
        winner = max(obs, key=lambda o: (TYPE_RANK.get(o.obs_type, 0), o.recorded_at))
    elif policy == "engineering_only.v1":
        vs = [o for o in obs if o.obs_type == "V"]
        winner = vs[-1] if vs else None
    elif policy == "occupancy.v2":
        explicit = [o for o in obs if o.obs_type == "V" or "email" in (o.source_label or "").lower()]
        latest_explicit = explicit[-1] if explicit else None
        template = obs[-1]
        winner = latest_explicit if latest_explicit and (latest_explicit.obs_type != "V" or latest_explicit.recorded_at >= template.recorded_at) else template
    else:
        winner = obs[-1]
    if winner is None:
        return None, False
    distinct = {_key(o.value) for o in obs if o.value is not None}
    conflict = len(distinct) > 1
    if policy == "roof_year.v3":
        ys = [o.value for o in obs if isinstance(o.value, (int, float))]
        conflict = bool(ys) and (max(ys) - min(ys) >= 3)
    if policy in ("term_value.v1", "latest", "vendor.v1"):
        conflict = False
    return winner, conflict


def _key(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def display(field_code: str, v: Any) -> str:
    if v is None:
        return "—"
    kind = FIELDS.get(field_code, ("", "text", ""))[1]
    try:
        if kind == "money":
            return f"${v:,.0f}"
        if kind == "money2":
            return f"${v:,.0f}"
        if kind == "pct":
            return f"{v * 100:.0f}%" if v * 100 == int(v * 100) else f"{v * 100:.1f}%"
        if kind == "sqft":
            return f"{v:,.0f} sq ft"
        if kind == "ft":
            return f"{v:.0f} ft"
        if kind == "class":
            return OCCUPANCY.get(v, (str(v),))[0]
        if kind == "construction":
            return CONSTRUCTION.get(int(v), (str(v),))[0]
        if kind == "bool":
            return "Yes" if v else "No"
        if kind == "latlon":
            return f"{v:.5f}"
        if kind == "int" or kind == "year" or kind == "score":
            return str(int(v))
    except (TypeError, ValueError):
        return str(v)
    return str(v)


def label(field_code: str) -> str:
    return FIELDS.get(field_code, (field_code.replace("_", " ").capitalize(),))[0]


def policy_of(field_code: str) -> str:
    return FIELDS.get(field_code, ("", "", "latest"))[2]


Normaliser = Callable[[str], Any]

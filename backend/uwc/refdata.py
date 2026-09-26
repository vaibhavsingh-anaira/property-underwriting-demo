"""Reference data: taxonomies, rating tables, guidelines, authority, zones.

Everything here is fictional/illustrative for the Northgate demo tenant, shaped
like the real thing (ISO construction classes, CSP-style classes, OED-style CAT
codes, versioned guidelines, an authority matrix and a statutory-notice table).
"""
from __future__ import annotations

from datetime import date

# --------------------------------------------------------------------- people
USERS = [
    {"user_id": "u_maya", "name": "Maya Chen", "role": "UNDERWRITER", "authority_level": 1, "title": "Property Underwriter", "initials": "MC"},
    {"user_id": "u_daniel", "name": "Daniel Okafor", "role": "UNDERWRITER", "authority_level": 2, "title": "Senior Property Underwriter", "initials": "DO"},
    {"user_id": "u_sofia", "name": "Sofia Alvarez", "role": "UNDERWRITER", "authority_level": 2, "title": "Property Underwriter", "initials": "SA"},
    {"user_id": "u_tom", "name": "Tom Becker", "role": "UNDERWRITER", "authority_level": 1, "title": "Property Underwriter", "initials": "TB"},
    {"user_id": "u_priya", "name": "Priya Raman", "role": "SENIOR_UNDERWRITER", "authority_level": 3, "title": "Head of Property Underwriting", "initials": "PR"},
    {"user_id": "u_robert", "name": "Robert Hale", "role": "CUO", "authority_level": 4, "title": "Chief Underwriting Officer", "initials": "RH"},
    {"user_id": "u_elena", "name": "Elena Brooks", "role": "RISK_ENGINEER", "authority_level": 1, "title": "Risk Engineer", "initials": "EB"},
    {"user_id": "u_claire", "name": "Claire Donovan", "role": "DA_MANAGER", "authority_level": 3, "title": "Head of Delegated Authority", "initials": "CD"},
]
USER_BY_ID = {u["user_id"]: u for u in USERS}
UNDERWRITER_IDS = ["u_maya", "u_daniel", "u_sofia", "u_tom"]

BROKERS = [
    ("Harlan & Pierce Risk Partners", "Jordan Pierce"),
    ("Keel & Crane Insurance Services", "Amelia Crane"),
    ("Brightwater Risk Advisors", "Luis Ortega"),
    ("Calder Street Brokerage", "Hannah Weiss"),
    ("Ironbridge Specialty Brokers", "Marcus Hale-Ng"),
    ("Tidewater Commercial Insurance", "Grace Oduya"),
]

# ------------------------------------------------------------ classification
# canonical family -> (label, carrier class code, NAICS, CSP-style code, attritional base rate per $100 TIV)
OCCUPANCY = {
    "office":        ("Office / professional", "NS-OFF-01", "531120", "0702", 0.055),
    "retail":        ("Retail / mercantile", "NS-RET-02", "448310", "0567", 0.085),
    "jewelry":       ("Jewelry / high-value retail", "NS-RET-07", "448310", "0567", 0.110),
    "restaurant":    ("Full-service restaurant", "NS-FS-01", "722511", "0542", 0.160),
    "hotel":         ("Hotel / motel", "NS-HAB-03", "721110", "0745", 0.090),
    "manufacturing": ("Light manufacturing", "NS-MFG-02", "332710", "2150", 0.120),
    "plastics":      ("Plastics manufacturing", "NS-MFG-09", "326199", "4150", 0.190),
    "warehouse":     ("General warehouse", "NS-WH-01", "493110", "1220", 0.080),
    "li_storage":    ("Warehouse — lithium-ion battery storage", "NS-WH-11", "493190", "1230", 0.140),
    "shopping_ctr":  ("Shopping center / multi-tenant retail", "NS-RET-10", "531120", "0580", 0.090),
    "hospital":      ("General hospital", "NS-HC-01", "622110", "0851", 0.070),
    "university":    ("University / college", "NS-EDU-02", "611310", "0900", 0.060),
    "data_center":   ("Data center", "NS-TEC-01", "518210", "0770", 0.065),
    "scrap":         ("Scrap metal / recycling yard", "NS-IND-14", "423930", "4950", 0.260),
    "multifamily":   ("Multifamily / apartment", "NS-HAB-01", "531110", "0311", 0.070),
    "cold_storage":  ("Cold storage / refrigerated warehouse", "NS-WH-05", "493120", "1225", 0.115),
}

# ISO construction class 1..6 -> (label, attritional factor, OED-style code, CAT vulnerability)
CONSTRUCTION = {
    1: ("Frame (ISO 1)", 1.35, 5050, 1.30),
    2: ("Joisted masonry (ISO 2)", 1.15, 5100, 1.10),
    3: ("Non-combustible (ISO 3)", 0.95, 5200, 1.00),
    4: ("Masonry non-combustible (ISO 4)", 0.85, 5150, 0.90),
    5: ("Modified fire resistive (ISO 5)", 0.72, 5250, 0.80),
    6: ("Fire resistive (ISO 6)", 0.65, 5300, 0.72),
}
CONSTRUCTION_SYNONYMS = {
    "frame": 1, "wood frame": 1, "wood": 1,
    "joisted masonry": 2, "jm": 2, "brick": 2, "masonry": 2, "ordinary": 2,
    "non-combustible": 3, "noncombustible": 3, "nc": 3, "metal": 3, "steel": 3, "light noncombustible": 3,
    "masonry non-combustible": 4, "masonry noncombustible": 4, "mnc": 4, "tilt-up": 4, "tilt up concrete": 4, "cmu": 4,
    "modified fire resistive": 5, "mfr": 5,
    "fire resistive": 6, "fr": 6, "reinforced concrete": 6, "concrete": 6,
    "tilt-up concrete": 4, "tilt up": 4, "steel frame / metal panel": 3, "steel frame": 3, "metal building": 3, "metal panel": 3, "pre-engineered metal": 3,
}

OCCUPANCY_SYNONYMS = {
    "office": "office", "offices": "office", "professional office": "office", "corporate office": "office",
    "retail": "retail", "retail store": "retail", "store": "retail",
    "jewelry store": "jewelry", "jewelry": "jewelry", "jeweler": "jewelry",
    "restaurant": "restaurant", "full service restaurant": "restaurant", "dining": "restaurant",
    "hotel": "hotel", "motel": "hotel", "resort": "hotel",
    "manufacturing": "manufacturing", "machining": "manufacturing", "metal fabrication": "manufacturing", "assembly": "manufacturing", "assembly / distribution": "manufacturing",
    "plastics": "plastics", "plastic injection molding": "plastics", "injection molding": "plastics",
    "warehouse": "warehouse", "distribution": "warehouse", "storage": "warehouse", "general warehouse": "warehouse",
    "battery storage": "li_storage", "lithium-ion storage": "li_storage", "e-bike battery storage": "li_storage",
    "shopping center": "shopping_ctr", "strip center": "shopping_ctr", "retail center": "shopping_ctr",
    "hospital": "hospital", "medical center": "hospital", "acute care": "hospital",
    "university": "university", "college": "university", "classroom": "university", "dormitory": "university", "library": "university", "laboratory": "university",
    "data center": "data_center", "colocation": "data_center",
    "scrap yard": "scrap", "scrap metal": "scrap", "recycling": "scrap",
    "apartments": "multifamily", "multifamily": "multifamily",
    "cold storage": "cold_storage", "refrigerated warehouse": "cold_storage",
}

PPC_FACTOR = {1: 0.85, 2: 0.88, 3: 0.92, 4: 0.97, 5: 1.0, 6: 1.06, 7: 1.12, 8: 1.2, 9: 1.35, 10: 1.55}

# ------------------------------------------------------------------- forms
FORMS = {
    "CP 00 10": "Building and Personal Property Coverage Form",
    "CP 00 30": "Business Income (and Extra Expense) Coverage Form",
    "CP 00 90": "Commercial Property Conditions",
    "CP 10 30": "Causes of Loss — Special Form",
    "CP 04 05": "Ordinance or Law Coverage",
    "CP 04 11": "Protective Safeguards",
    "CP 03 21": "Windstorm or Hail Percentage Deductible",
    "IL 00 17": "Common Policy Conditions",
    "NS-CP 03 40": "Named Storm Deductible (Northgate manuscript)",
    "NS-CP 04 70": "Vacancy Permit (Northgate manuscript)",
    "NS-CP 12 10": "Flood Sublimit Endorsement (Northgate manuscript)",
    "NS-CP 12 20": "Earthquake Sublimit Endorsement (Northgate manuscript)",
    "NS-CR 01 00": "Commercial Crime — Money & Securities (Northgate)",
}
SAFEGUARD_CODES = {
    "P-1": "Automatic sprinkler system",
    "P-2": "Automatic fire alarm",
    "P-3": "Security service",
    "P-4": "Service contract (monitored burglar alarm)",
    "P-5": "Automatic commercial cooking exhaust and extinguishing system",
}

# -------------------------------------------------------------- guidelines
# Versioned carrier guideline parameters. v2026 is published on 2026-07-01.
GUIDELINES = {
    "2025": {
        "version": "2025.1", "effective_from": "2025-01-01", "effective_to": "2026-06-30",
        "doc_title": "Northgate Commercial Property Underwriting Guidelines 2025",
        "wind_ded_floor_pct_t1": 0.02, "wind_ded_floor_pct_t2": 0.02, "ns_min_floor": 100_000,
        "adequacy_floor": 0.95, "valuation_ratio_min": 0.80, "roof_age_max": 20,
        "burglary_threshold": 80, "high_value_stock": 1_000_000, "vacancy_days_max": 60,
        "declined_classes": [], "repeat_loss_count": 2, "storage_height_tolerance_ft": 0,
        "appraisal_max_age_years": 3, "value_staleness_days": 365, "accumulation_util_refer": 0.90,
        "sections": {"wind": "§7.3", "adequacy": "§4.2", "valuation": "§5.1", "security": "§8.4", "vacancy": "§9.2", "appetite": "§2.1", "roof": "§6.2", "sprinkler": "§6.5", "cooking": "§6.8", "engineering": "§10.1", "authority": "§3.1", "accumulation": "§11.4"},
    },
    "2026": {
        "version": "2026.1", "effective_from": "2026-07-01", "effective_to": None,
        "doc_title": "Northgate Commercial Property Underwriting Guidelines 2026",
        "wind_ded_floor_pct_t1": 0.03, "wind_ded_floor_pct_t2": 0.02, "ns_min_floor": 250_000,
        "adequacy_floor": 0.95, "valuation_ratio_min": 0.80, "roof_age_max": 20,
        "burglary_threshold": 80, "high_value_stock": 1_000_000, "vacancy_days_max": 60,
        "declined_classes": ["scrap"], "repeat_loss_count": 2, "storage_height_tolerance_ft": 0,
        "appraisal_max_age_years": 3, "value_staleness_days": 365, "accumulation_util_refer": 0.90,
        "sections": {"wind": "§7.3", "adequacy": "§4.2", "valuation": "§5.1", "security": "§8.4", "vacancy": "§9.2", "appetite": "§2.1", "roof": "§6.2", "sprinkler": "§6.5", "cooking": "§6.8", "engineering": "§10.1", "authority": "§3.1", "accumulation": "§11.4"},
    },
}
GUIDELINE_PAGES = {"§2.1": 6, "§3.1": 9, "§4.2": 14, "§5.1": 18, "§6.2": 23, "§6.5": 26, "§6.8": 29, "§7.3": 41, "§8.4": 47, "§9.2": 52, "§10.1": 58, "§11.4": 63}


def guideline_for(d: date) -> dict:
    return GUIDELINES["2026"] if d >= date(2026, 7, 1) else GUIDELINES["2025"]


# --------------------------------------------------------------- authority
AUTHORITY = {
    1: {"min_rarc": -0.05, "max_account_tiv": 200_000_000, "max_loc_tiv": 40_000_000, "max_price_dev": 0.05, "max_premium": 500_000, "cat_t1_tiv": 60_000_000, "can_override_guideline": False},
    2: {"min_rarc": -0.10, "max_account_tiv": 400_000_000, "max_loc_tiv": 100_000_000, "max_price_dev": 0.10, "max_premium": 1_500_000, "cat_t1_tiv": 200_000_000, "can_override_guideline": False},
    3: {"min_rarc": -0.20, "max_account_tiv": 1_500_000_000, "max_loc_tiv": 400_000_000, "max_price_dev": 0.15, "max_premium": 5_000_000, "cat_t1_tiv": 750_000_000, "can_override_guideline": True},
    4: {"min_rarc": -1.0, "max_account_tiv": 10_000_000_000, "max_loc_tiv": 2_000_000_000, "max_price_dev": 0.30, "max_premium": 50_000_000, "cat_t1_tiv": 10_000_000_000, "can_override_guideline": True},
}

# ---------------------------------------------- statutory notice (illustrative)
# Days of advance notice for non-renewal / conditional renewal of ADMITTED
# commercial property. Illustrative demo table — verify with counsel.
NOTICE_DAYS = {"LA": 60, "FL": 45, "TX": 60, "OH": 30, "NV": 60, "PA": 60, "NY": 60, "CA": 60, "VA": 45, "GA": 45, "IL": 60, "NC": 45, "CO": 45, "AZ": 45, "TN": 60, "MA": 45, "WA": 45, "NJ": 30, "MI": 30, "MN": 60}
NOTICE_REF = "Demo notice table v1 — illustrative, verify with counsel"

# ------------------------------------------------------ CAT / accumulation zones
# zone_id -> (name, peril, lat, lon, radius_km, threshold (net 1-in-250 PML capacity), background exposure already in book)
ZONES = {
    "TPA": ("Tampa Bay", "Hurricane", 27.95, -82.46, 90, 412_000_000, 187_000_000),
    "MIA": ("South Florida", "Hurricane", 25.90, -80.30, 110, 418_000_000, 138_000_000),
    "HOU": ("Houston–Galveston", "Hurricane", 29.60, -95.20, 110, 353_000_000, 95_000_000),
    "MSY": ("New Orleans", "Hurricane", 29.95, -90.07, 80, 176_000_000, 37_000_000),
    "CHS": ("Carolinas coast", "Hurricane", 33.20, -79.60, 140, 664_000_000, 106_000_000),
    "LAX": ("Southern California", "Earthquake", 34.05, -118.25, 120, 319_000_000, 93_000_000),
    "SFO": ("San Francisco Bay Area", "Earthquake", 37.65, -122.20, 90, 246_000_000, 59_000_000),
    "RNO": ("Reno–Tahoe", "Earthquake", 39.50, -119.80, 70, 302_000_000, 39_000_000),
    "DFW": ("North Texas", "Severe convective storm", 32.85, -97.00, 130, 174_000_000, 33_000_000),
    "DEN": ("Front Range", "Severe convective storm", 39.75, -104.95, 110, 65_000_000, 4_000_000),
    "IAD": ("Northern Virginia cluster", "Fire / BI concentration", 39.00, -77.45, 40, 861_000_000, 361_000_000),
}

# peril base AAL rates (ground-up, per $ TIV) by zone and peril, before vulnerability
ZONE_PERIL_RATES = {
    "TPA": {"HU": 0.0034, "SCS": 0.0003, "FL": 0.0005},
    "MIA": {"HU": 0.0042, "SCS": 0.0002, "FL": 0.0005},
    "HOU": {"HU": 0.0026, "SCS": 0.0006, "FL": 0.0008},
    "MSY": {"HU": 0.0030, "SCS": 0.0004, "FL": 0.0009},
    "CHS": {"HU": 0.0021, "SCS": 0.0003, "FL": 0.0004},
    "LAX": {"EQ": 0.0022, "WF": 0.0004},
    "SFO": {"EQ": 0.0026, "WF": 0.0003},
    "RNO": {"EQ": 0.0011, "WF": 0.0006},
    "DFW": {"SCS": 0.0016},
    "DEN": {"SCS": 0.0014, "WF": 0.0002},
    "IAD": {"SCS": 0.0003},
    None: {"SCS": 0.0004},
}
PERIL_LABEL = {"HU": "Hurricane / named storm", "SCS": "Severe convective storm", "FL": "Flood", "EQ": "Earthquake", "WF": "Wildfire"}

# city anchors (lat, lon, state, zone, wind tier, flood zone, eq zone, wildfire score)
CITIES = {
    "Tampa":        (27.9506, -82.4572, "FL", "TPA", "T1", "AE", None, 5),
    "St. Petersburg": (27.7676, -82.6403, "FL", "TPA", "T1", "AE", None, 5),
    "Clearwater":   (27.9659, -82.8001, "FL", "TPA", "T1", "X", None, 6),
    "Miami":        (25.7617, -80.1918, "FL", "MIA", "T1", "AE", None, 4),
    "Fort Lauderdale": (26.1224, -80.1373, "FL", "MIA", "T1", "X", None, 4),
    "Houston":      (29.7604, -95.3698, "TX", "HOU", "T2", "AE", None, 8),
    "Galveston":    (29.3013, -94.7977, "TX", "HOU", "T1", "VE", None, 4),
    "New Orleans":  (29.9511, -90.0715, "LA", "MSY", "T1", "AE", None, 3),
    "Baton Rouge":  (30.4515, -91.1871, "LA", "MSY", "T2", "X", None, 6),
    "Charleston":   (32.7765, -79.9311, "SC", "CHS", "T1", "AE", None, 7),
    "Wilmington":   (34.2257, -77.9447, "NC", "CHS", "T2", "X", None, 9),
    "Los Angeles":  (34.0522, -118.2437, "CA", "LAX", None, "X", "Z4", 42),
    "Irvine":       (33.6846, -117.8265, "CA", "LAX", None, "X", "Z4", 48),
    "San Jose":     (37.3382, -121.8863, "CA", "SFO", None, "X", "Z4", 30),
    "Oakland":      (37.8044, -122.2712, "CA", "SFO", None, "X", "Z4", 36),
    "Reno":         (39.5296, -119.8138, "NV", "RNO", None, "X", "Z3", 58),
    "Sparks":       (39.5349, -119.7527, "NV", "RNO", None, "X", "Z3", 52),
    "Dallas":       (32.7767, -96.7970, "TX", "DFW", None, "X", None, 12),
    "Fort Worth":   (32.7555, -97.3308, "TX", "DFW", None, "X", None, 14),
    "Austin":       (30.2672, -97.7431, "TX", None, None, "X", None, 22),
    "Denver":       (39.7392, -104.9903, "CO", "DEN", None, "X", None, 26),
    "Ashburn":      (39.0438, -77.4874, "VA", "IAD", None, "X", None, 6),
    "Sterling":     (39.0062, -77.4286, "VA", "IAD", None, "X", None, 6),
    "Dayton":       (39.7589, -84.1916, "OH", None, None, "X", None, 4),
    "Columbus":     (39.9612, -82.9988, "OH", None, None, "X", None, 4),
    "Pittsburgh":   (40.4406, -79.9959, "PA", None, None, "X", None, 5),
    "Philadelphia": (39.9526, -75.1652, "PA", None, None, "X", None, 3),
    "Chicago":      (41.8781, -87.6298, "IL", None, None, "X", None, 3),
    "Atlanta":      (33.7490, -84.3880, "GA", None, None, "X", None, 10),
    "Nashville":    (36.1627, -86.7816, "TN", None, None, "X", None, 9),
    "Phoenix":      (33.4484, -112.0740, "AZ", None, None, "X", None, 28),
    "Minneapolis":  (44.9778, -93.2650, "MN", None, None, "X", None, 5),
    "Boston":       (42.3601, -71.0589, "MA", None, "T2", "X", None, 3),
    "Seattle":      (47.6062, -122.3321, "WA", None, None, "X", "Z3", 12),
    "Detroit":      (42.3314, -83.0458, "MI", None, None, "X", None, 3),
    "Newark":       (40.7357, -74.1724, "NJ", None, "T2", "AE", None, 3),
    "Charlotte":    (35.2271, -80.8431, "NC", None, None, "X", None, 8),
    "State College": (40.7934, -77.8600, "PA", None, None, "X", None, 5),
}

# fictional street names (never real addresses)
STREETS = ["Harbor Point Dr", "Industrial Pkwy", "Commerce Loop", "Riverbend Rd", "Lakeview Ave", "Quarry Rd", "Foundry St",
           "Meridian Way", "Cypress Ridge Blvd", "Willow Creek Ct", "Beacon Hill Rd", "Northgate Blvd", "Sawmill Ln", "Canal St E",
           "Keystone Ave", "Granite Ct", "Heron Bay Dr", "Stonegate Pkwy", "Ashford Cir", "Railyard Rd", "Mariner Blvd",
           "Summit Ave", "Juniper Way", "Kestrel Dr", "Ironworks Rd", "Orchard Park Dr", "Palisade Ave", "Tidewater Ln"]

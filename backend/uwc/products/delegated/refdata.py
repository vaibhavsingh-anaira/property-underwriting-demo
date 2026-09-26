"""Delegated Authority reference data: the five fictional coverholders, the program class taxonomy,
territories and the Lloyd's CRS v5.2-style field set. Everything here is generator input or public
reference data; the engine only ever sees what is parsed back from the documents."""
from __future__ import annotations

CARRIER = "Northgate Specialty Insurance Co."
MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08"]
MONTH_LABEL = {"2026-04": "Apr 2026", "2026-05": "May 2026", "2026-06": "Jun 2026", "2026-07": "Jul 2026", "2026-08": "Aug 2026", "2026-09": "Sep 2026"}

# program class taxonomy: code -> (label, base rate per $100 TIV)
CLASSES = {
    "OFF": ("Office", 0.180), "RET": ("Retail / mercantile", 0.240), "SCC": ("Strip shopping center", 0.260),
    "RST": ("Restaurant (no solid-fuel cooking)", 0.420), "WHS": ("Warehouse / distribution", 0.220), "LMF": ("Light manufacturing", 0.340),
    "APT": ("Apartments (4 stories or fewer)", 0.280), "HTL": ("Hotel / motel", 0.360), "SST": ("Self storage", 0.160),
    "CHU": ("House of worship", 0.220), "AUT": ("Auto service / repair", 0.380), "COL": ("Cold storage", 0.440),
}
OUT_OF_SCHEDULE = {"BAR": "Bar / tavern / nightclub", "CAN": "Cannabis cultivation or dispensary", "VAC": "Vacant building",
                   "SCR": "Scrap metal / recycling", "FWK": "Fireworks manufacture or storage"}
OCC_TEXT = {"OFF": ["Office", "Professional office", "Medical office"], "RET": ["Retail store", "Hardware store", "Pharmacy"],
            "SCC": ["Strip center", "Neighborhood shopping center"], "RST": ["Restaurant", "Family restaurant", "Cafe"],
            "WHS": ["Warehouse", "Distribution warehouse"], "LMF": ["Light manufacturing", "Machine shop", "Cabinet shop"],
            "APT": ["Apartments", "Garden apartments"], "HTL": ["Motel", "Limited-service hotel"], "SST": ["Self storage"],
            "CHU": ["Church", "House of worship"], "AUT": ["Auto repair", "Tire & lube"], "COL": ["Cold storage", "Refrigerated warehouse"],
            "BAR": ["Bar & grill (late night)", "Nightclub"], "CAN": ["Cannabis dispensary"], "VAC": ["Vacant building"],
            "SCR": ["Scrap yard"], "FWK": ["Fireworks storage"]}
CONSTRUCTION = {1: ("Frame", 1.30), 2: ("Joisted Masonry", 1.15), 3: ("Non-Combustible", 1.00), 4: ("Masonry Non-Combustible", 0.90),
                5: ("Modified Fire Resistive", 0.85), 6: ("Fire Resistive", 0.80)}
DED_FACTORS = [(5_000, 1.05), (10_000, 1.00), (25_000, 0.95), (50_000, 0.90), (100_000, 0.85)]
TIER_FACTOR = {"Inland": 1.00, "Tier 2": 1.35, "Tier 1": 2.40}

STREETS = ["Main St", "Commerce Dr", "Industrial Blvd", "Market St", "Oak Ave", "Harbor Rd", "Gateway Pkwy", "Center St", "Park Ave", "Lakeview Dr",
           "Railroad Ave", "Elm St", "Magnolia Blvd", "Airport Rd", "Enterprise Way", "Pine St", "River Rd", "Highland Ave", "Bayou Dr", "Mill St"]
NAME_A = ["Anchor", "Bluewater", "Cypress", "Delta", "Evergreen", "Frontier", "Granite", "Harbor", "Ironwood", "Juniper", "Keystone", "Lakeside", "Magnolia",
          "Northgate", "Oakridge", "Pioneer", "Quarry", "Redstone", "Summit", "Tidewater", "Union", "Valley", "Westfield", "Yellowpine", "Brookside",
          "Cedar", "Driftwood", "Eastgate", "Foxhollow", "Goldleaf", "Hillcrest", "Ivy", "Jetty", "Kingfisher", "Lighthouse", "Meadow", "Niagara", "Orchard"]
NAME_B = {"OFF": ["Professional Center", "Office Park", "Medical Plaza", "Law Offices"], "RET": ["Hardware", "Pharmacy", "Outfitters", "Supply Co."],
          "SCC": ["Shopping Center", "Plaza", "Crossing"], "RST": ["Grill", "Kitchen", "Diner", "Bistro"], "WHS": ["Logistics", "Distribution", "Storage"],
          "LMF": ["Fabrication", "Machine Works", "Millwork", "Components"], "APT": ["Apartments", "Residences", "Commons"], "HTL": ["Inn", "Motel", "Suites"],
          "SST": ["Self Storage", "Mini Storage"], "CHU": ["Community Church", "Baptist Church", "Fellowship"], "AUT": ["Auto Care", "Tire & Lube", "Collision"],
          "COL": ["Cold Storage", "Refrigerated Logistics"], "BAR": ["Tavern", "Nightclub", "Saloon"], "CAN": ["Wellness Dispensary"], "VAC": ["Holdings"],
          "SCR": ["Metals"], "FWK": ["Pyrotechnics"]}
SUFFIX = ["LLC", "Inc.", "LLC", "Co.", "LP", "Holdings LLC"]

# ----------------------------------------------------------------------------- coverholders
# territory rows: (state, county, city, zip3, tier, zone, status, weight)
COVERHOLDERS: dict[str, dict] = {
    "ch_meridian": {
        "scenario": "A1", "name": "Meridian Gulf Underwriting LLC", "short": "Meridian Gulf", "program": "Gulf Coast Small Commercial Property",
        "pin": "CH-24817", "umr": "B0823NGS26MGU01", "agreement": "NGS/DA/2026/014", "cert_prefix": "MGU", "broker": "Calder Street Brokerage",
        "contact": "Dana Whitfield", "contact_title": "Compliance Director", "domain": "meridiangulf.example", "hq": "Houston, TX",
        "period": ("2026-01-01", "2026-12-31"), "commission": 0.225, "max_limit": 5_000_000, "gpi_limit": 42_000_000,
        "layout": "variant", "response_days": 6, "received_day": {"2026-05": "2026-06-03", "2026-06": "2026-07-02", "2026-07": "2026-08-01", "2026-08": "2026-09-08"},
        "story": "Deteriorating: limit and deductible breaches, missing referrals and commission over-deduction trending up month on month",
        "title": "Exceptions trending up — limits, deductibles, missing referrals, commission",
        "rows": {"NEW": 108, "RENEWAL": 126, "ENDORSEMENT": 18, "CANCELLATION": 8}, "rarc": {"2026-05": -0.012, "2026-06": -0.028, "2026-07": -0.061, "2026-08": -0.074},
        "classes": {"OFF": "Permitted", "RET": "Permitted", "SCC": "Permitted", "RST": "Permitted", "WHS": "Permitted", "LMF": "Permitted", "APT": "Permitted",
                    "HTL": "Referral", "COL": "Permitted", "AUT": "Permitted", "CHU": "Permitted"},
        "class_mix": {"OFF": 14, "RET": 18, "SCC": 7, "RST": 11, "WHS": 14, "LMF": 9, "APT": 10, "HTL": 3, "COL": 4, "AUT": 6, "CHU": 4},
        "prohibited": ["CAN", "VAC", "SCR", "FWK"],
        "territories": [("TX", "Harris", "Houston", "770", "Tier 2", "HOU", "Permitted", 20), ("TX", "Fort Bend", "Sugar Land", "774", "Inland", "HOU", "Permitted", 6),
                        ("TX", "Montgomery", "Conroe", "773", "Inland", "HOU", "Permitted", 5), ("TX", "Dallas", "Dallas", "752", "Inland", "INL", "Permitted", 9),
                        ("TX", "Tarrant", "Fort Worth", "761", "Inland", "INL", "Permitted", 6), ("TX", "Bexar", "San Antonio", "782", "Inland", "INL", "Permitted", 6),
                        ("TX", "Galveston", "Galveston", "775", "Tier 1", "HOU", "Permitted", 4), ("TX", "Nueces", "Corpus Christi", "784", "Tier 1", "CCB", "Permitted", 4),
                        ("LA", "East Baton Rouge", "Baton Rouge", "708", "Inland", "INL", "Permitted", 6), ("LA", "Lafayette", "Lafayette", "705", "Inland", "INL", "Permitted", 4),
                        ("LA", "Orleans", "New Orleans", "701", "Tier 1", "MSY", "Permitted", 5), ("LA", "Jefferson", "Metairie", "700", "Tier 1", "MSY", "Permitted", 4),
                        ("LA", "Plaquemines", "Belle Chasse", "700", "Tier 1", "MSY", "Excluded", 0), ("MS", "Hinds", "Jackson", "392", "Inland", "INL", "Permitted", 4),
                        ("MS", "Harrison", "Gulfport", "395", "Tier 1", "GMA", "Permitted", 3), ("AL", "Jefferson", "Birmingham", "352", "Inland", "INL", "Permitted", 5),
                        ("AL", "Mobile", "Mobile", "366", "Tier 1", "GMA", "Permitted", 4), ("AL", "Baldwin", "Foley", "365", "Tier 1", "GMA", "Permitted", 2)],
        "min_aop": [(0, 1_000_000, 5_000), (1_000_000, 5_000_000, 10_000), (5_000_000, None, 25_000)],
        "ns_min": {"Tier 1": 0.05, "Tier 2": 0.02}, "tolerance": (0.08, 0.25),
        "referral": {"tiv_any": 7_500_000, "tiv_tier1": 2_500_000, "year_built": 1960},
        "aggregates": [("HOU", "Houston–Galveston", "Hurricane", 0.71), ("MSY", "New Orleans", "Hurricane", 0.64), ("GMA", "Mississippi–Alabama coast", "Hurricane", 0.58),
                       ("CCB", "Texas Coastal Bend", "Hurricane", 0.52)],
        "endorsement": {"effective": "2026-06-01", "issued": "2026-05-18", "reason": "Deductible structure for larger risks aligned with the carrier's 2026 property guidelines.",
                        "min_aop": [(5_000_000, None, 50_000)]},
        "tiv_range": (350_000, 4_800_000),
    },
    "ch_northfield": {
        "scenario": "A2", "name": "Northfield Specialty Partners", "short": "Northfield", "program": "Midwest Main Street Property",
        "pin": "CH-19034", "umr": "B1147NGS26NSP02", "agreement": "NGS/DA/2026/007", "cert_prefix": "NSP", "broker": "Harlan & Pierce Risk Partners",
        "contact": "Greg Lindqvist", "contact_title": "Chief Operating Officer", "domain": "northfieldsp.example", "hq": "Columbus, OH",
        "period": ("2026-01-01", "2026-12-31"), "commission": 0.20, "max_limit": 5_000_000, "gpi_limit": 22_000_000,
        "layout": "crs", "response_days": 2, "received_day": {"2026-05": "2026-06-02", "2026-06": "2026-07-01", "2026-07": "2026-08-01", "2026-08": "2026-09-03"},
        "story": "Clean benchmark: refers when it should, reports in the CRS template on time",
        "title": "Clean benchmark — requests a capacity increase",
        "rows": {"NEW": 64, "RENEWAL": 92, "ENDORSEMENT": 12, "CANCELLATION": 4}, "rarc": {"2026-05": 0.034, "2026-06": 0.029, "2026-07": 0.026, "2026-08": 0.024},
        "classes": {"OFF": "Permitted", "RET": "Permitted", "SCC": "Permitted", "RST": "Permitted", "WHS": "Permitted", "LMF": "Permitted", "APT": "Permitted",
                    "CHU": "Permitted", "AUT": "Permitted", "SST": "Permitted"},
        "class_mix": {"OFF": 16, "RET": 20, "SCC": 8, "RST": 12, "WHS": 12, "LMF": 12, "APT": 8, "CHU": 5, "AUT": 5, "SST": 4},
        "prohibited": ["CAN", "BAR", "VAC", "SCR", "FWK"],
        "territories": [("OH", "Franklin", "Columbus", "432", "Inland", "OHX", "Permitted", 14), ("OH", "Cuyahoga", "Cleveland", "441", "Inland", "OHX", "Permitted", 10),
                        ("OH", "Hamilton", "Cincinnati", "452", "Inland", "OHX", "Permitted", 8), ("IN", "Marion", "Indianapolis", "462", "Inland", "INX", "Permitted", 12),
                        ("IN", "Allen", "Fort Wayne", "468", "Inland", "INX", "Permitted", 5), ("MI", "Kent", "Grand Rapids", "495", "Inland", "MIX", "Permitted", 8),
                        ("MI", "Oakland", "Troy", "480", "Inland", "MIX", "Permitted", 8), ("IL", "DuPage", "Naperville", "605", "Inland", "ILX", "Permitted", 8),
                        ("IL", "Will", "Joliet", "604", "Inland", "ILX", "Permitted", 6), ("WI", "Milwaukee", "Milwaukee", "532", "Inland", "WIX", "Permitted", 6),
                        ("WI", "Dane", "Madison", "537", "Inland", "WIX", "Permitted", 4)],
        "min_aop": [(0, 1_000_000, 5_000), (1_000_000, 5_000_000, 10_000), (5_000_000, None, 25_000)],
        "ns_min": {}, "tolerance": (0.08, 0.25), "referral": {"tiv_any": 6_000_000, "tiv_tier1": None, "year_built": 1950},
        "aggregates": [("OHX", "Ohio", "Severe convective storm", 0.48), ("INX", "Indiana", "Severe convective storm", 0.44), ("MIX", "Michigan", "Severe convective storm", 0.39),
                       ("ILX", "Illinois", "Severe convective storm", 0.41), ("WIX", "Wisconsin", "Severe convective storm", 0.22)],
        "endorsement": {"effective": "2026-05-01", "issued": "2026-04-20", "reason": "Territory extended to Wisconsin (Milwaukee and Dane counties) following the carrier's filing approval.",
                        "territories_add": [("WI", "Milwaukee", "Inland", "1.00", "Permitted"), ("WI", "Dane", "Inland", "1.00", "Permitted")]},
        "tiv_range": (300_000, 4_200_000),
    },
    "ch_palmcoast": {
        "scenario": "A3", "name": "Palm Coast Commercial MGA", "short": "Palm Coast", "program": "Florida Coastal Commercial Property",
        "pin": "CH-31552", "umr": "B0931NGS26PCM03", "agreement": "NGS/DA/2026/021", "cert_prefix": "PCM", "broker": "Tidewater Commercial Insurance",
        "contact": "Rafael Ortiz", "contact_title": "Head of Underwriting", "domain": "palmcoastmga.example", "hq": "Fort Lauderdale, FL",
        "period": ("2026-01-01", "2026-12-31"), "commission": 0.25, "max_limit": 5_000_000, "gpi_limit": 38_000_000,
        "layout": "crs", "response_days": 3, "received_day": {"2026-05": "2026-06-04", "2026-06": "2026-07-03", "2026-07": "2026-08-01", "2026-08": "2026-09-09"},
        "story": "Florida coastal program running into its South Florida CAT aggregate",
        "title": "South Florida CAT aggregate through its warning threshold",
        "rows": {"NEW": 86, "RENEWAL": 88, "ENDORSEMENT": 10, "CANCELLATION": 4}, "rarc": {"2026-05": -0.038, "2026-06": -0.044, "2026-07": -0.051, "2026-08": -0.055},
        "classes": {"OFF": "Permitted", "RET": "Permitted", "SCC": "Permitted", "RST": "Permitted", "WHS": "Permitted", "APT": "Permitted", "HTL": "Permitted",
                    "SST": "Permitted", "CHU": "Permitted"},
        "class_mix": {"OFF": 16, "RET": 18, "SCC": 10, "RST": 10, "WHS": 12, "APT": 14, "HTL": 8, "SST": 6, "CHU": 4},
        "prohibited": ["CAN", "BAR", "VAC", "SCR", "FWK"],
        "territories": [("FL", "Miami-Dade", "Miami", "331", "Tier 1", "MIA", "Permitted", 17), ("FL", "Broward", "Fort Lauderdale", "333", "Tier 1", "MIA", "Permitted", 15),
                        ("FL", "Palm Beach", "West Palm Beach", "334", "Tier 1", "MIA", "Permitted", 11), ("FL", "Hillsborough", "Tampa", "336", "Tier 1", "TPA", "Permitted", 10),
                        ("FL", "Pinellas", "St. Petersburg", "337", "Tier 1", "TPA", "Permitted", 7), ("FL", "Pasco", "New Port Richey", "346", "Tier 2", "TPA", "Permitted", 3),
                        ("FL", "Lee", "Fort Myers", "339", "Tier 1", "SWF", "Permitted", 6), ("FL", "Collier", "Naples", "341", "Tier 1", "SWF", "Permitted", 4),
                        ("FL", "Orange", "Orlando", "328", "Inland", "CNF", "Permitted", 9), ("FL", "Duval", "Jacksonville", "322", "Tier 2", "CNF", "Permitted", 7),
                        ("FL", "Polk", "Lakeland", "338", "Inland", "CNF", "Permitted", 4), ("FL", "Monroe", "Key West", "330", "Tier 1", "MIA", "Excluded", 0)],
        "min_aop": [(0, 1_000_000, 5_000), (1_000_000, 5_000_000, 10_000), (5_000_000, None, 25_000)],
        "ns_min": {"Tier 1": 0.03, "Tier 2": 0.02}, "tolerance": (0.08, 0.25), "referral": {"tiv_any": 7_500_000, "tiv_tier1": 4_000_000, "year_built": 1970},
        "aggregates": [("MIA", "South Florida", "Hurricane", 0.93), ("TPA", "Tampa Bay", "Hurricane", 0.79), ("SWF", "Southwest Florida", "Hurricane", 0.71),
                       ("CNF", "Central & North Florida", "Hurricane", 0.55)],
        "endorsement": {"effective": "2026-07-01", "issued": "2026-06-15", "reason": "Minimum named storm deductible in Tier 1 counties raised after the carrier's 2026 wind review.",
                        "ns_min": {"Tier 1": 0.05}},
        "tiv_range": (400_000, 4_500_000),
    },
    "ch_ridgeway": {
        "scenario": "A4", "name": "Ridgeway Programs Inc.", "short": "Ridgeway", "program": "Mid-Atlantic Business Property",
        "pin": "CH-27761", "umr": "B1302NGS26RPI04", "agreement": "NGS/DA/2026/018", "cert_prefix": "RPI", "broker": "Keel & Crane Insurance Services",
        "contact": "Tessa Morgan", "contact_title": "Operations Manager", "domain": "ridgewayprograms.example", "hq": "King of Prussia, PA",
        "period": ("2026-01-01", "2026-12-31"), "commission": 0.20, "max_limit": 4_000_000, "gpi_limit": 14_000_000,
        "layout": "messy", "response_days": 5, "received_day": {"2026-05": "2026-06-26", "2026-06": "2026-07-24", "2026-07": "2026-08-24", "2026-08": "2026-09-25"},
        "story": "Bordereau quality: non-standard columns, missing mandatory CRS fields, arithmetic errors, late every month",
        "title": "Messy, late bordereaux hide authority breaches",
        "rows": {"NEW": 46, "RENEWAL": 58, "ENDORSEMENT": 8, "CANCELLATION": 3}, "rarc": {"2026-05": 0.012, "2026-06": 0.008, "2026-07": 0.004, "2026-08": 0.002},
        "classes": {"OFF": "Permitted", "RET": "Permitted", "SCC": "Permitted", "RST": "Permitted", "WHS": "Permitted", "LMF": "Permitted", "APT": "Permitted",
                    "AUT": "Permitted", "CHU": "Permitted"},
        "class_mix": {"OFF": 18, "RET": 20, "SCC": 8, "RST": 12, "WHS": 12, "LMF": 10, "APT": 10, "AUT": 6, "CHU": 4},
        "prohibited": ["CAN", "BAR", "VAC", "SCR", "FWK"],
        "territories": [("PA", "Allegheny", "Pittsburgh", "152", "Inland", "PAX", "Permitted", 10), ("PA", "Philadelphia", "Philadelphia", "191", "Inland", "PAX", "Permitted", 10),
                        ("PA", "Montgomery", "Norristown", "194", "Inland", "PAX", "Permitted", 8), ("PA", "Lancaster", "Lancaster", "176", "Inland", "PAX", "Permitted", 5),
                        ("NJ", "Bergen", "Hackensack", "076", "Inland", "NJX", "Permitted", 8), ("NJ", "Middlesex", "New Brunswick", "089", "Inland", "NJX", "Permitted", 7),
                        ("NJ", "Monmouth", "Freehold", "077", "Tier 2", "NJX", "Permitted", 5), ("NY", "Westchester", "White Plains", "106", "Inland", "NYX", "Permitted", 6),
                        ("NY", "Nassau", "Mineola", "115", "Tier 2", "NYX", "Permitted", 5), ("NY", "Kings", "Brooklyn", "112", "Tier 2", "NYX", "Excluded", 0),
                        ("MD", "Baltimore", "Towson", "212", "Inland", "MDX", "Permitted", 6), ("DE", "New Castle", "Wilmington", "198", "Inland", "MDX", "Permitted", 4)],
        "min_aop": [(0, 1_000_000, 2_500), (1_000_000, 4_000_000, 5_000), (4_000_000, None, 10_000)],
        "ns_min": {}, "tolerance": (0.08, 0.25), "referral": {"tiv_any": 5_000_000, "tiv_tier1": None, "year_built": 1955},
        "aggregates": [("PAX", "Pennsylvania", "Severe convective storm", 0.46), ("NJX", "New Jersey", "Hurricane", 0.52), ("NYX", "New York", "Hurricane", 0.49),
                       ("MDX", "Maryland & Delaware", "Hurricane", 0.33)],
        "endorsement": {"effective": "2026-07-01", "issued": "2026-06-20", "reason": "Commission increased in recognition of the coverholder taking on first-notice-of-loss handling.",
                        "commission": 0.22},
        "tiv_range": (250_000, 3_200_000),
    },
    "ch_sierra": {
        "scenario": "A5", "name": "Sierra Crest Underwriting", "short": "Sierra Crest", "program": "Western States Commercial Property",
        "pin": "CH-22408", "umr": "B0776NGS26SCU05", "agreement": "NGS/DA/2026/011", "cert_prefix": "SCU", "broker": "Brightwater Risk Advisors",
        "contact": "Nathan Cole", "contact_title": "Claims & Compliance Lead", "domain": "sierracrestuw.example", "hq": "Sacramento, CA",
        "period": ("2026-01-01", "2026-12-31"), "commission": 0.225, "max_limit": 5_000_000, "gpi_limit": 20_000_000,
        "layout": "crs", "response_days": 5, "received_day": {"2026-05": "2026-06-05", "2026-06": "2026-07-06", "2026-07": "2026-08-01", "2026-08": "2026-09-10"},
        "story": "Claims bordereau: a large wildfire loss on a risk written in an excluded county, a late-notified fire, reserve jumps",
        "title": "Large loss on an out-of-authority risk, notified late",
        "rows": {"NEW": 58, "RENEWAL": 70, "ENDORSEMENT": 8, "CANCELLATION": 4}, "rarc": {"2026-05": 0.058, "2026-06": 0.064, "2026-07": 0.071, "2026-08": 0.069},
        "classes": {"OFF": "Permitted", "RET": "Permitted", "SCC": "Permitted", "RST": "Permitted", "WHS": "Permitted", "LMF": "Permitted", "APT": "Permitted",
                    "SST": "Permitted", "AUT": "Permitted"},
        "class_mix": {"OFF": 16, "RET": 18, "SCC": 8, "RST": 14, "WHS": 14, "LMF": 10, "APT": 8, "SST": 6, "AUT": 6},
        "prohibited": ["CAN", "BAR", "VAC", "SCR", "FWK"],
        "territories": [("CA", "Los Angeles", "Los Angeles", "900", "Inland", "LAX", "Permitted", 16), ("CA", "Orange", "Irvine", "926", "Inland", "LAX", "Permitted", 9),
                        ("CA", "San Diego", "San Diego", "921", "Inland", "SAN", "Permitted", 9), ("CA", "Sacramento", "Sacramento", "958", "Inland", "SAC", "Permitted", 10),
                        ("CA", "Fresno", "Fresno", "937", "Inland", "SAC", "Permitted", 6), ("CA", "Butte", "Chico", "959", "Inland", "SAC", "Excluded", 0),
                        ("CA", "Shasta", "Redding", "960", "Inland", "SAC", "Excluded", 0), ("NV", "Clark", "Las Vegas", "891", "Inland", "LAS", "Permitted", 10),
                        ("NV", "Washoe", "Reno", "895", "Inland", "RNO", "Permitted", 5), ("AZ", "Maricopa", "Phoenix", "850", "Inland", "PHX", "Permitted", 12),
                        ("AZ", "Pima", "Tucson", "857", "Inland", "PHX", "Permitted", 4), ("OR", "Multnomah", "Portland", "972", "Inland", "PDX", "Permitted", 7)],
        "min_aop": [(0, 1_000_000, 5_000), (1_000_000, 5_000_000, 10_000), (5_000_000, None, 25_000)],
        "ns_min": {}, "tolerance": (0.08, 0.25), "referral": {"tiv_any": 6_000_000, "tiv_tier1": None, "year_built": 1960},
        "aggregates": [("LAX", "Southern California", "Earthquake", 0.62), ("SAN", "San Diego", "Earthquake", 0.48), ("SAC", "Sacramento Valley", "Wildfire", 0.57),
                       ("RNO", "Reno–Tahoe", "Earthquake", 0.36), ("PDX", "Portland", "Earthquake", 0.31)],
        "endorsement": {"effective": "2026-06-15", "issued": "2026-06-01", "reason": "Large-loss notification tightened after the 2026 wildfire season outlook.",
                        "large_loss_days": 5},
        "tiv_range": (300_000, 4_000_000),
    },
}
ORDER = ["ch_meridian", "ch_northfield", "ch_palmcoast", "ch_ridgeway", "ch_sierra"]

# ----------------------------------------------------------------------------- Lloyd's CRS v5.2-style field set
# field -> (CRS label, type, mandatory, synonyms)
RISK_FIELDS: dict[str, tuple[str, str, bool, list[str]]] = {
    "umr": ("Unique Market Reference (UMR)", "text", True, ["umr", "unique market reference"]),
    "agreement_no": ("Binding Authority Agreement Number", "text", True, ["agreement number", "binder number", "baa number", "binding authority ref", "binder ref"]),
    "reporting_period": ("Reporting Period (End Date)", "date", True, ["reporting period", "period end", "bdx period", "reporting month"]),
    "certificate_ref": ("Certificate Reference", "text", True, ["certificate ref", "certificate number", "certificate no", "policy number", "policy no", "pol no.", "pol no", "cert #", "cert no", "policy #"]),
    "transaction_type": ("Transaction Type", "enum", True, ["transaction", "txn type", "type", "trans type", "transaction code"]),
    "insured_name": ("Insured Name", "text", True, ["insured", "name insured", "insd name", "named insured", "policyholder"]),
    "address": ("Risk Address", "text", True, ["address", "location address", "loc addr", "risk location", "street address", "property address"]),
    "city": ("Risk City", "text", False, ["city", "town", "loc city"]),
    "state": ("Risk State", "state", True, ["state", "st", "risk state code", "loc state"]),
    "county": ("Risk County", "text", True, ["county", "parish", "county/parish", "region"]),
    "zip": ("Risk Zip Code", "zip", True, ["zip", "zip code", "zip cd", "postal code", "postcode"]),
    "class_code": ("Class of Business Code", "text", True, ["class code", "class", "program class", "cob code", "occ code"]),
    "occupancy": ("Occupancy Description", "text", True, ["occupancy", "occ", "occupancy desc", "business description", "description of operations"]),
    "construction": ("Construction", "text", True, ["construction type", "const", "const type", "iso construction", "constr"]),
    "year_built": ("Year Built", "year", True, ["yr built", "year of construction", "yob", "built"]),
    "tiv": ("Total Sum Insured (TIV)", "money", True, ["tiv", "total insured value", "sum insured", "total tiv", "total sum insured"]),
    "limit": ("Limit of Liability", "money", True, ["limit", "policy limit", "lmt", "limit of insurance"]),
    "aop_deductible": ("Deductible (All Other Perils)", "money", True, ["aop deductible", "aop ded", "deductible", "ded", "aop"]),
    "ns_deductible_pct": ("Named Storm Deductible %", "pct", False, ["named storm ded", "ns ded %", "wind deductible %", "named storm deductible", "hurricane ded"]),
    "written_date": ("Date Written", "date", True, ["bound date", "date bound", "bnd dt", "written date", "date of binding"]),
    "inception": ("Risk Inception Date", "date", True, ["inception", "effective date", "eff dt", "inception date", "policy effective"]),
    "expiry": ("Risk Expiry Date", "date", True, ["expiry", "expiration date", "exp dt", "expiry date", "policy expiration"]),
    "gross_premium": ("Gross Premium", "money", True, ["gross written premium", "gwp", "gross premium", "premium", "written premium"]),
    "referral_ref": ("Referral / Approval Reference", "text", False, ["referral ref", "ref #", "approval ref", "referral number", "carrier approval", "ngs ref"]),
    "prior_certificate": ("Renewal of Certificate", "text", False, ["expiring policy", "renewal of", "prior policy", "expiring certificate"]),
    "prior_premium": ("Expiring Gross Premium", "money", False, ["expiring premium", "prior premium", "exp gwp", "prior year premium", "prior yr prem"]),
    "prior_tiv": ("Expiring TIV", "money", False, ["expiring tiv", "prior tiv", "prior year tiv", "exp tiv", "prior yr tiv"]),
    "prior_aop_deductible": ("Expiring AOP Deductible", "money", False, ["expiring deductible", "prior deductible", "exp ded"]),
}
PREMIUM_FIELDS: dict[str, tuple[str, str, bool, list[str]]] = {
    "umr": RISK_FIELDS["umr"], "agreement_no": RISK_FIELDS["agreement_no"], "reporting_period": RISK_FIELDS["reporting_period"],
    "certificate_ref": RISK_FIELDS["certificate_ref"], "transaction_type": RISK_FIELDS["transaction_type"], "insured_name": RISK_FIELDS["insured_name"],
    "gross_premium": RISK_FIELDS["gross_premium"],
    "commission_pct": ("Commission %", "pct", True, ["commission", "brok %", "comm %", "commission rate", "brokerage %"]),
    "commission_amount": ("Commission Amount", "money", True, ["commission amt", "comm amt", "brokerage", "commission $"]),
    "taxes": ("Taxes & Fees", "money", False, ["taxes", "surplus lines tax", "sl tax & fees", "tax & fees", "fees"]),
    "net_premium": ("Net Premium Due to Carrier", "money", True, ["net premium", "net due", "net to carrier", "net"]),
}
CLAIM_FIELDS: dict[str, tuple[str, str, bool, list[str]]] = {
    "umr": RISK_FIELDS["umr"], "agreement_no": RISK_FIELDS["agreement_no"], "reporting_period": RISK_FIELDS["reporting_period"],
    "claim_ref": ("Claim Reference", "text", True, ["claim number", "claim no", "claim #", "claim ref"]),
    "certificate_ref": RISK_FIELDS["certificate_ref"], "insured_name": RISK_FIELDS["insured_name"], "state": RISK_FIELDS["state"],
    "date_of_loss": ("Date of Loss", "date", True, ["dol", "loss date", "date of loss"]),
    "date_reported": ("Date Claim Notified", "date", True, ["date reported", "notified", "report date", "date notified"]),
    "cause": ("Cause of Loss", "text", True, ["cause", "peril", "loss cause"]),
    "description": ("Loss Description", "text", False, ["description", "loss details", "narrative"]),
    "status": ("Claim Status", "text", True, ["status", "claim status"]),
    "paid": ("Paid to Date", "money", True, ["paid", "paid to date", "indemnity paid"]),
    "reserve": ("Outstanding Reserve", "money", True, ["reserve", "outstanding", "o/s reserve", "os reserve"]),
    "incurred": ("Total Incurred", "money", True, ["incurred", "total incurred"]),
    "handled_by": ("Claim Handled By", "text", False, ["handler", "tpa", "handled by"]),
}
EXPOSURE_FIELDS: dict[str, tuple[str, str, bool, list[str]]] = {
    "state": RISK_FIELDS["state"], "county": RISK_FIELDS["county"],
    "policies": ("Policies In Force", "int", True, ["policies", "policy count", "pif"]),
    "tiv": ("In-force TIV", "money", True, ["tiv", "in-force tiv", "total insured value", "sum insured"]),
}

# layout of the coverholder's own template (header text per field); fields missing here are absent from their file
LAYOUTS = {
    "variant": {  # Meridian's own system export: familiar synonyms, CRS order mostly
        "umr": "UMR", "agreement_no": "Binder Ref", "reporting_period": "Bdx Period", "certificate_ref": "Policy Number", "transaction_type": "Trans Type",
        "insured_name": "Named Insured", "address": "Location Address", "city": "City", "state": "State", "county": "County/Parish", "zip": "Zip",
        "class_code": "Program Class", "occupancy": "Occupancy", "construction": "Const Type", "year_built": "Yr Built", "tiv": "TIV", "limit": "Policy Limit",
        "aop_deductible": "AOP Ded", "ns_deductible_pct": "Named Storm Ded", "written_date": "Bound Date", "inception": "Effective Date", "expiry": "Expiration Date",
        "gross_premium": "Gross Written Premium", "referral_ref": "Carrier Approval", "prior_certificate": "Expiring Policy", "prior_premium": "Expiring Premium",
        "prior_tiv": "Expiring TIV", "prior_aop_deductible": "Expiring Deductible"},
    "messy": {  # Ridgeway's production report: abbreviated headers, no construction / year built / county
        "certificate_ref": "Pol No.", "transaction_type": "Type", "insured_name": "Insd Name", "address": "Loc Addr", "city": "City", "state": "St",
        "zip": "Zip Cd", "class_code": "Cls", "occupancy": "Occ", "tiv": "Sum Insured", "limit": "Lmt", "aop_deductible": "Ded", "written_date": "Bnd Dt",
        "inception": "Eff Dt", "expiry": "Exp Dt", "gross_premium": "GWP", "referral_ref": "NGS Ref", "prior_premium": "Prior Yr Prem", "prior_tiv": "Prior Yr TIV",
        "umr": "Mkt Ref", "reporting_period": "Month"},
}
PREMIUM_LAYOUTS = {
    "variant": {"umr": "UMR", "agreement_no": "Binder Ref", "reporting_period": "Bdx Period", "certificate_ref": "Policy Number", "transaction_type": "Trans Type",
                "insured_name": "Named Insured", "gross_premium": "Gross Written Premium", "commission_pct": "Comm %", "commission_amount": "Comm Amt",
                "taxes": "SL Tax & Fees", "net_premium": "Net Due"},
    "messy": {"certificate_ref": "Pol No.", "transaction_type": "Type", "insured_name": "Insd Name", "gross_premium": "GWP", "commission_pct": "Brok %",
              "commission_amount": "Brokerage", "taxes": "Fees", "net_premium": "Net", "reporting_period": "Month"},
}
TXN_MAP = {"new": "NEW", "nb": "NEW", "new business": "NEW", "n": "NEW", "renewal": "RENEWAL", "rn": "RENEWAL", "ren": "RENEWAL", "r": "RENEWAL",
           "endorsement": "ENDORSEMENT", "end": "ENDORSEMENT", "endt": "ENDORSEMENT", "mta": "ENDORSEMENT", "cancellation": "CANCELLATION",
           "cxl": "CANCELLATION", "canx": "CANCELLATION", "can": "CANCELLATION", "correction": "CORRECTION", "corr": "CORRECTION"}
TXN_LABEL = {"NEW": "New", "RENEWAL": "Renewal", "ENDORSEMENT": "Endorsement", "CANCELLATION": "Cancellation", "CORRECTION": "Correction"}
MESSY_TXN = {"NEW": "NB", "RENEWAL": "RN", "ENDORSEMENT": "END", "CANCELLATION": "CXL", "CORRECTION": "CORR"}
STATES = {"AL", "AZ", "CA", "DE", "FL", "IL", "IN", "LA", "MD", "MI", "MS", "NJ", "NV", "NY", "OH", "OR", "PA", "TX", "WI"}
STATE_NAMES = {"texas": "TX", "louisiana": "LA", "florida": "FL", "ohio": "OH", "pennsylvania": "PA", "new jersey": "NJ", "new york": "NY", "california": "CA",
               "nevada": "NV", "arizona": "AZ", "oregon": "OR", "mississippi": "MS", "alabama": "AL", "indiana": "IN", "michigan": "MI", "illinois": "IL",
               "wisconsin": "WI", "maryland": "MD", "delaware": "DE"}

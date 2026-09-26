"""Decision Assurance world: new-business submissions to Northgate (fictional). Six hero cases, each a distinct
real-life decision situation, plus a background book worked by simulated underwriters. This module holds the
*truth* each submission is rendered from; what the engine knows comes only from parsing the rendered files."""
from __future__ import annotations

import random
from datetime import date, timedelta

from uwc.refdata import BROKERS, CITIES, STREETS

L = lambda **kw: {"alarm": "Central station", "ppc": 3, "roof_type": "Built-up (BUR)", "storage": None, "design": None, "commodity": None,
                  "claims": {}, "stock": 0.0, **kw}

HEROES: dict[str, dict] = {
    # ------------------------------------------------------------------------------------------------ D1 (deck example)
    "nb_d1": {
        "scenario": "D1", "title": "Sprinkler contradiction and a 23-year roof — pass with flags",
        "insured": "Halvorsen Precision Components, Inc.", "short": "Halvorsen Precision", "fein": "75-4412930", "entity": "Corporation", "years": 31,
        "naics": "332710", "segment": "Middle market", "state": "TX", "mailing": "4410 Foundry St, Fort Worth, TX 76106",
        "description": "Precision machining, assembly and powder-coat finishing of aerospace and energy components; finished-parts distribution from Austin.",
        "broker": "Keel & Crane Insurance Services", "contact": "Amelia Crane", "uw": "u_maya",
        "arrive": "2026-08-03", "effective": "2026-09-01", "prior_carrier": "Westbrook Mutual (fictional)", "prior_premium": 468_000, "target": 495_000,
        "sched_mod": 1.15, "loss_years": 5,
        "locations": [
            L(name="Fort Worth machining & assembly", address="4410 Foundry St", city="Fort Worth", zip="76106", occ_raw="Precision machining & assembly", occ="manufacturing",
              cons_raw="Masonry non-combustible", cons=4, yb=1996, stories=1, sqft=620_000, roof=2003, spr=1.0, building=126_400_000, contents=55_900_000, stock=18_800_000, bi=35_200_000),
            L(name="Dallas finishing & coating plant", address="2250 Commerce Loop", city="Dallas", zip="75212", occ_raw="Metal fabrication, finishing & powder coating", occ="manufacturing",
              cons_raw="Non-combustible", cons=3, yb=2006, stories=1, sqft=380_000, roof=2014, spr=0.6, roof_type="Single-ply TPO", building=70_500_000, contents=35_200_000, stock=14_000_000, bi=25_500_000,
              claims={"app": {"spr": 1.0}, "sov": {"spr": 1.0}}),
            L(name="Austin distribution center", address="9120 Railyard Rd", city="Austin", zip="78744", occ_raw="Warehouse / distribution", occ="warehouse",
              cons_raw="Tilt-up concrete", cons=4, yb=2012, stories=1, sqft=440_000, roof=2012, spr=1.0, roof_type="Single-ply TPO", building=55_900_000, contents=8_500_000, stock=33_400_000, bi=11_500_000,
              storage=24, design=30, commodity="Finished machined parts (Class II)"),
        ],
        "losses": [dict(dol="2022-04-27", loc=0, cause="hail", status="Closed", paid=86_400, reserve=0, desc="Hail damage to BUR roof membrane and rooftop units, Fort Worth"),
                   dict(dol="2024-11-09", loc=1, cause="water", status="Closed", paid=31_200, reserve=0, desc="Domestic water line break in office area, Dallas")],
        "inspection": {"date": "2026-06-18", "firm": "Keystone Loss Control Services (fictional)", "engineer": "R. Delgado, CSP",
                       "notes": {1: "The finishing and powder-coating wing (about 40% of the floor area) is not sprinklered; the system covers the fabrication bay and offices only. Flammable-liquid storage is in listed cabinets."}},
        "email": "All three plants are fully sprinklered and the Fort Worth roof is in good shape.",
        "script": {"request": ["Roof replacement schedule — Fort Worth plant"], "request_wait": False,
                   "prerefer": {"approver": "u_daniel", "note": "Dallas coating wing unsprinklered (inspection); application states fully sprinklered. Requesting L2 sign-off on the sprinkler exposure before quoting.",
                                "envelope": {"min_premium": 495_000, "min_aop": 250_000}, "conditions": []},
                   "action": {"type": "QUOTE", "premium": 505_000, "aop": 250_000, "wh_pct": 0.01, "rationale": "Within the suggested range; incumbent at $468K with a lower deductible. Quote subject to the Fort Worth roof schedule."},
                   "broker_accepts": True, "outcome": {"days": 166, "cause": "hail", "loc": 0, "incurred": 182_000, "desc": "Hail — BUR roof membrane and skylights, Fort Worth plant"}},
    },
    # ------------------------------------------------------------------------------------------------ D2 clean office
    "nb_d2": {
        "scenario": "D2", "title": "Clean office submission — pass, decided in a day",
        "insured": "Larkspur Professional Plaza LLC", "short": "Larkspur Plaza", "fein": "31-5520847", "entity": "LLC", "years": 14,
        "naics": "531120", "segment": "Small commercial", "state": "OH", "mailing": "600 Northgate Blvd, Columbus, OH 43215",
        "description": "Owner and operator of a two-building professional office campus leased to medical and financial-services tenants.",
        "broker": "Calder Street Brokerage", "contact": "Hannah Weiss", "uw": "u_tom",
        "arrive": "2026-08-03", "effective": "2026-09-15", "prior_carrier": "Lakeshore Casualty (fictional)", "prior_premium": 51_000, "target": 55_000,
        "sched_mod": 1.0, "loss_years": 5,
        "locations": [
            L(name="Larkspur Plaza — Building A", address="600 Northgate Blvd", city="Columbus", zip="43215", occ_raw="Professional office", occ="office",
              cons_raw="Fire resistive", cons=6, yb=2008, stories=5, sqft=84_000, roof=2019, roof_type="Single-ply TPO", spr=1.0, ppc=2, building=19_600_000, contents=1_400_000, bi=1_800_000),
            L(name="Larkspur Plaza — Building B", address="640 Northgate Blvd", city="Columbus", zip="43215", occ_raw="Professional office", occ="office",
              cons_raw="Fire resistive", cons=6, yb=2011, stories=4, sqft=62_000, roof=2021, roof_type="Single-ply TPO", spr=1.0, ppc=2, building=14_700_000, contents=900_000, bi=1_300_000),
        ],
        "losses": [], "inspection": None, "email": "Two modern, fully sprinklered office buildings with no losses in five years.",
        "script": {"action": {"type": "QUOTE", "dev": 0.015, "rationale": "Technical plus a small margin; clean five-year history."},
                   "broker_accepts": True, "outcome": {"clean": True}},
    },
    # ------------------------------------------------------------------------------------------------ D3 bind below technical, loss runs short
    "nb_d3": {
        "scenario": "D3", "title": "Bind 18% below technical with 3 of 5 years of loss runs — hold, then corrected",
        "insured": "Cardinal Ridge Cold Storage, Inc.", "short": "Cardinal Ridge", "fein": "58-7730165", "entity": "Corporation", "years": 22,
        "naics": "493120", "segment": "Middle market", "state": "GA", "mailing": "3300 Kestrel Dr, Atlanta, GA 30336",
        "description": "Public refrigerated warehousing for food producers; ammonia refrigeration, blast freezing and cross-dock operations.",
        "broker": "Ironbridge Specialty Brokers", "contact": "Marcus Hale-Ng", "uw": "u_sofia",
        "arrive": "2026-08-04", "effective": "2026-08-20", "prior_carrier": "Summit Ridge Insurance (fictional)", "prior_premium": 152_000, "target": 0,
        "sched_mod": 1.0, "loss_years": 3,
        "locations": [
            L(name="Atlanta freezer & cross-dock", address="3300 Kestrel Dr", city="Atlanta", zip="30336", occ_raw="Cold storage / refrigerated warehouse", occ="cold_storage",
              cons_raw="Insulated metal panel", cons=3, yb=2001, stories=1, sqft=360_000, roof=2016, roof_type="Single-ply EPDM", spr=1.0, building=58_000_000, contents=22_000_000, stock=26_000_000, bi=11_000_000,
              storage=32, design=40, commodity="Frozen foods in corrugated (Class II)"),
            L(name="Nashville cooler", address="1180 Granite Ct", city="Nashville", zip="37210", occ_raw="Refrigerated warehouse", occ="cold_storage",
              cons_raw="Insulated metal panel", cons=3, yb=2009, stories=1, sqft=140_000, roof=2009, roof_type="Single-ply EPDM", spr=1.0, building=22_000_000, contents=9_000_000, stock=10_000_000, bi=4_000_000,
              storage=26, design=35, commodity="Chilled produce in corrugated (Class II)"),
        ],
        "losses": [],
        "hidden_losses": [dict(dol="2022-06-14", loc=0, cause="equipment", status="Closed", paid=598_000, reserve=0, desc="Ammonia compressor failure — product spoilage and refrigeration repair, Atlanta"),
                          dict(dol="2021-12-02", loc=1, cause="water", status="Closed", paid=74_500, reserve=0, desc="Condensate line freeze and rupture, Nashville")],
        "inspection": {"date": "2026-05-12", "firm": "Keystone Loss Control Services (fictional)", "engineer": "M. Osei, CSP", "notes": {}},
        "email": "Loss runs for the current carrier (three years) are attached; the prior carrier's runs will follow. The client is ready to bind at $140,000 if we can confirm this week.",
        "script": {"action": {"type": "BIND", "premium": 140_000, "aop": 100_000, "rationale": "Competitive: incumbent at $152K; clean three-year loss history."},
                   "request": ["Five years of currently valued loss runs (prior carrier 2021–2023)"], "request_after_verdict": True,
                   "revise": {"type": "QUOTE", "dev": -0.07, "aop": 100_000, "rationale": "Re-rated on five years of loss runs; 7% below technical on a clean current-carrier record, within L2."},
                   "broker_accepts": True, "outcome": {"clean": True}},
    },
    # ------------------------------------------------------------------------------------------------ D4 prohibited class
    "nb_d4": {
        "scenario": "D4", "title": "Declined class hidden in the operations description — hold and decline",
        "insured": "Rivergate Industrial Services LLC", "short": "Rivergate Industrial", "fein": "38-2294061", "entity": "LLC", "years": 9,
        "naics": "493110", "segment": "Small commercial", "state": "MI", "mailing": "2700 Ironworks Rd, Detroit, MI 48209",
        "description": "Industrial services: receiving, sorting, shredding and baling of ferrous and non-ferrous metals for mill supply; auto salvage parts storage.",
        "broker": "Harlan & Pierce Risk Partners", "contact": "Jordan Pierce", "uw": "u_tom",
        "arrive": "2026-08-05", "effective": "2026-09-01", "prior_carrier": "Great Lakes Specialty (fictional)", "prior_premium": 96_000, "target": 88_000,
        "sched_mod": 1.0, "loss_years": 5, "company_naics": "423930",
        "locations": [
            L(name="Ironworks Rd processing warehouse", address="2700 Ironworks Rd", city="Detroit", zip="48209", occ_raw="Warehouse / processing", occ="scrap",
              cons_raw="Metal building", cons=3, yb=1988, stories=1, sqft=88_000, roof=2011, spr=0.0, alarm="Local", ppc=4, building=7_900_000, contents=3_400_000, stock=2_600_000, bi=1_500_000,
              claims={"app": {"occ_raw": "Metal processing & warehouse"}}),
            L(name="Canal St yard office", address="415 Canal St E", city="Detroit", zip="48209", occ_raw="Office", occ="office",
              cons_raw="Joisted masonry", cons=2, yb=1972, stories=2, sqft=6_500, roof=2015, spr=0.0, alarm="Local", ppc=4, building=1_500_000, contents=250_000, bi=300_000),
        ],
        "losses": [dict(dol="2023-03-21", loc=0, cause="fire", status="Closed", paid=142_000, reserve=0, desc="Fire in shredder infeed conveyor, Ironworks Rd")],
        "inspection": None, "email": "A warehousing and light processing risk with a good fire history.",
        "script": {"override": [{"rule": "DA.APPETITE.PROHIBITED", "reason": "SOV and class code are warehousing; the processing is incidental to storage."}],
                   "action": {"type": "QUOTE", "premium": 28_000, "aop": 25_000, "rationale": "Rated as general warehouse per SOV and NAICS 493110."},
                   "referral_decision": {"approver": "u_robert", "decision": "DECLINE", "conditions": [], "note": "Scrap and recycling are declined under Guidelines 2026 §2.1. No exception."},
                   "outcome": None},
    },
    # ------------------------------------------------------------------------------------------------ D5 accumulation
    "nb_d5": {
        "scenario": "D5", "title": "Coastal hotels push Tampa Bay over its accumulation threshold — portfolio referral",
        "insured": "Pelican Bay Resort Holdings LLC", "short": "Pelican Bay Resorts", "fein": "59-6013384", "entity": "LLC", "years": 18,
        "naics": "721110", "segment": "Middle market", "state": "FL", "mailing": "1200 Heron Bay Dr, St. Petersburg, FL 33701",
        "description": "Owner-operator of two full-service beachfront hotels with restaurants, meeting space and pools.",
        "broker": "Tidewater Commercial Insurance", "contact": "Grace Oduya", "uw": "u_daniel",
        "arrive": "2026-08-06", "effective": "2026-10-01", "prior_carrier": "Coastline Mutual (fictional)", "prior_premium": 720_000, "target": 0,
        "sched_mod": 1.0, "loss_years": 5,
        "locations": [
            L(name="Pelican Bay Beach Resort", address="1200 Heron Bay Dr", city="St. Petersburg", zip="33701", occ_raw="Hotel / resort", occ="hotel",
              cons_raw="Reinforced concrete", cons=6, yb=1988, stories=7, sqft=265_000, roof=2016, roof_type="Modified bitumen", spr=1.0, building=76_000_000, contents=8_000_000, bi=16_000_000),
            L(name="Clearwater Bayfront Inn", address="80 Mariner Blvd", city="Clearwater", zip="33755", occ_raw="Hotel", occ="hotel",
              cons_raw="Masonry non-combustible", cons=4, yb=1979, stories=4, sqft=96_000, roof=2010, roof_type="Modified bitumen", spr=1.0, building=28_000_000, contents=3_000_000, bi=6_000_000),
        ],
        "losses": [dict(dol="2024-10-09", loc=0, cause="hurricane", status="Closed", paid=412_000, reserve=0, desc="Hurricane — wind-driven rain and pool deck damage, St. Petersburg")],
        "inspection": {"date": "2026-04-22", "firm": "Keystone Loss Control Services (fictional)", "engineer": "T. Whitfield, CSP", "notes": {}},
        "email": "Both hotels were fully renovated and are well protected. Named storm at 3% per our discussion.",
        "script": {"action": {"type": "QUOTE", "dev": 0.0, "aop": 100_000, "ns_pct": 0.03, "ns_min": 250_000, "line": 1.0, "rationale": "At technical on guideline named-storm terms."},
                   "referral_decision": {"approver": "u_priya", "decision": "APPROVE", "conditions": ["Line limited to 50% of the programme"],
                                         "envelope": {"max_line": 0.5, "min_ns_pct": 0.03}, "note": "Tampa Bay is at capacity after renewals. Approve a 50% line only."},
                   "revise": {"type": "QUOTE", "dev": 0.0, "aop": 100_000, "ns_pct": 0.03, "ns_min": 250_000, "line": 0.5, "rationale": "50% line per portfolio approval."},
                   "broker_accepts": True, "outcome": {"clean": True}},
    },
    # ------------------------------------------------------------------------------------------------ D6 override + manuscript
    "nb_d6": {
        "scenario": "D6", "title": "Flag overridden and manuscript deletes the water exclusion — senior approves with conditions",
        "insured": "Palmetto Gateway Distribution LLC", "short": "Palmetto Gateway", "fein": "57-1184402", "entity": "LLC", "years": 11,
        "naics": "493110", "segment": "Middle market", "state": "SC", "mailing": "7700 Tidewater Ln, Charleston, SC 29405",
        "description": "Third-party logistics: import consumer goods deconsolidation, racked storage and e-commerce fulfilment near the port.",
        "broker": "Brightwater Risk Advisors", "contact": "Luis Ortega", "uw": "u_sofia",
        "arrive": "2026-08-07", "effective": "2026-09-15", "prior_carrier": "Harborline Insurance (fictional)", "prior_premium": 610_000, "target": 0,
        "sched_mod": 1.0, "loss_years": 5,
        "locations": [
            L(name="North Charleston fulfilment center", address="7700 Tidewater Ln", city="Charleston", zip="29405", occ_raw="Warehouse / distribution", occ="warehouse",
              cons_raw="Tilt-up concrete", cons=4, yb=2015, stories=1, sqft=420_000, roof=2015, roof_type="Single-ply TPO", spr=1.0, building=38_000_000, contents=4_000_000, stock=26_000_000, bi=9_000_000,
              storage=30, design=20, commodity="Group A plastics — consumer goods", claims={"app": {"storage": 20}, "sov": {"storage": 20}}),
            L(name="Port transload building", address="15 Canal St E", city="Charleston", zip="29401", occ_raw="Warehouse", occ="warehouse",
              cons_raw="Metal building", cons=3, yb=2003, stories=1, sqft=160_000, roof=2003, roof_type="Metal standing seam", spr=1.0, building=14_500_000, contents=1_500_000, stock=12_000_000, bi=3_000_000,
              storage=18, design=25, commodity="Palletized mixed goods (Class III)"),
        ],
        "losses": [dict(dol="2023-08-30", loc=1, cause="wind", status="Closed", paid=118_000, reserve=0, desc="Tropical storm — roof panel damage, port transload building")],
        "inspection": {"date": "2026-07-08", "firm": "Keystone Loss Control Services (fictional)", "engineer": "L. Park, PE", "notes": {0: "Racks are loaded to about 30 ft; the ceiling-only sprinkler system is designed for 20 ft storage. No in-rack sprinklers were observed."}},
        "manuscript": {"form": "MS-WTR-01", "title": "Water Damage Amendment (broker manuscript)", "clause": "B.1.g", "subject": "Water exclusion"},
        "email": "Storage is within the sprinkler design. Please use our manuscript water damage amendment, which the incumbent accepted.",
        "script": {"override": [{"rule": "DA.PROT.STORAGE_ABOVE_DESIGN", "loc": 0, "reason": "In-rack sprinklers were installed in 2025 per the insured; storage is within design."}],
                   "action": {"type": "QUOTE", "dev": -0.04, "aop": 100_000, "ns_pct": 0.03, "ns_min": 250_000, "manuscript": "full",
                              "rationale": "Competitive with the incumbent; manuscript accepted by the prior carrier."},
                   "referral_decision": {"approver": "u_priya", "decision": "APPROVE",
                                         "conditions": ["Water exclusion reinstated for surface water, flood and storm surge; manuscript limited to sprinkler leakage and plumbing",
                                                        "In-rack sprinkler contractor letter and a verification survey before bind",
                                                        "Roof condition survey of the port transload building before bind"],
                                         "envelope": {"manuscript": "limited", "min_ns_pct": 0.03}, "note": "Approve with conditions. The manuscript as drafted gives back flood and surge in an AE zone."},
                   "revise": {"type": "QUOTE", "dev": -0.04, "aop": 100_000, "ns_pct": 0.03, "ns_min": 250_000, "manuscript": "limited",
                              "rationale": "Manuscript limited to sprinkler leakage per approval; conditions before bind."},
                   "request": ["In-rack sprinkler contractor completion letter"], "survey": True,
                   "broker_accepts": True, "outcome": {"days": 131, "cause": "flood", "loc": 1, "incurred": 1_350_000, "excluded": True,
                                                       "desc": "Nor'easter storm surge — surface water in the port transload building"}},
    },
}
HERO_IDS = list(HEROES)

# ============================================================================ background book
NAME_A = ["Ashgrove", "Bellwether", "Cobalt Ridge", "Dunmore", "Elmstead", "Fairhaven", "Glenrock", "Hollis Creek", "Ironvale", "Juniper Hill", "Kingsbury",
          "Lantern Bay", "Marlow", "Northwind", "Oakhurst", "Pinebrook", "Quarry Point", "Redfern", "Stonebridge", "Thornfield", "Upland", "Vantage Point",
          "Westmarch", "Yarrow", "Alderpoint", "Briar Glen", "Copperline", "Driftwood", "Eastgate", "Foxhollow", "Graystone", "Harrowgate", "Ivy Lane", "Keswick"]
OCC_SPEC = {  # class -> (suffix, sov raw, cons options, sqft range, $/sqft building, contents share, stock share, bi share, naics)
    "office": ("Office Partners", "Professional office", [6, 5, 4], (30_000, 140_000), 240, 0.08, 0.0, 0.1, "531120"),
    "manufacturing": ("Manufacturing", "Machining / assembly", [4, 3, 2], (60_000, 200_000), 120, 0.35, 0.15, 0.25, "332710"),
    "warehouse": ("Logistics", "Warehouse / distribution", [4, 3], (90_000, 380_000), 90, 0.05, 0.45, 0.12, "493110"),
    "retail": ("Retail Group", "Retail store", [2, 4, 3], (20_000, 90_000), 160, 0.1, 0.3, 0.15, "448310"),
    "hotel": ("Hospitality", "Hotel", [6, 4, 5], (60_000, 220_000), 290, 0.1, 0.0, 0.2, "721110"),
    "restaurant": ("Restaurant Group", "Full service restaurant", [2, 1], (5_000, 12_000), 280, 0.2, 0.05, 0.3, "722511"),
    "multifamily": ("Apartments", "Apartments", [1, 2, 4], (80_000, 260_000), 190, 0.02, 0.0, 0.08, "531110"),
    "cold_storage": ("Foods", "Cold storage", [3], (60_000, 160_000), 150, 0.3, 0.35, 0.12, "493120"),
    "scrap": ("Recovery", "Scrap metal", [3], (30_000, 90_000), 80, 0.3, 0.2, 0.1, "423930"),
}
BG_CITIES = ["Columbus", "Dayton", "Pittsburgh", "Philadelphia", "Chicago", "Atlanta", "Nashville", "Phoenix", "Minneapolis", "Charlotte", "Dallas", "Fort Worth",
             "Denver", "Houston", "Miami", "Charleston", "Los Angeles", "Irvine", "Seattle", "Detroit", "Boston", "Austin", "New Orleans"]
BG_UWS = ["u_maya", "u_daniel", "u_sofia", "u_tom"]
# issue archetypes for the simulated book: (weight, kind)
ARCHETYPES = [(10, "clean"), (4, "roof"), (3, "partial_spr"), (3, "below_tech"), (2, "loss_runs"), (2, "contra_cons"), (2, "ns_ded"), (1, "declined_class"),
              (2, "valuation"), (1, "override")]


def _pick(rng, weighted):
    tot = sum(w for w, _ in weighted)
    x = rng.uniform(0, tot)
    for w, k in weighted:
        x -= w
        if x <= 0:
            return k
    return weighted[-1][1]


def background(n: int = 36) -> dict[str, dict]:
    rng = random.Random(20260802)
    out = {}
    start = date(2024, 11, 4)
    for i in range(n):
        kind = _pick(rng, ARCHETYPES)
        if i in (1, 5, 9, 13):
            kind = "override"
        if i >= n - 6:
            kind = ["below_tech", "clean", "roof", "loss_runs", "below_tech", "clean"][i - (n - 6)]
        occ = rng.choice(["office", "manufacturing", "warehouse", "warehouse", "retail", "hotel", "restaurant", "multifamily", "cold_storage", "office"])
        if kind == "declined_class":
            occ = "scrap"
        suffix, raw, cons_opts, sq, rc, cs, ss, bs, naics = OCC_SPEC[occ]
        city = rng.choice(BG_CITIES)
        if kind == "ns_ded":
            city = rng.choice(["Miami", "Charleston", "Houston", "New Orleans"])
        if kind in ("roof", "override"):
            city = rng.choice(["Dallas", "Fort Worth", "Denver"])
        stt = CITIES[city][2]
        nloc = rng.choice([1, 1, 2, 2, 3])
        broker, contact = rng.choice(BROKERS)
        locs = []
        for j in range(nloc):
            sqft = round(rng.uniform(*sq) / 500) * 500
            cons = rng.choice(cons_opts)
            yb = rng.randint(1975, 2018)
            roof = max(yb, rng.randint(2008, 2023))
            if kind in ("roof", "override") and j == 0:
                roof = rng.randint(1998, 2004)
            spr = 1.0 if occ not in ("restaurant", "retail") or rng.random() < 0.6 else 0.0
            if kind == "partial_spr" and j == 0:
                spr = rng.choice([0.5, 0.6, 0.7])
            bld = round(sqft * rc * rng.uniform(0.9, 1.1), -4)
            if kind == "valuation" and j == 0:
                bld = round(bld * 0.62, -4)
            loc = L(name=f"{city} {['main site', 'second site', 'annex'][j]}", address=f"{rng.randint(100, 9800)} {rng.choice(STREETS)}", city=city,
                    zip=f"{rng.randint(10000, 99999)}", occ_raw=raw, occ=occ, cons_raw={1: "Frame", 2: "Joisted masonry", 3: "Non-combustible", 4: "Masonry non-combustible", 5: "Modified fire resistive", 6: "Fire resistive"}[cons],
                    cons=cons, yb=yb, stories=rng.choice([1, 1, 2, 3]) if occ not in ("office", "hotel", "multifamily") else rng.randint(2, 8), sqft=sqft, roof=roof, spr=spr,
                    building=bld, contents=round(bld * cs, -4), stock=round(bld * ss, -4), bi=round(bld * bs, -4), ppc=rng.choice([2, 3, 3, 4, 5]))
            if occ in ("warehouse", "cold_storage"):
                loc.update(storage=rng.choice([18, 22, 24, 26]), design=rng.choice([25, 30, 35]), commodity="Palletized mixed goods (Class III)")
            if kind == "contra_cons" and j == 0:
                loc["claims"] = {"app": {"cons_raw": "Masonry non-combustible" if cons != 4 else "Fire resistive"}}
            if kind == "partial_spr" and j == 0 and rng.random() < 0.5:
                loc["claims"] = {"app": {"spr": 1.0}}
            locs.append(loc)
        rec = start + timedelta(days=int(i * 560 / (n - 6)) + rng.randint(0, 4)) if i < n - 6 else date(2026, 7, [26, 29, 30, 27, 28, 31][i - (n - 6)])
        if kind in ("declined_class", "ns_ded") and rec < date(2026, 7, 1):
            rec = date(2026, 7, rng.randint(1, 24))
        eff = rec + timedelta(days=rng.randint(21, 45))
        losses = []
        for _ in range(rng.choice([0, 0, 0, 1, 1, 2])):
            y = rng.randint(2021, 2025)
            losses.append(dict(dol=f"{y}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}", loc=rng.randrange(nloc), cause=rng.choice(["water", "wind", "fire", "theft", "hail"]),
                               status="Closed", paid=round(rng.uniform(8_000, 160_000), -2), reserve=0, desc="Reported loss"))
        uw = rng.choice(BG_UWS)
        dev = rng.uniform(-0.035, 0.035)
        if kind == "below_tech":
            dev = rng.uniform(-0.22, -0.12)
        act = {"type": "QUOTE", "dev": round(dev, 3), "aop": None, "rationale": "Competitive position vs incumbent" if dev < -0.025 else "At or near technical"}
        script = {"action": act, "broker_accepts": rng.random() < 0.6, "bind_prob": 1.0}
        if kind == "ns_ded":
            act.update(ns_pct=0.02, ns_min=100_000)
            script["revise"] = dict(act, ns_pct=0.03, ns_min=250_000)
        if kind == "below_tech":
            script["revise"] = dict(act, dev=round(rng.uniform(-0.09, -0.03), 3), rationale="Re-priced after assurance hold")
            script["approve_pct"] = rng.random() < 0.35
        if kind == "loss_runs":
            act["type"] = "BIND"
            script["request"] = ["Five years of currently valued loss runs"]
            script["request_after_verdict"] = True
            script["revise"] = dict(act, type="QUOTE")
        if kind == "override":
            script["override"] = [{"rule": "DA.ROOF.AGE", "loc": 0, "reason": "Roof recently recoated per insured"}]
        if kind == "declined_class":
            script["referral_decision"] = {"approver": "u_robert", "decision": "DECLINE", "conditions": [], "note": "Declined class."}
        if kind == "partial_spr":
            script["prerefer"] = {"approver": "u_daniel" if uw != "u_daniel" else "u_priya", "note": "Partial sprinkler protection", "envelope": {}, "conditions": []}
        # outcome drawn later by the claims stub, with frequency linked to real risk features
        name = f"{NAME_A[i % len(NAME_A)]} {suffix}"
        cid = f"nb_b{i + 1:03d}"
        out[cid] = {"scenario": None, "title": kind, "insured": f"{name} {rng.choice(['LLC', 'Inc.', 'Holdings LLC', 'Co.'])}", "short": name,
                    "fein": f"{rng.randint(10, 99)}-{rng.randint(1000000, 9999999)}", "entity": "LLC", "years": rng.randint(3, 40), "naics": naics,
                    "segment": "Small commercial" if sum(l["building"] for l in locs) < 20e6 else "Middle market", "state": stt,
                    "mailing": f"{locs[0]['address']}, {city}, {stt} {locs[0]['zip']}", "description": f"{OCC_SPEC[occ][1]} operations.",
                    "broker": broker, "contact": contact, "uw": uw, "arrive": rec.isoformat(), "effective": eff.isoformat(), "prior_carrier": "Various (fictional)",
                    "prior_premium": 0, "target": 0, "sched_mod": round(rng.uniform(0.95, 1.05), 3), "loss_years": 3 if kind == "loss_runs" else 5,
                    "locations": locs, "losses": losses, "inspection": {"date": (rec - timedelta(days=40)).isoformat(), "firm": "Keystone Loss Control Services (fictional)", "engineer": "Field engineer", "notes": {}}
                    if sum(l["building"] + l["contents"] + l["stock"] + l["bi"] for l in locs) > 50e6 else None,
                    "email": "", "script": script, "kind": kind,
                    "hidden_losses": [dict(dol="2021-09-10", loc=0, cause="fire", status="Closed", paid=260_000, reserve=0, desc="Fire loss")] if kind == "loss_runs" and rng.random() < 0.5 else []}
        if kind == "declined_class":
            out[cid]["description"] = "Collection and processing of scrap metal and recyclable materials."
    return out


def tiv_of(loc: dict) -> float:
    return loc["building"] + loc["contents"] + loc["stock"] + loc["bi"]

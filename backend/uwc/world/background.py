"""108 background accounts with realistic variation and a controlled issue mix.

Target book outcome (blueprint §22.2): ~46% fast-track; the rest carry
reprice / restructure / refer / condition / data-request / non-renew actions.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from uwc.refdata import BROKERS, CITIES, UNDERWRITER_IDS
from uwc.world.builders import add_days, grow, loc, split_values
from uwc.world.scenarios import STD_FORMS
from uwc.world.truth import Account, Claim, Email, Recommendation, Terms

PREFIX = ["Allied", "Bayside", "Cobalt", "Driftwood", "Eastgate", "Falcon", "Granite", "Harborline", "Ironwood", "Juniper",
          "Kingsport", "Lakeshore", "Mesa", "Northfield", "Oakmont", "Pioneer", "Quarry", "Redwood", "Silverline", "Timberline",
          "Union", "Valley", "Westbrook", "Yardley", "Zenith", "Anchor", "Beacon", "Crescent", "Delta", "Evergreen", "Frontier",
          "Gateway", "Highland", "Keystone", "Liberty Row", "Magnolia", "Newport", "Orchard", "Prairie", "Ridgeway", "Sterling"]
SUFFIX = {
    "office": ["Properties", "Office Partners", "Realty Trust"], "retail": ["Stores", "Outfitters", "Home Goods"],
    "restaurant": ["Hospitality Group", "Kitchens", "Dining Co."], "hotel": ["Hotels", "Inns & Suites", "Hospitality"],
    "manufacturing": ["Manufacturing", "Industries", "Fabrication"], "warehouse": ["Logistics", "Distribution", "Freight Centers"],
    "shopping_ctr": ["Retail Centers", "Plaza Holdings", "Commons LLC"], "multifamily": ["Residential", "Apartments", "Living"],
    "cold_storage": ["Cold Chain", "Refrigerated Services", "Frozen Logistics"], "plastics": ["Polymers", "Molding", "Plastics"],
    "hospital": ["Health System", "Medical Group", "Care Network"], "scrap": ["Recycling", "Metals", "Salvage"],
}
OCC_RAW = {"office": "Office", "retail": "Retail store", "restaurant": "Restaurant", "hotel": "Hotel", "manufacturing": "Manufacturing",
           "warehouse": "Warehouse", "shopping_ctr": "Shopping center", "multifamily": "Apartments", "cold_storage": "Cold storage",
           "plastics": "Injection molding", "hospital": "Hospital", "scrap": "Scrap yard"}
CONS_RAW = {1: "Frame", 2: "Joisted masonry", 3: "Non-combustible", 4: "Masonry non-combustible", 5: "Modified fire resistive", 6: "Fire resistive"}

# issue -> share of background accounts (independent draws, some accounts get several)
ISSUES = {
    "undervalued": 0.13, "wind_floor": 0.12, "low_target": 0.16, "repeat_water": 0.08, "overdue_rec": 0.10,
    "binder_mismatch": 0.04, "occ_drift": 0.03, "old_roof": 0.07, "stale_values": 0.06, "dq_modifiers": 0.07,
}
CAT_CITIES = ["Tampa", "St. Petersburg", "Clearwater", "Miami", "Fort Lauderdale", "Houston", "Galveston", "New Orleans", "Charleston", "Wilmington"]
INLAND = ["Dallas", "Fort Worth", "Austin", "Denver", "Atlanta", "Nashville", "Charlotte", "Phoenix", "Chicago", "Columbus", "Dayton",
          "Pittsburgh", "Philadelphia", "Minneapolis", "Detroit", "Newark", "Boston", "Seattle", "Los Angeles", "Irvine", "San Jose", "Oakland", "Reno", "Sparks", "Ashburn", "Sterling"]


def build_background(rng: random.Random, n: int = 108) -> list[Account]:
    accounts: list[Account] = []
    start = date(2026, 9, 1)
    used_names: set[str] = set()
    for i in range(n):
        occ = rng.choices(list(SUFFIX), weights=[14, 10, 7, 8, 16, 14, 8, 8, 4, 4, 3, 2])[0]
        while True:
            name = f"{rng.choice(PREFIX)} {rng.choice(SUFFIX[occ])}"
            if name not in used_names:
                used_names.add(name)
                break
        expiry = start + timedelta(days=int(rng.triangular(0, 150, 50)))
        cat_heavy = rng.random() < 0.35
        nlocs = rng.choice([1, 1, 2, 2, 3, 3, 4, 5, 6, 8, 12])
        seg = "Large" if nlocs >= 8 or rng.random() < 0.12 else "E&S" if rng.random() < 0.1 else "Middle market"
        issues = {k for k, p in ISSUES.items() if rng.random() < p}
        if occ == "scrap":
            issues.add("declined")
        if not cat_heavy:
            issues.discard("wind_floor")
        locs = []
        for j in range(1, nlocs + 1):
            city = rng.choice(CAT_CITIES if cat_heavy and rng.random() < 0.7 else INLAND)
            tiv = rng.uniform(4e6, 45e6) * (1.6 if seg == "Large" else 1.0)
            vp = split_values(tiv, occ, rng)
            flat = "stale_values" in issues or "undervalued" in issues and rng.random() < 0.5
            vc = vp if flat else grow(vp, rng.uniform(1.02, 1.09))
            cons = rng.choice([2, 3, 3, 4, 4, 5, 6] if occ not in ("multifamily", "restaurant") else [1, 2, 2, 3])
            yb = rng.randint(1965, 2020)
            stories = rng.choice([1, 1, 1, 2, 3]) if occ in ("warehouse", "manufacturing", "cold_storage", "plastics", "scrap", "retail", "restaurant", "shopping_ctr") else rng.randint(2, 16)
            sqft = int(tiv / rng.uniform(150, 380))
            roof = rng.randint(max(yb, 1998), 2022)
            if "old_roof" in issues and j == 1:
                roof = rng.randint(1994, 2004)
            l = loc(rng, f"L{j}", f"{name.split()[0]} {city} {['Site', 'Facility', 'Building'][j % 3]}", city, occ, OCC_RAW[occ], cons,
                    CONS_RAW[cons], yb, stories, sqft, roof, vp, vc, ppc=rng.randint(1, 6), sprinkler_pct=rng.choice([1.0, 1.0, 1.0, 0.6, 0.0]),
                    loc_no_prior=str(j), loc_no_current=str(j))
            if "undervalued" in issues and j <= max(1, nlocs // 2):
                l.model_rc = round(vc.building / rng.uniform(0.66, 0.78), -3)
            if "occ_drift" in issues and j == 1 and occ == "warehouse":
                l.occupancy_prior = "warehouse"
                l.occupancy = "cold_storage"
            locs.append(l)
        wind_t1 = any(l.wind_tier == "T1" for l in locs)
        ns = None
        if cat_heavy:
            ns = 0.02 if ("wind_floor" in issues and wind_t1) else rng.choice([0.03, 0.05])
        t = Terms(limit=round(sum(l.values_current.tiv for l in locs), -5), aop_deductible=rng.choice([10_000, 25_000, 50_000, 100_000]),
                  named_storm_ded_pct=ns, named_storm_ded_min=((100_000 if "wind_floor" in issues else rng.choice([250_000, 250_000, 500_000])) if ns else None),
                  flood_sublimit=(10_000_000 if cat_heavy else None), forms=STD_FORMS + (["NS-CP 03 40"] if ns else []))
        issued = t
        if "binder_mismatch" in issues:
            issued = Terms(**{**t.dict(), "aop_deductible": t.aop_deductible / 2})
        claims = []
        if "repeat_water" in issues:
            for k in range(rng.choice([2, 3])):
                dol = (expiry - timedelta(days=rng.randint(40, 330))).isoformat()
                claims.append(Claim(f"CLM-{dol[2:4]}-{rng.randint(10000, 99999)}", "L1", dol, "water_nonweather", rng.randint(18, 140) * 1000, 0, "CLOSED",
                                    "Water damage from plumbing failure", report_date=dol))
        for _ in range(rng.choice([0, 0, 0, 1, 1, 2])):
            dol = (expiry - timedelta(days=rng.randint(400, 1700))).isoformat()
            claims.append(Claim(f"CLM-{dol[2:4]}-{rng.randint(10000, 99999)}", rng.choice([l.key for l in locs]), dol,
                                rng.choice(["wind_hail", "fire", "equipment", "theft", "water_nonweather"]), rng.randint(8, 220) * 1000, 0, "CLOSED",
                                "Historical loss", report_date=dol))
        recs = []
        if "overdue_rec" in issues:
            raised = (expiry - timedelta(days=rng.randint(420, 600))).isoformat()
            recs.append(Recommendation(f"R-{rng.randint(200, 999)}", "L1", raised, rng.choice(["Fire protection", "Electrical", "Roof", "Water / plumbing"]),
                                       rng.choice(["Repair impaired sprinkler branch lines in storage area", "Replace obsolete FPE Stab-Lok panels",
                                                   "Replace roof membrane over production area", "Install automatic water shutoff on domestic supply"]),
                                       rng.choice(["HIGH", "CRITICAL"]), (expiry - timedelta(days=rng.randint(120, 260))).isoformat(), "OPEN"))
        uw = rng.choice(UNDERWRITER_IDS)
        broker, contact = rng.choice(BROKERS)
        city_state = CITIES[locs[0].city][2]
        admitted = seg != "E&S"
        exp = expiry.isoformat()
        sov_date = add_days(exp, -rng.randint(45, 95))
        acct = Account(
            account_id=f"acc_{i + 1:03d}", name=name, scenario=None, scenario_title=None, segment=seg, occ_family=occ, hq_state=city_state,
            broker=broker, broker_contact=contact, underwriter_id=uw, tenure_years=rng.randint(1, 12), admitted=admitted,
            fein=f"{rng.randint(10, 99)}-{rng.randint(1000000, 9999999)}", policy_no=f"NSP-CP-2025-{rng.randint(30000, 49999)}",
            term_start=add_days(exp, -365), term_end=exp, locations=locs, terms_quoted=t, terms_binder=t, terms_issued=issued,
            claims=claims, recs=recs, renewal_sov_date=sov_date,
            sim={"adequacy": rng.uniform(0.86, 0.94) if "low_target" in issues else rng.uniform(1.04, 1.14), "issues": sorted(issues),
                 "target_rarc": rng.uniform(-0.09, -0.02) if "low_target" in issues else rng.uniform(-0.01, 0.04),
                 "accept_rate": rng.uniform(0.6, 0.9), "reported_bias": rng.gauss(0.052, 0.025)},
            loss_ratio_hist=rng.uniform(0.15, 0.9), brokerage_prior=rng.choice([0.10, 0.125, 0.15, 0.175]),
        )
        acct.brokerage_proposed = acct.brokerage_prior + (0.025 if rng.random() < 0.15 else 0.0)
        acct.emails = [Email(sov_date, f"{contact} <{contact.split()[0].lower()}@broker.example>", ["underwriting@northgate.example"],
                             f"{name} — {exp} property renewal", f"Please find attached the renewal SOV for {name}.\n\nRegards,\n{contact}\n{broker}",
                             attachments=["sov_2026"], kind="renewal_submission")]
        if "dq_modifiers" in issues:
            acct.sov_quirks["drop_roof_year"] = True
        accounts.append(acct)
    return accounts

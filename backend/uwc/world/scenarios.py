"""The 12 hero scenarios (S1–S12). Figures follow blueprint §10 and §22."""
from __future__ import annotations

import random

from uwc.world.builders import add_days, grow, loc, split_values
from uwc.world.truth import (Account, Building, Claim, Email, Endorsement, QuoteTruth, Recommendation, Terms, Values)

STD_FORMS = ["IL 00 17", "CP 00 90", "CP 00 10", "CP 00 30", "CP 10 30", "CP 04 05"]


def _acct(**kw) -> Account:
    kw.setdefault("term_start", add_days(kw["term_end"], -365))
    return Account(**kw)


# ---------------------------------------------------------------------- S1
def s1(rng: random.Random) -> Account:
    cities = ["Columbus", "Pittsburgh", "Chicago", "Atlanta", "Nashville", "Charlotte", "Minneapolis", "Philadelphia"]
    locs = []
    for i, c in enumerate(cities, 1):
        tiv = rng.uniform(14e6, 32e6)
        vp = split_values(tiv, "office", rng)
        locs.append(loc(rng, f"L{i}", f"Crestline Tower {c}", c, "office", "Class A office", rng.choice([5, 6]),
                        "__CONS__", rng.randint(1996, 2014), rng.randint(6, 18), int(tiv / 310), rng.randint(2016, 2022),
                        vp, grow(vp, 1.038), ppc=2, loc_no_prior=str(i), loc_no_current=str(i),
                        engineering_date="2025-05-12"))
    t = Terms(limit=sum(l.values_current.tiv for l in locs), aop_deductible=50_000, bi_sublimit=None,
              forms=STD_FORMS + ["CP 04 11"], safeguards=[{"code": "P-1", "location_key": l.key} for l in locs])
    return _acct(account_id="acc_s1", name="Crestline Office REIT", scenario="S1", scenario_title="Fast-track: no material change",
                 segment="Large", occ_family="office", hq_state="OH", broker="Calder Street Brokerage", broker_contact="Hannah Weiss",
                 underwriter_id="u_sofia", tenure_years=6, admitted=True, fein="31-4827719", policy_no="NSP-CP-2025-10231",
                 term_end="2026-09-15", locations=locs, terms_quoted=t, terms_binder=t, terms_issued=t,
                 renewal_sov_date="2026-07-20", sim={"adequacy": 1.04}, expected=[], loss_ratio_hist=0.18,
                 emails=[Email("2026-07-20", "Hannah Weiss <hweiss@calderstreet.example>", ["Sofia Alvarez <salvarez@northgate.example>"],
                               "Crestline Office REIT — 9/15 renewal SOV", "Sofia,\n\nRenewal SOV attached. Values trended per the REIT's annual appraisal update; no acquisitions or disposals.\n\nHannah",
                               attachments=["sov_2026"], kind="renewal_submission")],
                 brokerage_prior=0.125, brokerage_proposed=0.125)


# ---------------------------------------------------------------------- S2
def s2(rng: random.Random) -> Account:
    L1 = loc(rng, "L1", "Dayton Plant", "Dayton", "manufacturing", "Metal fabrication & assembly", 4, "Masonry non-combustible",
             1998, 1, 186_000, 2014, Values(30_000_000, 12_000_000, 3_000_000, 3_000_000),
             Values(31_000_000, 12_400_000, 3_000_000, 3_000_000), ppc=3, sprinkler_pct=1.0, street_no=4410, street="Foundry St",
             loc_no_prior="1", loc_no_current="1", model_rc_per_sqft=235, engineering_date="2024-03-15")
    L2 = loc(rng, "L2", "Tampa Assembly & DC", "Tampa", "manufacturing", "Assembly / distribution", 4, "Tilt-up concrete",
             2006, 1, 142_000, 2019, Values(19_500_000, 7_000_000, 3_000_000, 1_500_000),
             Values(23_800_000, 8_800_000, 4_000_000, 1_900_000), ppc=2, sprinkler_pct=1.0, street_no=1880, street="Harbor Point Dr",
             dx_km=2.0, dy_km=-3.0, loc_no_prior="2", loc_no_current="2", sov_roof_year=2011, engineering_date="2024-03-15",
             imagery=[{"date": "2024-05-02", "style": "roof_ok"}, {"date": "2026-06-11", "style": "roof_hail"}])
    L3 = loc(rng, "L3", "Reno Warehouse", "Reno", "li_storage", "Warehouse / battery storage", 3, "Steel frame / metal panel",
             2012, 1, 160_000, 2012, Values(15_000_000, 2_000_000, 8_000_000, 1_000_000),
             Values(15_000_000, 2_000_000, 8_000_000, 1_000_000), ppc=4, sprinkler_pct=1.0, street_no=955, street="Railyard Rd",
             loc_no_prior="3", loc_no_current="3", occupancy_prior="warehouse", occupancy_raw_prior="Warehouse", engineering_date="2024-04-02",
             storage_height_ft=24, sprinkler_design_ft=25, commodity="Lithium-ion battery packs (e-bike)", cat_construction_code=1)
    L4 = loc(rng, "L4", "Austin Components", "Austin", "manufacturing", "Machining", 4, "Masonry non-combustible",
             2001, 2, 64_000, 2008, Values(9_500_000, 3_600_000, 1_200_000, 700_000),
             Values(9_600_000, 3_600_000, 1_200_000, 700_000), ppc=3, sprinkler_pct=1.0, street_no=7020, street="Commerce Loop",
             loc_no_prior="4", loc_no_current="4", engineering_date="2024-04-10")
    L5 = loc(rng, "L5", "Tampa Expansion (Bldg 2)", "Tampa", "manufacturing", "Assembly", 3, "Metal building",
             2021, 1, 98_000, 2021, None, Values(13_000_000, 5_500_000, 2_500_000, 1_000_000), ppc=2, sprinkler_pct=1.0,
             street_no=1960, street="Harbor Point Dr", dx_km=2.6, dy_km=-2.7, status="new", loc_no_prior=None, loc_no_current="5")
    L5.values_prior = None
    L5.sov_roof_year = None
    locs = [L1, L2, L3, L4, L5]
    tq = Terms(limit=120_000_000, aop_deductible=100_000, named_storm_ded_pct=0.02, named_storm_ded_min=100_000,
               bi_sublimit=10_000_000, flood_sublimit=10_000_000, eq_sublimit=15_000_000,
               forms=STD_FORMS + ["CP 04 11", "NS-CP 03 40", "NS-CP 12 10", "NS-CP 12 20"],
               safeguards=[{"code": "P-1", "location_key": k} for k in ("L1", "L2", "L3", "L4")])
    issued = Terms(**{**tq.dict(), "bi_sublimit": 15_000_000})
    claims = [
        Claim("CLM-26-004411", "L4", "2025-12-03", "water_nonweather", 84_000, 0, "CLOSED", "Burst supply line above machining cell; ceiling and inventory damage", report_date="2025-12-04", linked_rec="R-114"),
        Claim("CLM-26-005902", "L4", "2026-04-19", "water_nonweather", 61_500, 22_000, "OPEN", "Roof drain backup into assembly area during heavy rain", report_date="2026-04-20", linked_rec="R-114"),
        Claim("CLM-25-001187", "L1", "2023-07-11", "equipment", 38_000, 0, "CLOSED", "Compressor motor failure", report_date="2023-07-12"),
    ]
    recs = [
        Recommendation("R-114", "L4", "2024-04-10", "Water / plumbing", "Replace corroded roof-drain leaders and install water-flow detection on domestic supply risers", "HIGH", "2025-10-31", "OPEN"),
        Recommendation("R-121", "L2", "2024-03-15", "Wind mitigation", "Upgrade roof-to-wall anchorage on east elevation; secure rooftop HVAC curbs", "MEDIUM", "2026-03-31", "OPEN"),
        Recommendation("R-098", "L1", "2024-03-15", "Housekeeping", "Remove combustible pallet storage from within 10 ft of building", "LOW", "2024-09-30", "VERIFIED_CLOSED", completion_evidence="Photo evidence + site revisit 2024-10-22"),
    ]
    quotes = [
        QuoteTruth(1, "2025-10-02", 432_000, Terms(**{**tq.dict(), "named_storm_ded_pct": 0.03}), "SUPERSEDED"),
        QuoteTruth(2, "2025-10-14", 418_000, Terms(**{**tq.dict(), "named_storm_ded_pct": 0.025}), "SUPERSEDED"),
        QuoteTruth(3, "2025-10-21", 410_000, tq, "ACCEPTED", approved_by="u_daniel", approval_date="2025-10-20", approval_terms_version=3),
    ]
    email = Email("2026-08-18", "Jordan Pierce <jpierce@harlanpierce.example>", ["Maya Chen <mchen@northgate.example>"],
                  "ABC Manufacturing — 11/1/2026 property renewal submission",
                  "Hi Maya,\n\nAttached is the renewal SOV for ABC Manufacturing (policy NSP-CP-2025-20417, expiring 11/1/2026).\n\n"
                  "Headline changes this year:\n"
                  " - New location: Tampa Expansion (Bldg 2) at 1960 Harbor Point Dr, operational since March.\n"
                  " - Values updated at Tampa and Dayton following the internal appraisal refresh.\n"
                  " - Reno is unchanged.\n\n"
                  "The client's budget for the renewal is a target premium of $450,000 with expiring terms (2% named storm).\n"
                  "Updated roof-replacement schedule to follow.\n\nThanks,\nJordan\nHarlan & Pierce Risk Partners",
                  attachments=["sov_2026"], kind="renewal_submission")
    return _acct(account_id="acc_s2", name="ABC Manufacturing", scenario="S2", scenario_title="Full renewal: exposure, RARC, terms, accumulation, contract",
                 segment="Middle market", occ_family="manufacturing", hq_state="OH", broker="Harlan & Pierce Risk Partners",
                 broker_contact="Jordan Pierce", underwriter_id="u_maya", tenure_years=4, admitted=True, fein="31-1170442",
                 policy_no="NSP-CP-2025-20417", term_end="2026-11-01", locations=locs, terms_quoted=tq, terms_binder=tq,
                 terms_issued=issued, quotes=quotes, premium_expiring=410_000, claims=claims, recs=recs, emails=[email],
                 renewal_sov_date="2026-08-18", renewal_target_premium=450_000, engineering_survey_dates=["2024-03-15"],
                 sim={"tp_e0t0_target": 395_000}, uw_reported_rarc=0.062, loss_ratio_hist=0.44, brokerage_prior=0.15, brokerage_proposed=0.15,
                 expected=["PRICE.RARC_AUTHORITY", "PRICE.ADEQUACY", "CAT.WIND.DED_FLOOR", "CAT.NS_MIN_FLOOR", "EXP.NEW_LOCATION_UNMODELLED", "ACC.ZONE_UTIL",
                           "CONTRACT.BINDER_POLICY", "OCC.DRIFT", "ROOF.YEAR_CONFLICT", "WATER.REPEAT", "ENG.OVERDUE_REC", "ENG.CLAIM_LINKED",
                           "VAL.RC_RATIO", "VAL.FLAT_VALUES", "CAT.INPUT_MISMATCH"])


# ---------------------------------------------------------------------- S3
def s3(rng: random.Random) -> Account:
    cities = ["Miami", "Fort Lauderdale", "Tampa", "Atlanta", "Dallas", "Houston", "Austin", "Nashville", "Charlotte",
              "Irvine", "Los Angeles", "Phoenix", "Chicago", "Newark"]
    locs = []
    hi_crime = {1, 5, 6, 11, 14}
    unmonitored = {5, 11, 14}
    for i, c in enumerate(cities, 1):
        stock = rng.uniform(1.8e6, 4.2e6)
        b = rng.uniform(0.9e6, 2.2e6)
        v = Values(round(b, -3), round(b * 0.35, -3), round(stock, -3), round(stock * 0.08, -3))
        l = loc(rng, f"L{i}", f"Lumen {c}", c, "jewelry", "Jewelry store", 2, "Joisted masonry", rng.randint(1985, 2012), 1,
                rng.randint(2400, 5200), rng.randint(2012, 2021), v, grow(v, 1.05), ppc=3, sprinkler_pct=0.0,
                loc_no_prior=str(i), loc_no_current=str(i), stock_value_peak=round(stock * 1.35, -3),
                burglary_score=rng.randint(92, 98) if i in hi_crime else rng.randint(35, 70),
                burglar_monitored=(i not in unmonitored))
        locs.append(l)
    t = Terms(limit=sum(l.values_current.tiv for l in locs), aop_deductible=10_000, named_storm_ded_pct=0.03, named_storm_ded_min=250_000,
              forms=STD_FORMS + ["CP 04 11", "NS-CP 03 40"], safeguards=[{"code": "P-4", "location_key": l.key} for l in locs])
    claims = [Claim("CLM-26-003301", "L6", "2026-02-08", "theft", 212_000, 0, "CLOSED", "Smash-and-grab burglary after hours; display cases emptied", report_date="2026-02-08"),
              Claim("CLM-25-009977", "L1", "2025-11-22", "theft", 96_000, 0, "CLOSED", "Burglary via rear service door", report_date="2025-11-23")]
    email = Email("2026-07-15", "Luis Ortega <lortega@brightwater.example>", ["Tom Becker <tbecker@northgate.example>"],
                  "Lumen Jewelers — renewal SOV + alarm certificates",
                  "Tom,\n\nPlease find the renewal SOV for Lumen Jewelers (14 stores). All stores have burglar alarms. "
                  "Alarm certificates attached for the stores we have them for.\n\nCash on premises runs up to $40,000 per store on weekends; "
                  "the client asked whether that is covered.\n\nRegards,\nLuis",
                  attachments=["sov_2026", "alarm_certs"], kind="renewal_submission")
    return _acct(account_id="acc_s3", name="Lumen Jewelers", scenario="S3", scenario_title="Theft & security: unmonitored alarms, safeguard, crime gap",
                 segment="Middle market", occ_family="jewelry", hq_state="FL", broker="Brightwater Risk Advisors", broker_contact="Luis Ortega",
                 underwriter_id="u_tom", tenure_years=3, admitted=True, fein="59-3380126", policy_no="NSP-CP-2025-20988",
                 term_end="2026-10-01", locations=locs, terms_quoted=t, terms_binder=t, terms_issued=t, claims=claims, emails=[email],
                 renewal_sov_date="2026-07-15", sim={"adequacy": 0.99}, uw_reported_rarc=0.05, loss_ratio_hist=0.61,
                 expected=["SEC.HIGH_VALUE_UNMONITORED", "SAFEGUARD.BREACH", "COV.CRIME_GAP"])


# ---------------------------------------------------------------------- S4
def s4(rng: random.Random) -> Account:
    L1 = loc(rng, "L1", "Dallas DC", "Dallas", "li_storage", "Warehouse", 4, "Tilt-up concrete", 2015, 1, 410_000, 2015,
             Values(38_000_000, 4_000_000, 22_000_000, 3_000_000), Values(39_000_000, 4_100_000, 31_000_000, 3_200_000),
             ppc=2, sprinkler_pct=1.0, loc_no_prior="1", loc_no_current="1", occupancy_prior="warehouse",
             storage_height_ft=28, sprinkler_design_ft=20, commodity="E-bike lithium-ion battery packs (rack storage)",
             engineering_date="2024-06-18", imagery=[{"date": "2024-05-20", "style": "yard_empty"}, {"date": "2026-06-02", "style": "yard_racks"}])
    L1.buildings = [Building("B-1", "Dallas DC", 180, 212, 1, story_h_m=12.2, kind="warehouse", racks=22, rack_height_ft=28,
                             sprinkler_design_ft=20, extras={"flag": "storage_over_design"})]
    L2 = loc(rng, "L2", "Phoenix DC", "Phoenix", "warehouse", "Warehouse", 4, "Tilt-up concrete", 2010, 1, 260_000, 2016,
             Values(22_000_000, 2_500_000, 12_000_000, 1_800_000), Values(22_400_000, 2_500_000, 12_600_000, 1_800_000),
             ppc=3, sprinkler_pct=1.0, loc_no_prior="2", loc_no_current="2", storage_height_ft=20, sprinkler_design_ft=25,
             commodity="General merchandise (Class III)", engineering_date="2024-06-20")
    L3 = loc(rng, "L3", "Atlanta DC", "Atlanta", "warehouse", "Warehouse", 3, "Metal building", 2004, 1, 190_000, 2012,
             Values(14_000_000, 1_500_000, 9_000_000, 1_000_000), Values(14_200_000, 1_500_000, 9_300_000, 1_000_000),
             ppc=3, sprinkler_pct=1.0, loc_no_prior="3", loc_no_current="3", storage_height_ft=18, sprinkler_design_ft=20,
             commodity="General merchandise (Class II)", engineering_date="2024-07-01")
    locs = [L1, L2, L3]
    t = Terms(limit=110_000_000, aop_deductible=50_000, forms=STD_FORMS + ["CP 04 11"],
              safeguards=[{"code": "P-1", "location_key": k} for k in ("L1", "L2", "L3")])
    email = Email("2026-07-20", "Grace Oduya <goduya@tidewater.example>", ["Sofia Alvarez <salvarez@northgate.example>"],
                  "Redline Logistics — new contract at Dallas",
                  "Hi Sofia,\n\nQuick heads-up ahead of the October renewal: Redline signed a distribution contract with an e-bike brand in May "
                  "and is now storing e-bike batteries at the Dallas facility, in new high-bay racking installed in June.\n\n"
                  "Renewal SOV to follow; values at Dallas will go up with the new stock.\n\nGrace",
                  attachments=[], kind="broker_update")
    email2 = Email("2026-07-29", "Grace Oduya <goduya@tidewater.example>", ["Sofia Alvarez <salvarez@northgate.example>"],
                   "Redline Logistics — 10/15/2026 renewal SOV", "Sofia,\n\nRenewal SOV attached. No other changes.\n\nGrace",
                   attachments=["sov_2026"], kind="renewal_submission")
    return _acct(account_id="acc_s4", name="Redline Logistics", scenario="S4", scenario_title="Occupancy drift + sprinkler adequacy",
                 segment="Middle market", occ_family="warehouse", hq_state="TX", broker="Tidewater Commercial Insurance", broker_contact="Grace Oduya",
                 underwriter_id="u_sofia", tenure_years=5, admitted=True, fein="75-2291845", policy_no="NSP-CP-2025-21104",
                 term_end="2026-10-15", locations=locs, terms_quoted=t, terms_binder=t, terms_issued=t, emails=[email, email2],
                 renewal_sov_date="2026-07-29", sim={"adequacy": 1.0}, uw_reported_rarc=0.04, loss_ratio_hist=0.22,
                 engineering_survey_dates=["2024-06-18"],
                 expected=["OCC.DRIFT", "FIRE.SPRINKLER_ADEQUACY"])


# ---------------------------------------------------------------------- S5
def s5(rng: random.Random) -> Account:
    spec = [("Miami", 210), ("Fort Lauderdale", 180), ("Charleston", 150), ("New Orleans", 240), ("Nashville", 200), ("Atlanta", 260)]
    locs = []
    for i, (c, rooms) in enumerate(spec, 1):
        sqft = rooms * 620
        b = sqft * 142
        v = Values(round(b, -3), round(b * 0.11, -3), round(b * 0.01, -3), round(b * 0.16, -3))
        locs.append(loc(rng, f"L{i}", f"Harborview {c}", c, "hotel", "Hotel", 6, "Reinforced concrete", rng.randint(1988, 2004),
                        rng.randint(6, 14), sqft, rng.randint(2010, 2018), v, v, ppc=2, sprinkler_pct=1.0,
                        loc_no_prior=str(i), loc_no_current=str(i), model_rc_per_sqft=209, last_appraisal="2021-03-10"))
    t = Terms(limit=sum(l.values_current.tiv for l in locs), aop_deductible=50_000, named_storm_ded_pct=0.05, named_storm_ded_min=250_000,
              forms=STD_FORMS + ["NS-CP 03 40", "NS-CP 12 10"], flood_sublimit=10_000_000)
    email = Email("2026-07-10", "Amelia Crane <acrane@keelcrane.example>", ["Daniel Okafor <dokafor@northgate.example>"],
                  "Harborview Hotels — renewal", "Daniel,\n\nRenewal SOV attached for Harborview. Values are unchanged from last year per the client.\n\nAmelia",
                  attachments=["sov_2026"], kind="renewal_submission")
    return _acct(account_id="acc_s5", name="Harborview Hotels", scenario="S5", scenario_title="Under-valuation: 68% of modelled replacement cost",
                 segment="Middle market", occ_family="hotel", hq_state="FL", broker="Keel & Crane Insurance Services", broker_contact="Amelia Crane",
                 underwriter_id="u_daniel", tenure_years=7, admitted=True, fein="65-0913377", policy_no="NSP-CP-2025-19750",
                 term_end="2026-09-30", locations=locs, terms_quoted=t, terms_binder=t, terms_issued=t, emails=[email],
                 renewal_sov_date="2026-07-10", sim={"adequacy": 1.01, "flat_years": 3}, uw_reported_rarc=0.03, loss_ratio_hist=0.35,
                 expected=["VAL.RC_RATIO", "VAL.FLAT_VALUES", "VAL.STALE_APPRAISAL"])


# ---------------------------------------------------------------------- S6
def s6(rng: random.Random) -> Account:
    cities = ["Austin", "Dallas", "Houston", "Atlanta", "Nashville", "Charlotte", "Tampa", "Fort Worth", "Denver", "Phoenix", "Columbus"]
    locs = []
    fire_sites = {3: 2, 8: 1, 15: 1}
    missing_hood = {2, 5, 9, 12, 15, 18, 21}
    for i in range(1, 23):
        c = cities[(i - 1) % len(cities)]
        tiv = rng.uniform(1.6e6, 3.4e6)
        v = split_values(tiv, "restaurant", rng)
        locs.append(loc(rng, f"L{i}", f"Ember & Oak #{i:02d} {c}", c, "restaurant", "Full service restaurant", rng.choice([2, 3]),
                        "Joisted masonry", rng.randint(1990, 2016), 1, rng.randint(4200, 7800), rng.randint(2008, 2020), v, grow(v, 1.04),
                        ppc=3, sprinkler_pct=rng.choice([0.0, 1.0]), loc_no_prior=str(i), loc_no_current=str(i), cooking=True,
                        cooking_suppression_verified=(i not in missing_hood), hood_cleaning_ok=(i not in missing_hood)))
    t = Terms(limit=sum(l.values_current.tiv for l in locs), aop_deductible=10_000, named_storm_ded_pct=0.03, named_storm_ded_min=250_000,
              forms=STD_FORMS + ["CP 04 11", "NS-CP 03 40"], safeguards=[{"code": "P-5", "location_key": l.key} for l in locs])
    claims = []
    n = 0
    for site, k in fire_sites.items():
        for j in range(k):
            n += 1
            dol = ["2023-11-04", "2025-02-17", "2025-09-08", "2026-01-30"][n - 1]
            claims.append(Claim(f"CLM-{dol[2:4]}-00{n}712", f"L{site}", dol, "fire", rng.choice([46_000, 88_000, 132_000, 64_000]), 0,
                                "CLOSED", "Grease fire in cooking line; hood and duct damage, smoke damage to dining room", report_date=dol))
    return _acct(account_id="acc_s6", name="Ember & Oak Restaurant Group", scenario="S6", scenario_title="Fire / cooking hazard",
                 segment="Middle market", occ_family="restaurant", hq_state="TX", broker="Ironbridge Specialty Brokers", broker_contact="Marcus Hale-Ng",
                 underwriter_id="u_tom", tenure_years=4, admitted=True, fein="74-3317760", policy_no="NSP-CP-2025-20512",
                 term_end="2026-10-10", locations=locs, terms_quoted=t, terms_binder=t, terms_issued=t, claims=claims,
                 renewal_sov_date="2026-07-24", sim={"adequacy": 0.97}, uw_reported_rarc=0.05, loss_ratio_hist=0.58,
                 emails=[Email("2026-07-24", "Marcus Hale-Ng <mhaleng@ironbridge.example>", ["Tom Becker <tbecker@northgate.example>"],
                               "Ember & Oak — renewal SOV and hood cleaning certificates",
                               "Tom,\n\nRenewal SOV attached. Hood cleaning certificates attached for the locations the client could find.\n\nMarcus",
                               attachments=["sov_2026", "hood_certs"], kind="renewal_submission")],
                 expected=["FIRE.COOKING_SUPPRESSION", "CLAIMS.REPEAT_CAUSE", "SAFEGUARD.BREACH"])


# ---------------------------------------------------------------------- S7
def s7(rng: random.Random) -> Account:
    v = Values(34_000_000, 1_200_000, 0, 5_800_000)
    L1 = loc(rng, "L1", "Pinecrest Plaza", "Charlotte", "shopping_ctr", "Strip center", 3, "Non-combustible", 1994, 1, 186_000, 2013,
             v, v, ppc=3, sprinkler_pct=1.0, loc_no_prior="1", loc_no_current="1",
             imagery=[{"date": "2025-06-14", "style": "lot_full"}, {"date": "2026-06-11", "style": "lot_empty"}])
    L1.buildings = [Building("B-1", "Anchor (vacant)", 95, 70, 1, story_h_m=7.5, kind="box", extras={"tenant": "Anchor — vacated 2026-03-31", "flag": "vacant"}),
                    Building("B-2", "Inline shops", 150, 32, 1, story_h_m=5.5, x_m=110, kind="box", extras={"tenant": "14 inline tenants"}),
                    Building("B-3", "Outparcel", 30, 25, 1, story_h_m=5.0, x_m=40, y_m=-90, kind="box", extras={"tenant": "Bank branch"})]
    t = Terms(limit=41_000_000, aop_deductible=25_000, forms=STD_FORMS + ["CP 04 11"], safeguards=[{"code": "P-1", "location_key": "L1"}])
    endt = [Endorsement("END-2026-0133", "2026-04-01", "Occupancy change", "Anchor tenant (62% of GLA) vacated 31 Mar 2026; building remains owned by insured", 0,
                        {"vacancy_pct": 0.62})]
    return _acct(account_id="acc_s7", name="Pinecrest Plaza", scenario="S7", scenario_title="Mid-term vacancy + sprinkler impairment (event-driven)",
                 segment="Middle market", occ_family="shopping_ctr", hq_state="NC", broker="Calder Street Brokerage", broker_contact="Hannah Weiss",
                 underwriter_id="u_daniel", tenure_years=2, admitted=True, fein="56-2204981", policy_no="NSP-CP-2026-00311",
                 term_end="2027-01-15", locations=[L1], terms_quoted=t, terms_binder=t, terms_issued=t, endorsements=endt,
                 renewal_sov_date=None, sim={"adequacy": 1.07}, loss_ratio_hist=0.12,
                 expected=["VAC.THRESHOLD", "VAC.FIRE_SPRINKLER_OFF", "SAFEGUARD.BREACH"])


# ---------------------------------------------------------------------- S8
def s8(rng: random.Random) -> Account:
    names = ["Main Hospital Tower", "Surgical Pavilion", "Emergency & Trauma", "Women's & Children's", "Medical Office Bldg A",
             "Medical Office Bldg B", "Central Utility Plant", "Imaging Center", "Research & Labs", "Parking & Admin",
             "Rehabilitation Center", "Education Center"]
    buildings = []
    x = 0
    for i, n in enumerate(names, 1):
        st = [9, 5, 3, 6, 4, 4, 2, 2, 4, 5, 3, 3][i - 1]
        w, dp = [(70, 45), (60, 40), (55, 40), (50, 40), (40, 30), (40, 30), (45, 35), (35, 30), (45, 30), (60, 35), (40, 30), (35, 28)][i - 1]
        buildings.append(Building(f"B-{i}", n, w, dp, st, x_m=(i - 1) % 4 * 85, y_m=(i - 1) // 4 * 70, kind="tower" if st >= 6 else "box",
                                  extras={"label": n, "stories": st, "flag": "generator" if n == "Central Utility Plant" else None}))
    v = Values(410_000_000, 120_000_000, 6_000_000, 64_000_000)
    L1 = loc(rng, "L1", "St. Aurelia Medical Center", "Charleston", "hospital", "Acute care hospital", 6, "Fire resistive", 1987, 9, 1_150_000, 2015,
             v, grow(v, 1.045), ppc=1, sprinkler_pct=1.0, loc_no_prior="1", loc_no_current="1", buildings=buildings, engineering_date="2025-09-22")
    t2 = Terms(limit=250_000_000, limit_basis="loss_limit", aop_deductible=250_000, named_storm_ded_pct=0.05, named_storm_ded_min=250_000,
               flood_sublimit=25_000_000, bi_sublimit=None, forms=STD_FORMS + ["NS-CP 03 40", "NS-CP 12 10"])
    t3 = Terms(**{**t2.dict(), "named_storm_ded_min": 100_000})
    issued = Terms(**{**t3.dict(), "named_storm_ded_min": None})
    quotes = [QuoteTruth(1, "2025-11-20", 1_940_000, Terms(**{**t2.dict(), "named_storm_ded_pct": 0.05}), "SUPERSEDED"),
              QuoteTruth(2, "2025-12-10", 1_880_000, t2, "SUPERSEDED", approved_by="u_priya", approval_date="2025-12-11", approval_terms_version=2),
              QuoteTruth(3, "2025-12-18", 1_880_000, t3, "ACCEPTED", approved_by=None)]
    return _acct(account_id="acc_s8", name="St. Aurelia Medical Center", scenario="S8", scenario_title="Contract integrity + authority",
                 segment="Large", occ_family="hospital", hq_state="SC", broker="Keel & Crane Insurance Services", broker_contact="Amelia Crane",
                 underwriter_id="u_daniel", tenure_years=3, admitted=False, fein="57-0348826", policy_no="NSP-CP-2025-23390",
                 term_end="2026-12-28", locations=[L1], terms_quoted=t3, terms_binder=t3, terms_issued=issued, quotes=quotes,
                 premium_expiring=1_880_000, subjectivities=[{"text": "Emergency generator full-load test report (Central Utility Plant)", "due": "2025-12-28", "status": "OPEN"}],
                 sim={"adequacy": 1.02}, loss_ratio_hist=0.29, site_layout="campus", engineering_survey_dates=["2025-09-22"],
                 emails=[Email("2026-10-14", "Amelia Crane <acrane@keelcrane.example>", ["Daniel Okafor <dokafor@northgate.example>"],
                               "St. Aurelia Medical Center — 12/28 renewal", "Daniel,\n\nRenewal SOV attached. The generator load test report is still being finalised by the facilities team.\n\nAmelia",
                               attachments=["sov_2026"], kind="renewal_submission")],
                 expected=["AUTH.APPROVAL_INVALID", "CONTRACT.BINDER_POLICY", "CONTRACT.SUBJECTIVITY_OPEN", "CAT.NS_MIN_FLOOR"])


# ---------------------------------------------------------------------- S9
def s9(rng: random.Random) -> Account:
    L1 = loc(rng, "L1", "Pittsburgh Molding Plant", "Pittsburgh", "plastics", "Plastic injection molding", 3, "Non-combustible", 1979, 1, 210_000, 2009,
             Values(24_000_000, 14_000_000, 5_000_000, 6_000_000), Values(24_500_000, 14_300_000, 5_200_000, 6_000_000),
             ppc=3, sprinkler_pct=0.85, loc_no_prior="1", loc_no_current="1", engineering_date="2025-08-14")
    L2 = loc(rng, "L2", "Columbus Finishing", "Columbus", "plastics", "Finishing & packaging", 4, "Masonry non-combustible", 1996, 1, 96_000, 2015,
             Values(9_000_000, 4_500_000, 2_000_000, 2_500_000), Values(9_100_000, 4_600_000, 2_000_000, 2_500_000),
             ppc=3, sprinkler_pct=1.0, loc_no_prior="2", loc_no_current="2", engineering_date="2025-08-15")
    recs = [Recommendation("R-0412", "L1", "2025-08-14", "Combustible dust / explosion", "Install spark detection & extinguishing on Line 3 dust collector ductwork; add explosion venting per NFPA 652/68", "CRITICAL",
                           "2025-12-31", "CLOSED", bind_condition=True, completion_evidence=None, closed_on="2026-01-20"),
            Recommendation("R-0415", "L1", "2025-08-14", "Housekeeping", "Implement documented dust housekeeping program (weekly high-level cleaning)", "HIGH", "2025-11-30", "IN_PROGRESS"),
            Recommendation("R-0420", "L2", "2025-08-15", "Electrical", "Infrared thermography of main switchgear annually", "MEDIUM", "2026-06-30", "VERIFIED_CLOSED", completion_evidence="IR report 2026-05-02")]
    claims = [Claim("CLM-26-002278", "L1", "2026-03-14", "fire", 1_120_000, 280_000, "OPEN", "Fire originating in Line 3 dust collector, spread via ductwork to molding hall; 9 days downtime", report_date="2026-03-14", linked_rec="R-0412")]
    t = Terms(limit=70_000_000, aop_deductible=50_000, forms=STD_FORMS + ["CP 04 11"], safeguards=[{"code": "P-1", "location_key": "L1"}, {"code": "P-1", "location_key": "L2"}])
    return _acct(account_id="acc_s9", name="Keystone Plastics", scenario="S9", scenario_title="Engineering commitment broken + linked loss",
                 segment="Middle market", occ_family="plastics", hq_state="PA", broker="Harlan & Pierce Risk Partners", broker_contact="Jordan Pierce",
                 underwriter_id="u_maya", tenure_years=2, admitted=True, fein="25-1874456", policy_no="NSP-CP-2025-21740",
                 term_end="2026-10-20", locations=[L1, L2], terms_quoted=t, terms_binder=t, terms_issued=t, recs=recs, claims=claims,
                 subjectivities=[{"text": "Completion of R-0412 (dust collector spark detection) within 120 days of bind", "due": "2025-12-31", "status": "CLEARED"}],
                 renewal_sov_date="2026-07-30", sim={"adequacy": 0.98}, uw_reported_rarc=0.07, loss_ratio_hist=1.85, engineering_survey_dates=["2025-08-14"],
                 emails=[Email("2026-07-30", "Jordan Pierce <jpierce@harlanpierce.example>", ["Maya Chen <mchen@northgate.example>"],
                               "Keystone Plastics — renewal", "Maya,\n\nRenewal SOV attached for Keystone. The March loss has been repaired and Line 3 is back in production.\n\nJordan",
                               attachments=["sov_2026"], kind="renewal_submission")],
                 expected=["ENG.UNVERIFIED_CLOSURE", "ENG.BROKEN_COMMITMENT", "ENG.CLAIM_LINKED", "CLAIMS.LARGE_LOSS", "ENG.OVERDUE_REC", "SAFEGUARD.BREACH"])


# ---------------------------------------------------------------------- S10
def s10(rng: random.Random) -> Account:
    v = Values(6_500_000, 3_000_000, 4_500_000, 1_200_000)
    L1 = loc(rng, "L1", "Delta Scrap — Baton Rouge Yard", "Baton Rouge", "scrap", "Scrap metal yard & shredder", 3, "Metal building", 1991, 1, 58_000, 2010,
             v, grow(v, 1.02), ppc=4, sprinkler_pct=0.0, loc_no_prior="1", loc_no_current="1")
    t = Terms(limit=15_200_000, aop_deductible=25_000, named_storm_ded_pct=0.05, named_storm_ded_min=100_000, forms=STD_FORMS + ["NS-CP 03 40"])
    return _acct(account_id="acc_s10", name="Delta Scrap Metals", scenario="S10", scenario_title="Appetite change + non-renewal notice deadline",
                 segment="Middle market", occ_family="scrap", hq_state="LA", broker="Tidewater Commercial Insurance", broker_contact="Grace Oduya",
                 underwriter_id="u_sofia", tenure_years=5, admitted=True, fein="72-1459903", policy_no="NSP-CP-2025-22415",
                 term_end="2026-11-15", locations=[L1], terms_quoted=t, terms_binder=t, terms_issued=t,
                 sim={"adequacy": 0.93}, loss_ratio_hist=0.71, expected=["APPETITE.DECLINED_CLASS"])


# ---------------------------------------------------------------------- S11
def s11(rng: random.Random) -> Account:
    kinds = ["Hall", "Library", "Laboratory", "Residence Hall", "Athletics", "Student Center", "Engineering", "Arts"]
    locs = []
    buildings_prior = []
    for i in range(1, 42):
        k = kinds[i % len(kinds)]
        nm = f"{['Aldridge', 'Birch', 'Carver', 'Dunmore', 'Ellison', 'Fairway', 'Garrow', 'Hollis', 'Ingram', 'Juniper', 'Kessler', 'Lowell', 'Marston', 'Norwood'][i % 14]} {k} {i}"
        buildings_prior.append((i, nm, k))
    # prior 41 buildings; current: 36 exact, 3 address variants (ambiguous), buildings 20+21 merged, 1 new (Innovation Center)
    x = 0
    for i, nm, k in buildings_prior:
        st = rng.randint(2, 7)
        sqft = rng.randint(22_000, 140_000)
        tiv = sqft * rng.uniform(260, 420)
        v = split_values(tiv, "university", rng)
        occ_raw = {"Residence Hall": "Dormitory", "Laboratory": "Laboratory", "Library": "Library"}.get(k, "Classroom")
        l = loc(rng, f"L{i}", nm, "State College", "university", occ_raw, rng.choice([4, 5, 6]), rng.choice(["Masonry", "Reinforced concrete", "Brick"]),
                rng.randint(1925, 2016), st, sqft, rng.randint(2004, 2021), v, grow(v, 1.035), ppc=2, sprinkler_pct=rng.choice([1.0, 1.0, 0.6]),
                street_no=100 + i * 10, street="College Ave", dx_km=((i - 1) % 7) * 0.18 - 0.5, dy_km=((i - 1) // 7) * 0.16 - 0.5,
                loc_no_prior=str(i), loc_no_current=None)
        l.buildings = [Building("B-1", nm, round((sqft * 0.0929 / st) ** 0.5 * 1.3, 1), round((sqft * 0.0929 / st) ** 0.5 / 1.3, 1), st,
                                x_m=((i - 1) % 7) * 95, y_m=((i - 1) // 7) * 80, kind="box", extras={"label": nm, "stories": st})]
        locs.append(l)
    # renumbering: current numbers shuffled
    order = list(range(len(locs)))
    rng.shuffle(order)
    for n, idx in enumerate(order, 1):
        locs[idx].loc_no_current = f"{n:03d}"
    for idx in (5, 17, 29):  # address variants -> ambiguous
        l = locs[idx]
        l.sov_address_variant = f"{l.street_no + 2} College Avenue, Bldg {idx + 1}"
    # merge L20 + L21 into L20 (renovation joined them)
    a, b = locs[19], locs[20]
    a.merged_from = [a.key, b.key]
    a.name = f"{a.name.split(' ')[0]} Commons (joined)"
    a.values_current = Values(a.values_current.building + b.values_current.building, a.values_current.contents + b.values_current.contents, 0,
                              a.values_current.bi + b.values_current.bi)
    a.sqft_prior = a.sqft
    a.sqft = a.sqft + b.sqft
    b.status = "deleted"
    b.values_current = None
    new = loc(rng, "L42", "Innovation Center", "State College", "university", "Laboratory", 6, "Reinforced concrete", 2025, 5, 118_000, 2025,
              None, split_values(118_000 * 480, "university", rng), ppc=2, sprinkler_pct=1.0, street_no=900, street="Research Dr",
              dx_km=0.9, dy_km=0.6, status="new", loc_no_prior=None, loc_no_current="041")
    new.values_prior = None
    new.buildings[0].x_m, new.buildings[0].y_m = 7 * 95, 2 * 80
    new.buildings[0].extras = {"label": "Innovation Center", "stories": 5, "flag": "new"}
    locs.append(new)
    t = Terms(limit=900_000_000, limit_basis="blanket", aop_deductible=100_000, forms=STD_FORMS)
    return _acct(account_id="acc_s11", name="Summit University", scenario="S11", scenario_title="Location matching & data quality",
                 segment="Large", occ_family="university", hq_state="PA", broker="Brightwater Risk Advisors", broker_contact="Luis Ortega",
                 underwriter_id="u_daniel", tenure_years=8, admitted=True, fein="24-6011872", policy_no="NSP-CP-2025-18802",
                 term_end="2026-09-01", locations=locs, terms_quoted=t, terms_binder=t, terms_issued=t, renewal_sov_date="2026-06-20",
                 sov_quirks={"scale_000s": True, "totals_row": True, "header_row": 5, "hidden_rows": [], "renumbered": True},
                 sim={"adequacy": 1.03}, uw_reported_rarc=0.035, loss_ratio_hist=0.24, site_layout="campus",
                 emails=[Email("2026-06-20", "Luis Ortega <lortega@brightwater.example>", ["Daniel Okafor <dokafor@northgate.example>"],
                               "Summit University — 9/1 renewal SOV", "Daniel,\n\nAttached is the Summit renewal SOV (values in $000s). The facilities team renumbered the "
                               "building inventory this year; Aldridge/Birch were joined in the renovation. The new Innovation Center opened in January.\n\nLuis",
                               attachments=["sov_2026"], kind="renewal_submission")],
                 expected=["DQ.MATCH_AMBIGUOUS", "EXP.NEW_LOCATION_UNMODELLED"])


# ---------------------------------------------------------------------- S12
def s12(rng: random.Random) -> Account:
    halls = []
    for i in range(1, 7):
        halls.append(Building(f"B-{i}", f"Data Hall {chr(64 + i)}", 110, 62, 2, story_h_m=7.0, x_m=((i - 1) % 3) * 125, y_m=((i - 1) // 3) * 80,
                              kind="datahall", extras={"label": f"Data Hall {chr(64 + i)}", "it_load_mw": 36, "stories": 2}))
    halls.append(Building("B-7", "Substation & generators", 60, 40, 1, story_h_m=6.0, x_m=380, y_m=40, kind="box", extras={"label": "Substation & generators", "generators": 48}))
    v = Values(385_000_000, 605_000_000, 0, 110_000_000)
    L1 = loc(rng, "L1", "Meridian Ashburn Campus", "Ashburn", "data_center", "Colocation data center", 6, "Reinforced concrete", 2019, 2, 1_450_000, 2019,
             grow(v, 0.94), v, ppc=1, sprinkler_pct=1.0, loc_no_prior="1", loc_no_current="1", buildings=halls, engineering_date="2025-10-02")
    t = Terms(limit=250_000_000, limit_basis="loss_limit", aop_deductible=1_000_000, forms=STD_FORMS + ["CP 04 11"],
              safeguards=[{"code": "P-1", "location_key": "L1"}])
    return _acct(account_id="acc_s12", name="Meridian Data Centers", scenario="S12", scenario_title="Shared layer: exposure on carrier share",
                 segment="Large", occ_family="data_center", hq_state="VA", broker="Ironbridge Specialty Brokers", broker_contact="Marcus Hale-Ng",
                 underwriter_id="u_daniel", tenure_years=3, admitted=False, fein="54-2230017", policy_no="NSP-XS-2025-00918",
                 term_end="2026-12-01", carrier_share=0.25, layer_attach=50_000_000, layer_limit=100_000_000, locations=[L1],
                 terms_quoted=t, terms_binder=t, terms_issued=t, renewal_sov_date="2026-07-28", sim={"adequacy": 1.06},
                 uw_reported_rarc=0.0, loss_ratio_hist=0.05, site_layout="campus", brokerage_prior=0.10, brokerage_proposed=0.10,
                 emails=[Email("2026-07-28", "Marcus Hale-Ng <mhaleng@ironbridge.example>", ["Daniel Okafor <dokafor@northgate.example>"],
                               "Meridian — excess renewal", "Daniel,\n\nRenewal SOV for Meridian Ashburn attached; 25% of $100M xs $50M as expiring.\n\nMarcus",
                               attachments=["sov_2026"], kind="renewal_submission")],
                 expected=[])


HEROES = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12]

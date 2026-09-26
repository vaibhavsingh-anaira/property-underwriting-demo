"""Product 02 — Decision Assurance: reference model (new-business standards, authority matrix,
classification guide), pipeline definition and small helpers shared by the other modules."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

ID = "decision"
META = {"id": ID, "name": "Decision Assurance", "short": "Decisions", "number": "02",
        "tagline": "Prepare the decision, then check the commitment",
        "description": "Before human review, a draft decision pack for every new-business submission; after the underwriter's judgement, "
                       "the intended action is checked independently against evidence, pricing, guidelines, appetite and authority. "
                       "The human underwriter remains the final decision owner.",
        "subject_label": "Case"}

GROUPS = ["Prepare the decision", "Support the judgement", "Control the commitment", "Learn"]
PIPE = [
    ("01", "Submission / risk", "Prepare the decision", "Submission intake (mailbox)", "MOCK",
     "Broker emails with ACORD application, SOV, loss runs and inspection attached; scripted arrivals, parsed like any other file", "MailboxPort"),
    ("02", "Risk & document intelligence", "Prepare the decision", "Extraction + evidence ledger", "REAL",
     "Every value extracted with its cell / page / email anchor, normalised to carrier classes; contradictions between sources and missing information detected", None),
    ("03", "Carrier context", "Prepare the decision", "Guidelines · authority · rater & CAT stubs", "REAL",
     "Appetite, guidelines and authority matrix applied (real); technical price from the mock rater and MockCat; hazard, property and company data from vendor stubs", "RaterPort · CatModelPort · VendorPort"),
    ("04", "Draft recommendation", "Prepare the decision", "Decision pack", "REAL",
     "Material risk factors, pricing context, referral requirements, suggested terms and a draft action — source-linked, before a human opens the file", None),
    ("05", "Underwriter judgement", "Support the judgement", "Underwriter workbench", "REAL",
     "The underwriter resolves contradictions, requests information (broker stub replies with documents), overrides flags with a reason, pre-refers", "BrokerPort · InspectionPort"),
    ("06", "Intended action", "Support the judgement", "Intended action", "REAL",
     "Quote, bind, refer, decline or override — with premium, deductible, limit, line and terms, and the underwriter's rationale", None),
    ("07", "Independent assurance", "Control the commitment", "Assurance engine (tier 1 + tier 2)", "REAL",
     "Tier 1 deterministic rules and a transparent tier-2 critique (stand-in for the production assurance model) check the action against evidence, pricing, guidelines, appetite and authority", None),
    ("08", "Pass / flag / refer", "Control the commitment", "Verdict & routing", "REAL",
     "Pass, pass with flags, or refer / hold — with the reasons, remaining conditions and who must decide (tier 3)", None),
    ("09", "Human final decision", "Control the commitment", "Decision record + policy admin stub", "REAL",
     "The decision owner commits, declines or approves with conditions; quote and binder issued through the mock policy system and read back", "PolicyAdminPort"),
    ("10", "Outcome feedback", "Learn", "Outcome capture + claims stub", "REAL",
     "Losses or clean experience months later feed flag precision, override outcomes and tier-2 calibration", "ClaimsPort"),
]
STANDS_IN = {"01": "Broker email / portal intake", "02": "Anaira ingestion & evidence ledger", "03": "Carrier guidelines + authority · hx / carrier rater · Moody's RMS / Verisk · Precisely / HazardHub / D&B",
             "04": "Anaira decision pack", "05": "Underwriting workbench · broker · loss-control vendor", "06": "Underwriting workbench", "07": "Anaira assurance engine",
             "08": "Anaira assurance engine", "09": "Guidewire PolicyCenter / Duck Creek (issuance)", "10": "Guidewire ClaimCenter feed · Anaira calibration"}
STAGE_NAME = {c: n for c, n, *_ in PIPE}

REAL_CORE = ["Document extraction into the evidence ledger (ACORD application, SOV, loss runs, inspection, email, manuscript wording) with anchors",
             "Contradiction and missing-information detection across sources, each priced by re-rating",
             "Guidelines, appetite and authority as versioned, tested YAML rules (tier 1)",
             "Tier-2 critique of rationale, overrides, wording and unusual features (transparent stand-in for the production model)",
             "Verdict, conditions, decision owner and approval envelopes; bind blocked on open conditions",
             "Outcome feedback into flag precision and calibration"]
MOCK_CORE = ["Submission mailbox and broker (returns requested documents after 3 days, accepts quotes by rule)",
             "Rater and CAT model (deterministic stand-ins: NS-PROP-RATER v8.0 mock, MockCat 3.1)",
             "Hazard, property-intelligence and company-data vendors; loss-control inspection vendor (report 7 days after order)",
             "Policy admin (quote and binder documents) and claims feed (outcomes)"]

# --------------------------------------------------------------------------- new-business standards (Northgate, fictional)
NB_STANDARDS = {
    "version": "NB-2026.1", "effective_from": "2026-07-01",
    "loss_run_years_required": 5, "loss_run_max_age_days": 90,
    "inspection_tiv_threshold": 50_000_000,
    "aop_table": [(25_000_000, 25_000), (100_000_000, 50_000), (250_000_000, 100_000), (750_000_000, 250_000), (10e12, 500_000)],
    "hail_ded_pct_min": 0.01,
    "partial_sprinkler_refer_tiv": 10_000_000,
    "large_limit": 500_000_000,
    "materiality_floor": 5_000, "materiality_pct": 0.02,
    "suggested_band": 0.04,
    "rationale_required_dev": 0.025,
}
NB_SECTIONS = {  # section -> (title, page in the NB standards PDF, text)
    "NB§1.2": ("Required submission", "A complete new-business submission contains an ACORD 125/140 application signed by the insured, a statement of values, five full years of currently valued loss runs (valued within 90 days) and, for total insured value above $50M, a loss-control inspection not older than 24 months. Bind is not permitted while a required document is outstanding."),
    "NB§2.3": ("Classification", "Risks are classified on the operations described across the application, schedule, inspection and third-party company data, using the Northgate classification guide. The most hazardous class evidenced governs. Declined classes under Guidelines §2.1 cannot be written without a Level 4 exception."),
    "NB§3.2": ("New-business authority", "Pricing deviation from the technical premium: Level 1 ±5%, Level 2 ±10%, Level 3 ±15%, Level 4 ±30%. Account TIV, location TIV and premium limits per the new-business authority matrix. Approvals apply to the envelope approved (minimum premium, minimum deductible, maximum line, wording)."),
    "NB§4.1": ("Deductibles", "Minimum all-other-perils deductible by total insured value: under $25M $25,000; under $100M $50,000; under $250M $100,000; under $750M $250,000; above $500,000. Hail-exposed locations (North Texas, Front Range) carry a wind/hail deductible of at least 1% per building."),
    "NB§5.4": ("Protection", "A partially sprinklered location with more than $10M insured value requires Level 2 referral. Storage above the sprinkler design basis requires verified in-rack protection or a re-survey before bind; an underwriter override of this condition requires Level 3."),
    "NB§6.1": ("Wording", "Manuscript wording that deletes or broadens a standard exclusion of CP 10 30 requires Level 3 approval and legal review of the clause."),
    "NB§7.2": ("Rationale", "Every intended action more than 2.5% from technical carries a written rationale; overrides of engine flags carry a reason and, where the reason relies on evidence, that evidence must be on file."),
}
NB_SECTION_PAGE = {k: i + 2 for i, k in enumerate(NB_SECTIONS)}
NB_DOC = "d_nb_standards_2026"
AUTH_DOC = "d_nb_authority_2026"
GUIDE_DOC = "d_ref_guidelines_2026"

NB_AUTHORITY = {
    1: {"max_price_dev": 0.05, "max_account_tiv": 750_000_000, "max_loc_tiv": 250_000_000, "max_premium": 750_000, "label": "Property Underwriter"},
    2: {"max_price_dev": 0.10, "max_account_tiv": 1_500_000_000, "max_loc_tiv": 500_000_000, "max_premium": 2_000_000, "label": "Senior Property Underwriter"},
    3: {"max_price_dev": 0.15, "max_account_tiv": 5_000_000_000, "max_loc_tiv": 1_500_000_000, "max_premium": 7_500_000, "label": "Head of Property"},
    4: {"max_price_dev": 0.30, "max_account_tiv": 10_000_000_000, "max_loc_tiv": 2_000_000_000, "max_premium": 50_000_000, "label": "Chief Underwriting Officer"},
}

# Northgate classification guide: phrases in operations descriptions -> class (most hazardous wins)
CLASS_GUIDE = [
    ("shredding and baling", "scrap", 0.93), ("ferrous and non-ferrous", "scrap", 0.9), ("auto salvage", "scrap", 0.92), ("metals recovery", "scrap", 0.9),
    ("materials recovery", "scrap", 0.88), ("metal processing", "scrap", 0.84), ("scrap", "scrap", 0.97), ("recycling", "scrap", 0.9),
    ("powder coating", "manufacturing", 0.9), ("machining", "manufacturing", 0.93), ("metal fabrication", "manufacturing", 0.92),
    ("cold storage", "cold_storage", 0.95), ("refrigerated", "cold_storage", 0.93), ("ammonia refrigeration", "cold_storage", 0.95),
    ("hotel", "hotel", 0.95), ("resort", "hotel", 0.93), ("office", "office", 0.95), ("warehous", "warehouse", 0.88), ("distribution", "warehouse", 0.86),
    ("third-party logistics", "warehouse", 0.9), ("restaurant", "restaurant", 0.95), ("apartment", "multifamily", 0.95), ("retail", "retail", 0.9),
]
HAZARD_RANK = {"scrap": 9, "plastics": 8, "li_storage": 8, "restaurant": 7, "manufacturing": 6, "cold_storage": 6, "jewelry": 5, "warehouse": 4,
               "retail": 4, "shopping_ctr": 4, "hotel": 3, "multifamily": 3, "hospital": 3, "university": 2, "data_center": 3, "office": 1}
NAICS_CLASS = {"423930": "scrap", "332710": "manufacturing", "332812": "manufacturing", "493110": "warehouse", "493120": "cold_storage", "531120": "office",
               "721110": "hotel", "722511": "restaurant", "531110": "multifamily", "448310": "retail", "326199": "plastics", "484110": "warehouse"}
HAIL_ZONES = ("DFW", "DEN")
PML_FACTOR = {"Hurricane": 0.22, "Earthquake": 0.16, "Severe convective storm": 0.06, "Fire / BI concentration": 0.30}
RC_PER_SQFT = {"office": 245, "manufacturing": 125, "warehouse": 92, "cold_storage": 150, "hotel": 290, "restaurant": 285, "retail": 165,
               "multifamily": 195, "scrap": 82, "shopping_ctr": 160, "plastics": 130}
CONS_RC = {1: 0.95, 2: 0.97, 3: 0.97, 4: 1.0, 5: 1.03, 6: 1.05}

REQUIRED_LOC_FIELDS = [("construction_class", "Construction"), ("occupancy_class", "Occupancy"), ("year_built", "Year built"), ("sqft", "Floor area"),
                       ("roof_year", "Roof year"), ("sprinkler_pct", "Sprinkler protection"), ("building_value", "Building value")]
ADDON_FIELDS = {"warehouse": [("storage_height_ft", "Max storage height"), ("commodity", "Commodity class")],
                "cold_storage": [("storage_height_ft", "Max storage height"), ("commodity", "Commodity class")]}
CONTRA_FIELDS = {"sprinkler_pct": 0.1, "roof_year": 3, "year_built": 3, "sqft": 0.1, "stories": 0, "construction_class": 0, "occupancy_class": 0}

VERDICT_LABEL = {"PASS": "Pass", "PASS_WITH_FLAGS": "Pass with flags", "REFER_HOLD": "Refer / hold"}
DIMENSIONS = [("evidence", "Evidence"), ("pricing", "Pricing"), ("guidelines", "Guidelines"), ("appetite", "Appetite"), ("authority", "Authority")]
ACTION_LABEL = {"QUOTE": "Quote", "BIND": "Bind", "REFER": "Refer", "DECLINE": "Decline", "OVERRIDE": "Override"}


@dataclass
class DState:
    """Everything Decision Assurance keeps on the runtime (picklable)."""
    built: bool = False
    cases: dict = field(default_factory=dict)
    order: list = field(default_factory=list)
    referrals: dict = field(default_factory=dict)
    assurance_log: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)          # rule_id -> {fired, accepted, overridden, confirmed, not_confirmed}
    seq: int = 0
    counter: int = 0
    heroes: list = field(default_factory=list)


def st(rt) -> DState:
    s = getattr(rt, "decision", None)
    if s is None:
        rt.decision = s = DState()
    return s


def nid(rt, prefix: str) -> str:
    s = st(rt)
    s.counter += 1
    return f"{prefix}{s.counter:05d}"


def h8(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:8]


def money(v: float | None, full: bool = True) -> str:
    if v is None:
        return "—"
    if not full and abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    return f"${v:,.0f}"


def pct(v: float | None, sign: bool = False, d: int = 1) -> str:
    if v is None:
        return "—"
    return (f"{v * 100:+.{d}f}%" if sign else f"{v * 100:.{d}f}%").replace("-", "−")


def aop_min(tiv: float) -> float:
    for lim, ded in NB_STANDARDS["aop_table"]:
        if tiv < lim:
            return ded
    return 500_000


def level_for_dev(dev: float) -> int:
    for lvl in (1, 2, 3, 4):
        if abs(dev) <= NB_AUTHORITY[lvl]["max_price_dev"] + 1e-9:
            return lvl
    return 5

"""Truth model for the demo world.

The generator builds a *true state* per account, then renders broker/carrier
documents from it with controlled, recorded errors. The engine never reads the
truth — it only sees documents and mock-system records, exactly like production.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Building:
    key: str                     # "B-1"
    label: str
    width_m: float
    depth_m: float
    stories: int
    story_h_m: float = 4.2
    x_m: float = 0.0             # offset within site
    y_m: float = 0.0
    roof: str = "flat"           # flat | gable
    kind: str = "box"            # box | warehouse | tower | datahall
    racks: int = 0               # warehouse interior racks
    rack_height_ft: float = 0.0
    sprinkler_design_ft: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class Values:
    building: float
    contents: float
    stock: float = 0.0
    bi: float = 0.0

    @property
    def tiv(self) -> float:
        return self.building + self.contents + self.stock + self.bi


@dataclass
class Location:
    key: str                     # stable truth key
    name: str
    street_no: int
    street: str
    city: str
    state: str
    zip: str
    lat: float
    lon: float
    occupancy: str               # canonical family key (refdata.OCCUPANCY)
    occupancy_raw: str           # as broker writes it (current SOV)
    construction: int            # ISO 1..6 (true)
    construction_raw: str
    year_built: int
    stories: int
    sqft: int
    roof_year: int               # true (engineering-verified) roof year
    roof_type: str
    ppc: int
    sprinkler_pct: float
    fire_alarm: bool = True
    burglar_alarm: bool = True
    burglar_monitored: bool = True
    values_prior: Values | None = None
    values_current: Values | None = None
    model_rc: float = 0.0        # modelled replacement cost of building
    status: str = "existing"     # existing | new | deleted
    loc_no_prior: str | None = None
    loc_no_current: str | None = None
    zone: str | None = None
    wind_tier: str | None = None
    flood_zone: str = "X"
    eq_zone: str | None = None
    wildfire: int = 5
    burglary_score: int = 40
    buildings: list[Building] = field(default_factory=list)
    # occupancy-specific / scenario facts
    occupancy_prior: str | None = None       # if occupancy drifted
    occupancy_raw_prior: str | None = None   # prior SOV description if different
    storage_height_ft: float | None = None
    sprinkler_design_ft: float | None = None
    commodity: str | None = None
    vacancy_pct: float = 0.0
    sprinkler_impaired: bool = False
    cooking: bool = False
    cooking_suppression_verified: bool | None = None
    hood_cleaning_ok: bool | None = None
    stock_value_peak: float = 0.0
    last_appraisal: str | None = None
    # document rendering quirks (errors injected in broker SOV)
    sov_roof_year: int | None = None           # stale roof year repeated by broker
    sov_construction_raw: str | None = None
    sov_address_variant: str | None = None     # e.g. "100 College Avenue, Bldg 4"
    cat_construction_code: int | None = None   # what the CAT team coded last year
    merged_from: list[str] = field(default_factory=list)
    sqft_prior: int | None = None
    imagery: list[dict[str, Any]] = field(default_factory=list)  # [{date, style}]
    engineering_date: str | None = None

    @property
    def address(self) -> str:
        return f"{self.street_no} {self.street}"


@dataclass
class Terms:
    limit: float
    limit_basis: str = "blanket"             # blanket | scheduled | loss_limit
    aop_deductible: float = 25_000
    named_storm_ded_pct: float | None = None
    named_storm_ded_min: float | None = None
    wind_hail_ded_pct: float | None = None
    bi_sublimit: float | None = None
    flood_sublimit: float | None = None
    eq_sublimit: float | None = None
    forms: list[str] = field(default_factory=list)
    safeguards: list[dict[str, Any]] = field(default_factory=list)   # [{code, location_key}]

    def dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    claim_id: str
    location_key: str | None
    dol: str
    cause: str                   # fire | water_nonweather | wind_hail | theft | vandalism | hurricane | equipment | collapse
    paid: float
    reserve: float
    status: str
    description: str
    cat_event: str | None = None
    report_date: str | None = None
    linked_rec: str | None = None


@dataclass
class Recommendation:
    rec_id: str
    location_key: str
    raised: str
    category: str
    description: str
    severity: str                # LOW..CRITICAL
    due: str
    status: str                  # OPEN | IN_PROGRESS | CLOSED | VERIFIED_CLOSED
    bind_condition: bool = False
    completion_evidence: str | None = None
    closed_on: str | None = None


@dataclass
class QuoteTruth:
    version: int
    date: str
    premium: float
    terms: Terms
    status: str                  # SENT | ACCEPTED | SUPERSEDED
    approved_by: str | None = None
    approval_date: str | None = None
    approval_terms_version: int | None = None


@dataclass
class Endorsement:
    endt_id: str
    effective: str
    type: str
    description: str
    premium_delta: float
    changes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Email:
    date: str
    sender: str
    to: list[str]
    subject: str
    body: str
    attachments: list[str] = field(default_factory=list)   # doc keys
    kind: str = "renewal_submission"


@dataclass
class Account:
    account_id: str
    name: str
    scenario: str | None
    scenario_title: str | None
    segment: str
    occ_family: str
    hq_state: str
    broker: str
    broker_contact: str
    underwriter_id: str
    tenure_years: int
    admitted: bool
    fein: str
    policy_no: str
    term_start: str
    term_end: str
    carrier_share: float = 1.0
    layer_attach: float = 0.0
    layer_limit: float | None = None
    locations: list[Location] = field(default_factory=list)
    terms_quoted: Terms | None = None      # accepted quote terms (prior term)
    terms_binder: Terms | None = None
    terms_issued: Terms | None = None
    quotes: list[QuoteTruth] = field(default_factory=list)
    endorsements: list[Endorsement] = field(default_factory=list)
    subjectivities: list[dict[str, Any]] = field(default_factory=list)
    premium_expiring: float = 0.0
    tp_at_bind: float = 0.0
    rater_model_at_bind: str = "NS-PROP-RATER v7.2"
    account_mod: float = 1.0
    brokerage_prior: float = 0.15
    brokerage_proposed: float = 0.15
    uw_reported_rarc: float | None = None   # what the UW self-reports (for the book comparison)
    claims: list[Claim] = field(default_factory=list)
    recs: list[Recommendation] = field(default_factory=list)
    emails: list[Email] = field(default_factory=list)
    renewal_sov_date: str | None = None     # when renewal SOV arrives
    renewal_target_premium: float | None = None
    sov_quirks: dict[str, Any] = field(default_factory=dict)  # scale_000s, totals_row, header_row, hidden_rows...
    engineering_survey_dates: list[str] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)   # expected rule ids (regression)
    sim: dict[str, Any] = field(default_factory=dict)   # simulated underwriter behaviour for background accounts
    loss_ratio_hist: float = 0.4
    revenue: float = 0.0
    site_layout: str = "scatter"            # scatter | campus

    @property
    def expiry(self) -> str:
        return self.term_end

    def loc(self, key: str) -> Location:
        return next(l for l in self.locations if l.key == key)

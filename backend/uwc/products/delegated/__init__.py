"""Product 03 — Delegated Authority Control. Is the coverholder actually writing the business we authorised?

Authority granted (BAA + endorsements, parsed from PDF) vs business written (risk, premium and claims bordereaux,
mapped to Lloyd's CRS v5.2) → control result (breach register per policy, authority report per coverholder,
scorecard, aggregates, quarterly RARC) → remediation (queries, corrections, commission reconciliation,
authority amendments), with the coverholder and carrier back-office systems mocked behind ports."""
from __future__ import annotations

import time

from . import core as C
from . import engine as E
from . import playbooks as PB
from . import stages as SG
from . import views as V
from .api import router  # noqa: F401
from .refdata import COVERHOLDERS, ORDER

ID = "delegated"
META = {"id": ID, "name": "Delegated Authority Control", "short": "Delegated", "number": "03", "tagline": "Is the coverholder writing the business we authorised?",
        "description": "Checks every policy a coverholder or MGA binds on the carrier's paper against the binding authority as endorsed — class, territory, limits, deductibles, "
                       "pricing, referrals, commission and aggregates — and closes the loop with the coverholder.",
        "subject_label": "Coverholder"}
GROUPS = ["Authority granted", "Business written", "Control result", "Remediation"]
PIPE = [
    ("01", "Binding authority onboarded", "Authority granted", "BAA extractor + versioned authority", "REAL",
     "Agreement and endorsements read back from PDF into a versioned authority contract; every term keeps its page and box", "DARegistryPort"),
    ("02", "Bordereau received", "Business written", "Coverholder portal / bordereau inbox", "MOCK",
     "Monthly risk, premium and claims bordereaux arrive by dated event in the coverholder's own template; lateness against the BAA due date is measured", "CoverholderPortalPort"),
    ("03", "Mapping & validation (CRS v5.2)", "Business written", "Bordereau mapper", "REAL",
     "Header detection, synonym mapping to Lloyd's CRS v5.2 with confidence, type / arithmetic / date / duplicate checks with cell references", None),
    ("04", "Risk-level authority checks", "Control result", "Authority rules", "REAL",
     "Class, territory, limit, deductibles, pricing range, referral triggers, exclusions, period and zone restrictions — each line against the authority in force when bound", None),
    ("05", "Referral reconciliation", "Control result", "Referral matcher + carrier referral system", "REAL",
     "Every referral trigger matched to an approval that exists, pre-dates binding and covers the written terms", "ReferralSystemPort"),
    ("06", "Premium & commission reconciliation", "Control result", "Reconciliation + finance ledger", "REAL",
     "Risk vs premium bordereau, commission contract vs reported, return premiums; over-deductions posted as debit notes", "FinanceLedgerPort"),
    ("07", "Aggregate & capacity monitoring", "Control result", "Aggregates + CAT feed", "REAL",
     "In-force TIV by zone from the exposure return and bordereau movements vs the BAA limits; premium income vs GPI", "CatAggregatePort"),
    ("08", "Claims bordereau review", "Control result", "Claims controls", "REAL",
     "Claims on out-of-authority risks, late large-loss notification, reserve movements, settlement authority, loss dates", None),
    ("09", "Breach register & carrier action", "Remediation", "Breach register", "REAL", "One entry per policy with the side-by-side authority result; query, ratify or escalate", None),
    ("10", "Coverholder query & response", "Remediation", "Coverholder responder", "MOCK",
     "The coverholder replies by rule after a few days: corrects, supplies a referral reference, cancels, disputes, agrees; corrections are re-checked", "CoverholderPort"),
    ("11", "Authority report, scorecard & amendment", "Remediation", "Reporting + endorsements", "REAL",
     "Monthly authority report, coverholder scorecard, quarterly RARC from bordereaux, audit, authority amendments by endorsement", "DARegistryPort"),
]
REAL_CORE = PB.REAL_CORE
MOCK_CORE = PB.MOCK_CORE


def init(rt):
    rt.delegated = C.new_state()


def build_world(rt):
    if getattr(rt, "delegated", None) is None:
        init(rt)
    C.build_world(rt)


def on_day(rt, ds):
    C.on_day(rt, ds)


def handle_event(rt, e):
    if getattr(rt, "delegated", None) and rt.delegated.get("built"):
        C.handle_event(rt, e)


def pipeline_counts(rt) -> dict:
    st = getattr(rt, "delegated", None)
    if not st or not st.get("built"):
        return {}
    ex = st["exceptions"].values()
    live = [e for e in ex if E.raised(e)]
    return {"01": [("agreements", len(st["authority"])), ("endorsements", sum(len(v) - 1 for v in st["authority"].values()))],
            "02": [("bordereaux", sum(1 for b in st["bdx"].values() if not b["correction"])), ("late", sum(1 for b in st["bdx"].values() if b["days_late"] and b["kind"] == "risk"))],
            "03": [("lines mapped", sum(b["rows"] for b in st["bdx"].values())), ("issues", sum(len(b["issues"]) for b in st["bdx"].values()))],
            "04": [("lines checked", len(st["rows"])), ("exceptions", sum(1 for e in live if e["subject_type"] == "policy"))],
            "05": [("referrals", len(st["referrals"])), ("missing", sum(1 for e in live if e.get("referral") and e["referral"]["result"] != E.REFER_OK))],
            "06": [("commission exc.", sum(1 for e in live if e["family"] == "commission")), ("debit notes", len(st["ledger"]))],
            "07": [("zones", sum(len(v[-1]["terms"].get("aggregates", {})) or len(v[0]["terms"].get("aggregates", {})) for v in st["authority"].values())),
                   ("restrictions", len(st["restrictions"]))],
            "08": [("claims", sum(len(v) for v in st["claims"].values())), ("exceptions", sum(1 for e in live if e["subject_type"] == "claim"))],
            "09": [("open", sum(1 for e in ex if e["status"] in E.OPEN_STATES))],
            "10": [("queries", len(st["queries"])), ("replies", sum(1 for q in st["queries"] if q["status"] != "SENT"))],
            "11": [("reports", len(st["reports"])), ("amendments", len(st["amendments"]))]}


def subjects(rt) -> list[dict]:
    return [{"id": ch, "label": f"{COVERHOLDERS[ch]['scenario']} · {COVERHOLDERS[ch]['name']} — {COVERHOLDERS[ch]['title']}"} for ch in ORDER]


def build_stage(rt, code, subject):
    return SG.build(rt, code, subject if subject in COVERHOLDERS else ORDER[0], PIPE)


def run_stage(rt, code, subject):
    return SG.run(rt, code, subject if subject in COVERHOLDERS else ORDER[0])


def playbooks(rt):
    return PB.all_playbooks(rt, PIPE)


def run_step(rt, p, step):
    return PB.run_step(rt, p, step)


def facts(rt, subject):
    return PB.facts(rt, subject) if subject in COVERHOLDERS else []


def mocks(rt) -> list[dict]:
    st = getattr(rt, "delegated", None) or {}
    if not st.get("built"):
        return []
    return [
        {"port": "CoverholderPortalPort", "name": "Coverholder portal / bordereau inbox (mock)", "stands_in_for": "Coverholder portal · Lloyd's DDM / bordereau management", "status": "UP",
         "records": sum(1 for b in st["bdx"].values()), "last_sync": rt.clock},
        {"port": "CoverholderPort", "name": "Coverholder responder (mock)", "stands_in_for": "The MGA / coverholder — email and portal replies", "status": "UP",
         "records": sum(1 for q in st["queries"] if q["status"] != "SENT"), "last_sync": rt.clock},
        {"port": "ReferralSystemPort", "name": "Carrier referral system (mock)", "stands_in_for": "Carrier referral queue (Duck Creek / Send, in-house workflow)", "status": "UP",
         "records": sum(1 for r in st["referrals"] if r["requested"] <= rt.clock), "last_sync": rt.clock},
        {"port": "FinanceLedgerPort", "name": "Finance ledger (mock)", "stands_in_for": "Carrier finance / credit control (SAP FS-CD, Charles Taylor)", "status": "UP",
         "records": len(st["ledger"]), "last_sync": rt.clock},
        {"port": "CatAggregatePort", "name": "CAT aggregate feed (mock)", "stands_in_for": "Accumulation zones and PML (Moody's RMS / Verisk)", "status": "UP",
         "records": sum(len(v) for v in st["zone_map"].values()), "last_sync": rt.clock},
        {"port": "DARegistryPort", "name": "DA registry & binder store (mock)", "stands_in_for": "Lloyd's delegated authority registry · binder document store", "status": "UP",
         "records": sum(len(v) for v in st["authority"].values()), "last_sync": rt.clock},
    ]


def rule_fired(rt, rule_id: str) -> int:
    st = getattr(rt, "delegated", None) or {}
    return sum(1 for e in st.get("exceptions", {}).values() if e["rule_id"] == rule_id and E.raised(e))


def reevaluate_all(rt):
    st = rt.delegated
    E.evaluate_rows(st, rt, list(st["rows"]), "Rule published")
    for ch in ORDER:
        for m in E.months_of(st, ch):
            E.evaluate_zones(st, rt, ch, V.month_end(m), m)
        E.evaluate_claims(st, rt, ch)
        for did in [d for d, b in st["bdx"].items() if b["ch"] == ch]:
            E.evaluate_bordereau(st, rt, did)


def backtest(rt, old, new) -> dict:
    """Run the candidate rule over every bordereau line held (frozen) and compare with the current rule."""
    import copy
    t0 = time.time()
    st = rt.delegated
    rid = new.rule_id

    def fire_set(rule):
        saved = rt.rules.get(rid)
        if rule is None:
            rt.rules.pop(rid, None)
        else:
            rt.rules[rid] = rule
        try:
            out = {}
            if new.applies_to in ("risk", "premium"):
                for rowid, r in st["rows"].items():
                    if r.get("duplicate"):
                        continue
                    for c in E.check_row(st, rt, r):
                        if c["rule_id"] == rid and c["result"] not in ("PASS", "NA"):
                            out[rowid] = r
            return out
        finally:
            if saved is None:
                rt.rules.pop(rid, None)
            else:
                rt.rules[rid] = saved
    before = fire_set(old)
    after = fire_set(new)

    def row(r):
        return {"account_id": r["ch"], "account_name": COVERHOLDERS[r["ch"]]["short"], "subject_label": f"{r['certificate_ref']} · {r.get('insured_name')}",
                "observed": f"{r.get('transaction_type')} · TIV ${r.get('tiv') or 0:,.0f} · limit ${r.get('limit') or 0:,.0f}"}
    return {"control_set": f"Delegated book as of {rt.clock}: {len(st['rows']):,} bordereau lines from {len(COVERHOLDERS)} coverholders (frozen)",
            "accounts": len(st["rows"]), "before": len(before), "after": len(after), "added": [row(r) for k, r in after.items() if k not in before][:200],
            "removed": [row(r) for k, r in before.items() if k not in after][:200], "duration_ms": int((time.time() - t0) * 1000)}

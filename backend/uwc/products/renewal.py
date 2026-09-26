"""Product 01 — Renewal & in-force integrity. Adapter over the renewal engine (runtime, stages, playbooks)."""
from __future__ import annotations

import time

from uwc.refdata import ZONES

ID = "renewal"
META = {"id": ID, "name": "Renewal Integrity", "short": "Renewals", "number": "01",
        "tagline": "Is the renewal what we think it is?",
        "description": "Re-checks every renewing account against the evidence, the carrier's guidelines and its own contract, before the carrier commits again. Like-for-like rate change, authority on exact terms, quote ↔ binder ↔ policy, in-force monitoring.",
        "subject_label": "Account"}
GROUPS = ["Intake & qualification", "Technical decision", "Placement & issuance", "Feedback loop"]
router = None

PIPE = [
    ("01", "Submission received", "Intake & qualification", "Broker mailbox + portal", "MOCK", "Scripted broker emails with attachments; the broker returns requested documents 3 days after a data request, which are parsed like any other", "MailboxPort"),
    ("02", "Clearance & completeness", "Intake & qualification", "Clearance service", "MOCK", "Duplicate check, broker licence by location state, sanctions screening — a HOLD blocks quoting and binding until resolved", "ClearancePort"),
    ("03", "Appetite & triage", "Intake & qualification", "Rule engine", "REAL", "Versioned guideline rules applied at the evaluation date", None),
    ("04", "Extraction & enrichment", "Intake & qualification", "Ingestion + vendor stubs", "REAL", "SOV / PDF / email extraction with anchors; geocode, hazard, valuation, crime, imagery vendors mocked", "VendorPort"),
    ("05", "Risk assessment", "Technical decision", "Engineering module", "MOCK", "Survey reports, recommendation register, site visits on request (+7 days) that verify completion or raise new recommendations", "EngineeringPort"),
    ("06", "Pricing, rating & modelling", "Technical decision", "Rater + CAT stubs", "MOCK", "Mock rater and event-based MockCat, called three times for the RARC split", "RaterPort · CatModelPort"),
    ("07", "Authority & portfolio checks", "Technical decision", "Authority + accumulation", "REAL", "Authority matrix, referrals locked to terms hash, zone accumulation", None),
    ("08", "Terms & quote", "Technical decision", "Quote builder", "REAL", "Terms and forms → quote version locked to a terms hash → quote PDF (read back by the extractor); blocked while clearance is on hold", None),
    ("09", "Broker negotiation", "Placement & issuance", "Broker bot", "MOCK", "Rule-based broker: accepts at or near target/technical, otherwise counters at the midpoint", "BrokerPort"),
    ("10", "Bind", "Placement & issuance", "Bind flow", "REAL", "Bind blocked without an approval for the exact terms; approval conditions printed as subjectivities and cleared by evidence", None),
    ("11", "Policy issuance", "Placement & issuance", "Policy admin stub", "MOCK", "Issues declarations (issuance-error toggle), corrective endorsements, premium invoice", "PolicyAdminPort"),
    ("12", "Mid-term monitoring", "Placement & issuance", "Endorsements + claims stub", "MOCK", "Endorsements, FNOL, impairments (scripted or raised live by the presenter) trigger event-driven re-evaluation", "PolicyAdminPort · ClaimsPort"),
    ("13", "Claims & exposure feedback", "Feedback loop", "Outcome capture", "REAL", "Claims and endorsements feed risk-quality deltas", None),
    ("14", "Portfolio steering", "Feedback loop", "Book view", "REAL", "CUO view; accumulation; exceptions by underwriter and broker", None),
    ("15", "Renewal", "Feedback loop", "Renewal engine", "REAL", "Passes 1–3; account re-enters stage 03", None),
]

from uwc.playbook_defs import MOCK_CORE, REAL_CORE  # noqa: E402,F401

HEROES = ["acc_s2", "acc_s1", "acc_s3", "acc_s4", "acc_s5", "acc_s6", "acc_s7", "acc_s8", "acc_s9", "acc_s10", "acc_s11", "acc_s12"]


def init(rt):
    pass


def build_world(rt):
    pass


def on_day(rt, ds):
    pass


def handle_event(rt, e):
    pass


def pipeline_counts(rt) -> dict:
    docs = rt.store.docs.values()
    counts = {
        "01": [("emails", sum(1 for d in docs if d["doc_type"] == "Broker email")), ("documents", len(rt.store.docs))],
        "02": [("accounts cleared", len(rt.systems["accounts"]))],
        "03": [("rules", len(rt.rules)), ("findings", sum(len(r.findings) for r in rt.ren.values()))],
        "04": [("observations", len(rt.store.obs)), ("locations", sum(len(v) for v in rt.store.locations.values()))],
        "05": [("recommendations", sum(len(v) for v in rt.recs.values()))],
        "06": [("CAT runs", sum(len(v) for v in rt.cat_runs.values()))],
        "07": [("referrals", sum(len(r.referrals) for r in rt.ren.values()))],
        "08": [("renewal quotes", sum(len(r.quotes) for r in rt.ren.values()))],
        "09": [("quotes sent", sum(1 for r in rt.ren.values() for q in r.quotes if q["status"] in ("SENT", "ACCEPTED", "BOUND")))],
        "10": [("bound", sum(1 for r in rt.ren.values() if r.r_bound))],
        "11": [("issued", sum(1 for r in rt.ren.values() if r.r_issued))],
        "12": [("endorsements", sum(len(p.get("endorsements_applied", [])) for p in rt.pas.values())), ("claims", sum(len(v) for v in rt.claims.values()))],
        "13": [("claims linked", sum(1 for v in rt.claims.values() for c in v if c.get("location_uid")))],
        "14": [("zones", len(ZONES))],
        "15": [("pass 1", sum(1 for r in rt.ren.values() if r.pass_no >= 1)), ("pass 2", sum(1 for r in rt.ren.values() if r.pass_no >= 2)), ("pass 3", sum(1 for r in rt.ren.values() if r.pass_no >= 3))],
    }
    return counts


def subjects(rt) -> list[dict]:
    return [{"id": a, "label": f"{rt.systems['accounts'][a]['scenario']} · {rt.systems['accounts'][a]['name']} — {rt.systems['accounts'][a].get('scenario_title', '')}"} for a in HEROES]


def build_stage(rt, code, subject):
    from uwc import stages as ST
    return ST.build(rt, code, subject)


def run_stage(rt, code, subject):
    from uwc import stages as ST
    return ST.run(rt, code, subject)


def playbooks(rt):
    from uwc import playbooks as PB
    return PB.all_playbooks(rt)


def run_step(rt, p, step):
    from uwc import playbooks as PB
    return PB.run_step(rt, p, step)


def facts(rt, acct: str) -> list[dict]:
    from uwc import fulfilment as F
    """Live, engine-computed facts for the playbook's account (what the client should take away, in numbers)."""
    ren = rt.ren[acct]
    r = ren.rarc or {}
    reg = rt.systems["accounts"][acct]
    out = [{"label": "Account", "value": f"{reg['name']} · {reg.get('scenario') or ''}"},
           {"label": "Clearance", "value": F.clearance(rt, acct)["status"]},
           {"label": "Expiring premium", "value": f"${rt.pas[acct].get('premium') or rt.systems['pas'][acct]['premium']:,.0f}"}]
    if r.get("tp_e1_t1"):
        out += [{"label": "Technical premium (renewal)", "value": f"${r['tp_e1_t1']:,.0f}"},
                {"label": "Expected premium (like-for-like)", "value": f"${r['expected_premium']:,.0f}"}]
    q = ren.quotes[-1] if ren.quotes else None
    if q:
        out += [{"label": f"Latest quote v{q['version']}", "value": f"${q['premium']:,.0f} · {q['status'].lower()}"},
                {"label": "RARC on latest quote", "value": f"{q['rarc'] * 100:+.1f}% (headline {r.get('headline_change', 0) * 100:+.1f}%)"}]
    mats = [f for f in ren.findings.values() if f["material"]]
    out.append({"label": "Material findings", "value": f"{len([f for f in mats if f['status'] == 'OPEN'])} open · {len([f for f in mats if f['status'] == 'ACCEPTED'])} accepted · {len([f for f in mats if f['status'] == 'RESOLVED'])} resolved"})
    if ren.referrals:
        x = ren.referrals[-1]
        out.append({"label": "Latest referral", "value": f"L{x['required_level']} · {x['status'].lower()}" + (f" by {x['approver']}" if x.get("approver") else "")})
    subj = F.renewal_subjectivities(rt, acct)
    if subj:
        out.append({"label": "Subjectivities", "value": f"{sum(1 for s in subj if s['status'] == 'CLEARED')}/{len(subj)} cleared"})
    if ren.r_bound:
        out.append({"label": "Bound", "value": f"{ren.r_bound['date']} at ${ren.r_bound['premium']:,.0f}"})
    if ren.r_issued:
        out.append({"label": "Issued", "value": f"{ren.r_issued['date']} — {ren.r_issued['injected'] or 'as bound'}" + (" · corrected by endorsement" if ren.r_issued.get("corrected") else "")})
    if ren.status == "NON_RENEWED":
        out.append({"label": "Outcome", "value": "Non-renewed"})
    return out



def mocks(rt) -> list[dict]:
    return [
        {"port": "PolicyAdminPort", "name": "PAS (mock)", "stands_in_for": "Guidewire PolicyCenter / Duck Creek", "status": "UP", "records": sum(1 for p in rt.pas.values() if p.get("policy_no")), "last_sync": rt.clock},
        {"port": "ClaimsPort", "name": "Claims (mock)", "stands_in_for": "Guidewire ClaimCenter", "status": "UP", "records": sum(len(v) for v in rt.claims.values()), "last_sync": rt.clock},
        {"port": "RaterPort", "name": "NS-PROP-RATER v8.0 (mock)", "stands_in_for": "hx Renew / carrier rating service", "status": "UP", "records": len(rt.systems["rater"]), "last_sync": rt.clock},
        {"port": "CatModelPort", "name": "MockCat 3.1", "stands_in_for": "Moody's RMS IRP / Verisk Touchstone", "status": "UP", "records": sum(len(v) for v in rt.cat_runs.values()), "last_sync": rt.clock},
        {"port": "EngineeringPort", "name": "Engineering (mock)", "stands_in_for": "Risk engineering platform", "status": "UP", "records": sum(len(v) for v in rt.recs.values()), "last_sync": rt.clock},
        {"port": "VendorPort", "name": "Vendors (mock)", "stands_in_for": "Precisely geocoder · HazardHub · 360Value · Nearmap · crime scores", "status": "UP", "records": len(rt.systems["vendors"]), "last_sync": rt.clock},
        {"port": "MailboxPort", "name": "Broker mailbox (mock)", "stands_in_for": "Email / broker portal", "status": "UP", "records": sum(1 for d in rt.store.docs.values() if d["doc_type"] == "Broker email"), "last_sync": rt.clock},
        {"port": "BrokerPort", "name": "Broker bot (mock)", "stands_in_for": "Broker negotiation", "status": "UP", "records": len(rt.outbox), "last_sync": rt.clock},
    ]


def rule_fired(rt, rule_id: str) -> int:
    return sum(1 for ren in rt.ren.values() for f in ren.findings.values() if f["rule_id"] == rule_id)


def reevaluate_all(rt):
    from uwc.engine.evaluate import evaluate_account
    for a, ren in rt.ren.items():
        if ren.pass_no:
            evaluate_account(rt, a)


def backtest(rt, old, new) -> dict:
    from uwc.engine.evaluate import evaluate_account
    rid = new.rule_id
    t0 = time.time()
    before = {f["subject_id"]: f for ren in rt.ren.values() for f in ren.findings.values() if f["rule_id"] == rid and f["status"] != "RESOLVED"}
    saved = {a: (dict(r.findings), dict(r.finding_ids), list(r.actions), r.integrity, r.narrative, r.status) for a, r in rt.ren.items()}
    rt.rules[rid] = new
    after = {}
    try:
        for a, ren in rt.ren.items():
            if ren.pass_no:
                evaluate_account(rt, a)
        after = {f["subject_id"]: f for ren in rt.ren.values() for f in ren.findings.values() if f["rule_id"] == new.rule_id and f["status"] != "RESOLVED"}
    finally:
        if old:
            rt.rules[rid] = old
        for a, (fs, ids, acts, integ, narr, stt) in saved.items():
            r = rt.ren[a]
            r.findings, r.finding_ids, r.actions, r.integrity, r.narrative, r.status = fs, ids, acts, integ, narr, stt
    def row(f):
        return {"account_id": f["account_id"], "account_name": rt.systems["accounts"][f["account_id"]]["name"], "subject_label": f["subject_label"], "observed": f["observed"]}
    return {"control_set": f"Northgate renewal book as of {rt.clock} (frozen)", "accounts": sum(1 for r in rt.ren.values() if r.pass_no),
            "before": len(before), "after": len(after), "added": [row(f) for k, f in after.items() if k not in before],
            "removed": [row(f) for k, f in before.items() if k not in after], "duration_ms": int((time.time() - t0) * 1000)}

"""End-to-end fulfilment: the parts of real life that close the loop.

- Broker replies to data requests with real documents, which are ingested and clear findings
  and subjectivities.
- Clearance (duplicates, broker licence by state, sanctions) that can put an account on HOLD
  and blocks quoting until resolved.
- Risk-engineering visits that verify recommendations and re-survey conditions.
- Approval conditions become renewal subjectivities, printed on the binder and cleared by evidence.
- Corrective endorsements that fix issuance errors; billing on issuance.
- Presenter-triggered in-force events (claim, impairment, vacancy).
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime
from typing import TYPE_CHECKING

from uwc.ingest import interpret as I
from uwc.refdata import USER_BY_ID
from uwc.world.pdfkit import Pdf, money

if TYPE_CHECKING:
    from uwc.runtime import Runtime

SANCTIONS = ["Volkov Trading LLC", "Orion Maritime Holdings", "Karsk Industrial Group"]
# broker → {state: licence expiry}; every broker is licensed everywhere to 2027-12-31 unless listed here
LICENCE_EXCEPTIONS = {"Ironbridge Specialty Brokers": {"AZ": "2026-06-30"}}


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def _plus(rt, days: int) -> str:
    return (rt.clock_date + timedelta(days=days)).isoformat()


def _st(rt) -> dict:
    """Lazily-created fulfilment state (survives old snapshots)."""
    s = getattr(rt, "ful", None)
    if s is None:
        rt.ful = s = {"licences": {}, "received": {}, "r_subj": {}, "billing": {}, "counter": 0}
    return s


def _nid(rt, prefix: str) -> str:
    s = _st(rt)
    s["counter"] += 1
    return f"{prefix}{s['counter']:04d}"


# ============================================================================ clearance
def clearance(rt: "Runtime", acct: str) -> dict:
    reg = rt.systems["accounts"][acct]
    locs = rt.store.account_locations(acct)
    states = sorted({e.state for e in locs.values() if e.state}) or [reg["hq_state"]]
    renewed = _st(rt)["licences"]
    checks = []
    dup = [a for a, x in rt.systems["accounts"].items() if a != acct and (x["fein"] == reg["fein"] or x["name"].lower() == reg["name"].lower())]
    checks.append({"check": "Duplicate submission", "result": "PASS" if not dup else "HOLD", "detail": "No other account with this FEIN or name" if not dup else ", ".join(dup)})
    lic_issues = []
    for stt in states:
        exp = renewed.get((reg["broker"], stt)) or LICENCE_EXCEPTIONS.get(reg["broker"], {}).get(stt, "2027-12-31")
        if exp < rt.clock:
            lic_issues.append(f"{stt} licence expired {exp}")
    lic_no = f"{int(hashlib.md5(reg['broker'].encode()).hexdigest()[:6], 16) % 900000 + 100000}"
    checks.append({"check": f"Broker licence ({', '.join(states)})", "result": "HOLD" if lic_issues else "PASS",
                   "detail": (f"{reg['broker']} · licence {lic_no} · " + ("; ".join(lic_issues) if lic_issues else "active in every location state"))})
    toks = set(re.findall(r"[a-z]+", reg["name"].lower())) - {"llc", "inc", "co", "group", "the", "and"}
    hit = next((n for n in SANCTIONS if len(toks & set(re.findall(r"[a-z]+", n.lower()))) >= 2), None)
    checks.append({"check": "Sanctions / OFAC screening", "result": "HOLD" if hit else "PASS", "detail": f"Possible match: {hit}" if hit else f"Named insured and FEIN {reg['fein']} clear against the screening list"})
    checks.append({"check": "Placement type", "result": "PASS", "detail": "Admitted" if reg["admitted"] else "Surplus lines — diligent-search affidavit on file"})
    status = "HOLD" if any(c["result"] == "HOLD" for c in checks) else "CLEARED"
    return {"status": status, "checks": checks, "reason": "; ".join(c["detail"] for c in checks if c["result"] == "HOLD")}


def require_cleared(rt: "Runtime", acct: str):
    c = clearance(rt, acct)
    if c["status"] == "HOLD":
        raise ValueError(f"Clearance hold — {c['reason']}. Resolve before quoting.")


# ============================================================================ documents from the broker
KINDS = [
    ("licence", re.compile(r"licen[cs]e", re.I)),
    ("alarm", re.compile(r"alarm", re.I)),
    ("hood", re.compile(r"hood|cooking|suppression", re.I)),
    ("sprinkler", re.compile(r"sprinkler restor|restoration cert", re.I)),
    ("roof", re.compile(r"roof", re.I)),
    ("completion", re.compile(r"completion|R-\d{3,4}", re.I)),
    ("generator", re.compile(r"generator", re.I)),
    ("appraisal", re.compile(r"apprais|valuation", re.I)),
]


def schedule_broker_docs(rt: "Runtime", acct: str, items: list[str], days: int = 3):
    reg = rt.systems["accounts"][acct]
    rt.dynamic.append({"date": _plus(rt, days), "type": "broker.docs", "account_id": acct, "account_name": reg["name"],
                       "title": "Broker returns the requested documents", "payload": {"items": items}})


def _pdf(rt, acct, kind: str, title: str, theme: str = "broker"):
    from uwc.runtime import RUNTIME_DOCS
    did = _nid(rt, f"r_{acct}_{kind}_")
    p = RUNTIME_DOCS / f"{did}.pdf"
    return did, p, Pdf(p, theme, title, did.upper())


def handle_broker_docs(rt: "Runtime", e: dict):
    acct = e["account_id"]
    reg = rt.systems["accounts"][acct]
    ren = rt.ren[acct]
    locs = rt.store.account_locations(acct)
    produced: list[tuple[str, str, str | None]] = []   # (doc_id, filename, role)
    notes: list[str] = []
    for item in e["payload"]["items"]:
        kind = next((k for k, rx in KINDS if rx.search(item)), "generic")
        if kind == "licence":
            for stt in {e_.state for e_ in locs.values()}:
                _st(rt)["licences"][(reg["broker"], stt)] = "2027-06-30"
            did, path, p = _pdf(rt, acct, "licence", "Producer licence certificate", "broker")
            p.title("Producer Licence Certificate", f"Issued {rt.clock}")
            p.kv([("Producer", reg["broker"]), ("States", ", ".join(sorted({e_.state for e_ in locs.values()}))), ("Status", "Active"), ("Expires", "2027-06-30")], cols=1, label_w=120)
            p.save()
            produced.append((did, "Producer_licence.pdf", None)); notes.append("renewed producer licence")
        elif kind == "alarm":
            did, path, p = _pdf(rt, acct, "alarm", "Burglar Alarm Certificates", "alarm")
            p.title("Burglar Alarm System Certificates", f"Issued {rt.clock} · {reg['name']}")
            n = 0
            for uid, loc in locs.items():
                mon = [o for o in rt.store.field_obs(uid, "burglar_monitored")]
                if mon and mon[-1].value is True:
                    continue
                if not ren.loc_ctx.get(uid, {}).get("stock_value"):
                    continue
                p.section(f"Certificate — {loc.label}")
                p.kv([("Protected premises", f"{loc.address}, {loc.city}, {loc.state}"), ("Alarm type", "Intrusion — motion, contact, glass-break"),
                      ("Central station monitoring", "Yes — UL listed central station"), ("Certificate date", rt.clock)], cols=1, label_w=170)
                n += 1
            p.save()
            produced.append((did, "Alarm_certificates.pdf", "alarm_certs")); notes.append(f"{n} monitored-alarm certificates")
        elif kind == "hood":
            did, path, p = _pdf(rt, acct, "hood", "Kitchen Exhaust Cleaning Certificates", "hood")
            p.title("Kitchen Exhaust Hood & Duct Cleaning Certificates", f"Issued {rt.clock}")
            n = 0
            for uid, loc in locs.items():
                ok = [o for o in rt.store.field_obs(uid, "cooking_suppression_verified")]
                if ok and ok[-1].value is True:
                    continue
                if ren.loc_ctx.get(uid, {}).get("occupancy_class") != "restaurant":
                    continue
                p.section(loc.label)
                p.kv([("Premises", f"{loc.address}, {loc.city}, {loc.state}"), ("Service", "Hood, duct & fan cleaned to bare metal (NFPA 96)"),
                      ("Service date", rt.clock), ("Suppression system inspected", "Yes — UL 300 wet chemical, tagged")], cols=1, label_w=170)
                n += 1
            p.save()
            produced.append((did, "Hood_cleaning_certificates.pdf", "hood_certs")); notes.append(f"{n} hood-cleaning certificates")
        elif kind == "sprinkler":
            did, path, p = _pdf(rt, acct, "sprinkler", "Sprinkler Restoration Certificate", "fire")
            p.title("Fire Protection System Restoration Certificate", f"Issued {rt.clock}")
            for uid, loc in locs.items():
                imp = rt.store.field_obs(uid, "sprinkler_impaired")
                if imp and imp[-1].value:
                    p.kv([("Premises", f"{loc.label}, {loc.address}, {loc.city}, {loc.state}"), ("System status", "Restored — riser valve open, main drain test passed"),
                          ("Date restored", rt.clock), ("Fire watch", "Maintained until restoration")], cols=1, label_w=150)
                    anc = {"doc_id": did, "kind": "pdf", "page": 1, "text": "Restored — riser valve open, main drain test passed"}
                    I._obs(rt, acct, "location", uid, "sprinkler_impaired", False, "V", "Engineering", "Sprinkler restoration certificate", rt.clock, anc, did, 0.97)
            p.save()
            produced.append((did, "Sprinkler_restoration_certificate.pdf", None)); notes.append("sprinkler restoration certificate")
        elif kind == "roof":
            did, path, p = _pdf(rt, acct, "roof", "Roof Replacement Schedule", "broker")
            p.title("Roof Replacement Schedule", f"Prepared by the insured's facilities team · {rt.clock}")
            rows = []
            for uid, loc in locs.items():
                ry = ren.loc_ctx.get(uid, {}).get("roof_year")
                rows.append((loc.label, loc.address, str(ry or "—"), "2029" if (ry or 2020) < 2012 else "—"))
            p.table(["Location", "Address", "Roof year", "Planned replacement"], rows, [140, 180, 80, 100])
            p.save()
            produced.append((did, "Roof_replacement_schedule.pdf", None)); notes.append("roof replacement schedule")
        elif kind == "completion":
            did, path, p = _pdf(rt, acct, "completion", "Contractor Completion Certificate", "broker")
            p.title("Contractor Completion Certificate", f"Issued {rt.clock}")
            done = []
            named = re.findall(r"R-\d{3,4}", item)
            for rec in rt.recs.get(acct, {}).values():
                if rec["status"] == "VERIFIED_CLOSED" or (named and rec["rec_id"] not in named) or (not named and rec["severity"] not in ("CRITICAL", "HIGH")):
                    continue
                p.kv([("Recommendation", rec["rec_id"]), ("Work", rec["description"][:90]), ("Completed", rt.clock), ("Contractor", "Apex Fire & Dust Controls (fictional)")], cols=1, label_w=120)
                rec["completion_evidence"] = f"Contractor completion certificate {did} ({rt.clock}) — awaiting engineering verification"
                if rec["status"] in ("OPEN",):
                    rec["status"] = "CLOSED"
                done.append(rec["rec_id"])
            p.save()
            produced.append((did, "Completion_certificate.pdf", None)); notes.append(f"completion evidence for {', '.join(done) or 'open recommendations'}")
        elif kind == "generator":
            did, path, p = _pdf(rt, acct, "generator", "Generator Load Test Report", "engineering")
            p.title("Emergency Generator Full-Load Test Report", f"Tested {rt.clock}")
            p.kv([("Equipment", "2 × 2.5 MW diesel generators, Central Utility Plant"), ("Load bank test", "4 hours at 100% nameplate — passed"), ("Transfer time", "8.2 s (NFPA 110 Level 1 ≤ 10 s)")], cols=1, label_w=140)
            p.save()
            produced.append((did, "Generator_load_test.pdf", None)); notes.append("generator load test report")
            for sj in rt.pas[acct].get("subjectivities", []):
                if "generator" in sj["text"].lower():
                    sj["status"] = "CLEARED"
        elif kind == "appraisal":
            did, path, p = _pdf(rt, acct, "appraisal", "Insurable Value Appraisal", "appraisal")
            p.title("Insurable Value Appraisal", f"Effective date {rt.clock} · Replacement cost new")
            p.kv([("Client", reg["name"]), ("Effective date", rt.clock), ("Valuation basis", "Replacement cost new")])
            p.save()
            produced.append((did, "Appraisal.pdf", "appraisal")); notes.append("updated appraisal")
        else:
            did, path, p = _pdf(rt, acct, "doc", item[:40], "broker")
            p.title(item[:60], f"Provided {rt.clock}")
            p.para(f"Document provided by {reg['broker']} in response to the carrier's request: {item}.")
            p.save()
            produced.append((did, f"{re.sub(r'[^A-Za-z0-9]+', '_', item)[:40]}.pdf", None)); notes.append(item.lower())
        _st(rt)["received"].setdefault(acct, []).append(item)
        _clear_subjectivities(rt, acct, item, did)

    # the broker's reply email with every document attached
    from uwc.runtime import RUNTIME_DOCS
    eid = _nid(rt, f"r_{acct}_reply_")
    m = EmailMessage()
    m["From"] = f"{reg['broker_contact']} <{reg['broker_contact'].split()[0].lower()}@broker.example>"
    m["To"] = f"{USER_BY_ID[reg['underwriter_id']]['name']} <underwriting@northgate.example>"
    m["Subject"] = f"RE: {reg['name']} — requested information"
    m["Date"] = format_datetime(datetime.fromisoformat(rt.clock + "T10:05:00-04:00"))
    m.set_content(f"Hi,\n\nPlease find attached: {', '.join(notes)}.\n\nRegards,\n{reg['broker_contact']}\n{reg['broker']}")
    attach_meta = []
    for did, fname, role in produced:
        doc_path = RUNTIME_DOCS / f"{did}.pdf"
        m.add_attachment(doc_path.read_bytes(), maintype="application", subtype="pdf", filename=fname)
        rt.add_runtime_doc(acct, did, "Certificate" if role in ("alarm_certs", "hood_certs") else "Appraisal" if role == "appraisal" else "Broker document", fname.replace("_", " ").replace(".pdf", ""), "pdf", doc_path, "Broker email")
        attach_meta.append({"doc_id": did, "role": role})
    ep = RUNTIME_DOCS / f"{eid}.eml"
    ep.write_bytes(bytes(m))
    edoc = rt.add_runtime_doc(acct, eid, "Broker email", m["Subject"], "eml", ep, "Broker email", attachments=[d for d, *_ in produced])
    I.ingest_document(rt, edoc, "email", rt.clock, {"attachments": [a for a in attach_meta if a["role"]]})
    rt.log(acct, "document", "01", "Broker returned the requested documents", "; ".join(notes), "Broker (mock)", eid)


def _clear_subjectivities(rt, acct, item: str, doc_id: str):
    words = {w for w in re.findall(r"[a-z]{4,}", item.lower())} - {"before", "bind", "with", "within", "three", "stores", "days"}
    for sj in _st(rt)["r_subj"].get(acct, []):
        if sj["status"] == "OPEN" and words & set(re.findall(r"[a-z]{4,}", sj["text"].lower())):
            sj["status"] = "CLEARED"
            sj["evidence"] = doc_id
            rt.log(acct, "system", "10", "Subjectivity cleared", sj["text"], "Control engine", doc_id)


def received(rt, acct) -> list[str]:
    return _st(rt)["received"].get(acct, [])


# ============================================================================ subjectivities from approvals
def add_subjectivities(rt: "Runtime", acct: str, conditions: str | None):
    if not conditions:
        return
    lst = _st(rt)["r_subj"].setdefault(acct, [])
    for part in [c.strip() for c in re.split(r";|\band\b(?= [A-Z])", conditions) if c.strip()]:
        if not any(s["text"] == part for s in lst):
            lst.append({"text": part, "due": rt.pas[acct]["term_end"], "status": "OPEN", "raised": rt.clock, "evidence": None})


def renewal_subjectivities(rt, acct) -> list[dict]:
    return _st(rt)["r_subj"].get(acct, [])


# ============================================================================ engineering
def order_survey(rt: "Runtime", acct: str, uid: str, scope: str = "Renewal verification survey"):
    reg = rt.systems["accounts"][acct]
    rt.dynamic.append({"date": _plus(rt, 7), "type": "eng.visit", "account_id": acct, "account_name": reg["name"],
                       "title": "Risk engineer site visit", "payload": {"scope": scope}})
    rt.log(acct, "user", "05", "Engineering survey ordered", f"{scope} · visit scheduled {_plus(rt, 7)}", USER_BY_ID[uid]["name"])


def handle_eng_visit(rt: "Runtime", e: dict):
    acct = e["account_id"]
    reg = rt.systems["accounts"][acct]
    ren = rt.ren[acct]
    locs = rt.store.account_locations(acct)
    did, path, p = _pdf(rt, acct, "eng", "Property Risk Engineering Report", "engineering")
    p.title("Property Risk Engineering Report", f"Survey date {rt.clock} · Elena Brooks, CSP")
    p.kv([("Insured", reg["name"]), ("Survey date", rt.clock), ("Engineer", "Elena Brooks, CSP"), ("Scope", e["payload"].get("scope", "Verification"))], cols=2)
    verified, new_recs = [], []
    for uid, loc in locs.items():
        s = ren.loc_ctx.get(uid, {})
        if not loc.in_current and not loc.in_prior:
            continue
        p.section(f"Location — {loc.label}")
        p.kv([("Address", f"{loc.address}, {loc.city}, {loc.state}")], cols=1, label_w=150)
        pairs = []
        if s.get("storage_height_ft") and s.get("sprinkler_design_ft"):
            pairs += [("Max storage height (ft)", str(int(s["storage_height_ft"]))), ("Sprinkler design storage height (ft)", str(int(s["sprinkler_design_ft"])))]
            if s.get("commodity"):
                pairs.append(("Commodity", str(s["commodity"])))
            if s["storage_height_ft"] > s["sprinkler_design_ft"] and not any(r["category"] == "Fire protection" and r["location_uid"] == uid for r in rt.recs.get(acct, {}).values()):
                rid = f"R-{900 + len(rt.recs.get(acct, {}))}"
                rt.recs.setdefault(acct, {})[rid] = {"rec_id": rid, "location_uid": uid, "location_address": loc.address, "raised": rt.clock, "category": "Fire protection",
                                                     "description": "Install in-rack sprinklers for lithium-ion storage or reduce storage to within the 20 ft design basis",
                                                     "severity": "CRITICAL", "due": _plus(rt, 45), "status": "OPEN", "bind_condition": True, "completion_evidence": None, "closed_on": None}
                new_recs.append(rid)
        if s.get("sprinkler_pct") is not None:
            pairs.append(("Sprinkler protection", f"{s['sprinkler_pct'] * 100:.0f}% of area"))
        if pairs:
            p.kv(pairs, cols=2, label_w=150)
    for rec in rt.recs.get(acct, {}).values():
        if rec["status"] == "CLOSED" and rec.get("completion_evidence"):
            rec["status"] = "VERIFIED_CLOSED"
            rec["completion_evidence"] = rec["completion_evidence"].replace("awaiting engineering verification", f"verified on site {rt.clock}")
            verified.append(rec["rec_id"])
    if verified or new_recs:
        p.section("Recommendations")
        rows = [(r, "Verified complete on site", "—") for r in verified] + [(r, rt.recs[acct][r]["description"][:70], "Critical") for r in new_recs]
        p.table(["Rec #", "Outcome / recommendation", "Priority"], rows, [60, 360, 80])
    p.save()
    doc = rt.add_runtime_doc(acct, did, "Engineering report", f"Risk engineering report — {rt.clock}", "pdf", path, "Engineering (mock)")
    I.ingest_document(rt, doc, "engineering", rt.clock)
    detail = (f"Verified: {', '.join(verified)}. " if verified else "") + (f"New critical recommendation {', '.join(new_recs)}." if new_recs else "")
    rt.log(acct, "system", "05", "Engineering visit report received", detail or "No change", "Engineering (mock)", did)
    for rid in new_recs:
        rt.log(acct, "system", "05", f"Recommendation {rid} raised (critical)", rt.recs[acct][rid]["description"], "Engineering (mock)")


def verify_rec(rt, acct, rec_id, uid):
    rec = rt.recs[acct][rec_id]
    rec["status"] = "VERIFIED_CLOSED"
    rec["completion_evidence"] = (rec.get("completion_evidence") or "Desk review") + f" · verified by {USER_BY_ID[uid]['name']} {rt.clock}"
    rt.log(acct, "user", "05", f"Recommendation {rec_id} verified closed", rec["completion_evidence"], USER_BY_ID[uid]["name"])


# ============================================================================ issuance: billing & corrective endorsement
def bill(rt, acct, premium: float):
    inv = {"invoice_no": _nid(rt, "INV-2026-"), "amount": premium, "issued": rt.clock, "due": _plus(rt, 30), "status": "OPEN"}
    _st(rt)["billing"][acct] = inv
    rt.log(acct, "mock", "11", "Premium invoiced (mock billing)", f"{inv['invoice_no']} · {money(premium)} due {inv['due']}", "Billing (mock)")
    return inv


def correct_issuance(rt: "Runtime", acct: str, uid: str) -> str:
    from uwc.engine.evaluate import contract_diffs, contract_views, evaluate_account
    labels = {u: e.label for u, e in rt.store.account_locations(acct).items()}
    views = contract_views(rt, acct, renewal=True)
    diffs = [d for d in contract_diffs(views, labels) if d["pair"] == "binder_policy"]
    if not diffs:
        return "Issued policy already matches the binder"
    did, path, p = _pdf(rt, acct, "endt", "Corrective Endorsement", "carrier")
    p.title("Corrective Endorsement", f"Effective {rt.ren[acct].r_bound['date']} · issued {rt.clock}")
    p.kv([("Endorsement number", did.upper()), ("Reason", "Correct issuance to match the bound terms")], cols=1, label_w=150)
    p.section("Corrected terms")
    from uwc.ingest.interpret import CONTRACT_KV
    rev = {v[0]: k for k, v in CONTRACT_KV.items()}
    pairs = []
    for d in diffs:
        if d["field"] in rev:
            pairs.append((rev[d["field"]], d["a"]))
    p.kv(pairs, cols=1, label_w=170)
    p.save()
    doc = rt.add_runtime_doc(acct, did, "Endorsement", "Corrective endorsement", "pdf", path, "PAS (mock)")
    # the endorsement restates the corrected fields on the issued policy; later observations supersede the mis-keyed ones
    I.ingest_document(rt, doc, "policy", rt.clock, {"stage": "r_policy", "term": "current"})
    rt.ren[acct].r_issued["corrected"] = {"date": rt.clock, "doc_id": did}
    rt.log(acct, "user", "11", "Corrective endorsement issued", "; ".join(f"{d['label']} → {d['a']}" for d in diffs), USER_BY_ID[uid]["name"], did)
    evaluate_account(rt, acct)
    return f"Corrective endorsement {did.upper()} restores {', '.join(d['label'] for d in diffs)}"


# ============================================================================ presenter-triggered in-force events
def presenter_event(rt: "Runtime", acct: str, kind: str, params: dict, uid: str) -> str:
    from uwc.engine.evaluate import evaluate_account
    locs = rt.store.account_locations(acct)
    uid_loc = params.get("location_uid") or next(iter(locs))
    loc = locs[uid_loc]
    who = USER_BY_ID[uid]["name"]
    if kind == "claim":
        cid = _nid(rt, "CLM-26-P")
        amt = float(params.get("amount", 250000))
        cause = params.get("cause", "fire")
        c = {"claim_id": cid, "location_key": None, "location_uid": uid_loc, "location_address": loc.address, "dol": rt.clock, "cause": cause, "paid": 0.0,
             "reserve": amt, "status": "OPEN", "description": params.get("description") or f"{cause.replace('_', ' ').title()} loss reported at {loc.label}",
             "cat_event": None, "report_date": rt.clock, "linked_rec": None}
        rt.claims.setdefault(acct, []).append(c)
        I._obs(rt, acct, "claim", f"{acct}:{cid}", "incurred", amt, "S", "Carrier systems", "Claims system (mock)", rt.clock,
               {"doc_id": None, "kind": "system", "system": "Claims (mock)", "record_id": cid}, None, 0.99)
        rt.log(acct, "system", "12", f"Claim {cid} reported ({cause.replace('_', ' ')})", f"{loc.label} · reserve {money(amt)}", "Claims (mock)")
        msg = f"Claim {cid} reported at {loc.label} ({money(amt)} reserve)"
    elif kind == "impairment":
        I._obs(rt, acct, "location", uid_loc, "sprinkler_impaired", True, "V", "Engineering", "Impairment notice (presenter)", rt.clock,
               {"doc_id": None, "kind": "system", "system": "Engineering (mock)", "record_id": "impairment"}, None, 0.97)
        rt.log(acct, "system", "12", "Sprinkler impairment reported", loc.label, "Engineering (mock)")
        msg = f"Sprinkler impairment recorded at {loc.label}"
    elif kind == "vacancy":
        pct = float(params.get("vacancy_pct", 0.6))
        since = params.get("since") or (rt.clock_date - timedelta(days=75)).isoformat()
        anc = {"doc_id": None, "kind": "system", "system": "PAS (mock)", "record_id": "endorsement"}
        I._obs(rt, acct, "location", uid_loc, "vacancy_pct", pct, "S", "Carrier systems", "Vacancy endorsement (presenter)", rt.clock, anc, None, 0.99)
        I._obs(rt, acct, "location", uid_loc, "vacancy_since", since, "S", "Carrier systems", "Vacancy endorsement (presenter)", rt.clock, anc, None, 0.99)
        rt.log(acct, "system", "12", "Vacancy endorsement", f"{loc.label} {pct * 100:.0f}% vacant since {since}", "PAS (mock)")
        msg = f"Vacancy of {pct * 100:.0f}% recorded at {loc.label}"
    else:
        raise ValueError(f"Unknown event kind {kind}")
    rt._event_driven(acct, msg) if rt.ren[acct].pass_no == 0 else evaluate_account(rt, acct)
    return msg + f" — account re-evaluated ({who})"

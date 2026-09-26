"""Per-stage workspaces for the 15-stage pipeline.

`build(rt, code, acct)` returns what that stage's system (real or mock) holds for one
account right now; `run(rt, code, acct)` performs that stage's step so an account can
be walked through the whole lifecycle one stage at a time.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from uwc.engine.evaluate import evaluate_account
from uwc.refdata import AUTHORITY, CONSTRUCTION, OCCUPANCY, USER_BY_ID, ZONES, guideline_for

if TYPE_CHECKING:
    from uwc.runtime import Runtime

STANDS_IN = {
    "01": "Broker email / broker portal", "02": "Clearance & compliance services", "03": "Anaira rule engine", "04": "Anaira ingestion + Precisely / HazardHub / 360Value / Nearmap",
    "05": "Risk engineering platform", "06": "hx Renew / carrier rater · Moody's RMS / Verisk", "07": "Anaira authority & accumulation", "08": "Underwriting workbench quote builder",
    "09": "Broker negotiation", "10": "Workbench bind flow", "11": "Guidewire PolicyCenter / Duck Creek", "12": "PolicyCenter endorsements · ClaimCenter FNOL",
    "13": "Anaira outcome capture", "14": "Anaira book view", "15": "Anaira renewal engine",
}
SANCTIONS_FIXTURE = ["Volkov Trading LLC", "Orion Maritime Holdings", "Karsk Industrial Group"]


def col(key: str, label: str, kind: str = "text") -> dict:
    return {"key": key, "label": label, "kind": kind}


def _events(rt, acct, stages: set[str]) -> list[dict]:
    return [e for e in reversed(rt.ren[acct].timeline) if e["stage"] in stages][:40]


def _docs(rt, acct, types: set[str]) -> list[dict]:
    from uwc.api import doc_meta
    out = [doc_meta(d) for d in rt.store.docs.values() if d.get("account_id") == acct and d["doc_type"] in types]
    return sorted(out, key=lambda d: d["received_at"], reverse=True)


def _next_event(rt, acct, types: tuple[str, ...], role: str | None = None) -> dict | None:
    for e in rt.events[rt.applied:]:
        if e.get("account_id") == acct and e["type"] in types and (role is None or e.get("payload", {}).get("role") == role or e.get("payload", {}).get("kind") == role):
            return e
    return None


def _latest_quote(ren) -> dict | None:
    return ren.quotes[-1] if ren.quotes else None


def build(rt: "Runtime", code: str, acct: str) -> dict:
    from uwc.api import PIPE, finding_payload, money
    meta = next(p for p in PIPE if p[0] == code)
    reg = rt.systems["accounts"][acct]
    ren = rt.ren[acct]
    pas = rt.pas[acct]
    r = ren.rarc or {}
    locs = rt.store.account_locations(acct)
    labels = {u: e.label for u, e in locs.items()}
    v: dict[str, Any] = {"code": code, "name": meta[1], "group": meta[2], "component": meta[3], "mode": meta[4], "description": meta[5], "port": meta[6],
                         "stands_in_for": STANDS_IN[code], "account": {"account_id": acct, "name": reg["name"], "scenario": reg.get("scenario")},
                         "clock": rt.clock, "status": "PENDING", "headline": "", "kpis": [], "tables": [], "documents": [], "events": [], "findings": [],
                         "next_action": None}
    fs = lambda *fam: [finding_payload(f) for f in ren.findings.values() if f["family"] in fam and f["status"] != "RESOLVED"]

    if code == "01":
        emails = [d for d in rt.store.docs.values() if d.get("account_id") == acct and d["doc_type"] == "Broker email"]
        rows = [{"date": d["received_at"], "subject": d["title"], "attachments": len(d.get("attachments", [])), "doc": d["doc_id"]} for d in sorted(emails, key=lambda d: d["received_at"])]
        sub = [d for d in emails if d["term"] == "current"]
        v["status"] = "DONE" if rt.renewal_sov.get(acct) else "READY"
        v["headline"] = (f"Renewal submission received {rt.store.docs[rt.renewal_sov[acct]]['received_at']} with the renewal SOV attached" if rt.renewal_sov.get(acct)
                         else "Waiting for the broker's renewal submission")
        v["kpis"] = [{"label": "Broker emails", "value": str(len(emails))}, {"label": "Attachments", "value": str(sum(r_["attachments"] for r_ in rows))},
                     {"label": "Broker", "value": reg["broker"]}, {"label": "Contact", "value": reg["broker_contact"]}]
        v["tables"] = [{"title": "Mailbox — submissions for this account", "columns": [col("date", "Received", "date"), col("subject", "Subject"), col("attachments", "Attachments"), col("doc", "Open", "doc")], "rows": rows}]
        v["documents"] = _docs(rt, acct, {"Broker email", "SOV", "Certificate", "Appraisal"})
        v["events"] = _events(rt, acct, {"01"})
        nxt = _next_event(rt, acct, ("doc.received",), "email")
        if nxt:
            v["next_action"] = {"label": f"Advance clock to {nxt['date']} — {nxt['title']}", "description": "Replays the mailbox up to the next broker email for this account; attachments are ingested automatically."}
    elif code == "02":
        from uwc import fulfilment as F
        c = F.clearance(rt, acct)
        rows = c["checks"][:1] + [{"check": "Existing in-force policy", "result": "PASS", "detail": f"Linked to {pas.get('policy_no') or rt.systems['pas'][acct]['policy_no']} (renewal)"}] + c["checks"][1:]
        v["status"] = "DONE" if c["status"] == "CLEARED" else "READY"
        v["headline"] = "Cleared — no duplicates, broker licensed in every location state, sanctions clear" if c["status"] == "CLEARED" else f"HOLD — {c['reason']}. Quoting is blocked until resolved."
        v["kpis"] = [{"label": "Clearance", "value": c["status"], "tone": "ok" if c["status"] == "CLEARED" else "crit"}, {"label": "Checks", "value": str(len(rows))},
                     {"label": "Passed", "value": str(sum(1 for x in rows if x["result"] == "PASS")), "tone": "ok"}, {"label": "FEIN", "value": reg["fein"]}]
        v["tables"] = [{"title": "Clearance checks (mock clearance service · licence table · screening list)", "columns": [col("check", "Check"), col("result", "Result", "badge"), col("detail", "Detail")], "rows": rows}]
        v["events"] = _events(rt, acct, {"02"})
        if c["status"] == "HOLD":
            v["next_action"] = {"label": "Request the renewed licence from the broker", "description": "Sends a data request; the broker returns the licence certificate in 3 days and clearance is re-screened automatically."}
    elif code == "03":
        g = guideline_for(rt.clock_date)
        app = fs("appetite", "data_completeness")
        v["status"] = "DONE" if ren.pass_no else "PENDING"
        declined = any(f["family"] == "appetite" for f in app)
        v["headline"] = (f"{OCCUPANCY.get(reg['occupancy_family'], ('—',))[0]} — " + ("DECLINED under guidelines " + g["version"] if declined else "in appetite under guidelines " + g["version"]))
        v["kpis"] = [{"label": "Guidelines in force", "value": g["version"]}, {"label": "Class", "value": OCCUPANCY.get(reg["occupancy_family"], ("—",))[0]},
                     {"label": "Appetite", "value": "Declined" if declined else "In appetite", "tone": "crit" if declined else "ok"},
                     {"label": "Rules evaluated", "value": str(sum(1 for x in rt.rules.values() if x.active(rt.clock)))}]
        rows = [{"rule": x.rule_id, "title": x.title, "origin": x.origin.replace("_", " "), "version": x.version,
                 "result": next((f["outcome"] for f in ren.findings.values() if f["rule_id"] == x.rule_id and f["status"] != "RESOLVED"), "PASS")}
                for x in rt.rules.values() if x.family in ("appetite", "data_completeness", "classification")]
        v["tables"] = [{"title": "Appetite & triage rules", "columns": [col("rule", "Rule", "mono"), col("title", "Rule"), col("origin", "Origin"), col("version", "v"), col("result", "Result", "badge")], "rows": rows}]
        v["findings"] = app
        v["events"] = _events(rt, acct, {"03"}) + [e for e in rt.global_log if e["stage"] == "03"][-3:]
    elif code == "04":
        from uwc.api import doc_meta
        drows = []
        for d in sorted((x for x in rt.store.docs.values() if x.get("account_id") == acct and x["format"] in ("pdf", "xlsx", "eml")), key=lambda x: x["received_at"]):
            m = doc_meta(d)
            if not m["extraction"] or not m["extraction"]["fields"]:
                continue
            drows.append({"doc": d["doc_id"], "type": d["doc_type"], "title": d["title"], "fields": m["extraction"]["fields"], "confidence": m["extraction"]["avg_confidence"],
                          "issues": len(rt.store.doc_issues.get(d["doc_id"], []))})
        lrows = []
        for u, e in locs.items():
            s = ren.loc_ctx.get(u, {})
            lrows.append({"location": e.label, "geocode": e.geocode_level or "—", "zone": ZONES.get(s.get("cat_zone"), ("—",))[0] if s.get("cat_zone") else "—",
                          "wind": s.get("wind_tier") or "—", "flood": s.get("flood_zone") or "—", "model_rc": s.get("model_rc"), "burglary": s.get("burglary_score"),
                          "match": e.match_status, "method": e.match_method or "—"})
        n_obs = sum(1 for _ in rt.store.account_obs(acct))
        v["status"] = "DONE" if drows else "PENDING"
        v["headline"] = f"{len(drows)} documents extracted into {n_obs:,} anchored observations; {len(lrows)} locations geocoded and enriched"
        v["kpis"] = [{"label": "Observations", "value": f"{n_obs:,}"}, {"label": "Documents extracted", "value": str(len(drows))},
                     {"label": "Locations", "value": str(len(lrows))}, {"label": "Needs review", "value": str(sum(1 for e in locs.values() if e.match_status == "AMBIGUOUS")), "tone": "high"}]
        v["tables"] = [{"title": "Extraction — every value keeps its cell / page anchor", "columns": [col("type", "Type"), col("title", "Document"), col("fields", "Fields"), col("confidence", "Avg conf.", "pct"), col("issues", "Issues"), col("doc", "Open", "doc")], "rows": drows},
                       {"title": "Enrichment & location matching (vendor mocks)", "columns": [col("location", "Location"), col("match", "Match", "badge"), col("method", "Method", "mono"), col("geocode", "Geocode"), col("zone", "CAT zone"), col("wind", "Wind"), col("flood", "Flood"), col("model_rc", "Modelled RC", "money"), col("burglary", "Burglary")], "rows": lrows}]
        v["documents"] = _docs(rt, acct, {"Vendor payload", "Aerial imagery", "3D site model"})
        v["findings"] = fs("data_integrity", "sov_integrity")
        v["events"] = _events(rt, acct, {"04", "01"})
    elif code == "05":
        rrows = [{"rec": x["rec_id"], "location": labels.get(x.get("location_uid"), ""), "category": x["category"], "severity": x["severity"], "due": x["due"], "status": x["status"],
                  "bind": "Yes" if x["bind_condition"] else "", "evidence": x.get("completion_evidence") or "—"} for x in rt.recs.get(acct, {}).values()]
        overdue = [x for x in rt.recs.get(acct, {}).values() if x["status"] in ("OPEN", "IN_PROGRESS") and x["due"] < rt.clock]
        v["status"] = "DONE" if rrows or _docs(rt, acct, {"Engineering report"}) else "NOT_APPLICABLE"
        v["headline"] = f"{len(rrows)} recommendations on the register · {len(overdue)} overdue" if rrows else "No engineering recommendations on file"
        v["kpis"] = [{"label": "Surveys", "value": str(len(_docs(rt, acct, {'Engineering report'})))}, {"label": "Recommendations", "value": str(len(rrows))},
                     {"label": "Overdue", "value": str(len(overdue)), "tone": "crit" if overdue else "ok"}]
        v["tables"] = [{"title": "Recommendation register (mock engineering system)", "columns": [col("rec", "Rec", "mono"), col("location", "Location"), col("category", "Category"), col("severity", "Severity", "badge"), col("due", "Due", "date"), col("status", "Status", "badge"), col("bind", "Bind condition"), col("evidence", "Completion evidence")], "rows": rrows}]
        v["documents"] = _docs(rt, acct, {"Engineering report", "Certificate"})
        v["findings"] = fs("engineering", "fire", "security", "protective_safeguards", "construction", "vacancy")
        pend = [e for e in rt.dynamic if e.get("account_id") == acct and e["type"] == "eng.visit" and not e.get("done")]
        if pend:
            v["headline"] += f" · site visit scheduled {pend[0]['date']}"
        v["events"] = _events(rt, acct, {"05"})
        if not pend:
            v["next_action"] = {"label": "Order a verification survey", "description": "Schedules a risk-engineer visit (+7 days). The report is ingested as verified (V) evidence, closes recommendations with completion evidence and can raise new ones."}
    elif code == "06":
        v["status"] = "DONE" if r else "PENDING"
        if r:
            v["headline"] = f"Technical {money(r['tp_e0_t0'])} → {money(r['tp_e1_t1'])} · exposure ×{r['exposure_factor']:.3f} · terms ×{r['terms_factor']:.3f} · RARC {r['rarc'] * 100:+.1f}%"
            v["kpis"] = [{"label": "TP(E0,T0)", "value": money(r["tp_e0_t0"], full=True)}, {"label": "TP(E1,T0)", "value": money(r["tp_e1_t0"], full=True)},
                         {"label": "TP(E1,T1)", "value": money(r["tp_e1_t1"], full=True)}, {"label": "RARC", "value": f"{r['rarc'] * 100:+.1f}%", "tone": "crit" if r["rarc"] < -0.05 else "ok"}]
            v["tables"].append({"title": f"Rater — three controlled runs ({r['model_version']})", "columns": [col("component", "Component"), col("e0t0", "TP(E0,T0)", "money"), col("e1t0", "TP(E1,T0)", "money"), col("e1t1", "TP(E1,T1)", "money")], "rows": r["breakdown"]})
        runs = rt.cat_runs.get(acct, [])
        v["tables"].append({"title": "CAT model runs (MockCat)", "columns": [col("snapshot", "Snapshot", "badge"), col("run_date", "Run", "date"), col("aal", "AAL", "money"), col("oep100", "OEP 1-in-100", "money"), col("oep250", "OEP 1-in-250", "money"), col("doc", "EP curve", "doc")],
                            "rows": [{"snapshot": x["snapshot"], "run_date": x["run_date"], "aal": x["result"]["aal_total"], "oep100": next((o["loss"] for o in x["result"]["oep"] if o["rp"] == 100), 0),
                                      "oep250": next((o["loss"] for o in x["result"]["oep"] if o["rp"] == 250), 0), "doc": x["ep_doc_id"]} for x in runs]})
        v["documents"] = _docs(rt, acct, {"CAT exposure file", "CAT event loss table", "CAT EP curve"})
        v["findings"] = fs("pricing", "cat_integrity", "valuation")
        v["events"] = _events(rt, acct, {"06"})
        v["next_action"] = {"label": "Re-run rater and CAT on the current evidence", "description": "Rebuilds E0/E1 snapshots and reruns the three technical runs and both CAT runs."}
    elif code == "07":
        q = _latest_quote(ren)
        pending = [x for x in ren.referrals if x["status"] == "PENDING"]
        v["status"] = "DONE" if (q and (not q["needs_referral"] or any(x["status"] == "APPROVED" and x["terms_hash"] == q["terms_hash"] for x in ren.referrals))) else ("READY" if q else "PENDING")
        v["headline"] = (f"Working proposal needs L{r.get('required_authority_level')} authority" if r else "No pricing yet") + (f" · {len(pending)} referral pending" if pending else "")
        a = ren.acct_ctx or {}
        v["kpis"] = [{"label": "Required authority", "value": f"L{r.get('required_authority_level', 1)}", "tone": "high" if r.get("required_authority_level", 1) > 1 else "ok"},
                     {"label": "Underwriter", "value": f"{USER_BY_ID[reg['underwriter_id']]['name']} · L{USER_BY_ID[reg['underwriter_id']]['authority_level']}"},
                     {"label": "Zone (post-renewal)", "value": f"{a.get('zone_name') or '—'} {a.get('zone_util_post', 0) * 100:.1f}%", "tone": "crit" if a.get("zone_util_post", 0) > 0.9 else "ok"}]
        v["tables"] = [{"title": "Why this level", "columns": [col("reason", "Reason")], "rows": [{"reason": x} for x in r.get("authority_reasons", [])]},
                       {"title": "Referrals (approvals locked to a terms hash)", "columns": [col("id", "Referral", "mono"), col("level", "Level"), col("by", "Requested by"), col("status", "Status", "badge"), col("approver", "Approver"), col("hash", "Terms hash", "mono"), col("note", "Note")],
                        "rows": [{"id": x["referral_id"], "level": f"L{x['required_level']}", "by": x["requested_by"], "status": x["status"], "approver": x.get("approver") or "—", "hash": x.get("terms_hash") or "—", "note": x.get("invalidated_reason") or x.get("conditions") or ""} for x in ren.referrals]}]
        v["findings"] = fs("authority", "accumulation", "appetite")
        v["events"] = _events(rt, acct, {"07"})
        if not q and r and not ren.r_bound:
            v["next_action"] = {"label": "Draft the working quote so authority can be checked", "description": "Authority is checked on the intended terms — this drafts the quote (stage 08) and re-checks."}
        elif q and q["needs_referral"] and not pending and not any(x["status"] == "APPROVED" and x["terms_hash"] == q["terms_hash"] for x in ren.referrals):
            v["next_action"] = {"label": f"Refer quote v{q['version']} to L{q['required_level']}", "description": "Creates a referral memo citing the evidence; routed to the referral queue."}
        elif pending:
            appr = _approver(pending[0]["required_level"])
            v["next_action"] = {"label": f"Approve as {USER_BY_ID[appr]['name']} (L{USER_BY_ID[appr]['authority_level']})", "description": "Approval is locked to the referred terms hash."}
    elif code == "08":
        rows = [{"v": q["version"], "created": q["created_at"], "by": q["created_by"], "premium": q["premium"], "rarc": q["rarc"], "adequacy": q["adequacy"], "status": q["status"], "hash": q["terms_hash"], "doc": q["doc_id"]} for q in ren.quotes]
        v["status"] = "DONE" if ren.quotes else ("READY" if r else "PENDING")
        v["headline"] = f"{len(ren.quotes)} renewal quote version(s)" if ren.quotes else "No renewal quote drafted yet"
        v["kpis"] = [{"label": "Expiring premium", "value": money(pas.get("premium"), full=True)}, {"label": "Technical (proposed terms)", "value": money(r.get("tp_e1_t1"), full=True)},
                     {"label": "Broker target", "value": money(rt.account_value(acct, "target_premium"), full=True) if rt.account_value(acct, "target_premium") else "—"}]
        v["tables"] = [{"title": "Quote versions (terms editor → quote PDF)", "columns": [col("v", "v"), col("created", "Created", "date"), col("by", "By"), col("premium", "Premium", "money"), col("rarc", "RARC", "pct"), col("adequacy", "Adequacy", "pct"), col("status", "Status", "badge"), col("hash", "Terms hash", "mono"), col("doc", "PDF", "doc")], "rows": rows}]
        v["documents"] = _docs(rt, acct, {"Quote"})
        v["events"] = _events(rt, acct, {"08"})
        if r and not ren.r_bound:
            prem = _suggested_premium(rt, acct)
            v["next_action"] = {"label": f"Draft quote at {money(prem, full=True)} on guideline-compliant terms", "description": "Premium = max(broker target, 95% of technical); named-storm deductible and minimum set to the guideline floors."}
    elif code == "09":
        q = _latest_quote(ren)
        msgs = [m for m in rt.outbox if m.get("account_id") == acct]
        v["status"] = "DONE" if q and q["status"] in ("ACCEPTED", "BOUND") else ("READY" if q else "PENDING")
        v["headline"] = (f"Quote v{q['version']} {q['status'].lower()}" + (f" · broker countered at {money(q['broker_counter'], full=True)}" if q.get("broker_counter") else "")) if q else "Nothing sent to the broker yet"
        v["tables"] = [{"title": "Broker bot — messages", "columns": [col("at", "Date", "date"), col("to", "To"), col("subject", "Subject"), col("body", "Body")], "rows": [{"at": m["at"], "to": m["to"], "subject": m["subject"], "body": m["body"][:160]} for m in msgs]}]
        v["events"] = _events(rt, acct, {"09"})
        if q and q["status"] in ("DRAFT", "APPROVED") and (not q["needs_referral"] or q["status"] == "APPROVED"):
            v["next_action"] = {"label": f"Send quote v{q['version']} to {reg['broker']}", "description": "Emails the quote; the broker bot replies after 4 days."}
        elif q and q["status"] == "SENT":
            v["next_action"] = {"label": "Advance 5 days for the broker's reply", "description": "Broker bot accepts adequately priced quotes and counters otherwise."}
    elif code == "10":
        v["status"] = "DONE" if ren.r_bound else "READY" if any(q["status"] == "ACCEPTED" for q in ren.quotes) else "PENDING"
        v["headline"] = f"Bound {ren.r_bound['date']} at {money(ren.r_bound['premium'], full=True)}" + ("" if ren.r_bound["authority_valid"] else " — without valid approval") if ren.r_bound else "Not bound"
        prior = [{"term": "Expiring", "date": pas.get("bind_date"), "premium": pas.get("premium"), "doc": rt.systems["pas"][acct]["binder"]["doc_id"]}]
        if ren.r_bound:
            prior.append({"term": "Renewal", "date": ren.r_bound["date"], "premium": ren.r_bound["premium"], "doc": f"{acct}_r_binder"})
        v["tables"] = [{"title": "Binders", "columns": [col("term", "Term"), col("date", "Bound", "date"), col("premium", "Premium", "money"), col("doc", "Binder", "doc")], "rows": prior}]
        from uwc import fulfilment as F
        subj = F.renewal_subjectivities(rt, acct)
        if subj:
            v["tables"].append({"title": "Renewal subjectivities (from approval conditions · printed on the binder)", "columns": [col("text", "Subjectivity"), col("raised", "Raised", "date"), col("status", "Status", "badge"), col("evidence", "Cleared by", "doc")],
                                "rows": [dict(x, evidence=x["evidence"] or "—") for x in subj]})
        v["documents"] = _docs(rt, acct, {"Binder"})
        v["findings"] = [finding_payload(f) for f in ren.findings.values() if f["pass"] == 3 and f["status"] != "RESOLVED"]
        v["events"] = _events(rt, acct, {"10"})
        if any(q["status"] == "ACCEPTED" for q in ren.quotes) and not ren.r_bound:
            v["next_action"] = {"label": "Bind the accepted quote", "description": "Generates the binder, re-checks authority on the bound terms and runs Pass 3 (quote ↔ binder)."}
    elif code == "11":
        v["status"] = "DONE" if ren.r_issued else "READY" if ren.r_bound else "PENDING"
        v["headline"] = (f"Issued {ren.r_issued['date']} — {ren.r_issued['injected'] or 'as bound'}" if ren.r_issued else "Not issued")
        v["kpis"] = [{"label": "Issuance-error injection", "value": "ON" if rt.injections.get("issuance_error") else "OFF", "tone": "high" if rt.injections.get("issuance_error") else "ok"},
                     {"label": "Policy number", "value": pas.get("policy_no") or "—"}]
        rows = [{"term": "Expiring", "policy": pas.get("policy_no"), "issued": rt.systems["pas"][acct]["issued"]["date"], "doc": rt.systems["pas"][acct]["issued"]["doc_id"]}]
        if ren.r_issued:
            rows.append({"term": "Renewal", "policy": (pas.get("policy_no") or "").replace("2025", "2026"), "issued": ren.r_issued["date"], "doc": ren.r_issued["doc_id"]})
        v["tables"] = [{"title": "Policy records (mock PAS)", "columns": [col("term", "Term"), col("policy", "Policy", "mono"), col("issued", "Issued", "date"), col("doc", "Declarations", "doc")], "rows": rows}]
        from uwc import fulfilment as F
        inv = F._st(rt)["billing"].get(acct)
        if inv:
            v["kpis"].append({"label": "Invoice", "value": f"{inv['invoice_no']} · {money(inv['amount'], full=True)}"})
        if ren.r_issued and ren.r_issued.get("corrected"):
            v["headline"] += f" · corrected by endorsement {ren.r_issued['corrected']['date']}"
            rows.append({"term": "Renewal — corrective endorsement", "policy": (pas.get("policy_no") or "").replace("2025", "2026"), "issued": ren.r_issued["corrected"]["date"], "doc": ren.r_issued["corrected"]["doc_id"]})
        v["documents"] = _docs(rt, acct, {"Declarations", "Endorsement"})
        v["findings"] = fs("contract_integrity")
        v["events"] = _events(rt, acct, {"11"})
        if ren.r_issued and not ren.r_issued.get("corrected") and any(f["rule_id"] == "CONTRACT.BINDER_POLICY" and f["status"] == "OPEN" for f in ren.findings.values()):
            v["next_action"] = {"label": "Issue a corrective endorsement", "description": "Restates the mis-keyed terms on the issued policy; Pass 3 re-runs and the binder ↔ policy finding resolves."}
        if ren.r_bound and not ren.r_issued:
            v["next_action"] = {"label": "Issue the renewal policy (mock PAS)", "description": "With injection ON the mock PAS keys one term incorrectly; Pass 3 compares binder ↔ issued policy."}
    elif code == "12":
        endts = pas.get("endorsements_applied", [])
        rows = [{"date": e["effective"], "kind": "Endorsement", "detail": f"{e['endt_id']} · {e['type']} — {e['description']}"} for e in endts]
        rows += [{"date": c["report_date"] or c["dol"], "kind": "Claim (FNOL)", "detail": f"{c['claim_id']} · {c['cause'].replace('_', ' ')} · ${c['paid'] + c['reserve']:,.0f}"} for c in rt.claims.get(acct, []) if c["dol"] >= (pas.get("term_start") or "")]
        rows += [{"date": e["date"], "kind": "Event-driven re-evaluation", "detail": e["title"]} for e in ren.timeline if e["title"].startswith("Event-driven")]
        v["status"] = "DONE" if rows else "NOT_APPLICABLE"
        v["headline"] = f"{len(rows)} mid-term event(s) this term"
        v["tables"] = [{"title": "In-force events (PAS endorsements · claims FNOL · impairments)", "columns": [col("date", "Date", "date"), col("kind", "Kind", "badge"), col("detail", "Detail")], "rows": sorted(rows, key=lambda x: x["date"])}]
        v["findings"] = fs("vacancy", "claims")
        v["events"] = _events(rt, acct, {"12"})
        nxt = _next_event(rt, acct, ("pas.endorsement", "eng.impairment", "claims.fnol", "vendor.imagery"))
        if nxt:
            v["next_action"] = {"label": f"Advance to {nxt['date']} — {nxt['title']}", "description": "Replays the next in-force event; the engine re-evaluates the account immediately."}
    elif code == "13":
        cl = rt.claims.get(acct, [])
        rows = [{"claim": c["claim_id"], "dol": c["dol"], "location": labels.get(c.get("location_uid"), "—"), "cause": c["cause"].replace("_", " "), "incurred": c["paid"] + c["reserve"], "rec": c.get("linked_rec") or "—"} for c in cl]
        v["status"] = "DONE"
        v["headline"] = f"{len(cl)} claims linked to locations and fed into risk-quality deltas"
        v["kpis"] = [{"label": "Claims", "value": str(len(cl))}, {"label": "Incurred", "value": money(sum(c["paid"] + c["reserve"] for c in cl), full=True)},
                     {"label": "Linked to open recs", "value": str(sum(1 for c in cl if c.get("linked_rec"))), "tone": "high"}]
        v["tables"] = [{"title": "Claims (mock claims system → outcome capture)", "columns": [col("claim", "Claim", "mono"), col("dol", "Loss date", "date"), col("location", "Location"), col("cause", "Cause"), col("incurred", "Incurred", "money"), col("rec", "Linked rec", "mono")], "rows": rows}]
        v["findings"] = fs("claims", "engineering")
        v["documents"] = _docs(rt, acct, {"Loss run"})
        v["events"] = _events(rt, acct, {"13"})
    elif code == "14":
        zc = rt.zone_contrib.get(acct, {})
        rows = []
        for z in set(zc.get("prior", {})) | set(zc.get("current", {})):
            rows.append({"zone": ZONES[z][0], "peril": ZONES[z][1], "prior": zc.get("prior", {}).get(z, 0), "current": zc.get("current", {}).get(z, 0),
                         "util": rt.zone_total(z, "current") / ZONES[z][5]})
        v["status"] = "DONE" if ren.pass_no else "PENDING"
        v["headline"] = "Account's contribution to CAT-zone accumulation (1-in-250 PML, carrier share)"
        v["tables"] = [{"title": "Zone contribution", "columns": [col("zone", "Zone"), col("peril", "Peril"), col("prior", "As bound", "money"), col("current", "After renewal", "money"), col("util", "Zone utilisation", "pct")], "rows": rows}]
        v["findings"] = fs("accumulation")
        v["events"] = _events(rt, acct, {"14"})
    elif code == "15":
        rows = [{"pass": f"Pass {k}", "name": {1: "Internal drift (T-150)", 2: "Submission delta", 3: "Contract integrity"}[int(k)], "date": d} for k, d in sorted(ren.pass_dates.items())]
        v["status"] = "DONE" if ren.pass_no >= 3 else "READY" if ren.pass_no else "PENDING"
        v["headline"] = f"Pass {ren.pass_no} of 3 · status {ren.status.replace('_', ' ').lower()} · integrity {ren.integrity:.0f}"
        v["kpis"] = [{"label": "Pass", "value": f"{ren.pass_no} / 3"}, {"label": "Integrity", "value": f"{ren.integrity:.0f}"},
                     {"label": "Material findings", "value": str(sum(1 for f in ren.findings.values() if f["material"] and f["status"] != "RESOLVED"))},
                     {"label": "Actions", "value": ", ".join(a.replace("_", " ").lower() for a in ren.recommended_actions) or "—"}]
        v["tables"] = [{"title": "Renewal passes", "columns": [col("pass", "Pass"), col("name", "Name"), col("date", "Run", "date")], "rows": rows},
                       {"title": "Actions", "columns": [col("type", "Action", "badge"), col("title", "Title"), col("impact", "$ impact", "money"), col("due", "Due", "date")],
                        "rows": [{"type": a["type"], "title": a["title"], "impact": a["impact_usd"], "due": a["due"]} for a in ren.actions]}]
        v["events"] = _events(rt, acct, {"15"})
        v["next_action"] = {"label": "Re-evaluate the account now", "description": "Runs the rule library against the current evidence and records any changes."}
    return v


def _approver(level: int) -> str:
    for uid in ("u_daniel", "u_priya", "u_robert"):
        if USER_BY_ID[uid]["authority_level"] >= level:
            return uid
    return "u_robert"


def _suggested_premium(rt, acct) -> float:
    r = rt.ren[acct].rarc or {}
    tgt = rt.account_value(acct, "target_premium") or 0
    return round(max(tgt, 0.95 * (r.get("tp_e1_t1") or 0), rt.pas[acct].get("premium") or 0) / 1000) * 1000


def run(rt: "Runtime", code: str, acct: str) -> str:
    ren = rt.ren[acct]
    reg = rt.systems["accounts"][acct]
    uw = reg["underwriter_id"]
    if code == "01":
        nxt = _next_event(rt, acct, ("doc.received",), "email")
        if not nxt:
            return "No further broker emails scheduled for this account"
        rt.advance_to(nxt["date"])
        return f"Clock advanced to {nxt['date']}: {nxt['title']}"
    if code == "12":
        nxt = _next_event(rt, acct, ("pas.endorsement", "eng.impairment", "claims.fnol", "vendor.imagery"))
        if not nxt:
            return "No further in-force events scheduled"
        rt.advance_to(nxt["date"])
        return f"Clock advanced to {nxt['date']}: {nxt['title']}"
    if code == "02":
        from uwc import fulfilment as F
        c = F.clearance(rt, acct)
        if c["status"] == "CLEARED":
            return "Clearance passed — duplicates, licence, sanctions and placement checks all clear"
        m = rt.data_request(acct, ["Renewed producer licence"], uw)
        rt.advance_to(m["reply_due"])
        return f"Clearance hold ({c['reason']}) → licence requested → broker returned it {m['reply_due']} → re-screened: {F.clearance(rt, acct)['status']}"
    if code == "05" and not any(e.get("account_id") == acct and e["type"] == "eng.visit" and not e.get("done") for e in rt.dynamic) and rt.recs.get(acct):
        from uwc import fulfilment as F
        F.order_survey(rt, acct, "u_elena")
        rt.advance_to((rt.clock_date + timedelta(days=7)).isoformat())
        return "Verification survey ordered and completed (+7 days) — report ingested as verified evidence"
    if code in ("06", "15", "03", "04", "05", "13", "14", "02"):
        if ren.pass_no == 0:
            rt._enrich(acct)
            evaluate_account(rt, acct, pass_no=1)
        else:
            evaluate_account(rt, acct)
        return "Account re-evaluated on the current evidence"
    if code == "08":
        if any(f["outcome"] == "DECLINE" and f["status"] in ("OPEN", "ACCEPTED") for f in ren.findings.values()):
            return "Class declined under current guidelines — not quoted (see the decline & non-renewal playbook)"
        q = _latest_quote(ren)
        if q and q["status"] != "SUPERSEDED":
            return f"Quote v{q['version']} already {q['status'].lower()} at ${q['premium']:,.0f}"
        from uwc.engine.pricing import recommended_terms
        from uwc.engine.evaluate import contract_views
        exp = contract_views(rt, acct).get("endorsed", {})
        has_t1 = any(s.get("wind_tier") == "T1" for s in ren.loc_ctx.values())
        t = recommended_terms(rt, acct, exp, has_t1)
        terms = {k: t.get(k) for k in ("named_storm_ded_pct", "named_storm_ded_min")}
        q = rt.create_quote(acct, _suggested_premium(rt, acct), terms, uw)
        return f"Quote v{q['version']} drafted at ${q['premium']:,.0f} · RARC {q['rarc'] * 100:+.1f}% · adequacy {q['adequacy'] * 100:.1f}%"
    if code == "07":
        msgs = []
        q = _latest_quote(ren)
        if not q or q["status"] == "SUPERSEDED":
            msgs.append(run(rt, "08", acct))
            q = _latest_quote(ren)
            if not q:
                return msgs[-1]
        if q["needs_referral"] and not any(x["status"] == "APPROVED" and x["terms_hash"] == q["terms_hash"] for x in ren.referrals):
            pending = [x for x in ren.referrals if x["status"] == "PENDING"]
            if not pending:
                ref = rt.create_referral(acct, q["quote_id"], "Pipeline walkthrough referral", uw)
                msgs.append(f"referred to L{ref['required_level']}")
                pending = [ref]
            appr = _approver(pending[0]["required_level"])
            rt.decide_referral(pending[0]["referral_id"], "APPROVE", None, appr)
            msgs.append(f"approved by {USER_BY_ID[appr]['name']} (L{USER_BY_ID[appr]['authority_level']})")
        else:
            msgs.append(f"quote v{q['version']} within authority or already approved")
        return " · ".join(msgs)
    if code == "09":
        q = _latest_quote(ren)
        if not q:
            return "Draft a quote first (stage 08)"
        msgs = []
        if q["status"] in ("DRAFT", "APPROVED", "REFERRED"):
            if q["needs_referral"] and q["status"] != "APPROVED":
                msgs.append(run(rt, "07", acct))
            rt.send_quote(acct, q["quote_id"], uw)
            msgs.append(f"quote v{q['version']} sent to {reg['broker']}")
        if q["status"] == "SENT":
            rt.advance_to((date.fromisoformat(rt.clock) + timedelta(days=5)).isoformat())
            msgs.append(f"clock +5 days — broker {'accepted' if q['status'] == 'ACCEPTED' else 'countered' if q.get('broker_counter') else 'pending'}")
        return " · ".join(msgs) or f"Quote v{q['version']} is {q['status'].lower()}"
    if code == "10":
        if ren.r_bound:
            return "Already bound"
        q = next((x for x in ren.quotes if x["status"] == "ACCEPTED"), None)
        if not q:
            return "No accepted quote to bind"
        rt.bind(acct, q["quote_id"], uw)
        return "Bound — Pass 3 ran on the binder"
    if code == "11":
        if not ren.r_bound:
            return "Nothing bound yet — bind first (stage 10)"
        if ren.r_issued:
            if not ren.r_issued.get("corrected") and any(f["rule_id"] == "CONTRACT.BINDER_POLICY" and f["status"] == "OPEN" for f in ren.findings.values()):
                from uwc import fulfilment as F
                return F.correct_issuance(rt, acct, uw)
            return "Already issued"
        rt.issue(acct, uw)
        msg = f"Issued — {ren.r_issued['injected'] or 'as bound'}"
        if any(f["rule_id"] == "CONTRACT.BINDER_POLICY" and f["status"] == "OPEN" for f in ren.findings.values()):
            from uwc import fulfilment as F
            msg += " · Pass 3 caught it → " + F.correct_issuance(rt, acct, uw)
        return msg
    return "Nothing to run at this stage"

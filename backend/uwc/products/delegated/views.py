"""Payloads for the delegated authority API and stage workspaces (read-only views over the state)."""
from __future__ import annotations

from datetime import date

from . import baa as B
from . import engine as E
from .refdata import CLASSES, COVERHOLDERS, MONTH_LABEL, ORDER, TXN_LABEL

SEV = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
STATUS_RANK = {"OPEN": 6, "QUERIED": 5, "RESPONDED": 5, "ESCALATED": 7, "ACCEPTED": 2, "RESOLVED": 1, "AUTHORISED": 0}


def doc_meta(rt, doc_id):
    from uwc.api import doc_meta as dm
    d = rt.store.docs.get(doc_id) or rt.world_docs.get(doc_id)
    return dm(d) if d else None


def latest_month(st, ch) -> str | None:
    ms = E.months_of(st, ch)
    return ms[-1] if ms else None


def all_months(st) -> list[str]:
    return sorted({m for ch in ORDER for m in E.months_of(st, ch)})


def month_end(m: str) -> str:
    from .world import month_end as me
    return me(m)


# ============================================================================ coverholders
def summary(st, rt, ch) -> dict:
    cfg = COVERHOLDERS[ch]
    sc = E.scorecard(st, rt, ch)
    lm = latest_month(st, ch)
    ms = E.month_stats(st, ch, lm) if lm else None
    ex = [e for e in st["exceptions"].values() if e["ch"] == ch and e["status"] in E.OPEN_STATES]
    zs = E.aggregates(st, ch, rt.clock)
    cap = E.capacity(st, ch, rt.clock)
    terms, _a, ver = E.authority(st, ch, rt.clock)
    rq = E.rarc(st, ch)["quarters"]
    return {"id": ch, "scenario": cfg["scenario"], "name": cfg["name"], "short": cfg["short"], "program": cfg["program"], "agreement": cfg["agreement"], "umr": cfg["umr"],
            "pin": cfg["pin"], "broker": cfg["broker"], "contact": f"{cfg['contact']}, {cfg['contact_title']}", "hq": cfg["hq"], "story": cfg["story"], "title": cfg["title"],
            "period": [terms.get("period_start"), terms.get("period_end")], "authority_version": ver, "commission": terms.get("commission_pct"), "max_limit": terms.get("max_limit"),
            "grade": sc["grade"], "score": sc["score"], "within_authority": sc["within_authority"], "direction": sc["direction"], "trend": sc["trend"],
            "latest_month": lm, "latest": ms, "open_exceptions": len(ex), "open_policies": len({e["policy_key"] for e in ex if e["subject_type"] == "policy"}),
            "at_stake": sum(e["impact_usd"] for e in ex if e["subject_type"] in ("policy", "claim")), "premium_tied": sum(abs(st["rows"][rid].get("gross_premium") or 0) for rid in {e["row_id"] for e in ex if e.get("row_id")}),
            "commission_open": sum(e["impact_usd"] for e in ex if e["family"] == "commission"),
            "top_zone": ({"zone": zs[0]["zone"], "name": zs[0]["name"], "util": zs[0]["util"], "warn": zs[0]["warn"], "status": zs[0]["status"]} if zs else None),
            "gpi_util": cap.get("util"), "dq_score": sc["dq_score"], "avg_days_late": sc["avg_days_late"], "loss_ratio": sc["loss_ratio"], "turnaround_days": sc["turnaround_days"],
            "open_queries": sc["open_queries"], "rarc": rq[-1] if rq else None, "policies": sc["policies"], "gwp": sc["gwp"]}


def authority_view(st, rt, ch) -> dict:
    terms, anchors, ver = E.authority(st, ch, rt.clock)
    versions = st["authority"][ch]
    src = {}
    for v in versions:
        for k in v["anchors"]:
            src[k] = v["doc_id"]
    def a(k):
        return {"anchor": anchors.get(k), "doc_id": src.get(k)}
    kv = []
    for key, label in (("agreement_no", "Agreement number"), ("umr", "UMR"), ("period_start", "Authority period"), ("max_limit", "Maximum limit any one risk"),
                       ("gpi_limit", "Gross premium income limit"), ("commission_pct", "Commission"), ("tolerance_low", "Premium tolerance below rated"),
                       ("ref_tiv_any", "Referral: TIV any one location"), ("ref_tiv_tier1", "Referral: TIV in Tier 1"), ("ref_year_built", "Referral: year built before"),
                       ("bordereau_due_days", "Bordereau due (days after month end)"), ("large_loss_threshold", "Large loss notification threshold"),
                       ("large_loss_days", "Large loss notification period (days)"), ("claims_authority", "Claims settlement authority")):
        if terms.get(key) is None:
            continue
        v = terms[key]
        disp = f"{B.dmy(terms['period_start'])} to {B.dmy(terms['period_end'])}" if key == "period_start" else B.pctf(v) if isinstance(v, float) and v < 1 else \
            B.usd(v) if isinstance(v, (int, float)) and key not in ("ref_year_built", "bordereau_due_days", "large_loss_days") else str(v)
        kv.append({"key": key, "label": label, "value": disp, **a(key)})
    for tier, v in (terms.get("ns_min") or {}).items():
        kv.append({"key": f"ns_min.{tier}", "label": f"Minimum named storm deductible ({tier})", "value": B.pctf(v), **a(f"ns_min.{tier}")})
    return {"version": ver, "kv": kv,
            "classes": [{"code": c, **x, **a(f"classes.{c}")} for c, x in (terms.get("classes") or {}).items()],
            "territories": [{"key": k, **x, **a(f"territories.{k}")} for k, x in (terms.get("territories") or {}).items()],
            "min_aop": [{"from": x[0], "to": x[1], "min": x[2], **a(f"min_aop.{int(x[0])}")} for x in (terms.get("min_aop") or [])],
            "ded_factors": [{"deductible": d, "factor": f, **a(f"ded_factors.{int(d)}")} for d, f in (terms.get("ded_factors") or [])],
            "construction": [{"iso": i, "factor": f, **a(f"construction.{i}")} for i, f in sorted((terms.get("construction") or {}).items())],
            "prohibited": [{"code": c, "label": x, **a(f"prohibited.{c}")} for c, x in (terms.get("prohibited") or {}).items()],
            "aggregates": [{"zone": z, **x, **a(f"aggregates.{z}")} for z, x in (terms.get("aggregates") or {}).items()],
            "versions": [{"version": v["version"], "kind": v["kind"], "number": v["number"], "title": v["title"], "doc_id": v["doc_id"], "effective": v["effective"],
                          "issued": v["issued"], "changes": v["changes"], "terms": v["parsed_terms"], "in_force": v["effective"] <= rt.clock} for v in versions]}


def detail(st, rt, ch) -> dict:
    s = summary(st, rt, ch)
    months = E.months_of(st, ch)
    zhist = []
    for m in ["2026-04"] + months:
        me = "2026-04-30" if m == "2026-04" else month_end(m)
        zhist.append({"month": m, "zones": {z["zone"]: z["util"] for z in E.aggregates(st, ch, me)}})
    docs = [doc_meta(rt, d) for d in st["docs"].get(ch, [])]
    return {**s, "authority": authority_view(st, rt, ch), "scorecard": E.scorecard(st, rt, ch), "reports": [E.report(st, rt, ch, m) for m in months],
            "bordereaux": bordereaux(st, rt, ch), "aggregates": E.aggregates(st, ch, rt.clock), "zone_history": zhist, "capacity": E.capacity(st, ch, rt.clock),
            "claims": claims(st, ch), "referrals": [r for r in st["referrals"] if r["ch"] == ch and r["requested"] <= rt.clock][-60:][::-1],
            "queries": [q for q in st["queries"] if q["ch"] == ch][::-1], "ledger": [x for x in st["ledger"] if x["ch"] == ch][::-1],
            "audits": [a for a in st["audits"] if a["ch"] == ch][::-1], "issued_reports": [r for r in st["reports"] if r["ch"] == ch][::-1],
            "restrictions": [r for r in st["restrictions"] if r["ch"] == ch], "amendments": [a for a in st["amendments"] if a["ch"] == ch],
            "prevented": [p for p in st["prevented"] if p["ch"] == ch], "rarc_detail": E.rarc(st, ch), "timeline": list(reversed(st["timeline"].get(ch, [])))[:80],
            "documents": sorted([d for d in docs if d], key=lambda d: d["received_at"], reverse=True),
            "register": register(st, rt, {"ch": ch, "status": "all"})}


def claims(st, ch) -> list[dict]:
    out = []
    for c in E.claims_view(st, ch):
        ex = [e for e in st["exceptions"].values() if e["ch"] == ch and e["subject_type"] == "claim" and e.get("claim_ref") == c["claim_ref"] and e["status"] in E.OPEN_STATES]
        out.append({k: c.get(k) for k in ("claim_ref", "certificate_ref", "insured_name", "state", "date_of_loss", "date_reported", "cause", "description", "status", "paid",
                                          "reserve", "incurred", "prior_incurred", "incurred_change", "first_seen", "days_to_carrier", "handled_by", "anchor", "doc_id")}
                   | {"exceptions": [{"exc_id": e["exc_id"], "title": e["title"], "severity": e["severity"]} for e in ex]})
    return sorted(out, key=lambda c: -(c["incurred"] or 0))


# ============================================================================ register
def _entry(st, rt, key, exs) -> dict:
    e0 = max(exs, key=lambda e: (STATUS_RANK.get(e["status"], 0), SEV.get(e["severity"], 0)))
    ch = e0["ch"]
    row = st["rows"].get(e0["row_id"]) if e0.get("row_id") else None
    live = [e for e in exs if E.raised(e)]
    open_ = [e for e in live if e["status"] in E.OPEN_STATES]
    status = e0["status"] if live else "AUTHORISED"
    if live and not open_:
        status = "ACCEPTED" if any(e["status"] == "ACCEPTED" for e in live) else "RESOLVED"
    return {"key": key, "ch": ch, "ch_name": COVERHOLDERS[ch]["short"], "scenario": COVERHOLDERS[ch]["scenario"], "certificate_ref": e0["certificate_ref"], "insured": e0["insured"],
            "subject_type": e0["subject_type"], "month": e0["month"], "txn": TXN_LABEL.get(e0.get("txn") or "", e0.get("txn")), "status": status,
            "severity": max((e["severity"] for e in live or exs), key=lambda s: SEV.get(s, 0)), "families": sorted({e["family"] for e in live}),
            "checks": [{"exc_id": e["exc_id"], "check": e["check"], "title": e["title"], "family": e["family"], "status": e["status"], "outcome": e["outcome"], "written": e["written"],
                        "authority": e["authority"], "delta": e.get("delta"), "impact_usd": e["impact_usd"], "referral": (e.get("referral") or {}).get("result")} for e in exs],
            "exceptions": len(live), "open": len(open_), "premium_tied": abs(row.get("gross_premium") or 0) if row else 0.0, "impact_usd": round(sum(e["impact_usd"] for e in open_), 2),
            "commission_discrepancy": round(sum(e["impact_usd"] for e in live if e["family"] == "commission"), 2),
            "exposure_above": round(sum(e["impact_usd"] for e in live if e["family"] == "limit"), 2), "raised_at": min(e["raised_at"] for e in exs),
            "resolved_at": max((e["resolved_at"] or "") for e in live) if live and not open_ else None, "query_ids": sorted({q for e in exs for q in e["query_ids"]}),
            "action": e0.get("action"), "tiv": row.get("tiv") if row else None, "state": row.get("state") if row else None}


def register(st, rt, f: dict) -> list[dict]:
    groups: dict[str, list] = {}
    for e in st["exceptions"].values():
        if f.get("ch") and e["ch"] != f["ch"]:
            continue
        groups.setdefault(e["policy_key"], []).append(e)
    out = []
    for k, exs in groups.items():
        en = _entry(st, rt, k, exs)
        stt = f.get("status") or "open"
        if stt == "open" and en["status"] in ("RESOLVED", "ACCEPTED", "AUTHORISED"):
            continue
        if stt == "closed" and en["status"] not in ("RESOLVED", "ACCEPTED"):
            continue
        if stt != "all" and stt not in ("open", "closed") and en["status"] != stt:
            continue
        if stt == "all" and en["status"] == "AUTHORISED" and not f.get("include_authorised"):
            continue
        if f.get("family") and f["family"] not in en["families"] and not any(c["family"] == f["family"] for c in en["checks"]):
            continue
        if f.get("month") and en["month"] != f["month"]:
            continue
        if f.get("subject") and en["subject_type"] != f["subject"]:
            continue
        if f.get("query") and f["query"] not in en["query_ids"]:
            continue
        if f.get("q"):
            ql = f["q"].lower()
            if ql not in f"{en['insured']} {en['certificate_ref']} {en['ch_name']}".lower():
                continue
        out.append(en)
    out.sort(key=lambda x: (-STATUS_RANK.get(x["status"], 0), -SEV.get(x["severity"], 0), -x["impact_usd"], x["key"]))
    return out


def policy_detail(st, rt, key) -> dict:
    exs = [e for e in st["exceptions"].values() if e["policy_key"] == key]
    if not exs:
        raise KeyError(key)
    en = _entry(st, rt, key, exs)
    ch = en["ch"]
    e0 = exs[0]
    row = st["rows"].get(e0.get("row_id")) if e0.get("row_id") else None
    checks, fields, corrections, auth_doc = [], [], [], None
    if row:
        res = E.check_row(st, rt, row, full=True)
        byrule = {e["rule_id"]: e for e in exs if e.get("row_id") == row["row_id"]}
        for c in res:
            e = byrule.get(c["rule_id"])
            ref = E.reconcile_referral(st, rt, row, c["rule_id"]) if c["result"] == "REFER" else None
            checks.append({**{k: c[k] for k in ("rule_id", "check", "title", "result", "outcome", "severity", "written", "authority", "delta", "impact_usd", "source", "action",
                                                  "anchor_written", "anchor_authority", "authority_version")},
                           "referral": ref, "exc_id": e["exc_id"] if e else None, "status": e["status"] if e else ("PASS" if c["result"] in ("PASS", "NA") else "OPEN")})
        refer = [c for c in checks if c["result"] == "REFER"]
        found = [c for c in refer if (c["referral"] or {}).get("result") == E.REFER_OK]
        rref = row.get("referral_ref")
        checks.append({"rule_id": "REFERRAL", "check": "Referral required / approval found", "title": "Referral reconciliation", "result": "BREACH" if refer and len(found) < len(refer) else "PASS",
                       "outcome": "REFER", "severity": "HIGH", "written": f"{'Yes' if refer else 'No'} ({len(refer)} trigger{'s' if len(refer) != 1 else ''})",
                       "authority": (rref + (" — approved" if found and len(found) == len(refer) else " — does not cover the written terms" if refer else "")) if rref else ("None located" if refer else "Not required"),
                       "delta": None, "impact_usd": 0, "source": "Carrier referral system (mock)", "action": None, "anchor_written": E._anchor(st, row, "referral_ref") if row.get("cells", {}).get("referral_ref") else None,
                       "anchor_authority": None, "referral": None, "exc_id": None, "status": "OPEN" if refer and len(found) < len(refer) else "PASS"})
        order = ["DA.CLASS.PERMITTED", "DA.TERRITORY.PERMITTED", "DA.TERRITORY.EXCLUDED", "DA.LIMIT.MAX", "DA.DEDUCTIBLE.MIN_AOP", "DA.DEDUCTIBLE.MIN_NS", "DA.PRICING.BELOW_RANGE", "REFERRAL",
                 "DA.COMMISSION.CONTRACT"]
        checks.sort(key=lambda c: (order.index(c["rule_id"]) if c["rule_id"] in order else 50, c["rule_id"]))
        for f, label in (("certificate_ref", "Certificate"), ("transaction_type", "Transaction"), ("insured_name", "Insured"), ("address", "Address"), ("city", "City"), ("state", "State"),
                         ("county", "County"), ("class_code", "Class"), ("occupancy", "Occupancy"), ("construction", "Construction"), ("year_built", "Year built"), ("tiv", "TIV"),
                         ("limit", "Limit"), ("aop_deductible", "AOP deductible"), ("ns_deductible_pct", "Named storm deductible"), ("written_date", "Bound"), ("inception", "Inception"),
                         ("expiry", "Expiry"), ("gross_premium", "Gross premium"), ("referral_ref", "Referral ref"), ("prior_premium", "Expiring premium"), ("prior_tiv", "Expiring TIV")):
            v = row.get(f)
            disp = "—" if v is None else B.usd(v) if f in ("tiv", "limit", "aop_deductible", "gross_premium", "prior_premium", "prior_tiv") else B.pctf(v) if f == "ns_deductible_pct" else \
                TXN_LABEL.get(v, v) if f == "transaction_type" else str(v)
            if f == "class_code" and v:
                disp = f"{v} · {CLASSES.get(v, (v,))[0]}" + (f" (derived from occupancy, {row['class_derived']:.2f})" if row.get("class_derived") else "")
            fields.append({"field": f, "label": label, "value": disp, "anchor": E._anchor(st, row, f)})
        if row.get("prem"):
            for f, label in (("commission_pct", "Commission %"), ("commission_amount", "Commission amount"), ("net_premium", "Net premium"), ("taxes", "Taxes & fees")):
                v = row["prem"].get(f)
                fields.append({"field": f, "label": label, "value": "—" if v is None else B.pctf(v) if f == "commission_pct" else f"${v:,.2f}", "anchor": E._anchor(st, row, f, premium=True)})
        corrections = [{"date": c["date"], "doc_id": c["doc_id"], "fields": c["fields"]} for c in row.get("changes", [])]
        _t, _a, v = E.authority(st, ch, row.get("written_date"))
        auth_doc = next((x["doc_id"] for x in st["authority"][ch] if x["version"] == v), None)
    else:
        checks = [{"rule_id": e["rule_id"], "check": e["check"], "title": e["title"], "result": e["outcome"], "outcome": e["outcome"], "severity": e["severity"], "written": e["written"],
                   "authority": e["authority"], "delta": e.get("delta"), "impact_usd": e["impact_usd"], "source": e["source"], "action": e["action"], "anchor_written": e.get("anchor_written"),
                   "anchor_authority": e.get("anchor_authority"), "authority_version": None, "referral": e.get("referral"), "exc_id": e["exc_id"], "status": e["status"]} for e in exs]
    claims_on = [c for c in claims(st, ch) if c["certificate_ref"] == en["certificate_ref"]]
    history = sorted([{**h, "exc_id": e["exc_id"], "check": e["check"]} for e in exs for h in e["history"]], key=lambda h: h["date"])
    responses = [{"exc_id": e["exc_id"], "check": e["check"], **e["response"]} for e in exs if e.get("response")]
    queries = [q for q in st["queries"] if q["query_id"] in en["query_ids"]]
    recs = []
    if any(c["result"] == "REFER" and (c.get("referral") or {}).get("result") != E.REFER_OK for c in checks):
        recs.append("Carrier review: referral evidence or retrospective approval")
    if any(c["rule_id"] == "DA.PRICING.BELOW_RANGE" and c["result"] == "REFER" for c in checks):
        recs.append("Premium reconciliation against the rated premium")
    if any(c["rule_id"] == "DA.COMMISSION.CONTRACT" and c["result"] == "BREACH" for c in checks):
        recs.append("Commission reconciliation — debit note for the over-deduction")
    if any(c["result"] == "BREACH" and c["rule_id"] not in ("DA.COMMISSION.CONTRACT", "REFERRAL") for c in checks):
        recs.append("Outside authority whatever the approval — cancellation or ratification decision")
    if claims_on:
        recs.append("Claims on this policy — coverage review")
    return {**en, "row_fields": fields, "side_by_side": checks, "claims": claims_on, "history": history, "responses": responses, "queries": queries, "corrections": corrections,
            "authority_doc_id": auth_doc, "bordereau_doc_id": row["doc_id"] if row else None, "recommended": recs or [en.get("action") or "Monitor"],
            "exc_ids_open": [e["exc_id"] for e in exs if e["status"] in E.OPEN_STATES], "row_versions": row.get("versions") if row else []}


# ============================================================================ bordereaux
def bordereaux(st, rt, ch=None) -> list[dict]:
    out = []
    for did, b in st["bdx"].items():
        if ch and b["ch"] != ch:
            continue
        ex = [e for e in st["exceptions"].values() if e.get("row_id") and st["rows"].get(e["row_id"], {}).get("doc_id") == did and E.raised(e)] if b["kind"] == "risk" else []
        out.append({"doc_id": did, "ch": b["ch"], "ch_name": COVERHOLDERS[b["ch"]]["short"], "kind": b["kind"], "month": b["month"], "title": b["title"], "received": b["received"],
                    "due": b["due"], "days_late": b["days_late"], "rows": b["rows"], "dq_score": b["dq_score"], "mapping_confidence": b["stats"].get("mapping_confidence"),
                    "missing": b["missing_labels"], "issues": len(b["issues"]), "issues_high": sum(1 for i in b["issues"] if i["severity"] == "HIGH"), "correction": b["correction"],
                    "superseded_by": b["superseded_by"], "replaces": b.get("replaces"), "exceptions": len(ex)})
    return sorted(out, key=lambda x: (x["received"], x["ch"], x["kind"]), reverse=True)


def bordereau_detail(st, rt, did) -> dict:
    b = st["bdx"][did]
    ids = [r["row_id"] for r in st["rows"].values() if r.get("doc_id") == did or (r.get("prem") or {}).get("doc_id") == did]
    ex = [e for e in st["exceptions"].values() if e.get("row_id") in set(ids) and E.raised(e)]
    return {**{k: b[k] for k in ("doc_id", "ch", "kind", "month", "title", "received", "due", "days_late", "sheet", "header_row", "mapping", "missing", "missing_labels", "issues",
                                 "stats", "dq_score", "rows", "correction", "replaces", "superseded_by", "skipped", "method")},
            "ch_name": COVERHOLDERS[b["ch"]]["short"], "document": doc_meta(rt, did),
            "exceptions": [{"exc_id": e["exc_id"], "policy_key": e["policy_key"], "certificate_ref": e["certificate_ref"], "insured": e["insured"], "check": e["check"], "written": e["written"],
                            "authority": e["authority"], "status": e["status"], "anchor": e.get("anchor_written")} for e in ex]}


# ============================================================================ portfolio
def overview(st, rt, month: str | None = None) -> dict:
    months = all_months(st)
    m = month or (months[-1] if months else None)
    chs = [summary(st, rt, ch) for ch in ORDER]
    per = {ch: E.month_stats(st, ch, m) for ch in ORDER if m in E.months_of(st, ch)}
    tot = {"policies": sum(x["policies"] for x in per.values()), "with_exceptions": sum(x["with_exceptions"] for x in per.values()),
           "premium_tied": sum(x["premium_tied"] for x in per.values()), "commission": sum(x["commission_discrepancy"] for x in per.values()),
           "missing_referrals": sum(x["missing_referrals"] for x in per.values()), "open_policies": sum(x["open_policies"] for x in per.values()),
           "exposure_above": sum(x["exposure_above"] for x in per.values()), "premium": sum(x["premium"] for x in per.values())}
    tot["exception_rate"] = tot["with_exceptions"] / tot["policies"] if tot["policies"] else 0
    tot["within_authority"] = 1 - tot["open_policies"] / tot["policies"] if tot["policies"] else 1
    types: dict[str, dict] = {}
    for ch in per:
        for fam, n in per[ch]["by_type"].items():
            t = types.setdefault(fam, {"family": fam, "label": E.FAMILY_LABEL.get(fam, fam), "count": 0, "by_ch": {}})
            t["count"] += n
            t["by_ch"][ch] = n
    trend = []
    for mm in months:
        x = {"month": mm, "label": MONTH_LABEL[mm]}
        for ch in ORDER:
            if mm in E.months_of(st, ch):
                x[ch] = round(E.month_stats(st, ch, mm)["exception_rate"] * 100, 2)
        trend.append(x)
    zones = []
    for ch in ORDER:
        for z in E.aggregates(st, ch, rt.clock):
            zones.append({"ch": ch, "ch_name": COVERHOLDERS[ch]["short"], **{k: z.get(k) for k in ("zone", "name", "peril", "tiv", "limit", "util", "warn", "status", "pml_100")}})
    zones.sort(key=lambda z: -(z["util"] or 0))
    open_all = [e for e in st["exceptions"].values() if e["status"] in E.OPEN_STATES]
    res = [e for e in st["exceptions"].values() if e["status"] == "RESOLVED" and e.get("query_ids") and e.get("resolved_at")]
    turn = [(date.fromisoformat(e["resolved_at"]) - date.fromisoformat(e["raised_at"])).days for e in res]
    corrected = [e for e in st["exceptions"].values() if e["status"] in ("RESOLVED",) and e["subject_type"] == "policy" and E.raised(e)]
    return {"as_of": rt.clock, "month": m, "months": months, "totals": tot, "types": sorted(types.values(), key=lambda t: -t["count"]), "trend": trend, "coverholders": chs,
            "zones": zones[:12], "at_stake": sum(e["impact_usd"] for e in open_all if e["subject_type"] in ("policy", "claim")), "open_exceptions": len(open_all),
            "open_policies": len({e["policy_key"] for e in open_all if e["subject_type"] == "policy"}),
            "corrected": {"count": len(corrected), "exposure": sum(e["impact_usd"] for e in corrected if e["family"] == "limit"),
                          "premium": sum(e.get("premium_tied") or 0 for e in corrected)},
            "prevented": {"count": len(st["prevented"]), "tiv": sum(p["tiv"] for p in st["prevented"])}, "turnaround_days": round(sum(turn) / len(turn), 1) if turn else None,
            "queries_open": sum(1 for q in st["queries"] if q["status"] == "SENT"), "aggregate_warnings": sum(1 for z in zones if z["util"] and z["warn"] and z["util"] >= z["warn"]),
            "ledger": st["ledger"][::-1][:10], "recent": sorted([{**e, "ch": ch, "ch_name": COVERHOLDERS[ch]["short"]} for ch in ORDER for e in st["timeline"].get(ch, [])],
                                                                key=lambda e: (e["date"], e["event_id"]), reverse=True)[:14]}

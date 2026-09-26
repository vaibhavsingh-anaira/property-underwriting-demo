"""Delegated authority engine: authority in force on a date, per-risk checks (YAML rules), referral
reconciliation, premium & commission reconciliation, zone aggregates, claims controls, the breach
register, monthly authority report, coverholder scorecard and quarterly RARC from bordereaux."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import operator as _operator
import re as _re

from uwc.engine.rules import FUNCS, Ctx, _cmp_guard, compile_expr, evaluate

from . import baa as B
from .refdata import CLASSES, COVERHOLDERS, OCC_TEXT, OUT_OF_SCHEDULE, TXN_LABEL

REFER_OK = "AUTHORISED"
OPEN_STATES = ("OPEN", "QUERIED", "RESPONDED", "ESCALATED")
FAMILY_LABEL = {"class": "Outside permitted class", "limit": "Above limit authority", "deductible": "Deductible breaches", "pricing": "Pricing deviations",
                "referral": "Missing mandatory referrals", "commission": "Commission discrepancies", "exclusion": "Prohibited risks", "territory": "Outside territory",
                "period": "Outside authority period", "aggregate": "Aggregate & restrictions", "premium": "Premium reconciliation", "claims": "Claims controls",
                "capacity": "Capacity", "timeliness": "Late bordereaux", "data_quality": "Bordereau data quality"}
# CAT aggregate feed (mock): modelled 1-in-100 PML as a share of TIV by zone peril
PML_RATIO = {"Hurricane": 0.14, "Earthquake": 0.09, "Wildfire": 0.06, "Severe convective storm": 0.035}


_FMT: dict = {}


def fmt(template: str, env: dict) -> str:
    """Same semantics as uwc.engine.rules.fmt ({expr}, usd()/pct()/num()), with compiled expressions cached."""
    ns = {"__builtins__": {}, "_cmp": _cmp_guard, "_op": _operator, **FUNCS}
    ns.update({k: (Ctx(v) if isinstance(v, dict) else v) for k, v in env.items()})

    def rep(m):
        expr = m.group(1)
        fn = None
        if expr.startswith(("usd(", "pct(", "num(")):
            fn, expr = expr[:3], expr[4:-1]
        code = _FMT.get(expr)
        if code is None:
            code = _FMT[expr] = compile_expr(expr)
        try:
            v = eval(code, ns)
        except Exception:  # noqa: BLE001
            return "—"
        if v is None or isinstance(v, Ctx):
            return "—"
        if fn == "usd":
            return f"${v:,.0f}" if v >= 0 else f"−${-v:,.0f}"
        if fn == "pct":
            return f"{v * 100:.1f}%".replace(".0%", "%")
        if fn == "num":
            return f"{v:,.0f}"
        return str(v)
    return _re.sub(r"\{([^{}]+)\}", rep, template)


def st_of(rt) -> dict:
    return rt.delegated


def rules(rt, applies_to: str):
    return [r for r in rt.rules.values() if r.product == "delegated" and r.applies_to == applies_to and r.active(rt.clock)]


# ============================================================================ authority
def authority(st: dict, ch: str, as_of: str | None = None) -> tuple[dict, dict, int]:
    versions = st["authority"].get(ch, [])
    key = (ch, len(versions), as_of)
    cache = st.setdefault("_auth_cache", {})
    if key not in cache:
        cache[key] = B.fold(versions, as_of)
    return cache[key]


def auth_env(terms: dict) -> dict:
    classes = terms.get("classes", {})
    terr = terms.get("territories", {})
    return {**{k: v for k, v in terms.items() if not isinstance(v, (dict, list))},
            "class_codes": [c for c, x in classes.items() if x.get("status") in ("Permitted", "Referral")],
            "referral_classes": [c for c, x in classes.items() if x.get("status") == "Referral"],
            "prohibited_codes": list(terms.get("prohibited", {})),
            "states": sorted({x["state"] for x in terr.values() if x.get("status") != "Excluded"}),
            "excluded_territories": [k for k, x in terr.items() if x.get("status") == "Excluded"],
            "class_list": ", ".join(c for c, x in classes.items() if x.get("status") in ("Permitted", "Referral")),
            "state_list": ", ".join(sorted({x["state"] for x in terr.values() if x.get("status") != "Excluded"}))}


def ded_factor(terms, d):
    fs = sorted(terms.get("ded_factors") or [(10_000, 1.0)])
    f = fs[0][1]
    for dd, ff in fs:
        if d is not None and d >= dd:
            f = ff
    return f


def min_aop(terms, tiv):
    for a, b, m in sorted(terms.get("min_aop") or []):
        if tiv is not None and tiv >= a and (b is None or tiv < b):
            return m
    return None


def rated(terms: dict, r: dict) -> float | None:
    """Rated premium from the BAA rating rules: TIV/100 × base rate × construction × territory × deductible factor."""
    cls = (terms.get("classes") or {}).get(r.get("class_code") or "")
    terr = (terms.get("territories") or {}).get(f"{r.get('state')}|{r.get('county')}")
    iso = r.get("iso")
    cf = (terms.get("construction") or {}).get(iso) if iso else None
    if not cls or not terr or terr.get("factor") is None or cf is None or r.get("tiv") is None or r.get("aop_deductible") is None:
        return None
    return r["tiv"] / 100 * cls["rate"] * cf * terr["factor"] * ded_factor(terms, r["aop_deductible"])


def map_class(occupancy: str | None) -> tuple[str | None, float]:
    if not occupancy:
        return None, 0.0
    t = occupancy.strip().lower()
    for code, texts in OCC_TEXT.items():
        if t in (x.lower() for x in texts):
            return code, 0.9
    for code, (label, _r) in list(CLASSES.items()) + [(k, (v, 0)) for k, v in OUT_OF_SCHEDULE.items()]:
        if any(w in t for w in label.lower().replace("/", " ").split() if len(w) > 4):
            return code, 0.72
    return None, 0.0


def zone_of(st: dict, ch: str, state: str | None, county: str | None) -> str | None:
    """CAT aggregate feed (mock): county → accumulation zone."""
    return st["zone_map"].get(ch, {}).get(f"{state}|{county}")


# ============================================================================ per-risk environment
def row_env(st: dict, r: dict, terms: dict, zone_terms: dict | None = None) -> dict:
    ch = r["ch"]
    key = f"{r.get('state')}|{r.get('county')}"
    terr = (terms.get("territories") or {}).get(key) or {}
    tier = terr.get("tier")
    z = zone_of(st, ch, r.get("state"), r.get("county"))
    agg = ((zone_terms or terms).get("aggregates") or {}).get(z or "", {})
    tech = rated(terms, r)
    lo, hi = terms.get("tolerance_low"), terms.get("tolerance_high")
    txn = r.get("transaction_type")
    adds = txn == "NEW" or (txn in ("RENEWAL", "ENDORSEMENT") and (r.get("tiv") or 0) > (r.get("prior_tiv") or 0) * 1.05 and r.get("prior_tiv") is not None)
    exp_ret = None
    if txn == "CANCELLATION" and r.get("expiry") and r.get("written_date"):
        base = st["annual_premium"].get(f"{ch}|{r.get('certificate_ref')}") or rated(terms, r)
        if base:
            exp_ret = base * max(0, (date.fromisoformat(r["expiry"]) - date.fromisoformat(r["written_date"])).days) / 365
    row = {"class_code": r.get("class_code"), "occupancy": r.get("occupancy"), "state": r.get("state"), "county": r.get("county"), "territory_key": key,
           "tiv": r.get("tiv"), "limit": r.get("limit"), "aop_deductible": r.get("aop_deductible"), "ns_deductible_pct": r.get("ns_deductible_pct"),
           "gross_premium": r.get("gross_premium") if txn in ("NEW", "RENEWAL", "CANCELLATION") else None, "year_built": r.get("year_built"),
           "written_date": r.get("written_date"), "inception": r.get("inception"), "txn": txn, "adds_exposure": adds, "commission_pct": r.get("commission_pct")}
    if txn == "CANCELLATION":
        row.update(limit=None, aop_deductible=None, ns_deductible_pct=None, year_built=None, adds_exposure=False)
    req = {"min_aop": min_aop(terms, r.get("tiv")), "ns_min": (terms.get("ns_min") or {}).get(tier) if tier in ("Tier 1", "Tier 2") else None, "tier": tier,
           "technical": tech, "premium_low": tech * (1 - lo) if tech and lo is not None else None, "premium_high": tech * (1 + hi) if tech and hi is not None else None,
           "zone": z, "zone_name": agg.get("name") or z, "zone_status": agg.get("status") if agg.get("status") in ("Refer", "Stop") else None, "expected_return": exp_ret}
    return {"row": row, "auth": auth_env(terms), "req": req}


IMPACT = {
    "exposure_above_limit": lambda e: (e["row"]["limit"] or 0) - (e["auth"].get("max_limit") or 0),
    "deductible_gap": lambda e: (e["req"]["min_aop"] or 0) - (e["row"]["aop_deductible"] or 0),
    "ns_gap": lambda e: ((e["req"]["ns_min"] or 0) - (e["row"]["ns_deductible_pct"] or 0)) * (e["row"]["tiv"] or 0),
    "premium_shortfall": lambda e: (e["req"]["premium_low"] or 0) - (e["row"]["gross_premium"] or 0),
    "premium_tied": lambda e: abs(e["row"]["gross_premium"] or 0),
    "commission_diff": lambda e: ((e["row"]["commission_pct"] or 0) - (e["auth"].get("commission_pct") or 0)) * (e.get("_gross") or 0),
    "tiv_added": lambda e: e["row"]["tiv"] or 0,
    "return_excess": lambda e: -(e["row"]["gross_premium"] or 0) - (e["req"]["expected_return"] or 0),
    "none": lambda e: 0.0,
}


def _delta(rule_id: str, e: dict) -> str | None:
    r, a, q = e["row"], e["auth"], e["req"]
    try:
        if rule_id == "DA.LIMIT.MAX":
            return f"+{B.usd(r['limit'] - a['max_limit'])}"
        if rule_id == "DA.DEDUCTIBLE.MIN_AOP":
            return f"−{B.usd(q['min_aop'] - r['aop_deductible'])}"
        if rule_id == "DA.DEDUCTIBLE.MIN_NS":
            return f"−{(q['ns_min'] - r['ns_deductible_pct']) * 100:.1f} pts"
        if rule_id == "DA.PRICING.BELOW_RANGE":
            return f"{(r['gross_premium'] / q['technical'] - 1) * 100:+.1f}% vs rated"
        if rule_id == "DA.COMMISSION.CONTRACT":
            return f"+{(r['commission_pct'] - a['commission_pct']) * 100:.1f} pts"
        if rule_id in ("DA.REFERRAL.TIV",):
            return f"+{B.usd(r['tiv'] - a['ref_tiv_any'])}"
        if rule_id == "DA.REFERRAL.TIER1_TIV":
            return f"+{B.usd(r['tiv'] - a['ref_tiv_tier1'])}"
    except (TypeError, KeyError):
        return None
    return None


def _anchor(st, r, f, premium=False) -> dict | None:
    src = r.get("prem") if premium else r
    if not src or f not in (src.get("cells") or {}):
        return None
    cell = src["cells"][f]
    rn = src["r"]
    return {"doc_id": src["doc_id"], "kind": "xlsx", "sheet": src["sheet"], "cell": cell, "range": f"A{rn}:{src.get('last_col', 'Z')}{rn}"}


RULE_FIELDS = {"DA.CLASS.PERMITTED": ("class_code", "classes"), "DA.CLASS.REFERRAL": ("class_code", "classes"), "DA.EXCLUSION.PROHIBITED": ("class_code", "prohibited"),
               "DA.TERRITORY.PERMITTED": ("state", "territories"), "DA.TERRITORY.EXCLUDED": ("county", "territories"), "DA.LIMIT.MAX": ("limit", "max_limit"),
               "DA.DEDUCTIBLE.MIN_AOP": ("aop_deductible", "min_aop"), "DA.DEDUCTIBLE.MIN_NS": ("ns_deductible_pct", "ns_min"),
               "DA.PRICING.BELOW_RANGE": ("gross_premium", "tolerance_low"), "DA.REFERRAL.TIV": ("tiv", "ref_tiv_any"), "DA.REFERRAL.TIER1_TIV": ("tiv", "ref_tiv_tier1"),
               "DA.REFERRAL.YEAR_BUILT": ("year_built", "ref_year_built"), "DA.PERIOD.AUTHORITY": ("written_date", "period_start"),
               "DA.RESTRICTION.REFER": ("tiv", "aggregates"), "DA.RESTRICTION.STOP": ("tiv", "aggregates"), "DA.COMMISSION.CONTRACT": ("commission_pct", "commission_pct"),
               "DA.CANX.RETURN_PREMIUM": ("gross_premium", "commission_pct")}


def _auth_anchor(anchors: dict, rule_id: str, r: dict, env: dict) -> dict | None:
    term = RULE_FIELDS.get(rule_id, (None, None))[1]
    if term == "classes":
        return anchors.get(f"classes.{r.get('class_code')}") or next((v for k, v in anchors.items() if k.startswith("classes.")), None)
    if term == "prohibited":
        return anchors.get(f"prohibited.{r.get('class_code')}")
    if term == "territories":
        return anchors.get(f"territories.{r.get('state')}|{r.get('county')}") or next((v for k, v in anchors.items() if k.startswith("territories.")), None)
    if term == "min_aop":
        bands = sorted(k for k in anchors if k.startswith("min_aop."))
        for k in reversed(bands):
            if (r.get("tiv") or 0) >= float(k.split(".", 1)[1]):
                return anchors[k]
        return None
    if term == "ns_min":
        return anchors.get(f"ns_min.{env['req']['tier']}")
    if term == "aggregates":
        return anchors.get(f"aggregates.{env['req']['zone']}")
    return anchors.get(term)


ENDT_RULES = {"DA.LIMIT.MAX", "DA.REFERRAL.TIV", "DA.REFERRAL.TIER1_TIV", "DA.RESTRICTION.REFER", "DA.RESTRICTION.STOP", "DA.DEDUCTIBLE.MIN_AOP", "DA.PERIOD.AUTHORITY"}


def check_row(st: dict, rt, r: dict, full: bool = False) -> list[dict]:
    """All risk- and premium-level rule results for one bordereau line. Text and evidence are rendered for fired
    results (and for every result when full=True, for the side-by-side view)."""
    endt = r.get("transaction_type") == "ENDORSEMENT"
    terms, anchors, ver = authority(st, r["ch"], (r.get("inception") if endt else r.get("written_date")) or r.get("inception"))
    zterms = authority(st, r["ch"], r.get("written_date"))[0] if endt else terms
    env = row_env(st, r, terms, zterms)
    env["_gross"] = r.get("gross_premium")
    out = []
    for rule in rules(rt, "risk") + rules(rt, "premium"):
        if rule.applies_to == "premium" and not r.get("prem"):
            continue
        if r.get("transaction_type") == "CANCELLATION" and rule.rule_id not in ("DA.CANX.RETURN_PREMIUM", "DA.COMMISSION.CONTRACT"):
            continue
        if endt and rule.rule_id not in ENDT_RULES:
            continue
        v = evaluate(rule.code, env)
        res = "NA" if v is None else (rule.outcome if v else "PASS")
        if not v and not full:
            out.append({"rule_id": rule.rule_id, "result": res, "outcome": rule.outcome})
            continue
        wf = RULE_FIELDS.get(rule.rule_id, (None,))[0]
        out.append({"rule_id": rule.rule_id, "rule_version": rule.version, "family": rule.family, "check": rule.description or rule.title, "title": rule.title,
                    "result": res, "outcome": rule.outcome, "severity": rule.severity, "written": fmt(rule.observed, env), "authority": fmt(rule.expected, env),
                    "delta": _delta(rule.rule_id, env) if v else None, "impact_usd": round(max(0.0, IMPACT.get(rule.impact, IMPACT["none"])(env)), 2) if v else 0.0,
                    "impact_method": rule.impact, "action": rule.action, "source": rule.source, "authority_version": ver,
                    "anchor_written": _anchor(st, r, wf, premium=rule.applies_to == "premium" or wf == "commission_pct") if wf else None,
                    "anchor_authority": _auth_anchor(anchors, rule.rule_id, r, env)})
    return out


# ============================================================================ referral reconciliation
COVER = {"DA.LIMIT.MAX": lambda a, r: (a.get("limit") or 0) >= (r.get("limit") or 0),
         "DA.DEDUCTIBLE.MIN_AOP": lambda a, r: a.get("aop_min") is not None and (r.get("aop_deductible") or 0) >= a["aop_min"],
         "DA.DEDUCTIBLE.MIN_NS": lambda a, r: a.get("ns_min") is not None and (r.get("ns_deductible_pct") or 0) >= a["ns_min"] - 1e-9,
         "DA.PRICING.BELOW_RANGE": lambda a, r: a.get("premium_min") is not None and (r.get("gross_premium") or 0) >= a["premium_min"] - 1,
         "DA.REFERRAL.TIV": lambda a, r: (a.get("tiv") or 0) >= (r.get("tiv") or 0), "DA.REFERRAL.TIER1_TIV": lambda a, r: (a.get("tiv") or 0) >= (r.get("tiv") or 0),
         "DA.RESTRICTION.REFER": lambda a, r: (a.get("tiv") or 0) >= (r.get("tiv") or 0)}


def reconcile_referral(st: dict, rt, r: dict, rule_id: str) -> dict:
    """Carrier referral system lookup for one REFER result. Approval must exist, cover the written terms and pre-date binding."""
    ref = r.get("referral_ref")
    if not ref:
        return {"required": True, "ref": None, "result": "NOT_FOUND", "detail": "No referral reference on the bordereau; none located in the referral system"}
    rec = next((x for x in st["referrals"] if x["ref"] == ref and x["ch"] == r["ch"] and x["requested"] <= rt.clock), None)
    if not rec:
        return {"required": True, "ref": ref, "result": "NOT_FOUND", "detail": f"{ref} not found in the carrier referral system"}
    if rec["certificate_ref"] != r.get("certificate_ref") and rec["insured"].lower() != (r.get("insured_name") or "").lower():
        return {"required": True, "ref": ref, "result": "WRONG_RISK", "detail": f"{ref} was issued for {rec['insured']} ({rec['certificate_ref']})"}
    if rec["status"] == "DECLINED":
        return {"required": True, "ref": ref, "result": "DECLINED", "detail": f"{ref} declined by {rec['approver']} on {rec['decided']} — bound anyway"}
    if rec["status"] != "APPROVED":
        return {"required": True, "ref": ref, "result": "PENDING", "detail": f"{ref} still pending — bound before approval"}
    if rec["decided"] > (r.get("written_date") or "9999"):
        return {"required": True, "ref": ref, "result": "AFTER_BINDING", "detail": f"{ref} approved {rec['decided']}, after binding on {r.get('written_date')}"}
    fn = COVER.get(rule_id)
    if fn and not fn(rec["approved"], r):
        a = rec["approved"]
        what = {"DA.LIMIT.MAX": f"limit {B.usd(a.get('limit'))}", "DA.REFERRAL.TIV": f"TIV {B.usd(a.get('tiv'))}", "DA.REFERRAL.TIER1_TIV": f"TIV {B.usd(a.get('tiv'))}",
                "DA.DEDUCTIBLE.MIN_AOP": f"AOP deductible {B.usd(a.get('aop_min'))}", "DA.PRICING.BELOW_RANGE": f"premium {B.usd(a.get('premium_min'))}",
                "DA.RESTRICTION.REFER": f"TIV {B.usd(a.get('tiv'))}"}.get(rule_id, "different terms")
        return {"required": True, "ref": ref, "result": "DIFFERENT_TERMS", "detail": f"{ref} approved {what} — written terms exceed the approval"}
    return {"required": True, "ref": ref, "result": REFER_OK, "detail": f"{ref} approved by {rec['approver']} on {rec['decided']}"}


# ============================================================================ exceptions (the breach register)
def _nid(st, prefix):
    st["seq"][prefix] = st["seq"].get(prefix, 0) + 1
    return f"{prefix}-{st['seq'][prefix]:04d}"


def _hist(e, rt, event, by="Control engine", note=""):
    e["history"].append({"date": rt.clock, "event": event, "by": by, "note": note})


def evaluate_rows(st: dict, rt, row_ids: list[str], reason: str = "Re-evaluated") -> dict:
    """(Re)check rows; open, update or resolve their exceptions. Returns counts."""
    added = resolved = 0
    for rid in row_ids:
        r = st["rows"][rid]
        if r.get("duplicate"):
            continue
        results = check_row(st, rt, r)
        r["checks"] = results
        fired = {}
        for c in results:
            if c["result"] in ("PASS", "NA"):
                continue
            ref = reconcile_referral(st, rt, r, c["rule_id"]) if c["outcome"] == "REFER" else None
            fired[c["rule_id"]] = (c, ref)
        for rule_id, (c, ref) in fired.items():
            key = f"{rid}|{rule_id}"
            eid = st["exc_index"].get(key)
            ok = ref is not None and ref["result"] == REFER_OK
            if eid is None:
                eid = _nid(st, "EX")
                e = {"exc_id": eid, "ch": r["ch"], "row_id": rid, "subject_type": "policy", "policy_key": f"{r['ch']}|{r['certificate_ref']}",
                     "certificate_ref": r["certificate_ref"], "insured": r.get("insured_name"), "txn": r.get("transaction_type"), "month": r["month"],
                     "status": REFER_OK if ok else "OPEN", "raised_at": rt.clock, "resolved_at": None, "resolution": None, "query_ids": [], "history": [],
                     "response": None}
                _hist(e, rt, "Authorised by referral" if ok else "Raised", note=(ref or {}).get("detail", ""))
                st["exceptions"][eid] = e
                st["exc_index"][key] = eid
                if not ok:
                    added += 1
            e = st["exceptions"][eid]
            e.update({k: c[k] for k in ("rule_id", "rule_version", "family", "check", "title", "severity", "outcome", "written", "authority", "delta", "impact_usd",
                                        "impact_method", "action", "source", "anchor_written", "anchor_authority", "authority_version")})
            e["referral"] = ref
            e["premium_tied"] = abs(r.get("gross_premium") or 0)
            if ok and e["status"] in OPEN_STATES:
                e["status"], e["resolved_at"] = "RESOLVED", rt.clock
                e["resolution"] = f"Referral approval located — {ref['detail']}"
                _hist(e, rt, "Resolved", note=e["resolution"])
                resolved += 1
            elif not ok and e["status"] in ("RESOLVED", REFER_OK) and e.get("resolution_kind") != "cancelled":
                e["status"], e["resolved_at"], e["resolution"] = "OPEN", None, None
                _hist(e, rt, "Re-opened", note=reason)
                added += 1
        full = None
        for c in results:
            key = f"{rid}|{c['rule_id']}"
            eid = st["exc_index"].get(key)
            if eid and c["rule_id"] not in fired:
                e = st["exceptions"][eid]
                if e["status"] in OPEN_STATES:
                    if full is None:
                        full = {x["rule_id"]: x for x in check_row(st, rt, r, full=True)}
                    c = full[c["rule_id"]]
                    e["status"], e["resolved_at"] = "RESOLVED", rt.clock
                    e["resolution"] = f"{reason} — now within authority ({c['written']} vs {c['authority']})"
                    e["written"] = c["written"]
                    _hist(e, rt, "Resolved", note=e["resolution"])
                    resolved += 1
    return {"added": added, "resolved": resolved}


def subject_exception(st, rt, ch, subject_type, key, rule, env, month, result_outcome, written, expected, impact, anchors=None, extra=None):
    """Zone, claim, capacity and bordereau-level exceptions (one per subject and rule, kept current)."""
    ikey = f"{ch}|{subject_type}|{key}|{rule.rule_id}"
    eid = st["exc_index"].get(ikey)
    if eid is None:
        eid = _nid(st, "EX")
        e = {"exc_id": eid, "ch": ch, "row_id": None, "subject_type": subject_type, "policy_key": (extra or {}).get("policy_key") or f"{ch}|{subject_type}:{key}",
             "certificate_ref": (extra or {}).get("certificate_ref") or key, "insured": (extra or {}).get("insured") or key, "txn": None, "month": month, "status": "OPEN",
             "raised_at": rt.clock, "resolved_at": None, "resolution": None, "query_ids": [], "history": [], "referral": None, "response": None}
        _hist(e, rt, "Raised")
        st["exceptions"][eid] = e
        st["exc_index"][ikey] = eid
    e = st["exceptions"][eid]
    e.update({"rule_id": rule.rule_id, "rule_version": rule.version, "family": rule.family, "check": rule.description or rule.title, "title": rule.title,
              "severity": rule.severity, "outcome": result_outcome, "written": written, "authority": expected, "delta": (extra or {}).get("delta"),
              "impact_usd": round(max(0.0, impact), 2), "impact_method": rule.impact, "action": rule.action, "source": rule.source,
              "anchor_written": (anchors or {}).get("written"), "anchor_authority": (anchors or {}).get("authority"), "premium_tied": (extra or {}).get("premium_tied", 0.0),
              "month": month, "subject_key": key, "claim_ref": (extra or {}).get("claim_ref")})
    if e["status"] == "RESOLVED" and e.get("resolution_kind") == "auto":
        e["status"], e["resolved_at"] = "OPEN", None
        _hist(e, rt, "Re-opened")
    return e


def clear_subject(st, rt, ch, subject_type, key, rule_id, why):
    eid = st["exc_index"].get(f"{ch}|{subject_type}|{key}|{rule_id}")
    if eid:
        e = st["exceptions"][eid]
        if e["status"] in OPEN_STATES:
            e["status"], e["resolved_at"], e["resolution"], e["resolution_kind"] = "RESOLVED", rt.clock, why, "auto"
            _hist(e, rt, "Resolved", note=why)


# ============================================================================ aggregates & capacity
def aggregates(st: dict, ch: str, as_of: str) -> list[dict]:
    terms, anchors, _v = authority(st, ch, as_of)
    zones = {z: {"zone": z, **a, "tiv": 0.0, "opening": 0.0, "movement": 0.0, "policies": 0, "new_tiv": 0.0} for z, a in (terms.get("aggregates") or {}).items()}
    for k, x in st["exposure"].get(ch, {}).items():
        z = zone_of(st, ch, x["state"], x["county"])
        if z in zones:
            zones[z]["opening"] += x["tiv"]
            zones[z]["policies"] += x["policies"]
    for r in st["rows"].values():
        if r["ch"] != ch or r.get("duplicate") or (r.get("written_date") or "9999") > as_of:
            continue
        z = zone_of(st, ch, r.get("state"), r.get("county"))
        if z not in zones or r.get("tiv") is None:
            continue
        t = r.get("transaction_type")
        d = r["tiv"] if t == "NEW" else (r["tiv"] - (r.get("prior_tiv") or r["tiv"])) if t in ("RENEWAL", "ENDORSEMENT") else -r["tiv"] if t == "CANCELLATION" else 0
        zones[z]["movement"] += d
        zones[z]["policies"] += 1 if t == "NEW" else -1 if t == "CANCELLATION" else 0
        if t == "NEW":
            zones[z]["new_tiv"] += r["tiv"]
    out = []
    for z, x in zones.items():
        x["tiv"] = x["opening"] + x["movement"]
        x["util"] = x["tiv"] / x["limit"] if x.get("limit") else None
        x["pml_100"] = x["tiv"] * PML_RATIO.get(x.get("peril"), 0.05)
        x["anchor"] = anchors.get(f"aggregates.{z}")
        out.append(x)
    return sorted(out, key=lambda x: -(x["util"] or 0))


def capacity(st: dict, ch: str, as_of: str) -> dict:
    terms, anchors, _v = authority(st, ch, as_of)
    ytd = st["opening_gwp"].get(ch, 0.0) + sum(r.get("gross_premium") or 0 for r in st["rows"].values() if r["ch"] == ch and not r.get("duplicate")
                                                 and (r.get("written_date") or "9999") <= as_of)
    months = max(1, int(as_of[5:7]))
    return {"ytd": ytd, "projected": ytd / months * 12, "limit": terms.get("gpi_limit"), "util": ytd / months * 12 / terms["gpi_limit"] if terms.get("gpi_limit") else None,
            "anchor": anchors.get("gpi_limit")}


def evaluate_zones(st, rt, ch: str, month_end: str, month: str):
    zs = aggregates(st, ch, month_end)
    for rule in rules(rt, "zone"):
        for z in zs:
            if z.get("util") is None:
                continue
            env = {"zone": {k: z.get(k) for k in ("util", "warn", "tiv", "limit", "name")}}
            v = evaluate(rule.code, env)
            if v:
                subject_exception(st, rt, ch, "zone", z["zone"], rule, env, month, rule.outcome, fmt(rule.observed, env), fmt(rule.expected, env),
                                  z["tiv"] - (z.get("warn") or 1) * z["limit"], {"written": None, "authority": z.get("anchor")},
                                  {"insured": f"{z['name']} ({z['zone']})", "certificate_ref": z["zone"], "policy_key": f"{ch}|zone:{z['zone']}",
                                   "delta": f"{(z['util'] - (z.get('warn') or 1)) * 100:+.1f} pts"})
            else:
                clear_subject(st, rt, ch, "zone", z["zone"], rule.rule_id, f"{z['name']} at {z['util'] * 100:.1f}% on {month_end}")
    cap = capacity(st, ch, month_end)
    for rule in rules(rt, "capacity"):
        env = {"cap": {k: cap[k] for k in ("ytd", "projected", "limit")}}
        if evaluate(rule.code, env):
            subject_exception(st, rt, ch, "capacity", "GPI", rule, env, month, rule.outcome, fmt(rule.observed, env), fmt(rule.expected, env), 0.0,
                              {"authority": cap.get("anchor")}, {"insured": "Gross premium income", "certificate_ref": "GPI"})
        else:
            clear_subject(st, rt, ch, "capacity", "GPI", rule.rule_id, "Projection within the GPI limit")


# ============================================================================ claims
def claims_view(st: dict, ch: str) -> list[dict]:
    """Latest snapshot of every claim with movement, first carrier notice and the policy it sits on."""
    out = []
    for cref, snaps in st["claims"].get(ch, {}).items():
        months = sorted(snaps)
        cur = snaps[months[-1]]
        prev = snaps[months[-2]] if len(months) > 1 else None
        first = snaps[months[0]]
        out.append({**cur, "claim_ref": cref, "months": months, "prior_incurred": prev["incurred"] if prev else None, "first_incurred": first["incurred"],
                    "first_seen": first["received"], "incurred_change": (cur["incurred"] - prev["incurred"]) if prev else 0.0,
                    "incurred_change_pct": ((cur["incurred"] - prev["incurred"]) / prev["incurred"]) if prev and prev["incurred"] else 0.0})
    return out


def evaluate_claims(st, rt, ch: str):
    terms, anchors, _v = authority(st, ch, rt.clock)
    a = auth_env(terms)
    pol_rows = {}
    for r in st["rows"].values():
        if r["ch"] == ch and r.get("transaction_type") in ("NEW", "RENEWAL"):
            pol_rows[r["certificate_ref"]] = r
    for c in claims_view(st, ch):
        pol = pol_rows.get(c["certificate_ref"])
        open_exc = [e for e in st["exceptions"].values() if pol and e.get("row_id") == pol["row_id"] and e["status"] in OPEN_STATES + ("ACCEPTED",)
                    and e["outcome"] in ("BREACH", "REFER") and e.get("status") != "ACCEPTED"]
        lla = st["loss_advices"].get(f"{ch}|{c['claim_ref']}")
        notice = min([x for x in (lla, c["first_seen"]) if x])
        days = (date.fromisoformat(notice) - date.fromisoformat(c["date_reported"])).days if c.get("date_reported") else None
        env = {"claim": {"claim_ref": c["claim_ref"], "incurred": c["incurred"], "paid": c["paid"], "first_incurred": c["first_incurred"], "days_to_carrier": days,
                         "incurred_change": c["incurred_change"], "incurred_change_pct": c["incurred_change_pct"], "prior_incurred": c["prior_incurred"],
                         "policy_outside_authority": bool(open_exc), "policy_exception": open_exc[0]["title"] if open_exc else None,
                         "handled_by_coverholder": (c.get("handled_by") or "").lower().startswith("coverholder"), "date_of_loss": c["date_of_loss"],
                         "policy_inception": pol.get("inception") if pol else None, "policy_expiry": pol.get("expiry") if pol else None}, "auth": a}
        c["days_to_carrier"] = days
        for rule in rules(rt, "claim"):
            v = evaluate(rule.code, env)
            if v:
                imp = {"claim_incurred": c["incurred"], "claim_change": c["incurred_change"], "claim_paid_excess": c["paid"] - (a.get("claims_authority") or 0)}.get(rule.impact, 0.0)
                subject_exception(st, rt, ch, "claim", c["claim_ref"], rule, env, c["months"][-1], rule.outcome, fmt(rule.observed, env), fmt(rule.expected, env), imp,
                                  {"written": c.get("anchor"), "authority": anchors.get({"DA.CLAIM.LATE_LARGE_LOSS": "large_loss_days", "DA.CLAIM.SETTLEMENT_AUTHORITY": "claims_authority"}.get(rule.rule_id, ""))
                                   or (open_exc[0].get("anchor_authority") if open_exc else None)},
                                  {"insured": c["insured_name"], "certificate_ref": c["certificate_ref"], "policy_key": f"{ch}|{c['certificate_ref']}", "claim_ref": c["claim_ref"]})
            else:
                clear_subject(st, rt, ch, "claim", c["claim_ref"], rule.rule_id, "No longer applies on the latest claims bordereau")


def evaluate_bordereau(st, rt, doc_id: str):
    b = st["bdx"][doc_id]
    ch = b["ch"]
    terms, anchors, _v = authority(st, ch, b["due"])
    env = {"bdx": {"days_late": b["days_late"], "received": b["received"], "due": b["due"], "missing": b["missing"],
                   "missing_list": ", ".join(b.get("missing_labels", []))}, "auth": auth_env(terms)}
    if b.get("correction") and not b.get("replaces"):
        return
    for rule in rules(rt, "bordereau"):
        key = f"{b['kind']}:{b['month']}"
        if b.get("superseded_by") and rule.rule_id == "DA.DATA.MANDATORY_FIELDS":
            continue
        if (rule.rule_id == "DA.DATA.LATE_BORDEREAU" and (b["kind"] != "risk" or b.get("correction"))) or (rule.rule_id == "DA.DATA.MANDATORY_FIELDS" and b["kind"] == "claims"):
            continue
        if evaluate(rule.code, env):
            e = subject_exception(st, rt, ch, "bordereau", key, rule, env, b["month"], rule.outcome, fmt(rule.observed, env), fmt(rule.expected, env), 0.0,
                              {"written": {"doc_id": doc_id, "kind": "xlsx", "sheet": b["sheet"], "cell": f"A{b['header_row'] or 1}"}, "authority": anchors.get("bordereau_due_days")},
                              {"insured": f"{b['kind'].capitalize()} bordereau {b['month']}", "certificate_ref": b["title"], "policy_key": f"{ch}|bdx:{key}"})
            if rule.rule_id == "DA.DATA.LATE_BORDEREAU" and e["status"] == "OPEN":
                e["status"], e["resolved_at"], e["resolution"] = "ACCEPTED", rt.clock, "Recorded on the coverholder scorecard (timeliness)"
                _hist(e, rt, "Recorded", note=e["resolution"])
        else:
            clear_subject(st, rt, ch, "bordereau", key, rule.rule_id, f"Resolved by {b['title']}")


# ============================================================================ reporting
def policy_rows(st, ch=None, month=None):
    return [r for r in st["rows"].values() if (ch is None or r["ch"] == ch) and (month is None or r["month"] == month) and not r.get("duplicate")]


def raised(e) -> bool:
    return e["status"] != REFER_OK


def month_stats(st: dict, ch: str, month: str) -> dict:
    rows = policy_rows(st, ch, month)
    ids = {r["row_id"] for r in rows}
    ex = [e for e in st["exceptions"].values() if e.get("row_id") in ids and raised(e)]
    pol_ex = {e["row_id"] for e in ex}
    open_pol = {e["row_id"] for e in ex if e["status"] in OPEN_STATES}
    by = {}
    for e in ex:
        by.setdefault(e["family"], []).append(e)
    comm = sum(e["impact_usd"] for e in ex if e["family"] == "commission")
    return {"month": month, "policies": len(rows), "with_exceptions": len(pol_ex), "exception_rate": len(pol_ex) / len(rows) if rows else 0.0,
            "open_policies": len(open_pol), "within_authority": 1 - len(open_pol) / len(rows) if rows else 1.0,
            "premium": sum(r.get("gross_premium") or 0 for r in rows), "premium_tied": sum(abs(st["rows"][rid].get("gross_premium") or 0) for rid in pol_ex),
            "commission_discrepancy": comm, "exposure_above": sum(e["impact_usd"] for e in ex if e["family"] == "limit"),
            "missing_referrals": sum(1 for e in ex if e.get("referral") and e["referral"]["result"] != REFER_OK), "by_type": {k: len(v) for k, v in by.items()},
            "exceptions": len(ex), "open": sum(1 for e in ex if e["status"] in OPEN_STATES)}


def months_of(st, ch) -> list[str]:
    return sorted({b["month"] for b in st["bdx"].values() if b["ch"] == ch and b["kind"] == "risk" and not b.get("correction")})


def scorecard(st: dict, rt, ch: str) -> dict:
    ms = [month_stats(st, ch, m) for m in months_of(st, ch)]
    bd = [b for b in st["bdx"].values() if b["ch"] == ch and b["kind"] in ("risk", "premium", "claims") and not b.get("correction")]
    latest = {}
    for b in st["bdx"].values():
        if b["ch"] == ch and b["kind"] in ("risk", "premium"):
            k = (b["kind"], b["month"])
            if k not in latest or b["received"] >= latest[k]["received"]:
                latest[k] = b
    dq = sum(b["dq_score"] for b in latest.values()) / len(latest) if latest else None
    late = [b["days_late"] for b in bd if b["kind"] == "risk"]
    rows = policy_rows(st, ch)
    open_pol = {e["row_id"] for e in st["exceptions"].values() if e["ch"] == ch and e.get("row_id") and e["status"] in OPEN_STATES}
    gwp = st["opening_gwp"].get(ch, 0) + sum(r.get("gross_premium") or 0 for r in rows)
    incurred = sum(c["incurred"] for c in claims_view(st, ch))
    months_written = 4 + len(ms)
    lr = incurred / gwp if gwp else None
    res = [e for e in st["exceptions"].values() if e["ch"] == ch and e["status"] == "RESOLVED" and e.get("query_ids") and e.get("resolved_at")]
    turn = [(date.fromisoformat(e["resolved_at"]) - date.fromisoformat(e["raised_at"])).days for e in res]
    last2 = [m["exception_rate"] for m in ms[-2:]]
    rate_recent = sum(last2) / len(last2) if last2 else 0
    trend = [round(m["exception_rate"], 4) for m in ms]
    delta = trend[-1] - trend[0] if len(trend) >= 2 else 0.0
    claims_open = sum(1 for e in st["exceptions"].values() if e["ch"] == ch and e["subject_type"] == "claim" and e["status"] in OPEN_STATES and e["severity"] in ("CRITICAL", "HIGH"))
    c_auth = max(0.0, 100 - 3000 * rate_recent - 8 * claims_open)
    c_dq = dq or 0
    c_time = max(0.0, 100 - 8 * (sum(late) / len(late) if late else 0))
    c_loss = max(0.0, 100 - max(0.0, (lr or 0) - 0.45) * 200)
    c_trend = max(0.0, 100 - max(0.0, delta - 0.003) * 5000)
    score = 0.35 * c_auth + 0.2 * c_dq + 0.15 * c_time + 0.15 * c_loss + 0.15 * c_trend
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "E"
    return {"ch": ch, "policies": len(rows), "within_authority": 1 - len(open_pol) / len(rows) if rows else 1.0, "open_policies": len(open_pol),
            "trend": [{"month": m["month"], "rate": m["exception_rate"], "policies": m["policies"], "with_exceptions": m["with_exceptions"]} for m in ms],
            "direction": "deteriorating" if delta > 0.008 else "improving" if delta < -0.008 else "stable",
            "dq_score": round(dq, 1) if dq is not None else None, "avg_days_late": round(sum(late) / len(late), 1) if late else 0, "on_time": sum(1 for x in late if x <= 0) / len(late) if late else 1.0,
            "gwp": gwp, "incurred": incurred, "loss_ratio": lr, "turnaround_days": round(sum(turn) / len(turn), 1) if turn else None, "resolved_via_query": len(res),
            "open_queries": sum(1 for q in st["queries"] if q["ch"] == ch and q["status"] in ("SENT", "RESPONDED")),
            "components": {"authority": round(c_auth, 1), "data_quality": round(c_dq, 1), "timeliness": round(c_time, 1), "loss": round(c_loss, 1), "trend": round(c_trend, 1)},
            "score": round(score, 1), "grade": grade}


def rarc(st: dict, ch: str) -> dict:
    """Quarterly RARC from renewal lines on the risk bordereaux.
    Per renewal: expected = expiring premium × (renewal TIV ÷ expiring TIV) × (deductible factor now ÷ deductible factor expiring),
    factors from the BAA rating rules. RARC = Σ renewal premium ÷ Σ expected − 1 (weighted by expiring premium).
    Headline = Σ renewal premium ÷ Σ expiring premium − 1. Rate on TIV = premium per $100 TIV, renewal vs expiring.
    Renewals without expiring premium or TIV are excluded and counted."""
    qs: dict[str, dict] = {}
    for r in policy_rows(st, ch):
        if r.get("transaction_type") != "RENEWAL":
            continue
        m = r["month"]
        q = f"Q{(int(m[5:7]) - 1) // 3 + 1} {m[:4]}"
        x = qs.setdefault(q, {"quarter": q, "months": set(), "renewals": 0, "used": 0, "excluded": 0, "p0": 0.0, "p1": 0.0, "expected": 0.0, "tiv0": 0.0, "tiv1": 0.0,
                              "lim1": 0.0, "by_month": {}})
        x["months"].add(m)
        x["renewals"] += 1
        if not (r.get("prior_premium") and r.get("prior_tiv") and r.get("gross_premium") and r.get("tiv")):
            x["excluded"] += 1
            continue
        terms, _a, _v = authority(st, ch, r.get("written_date"))
        d1 = ded_factor(terms, r.get("aop_deductible"))
        d0 = ded_factor(terms, r.get("prior_aop_deductible") or r.get("aop_deductible"))
        e = r["prior_premium"] * (r["tiv"] / r["prior_tiv"]) * (d1 / d0)
        x["used"] += 1
        x["p0"] += r["prior_premium"]
        x["p1"] += r["gross_premium"]
        x["expected"] += e
        x["tiv0"] += r["prior_tiv"]
        x["tiv1"] += r["tiv"]
        x["lim1"] += r.get("limit") or 0
        bm = x["by_month"].setdefault(m, {"month": m, "p0": 0.0, "p1": 0.0, "expected": 0.0, "n": 0})
        bm["p0"] += r["prior_premium"]
        bm["p1"] += r["gross_premium"]
        bm["expected"] += e
        bm["n"] += 1
    out = []
    for q, x in sorted(qs.items(), key=lambda kv: (kv[0][-4:], kv[0])):
        ms = sorted(x["months"])
        out.append({"quarter": q, "months": ms, "label": f"{q} ({', '.join(m[5:] for m in ms)} reported)", "renewals": x["renewals"], "used": x["used"], "excluded": x["excluded"],
                    "expiring_premium": x["p0"], "renewal_premium": x["p1"], "expected_premium": x["expected"],
                    "headline": x["p1"] / x["p0"] - 1 if x["p0"] else None, "rarc": x["p1"] / x["expected"] - 1 if x["expected"] else None,
                    "exposure_change": x["tiv1"] / x["tiv0"] - 1 if x["tiv0"] else None,
                    "rate_on_tiv": (x["p1"] / x["tiv1"] * 100) if x["tiv1"] else None, "rate_on_tiv_prior": (x["p0"] / x["tiv0"] * 100) if x["tiv0"] else None,
                    "rate_on_line": x["p1"] / x["lim1"] if x["lim1"] else None,
                    "by_month": [{"month": b["month"], "renewals": b["n"], "headline": b["p1"] / b["p0"] - 1 if b["p0"] else None,
                                  "rarc": b["p1"] / b["expected"] - 1 if b["expected"] else None} for b in sorted(x["by_month"].values(), key=lambda b: b["month"])]})
    return {"method": rarc.__doc__.split("\n", 1)[1].strip().replace("\n    ", " "), "quarters": out}


def report(st: dict, rt, ch: str, month: str) -> dict:
    """Monthly authority report for one coverholder."""
    s = month_stats(st, ch, month)
    me = f"{month}-{'31' if month[5:] in ('05', '07', '08') else '30'}"
    zs = aggregates(st, ch, me)
    ids = {r["row_id"] for r in policy_rows(st, ch, month)}
    ex = [e for e in st["exceptions"].values() if e.get("row_id") in ids and raised(e)]
    types = {}
    for e in ex:
        t = types.setdefault(e["family"], {"family": e["family"], "label": FAMILY_LABEL.get(e["family"], e["family"]), "count": 0, "open": 0, "impact_usd": 0.0, "premium_tied": 0.0})
        t["count"] += 1
        t["open"] += e["status"] in OPEN_STATES
        t["impact_usd"] += e["impact_usd"]
        t["premium_tied"] += e["premium_tied"]
    sc = scorecard(st, rt, ch)
    recs = []
    if s["open"]:
        recs.append("Carrier review of open exceptions; query the coverholder with the side-by-side evidence")
    if s["commission_discrepancy"] > 0:
        recs.append("Commission reconciliation — debit note for over-deducted commission")
    if s["missing_referrals"]:
        recs.append("Reconcile missing referrals; repeated gaps warrant an audit visit")
    for z in zs:
        if z.get("util") and z["util"] >= (z.get("warn") or 0.9):
            recs.append(f"{z['name']} at {z['util'] * 100:.0f}% of aggregate — refer or stop incremental business")
    if sc["direction"] == "deteriorating":
        recs.append("Exception rate deteriorating month on month — audit visit and authority review")
    return {**s, "ch": ch, "zones": zs, "types": sorted(types.values(), key=lambda t: -t["count"]), "trend": sc["trend"], "direction": sc["direction"],
            "recommendations": recs, "grade": sc["grade"]}

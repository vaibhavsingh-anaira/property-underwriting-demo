"""Account evaluation: snapshots → contexts → rules → findings → impact → actions → narrative."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import TYPE_CHECKING, Any

from uwc.engine import pricing as P
from uwc.engine.rules import evaluate as eval_rule, fmt
from uwc.engine.views import contract_stage, snapshots
from uwc.ledger.fields import display
from uwc.mocks import cat as catmodel, rater
from uwc.refdata import CONSTRUCTION, NOTICE_DAYS, NOTICE_REF, OCCUPANCY, SAFEGUARD_CODES, ZONES, guideline_for, USER_BY_ID, AUTHORITY

if TYPE_CHECKING:
    from uwc.runtime import Runtime

PML_FACTOR = {"Hurricane": 0.22, "Earthquake": 0.16, "Severe convective storm": 0.06, "Fire / BI concentration": 0.30}
SEV_PENALTY = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2.5, "LOW": 1}
OUTCOME_ACTION = {"PRICE_ADJUST": "REPRICE", "TERM_BREACH": "RESTRUCTURE", "CONDITION": "CONDITION", "REFER": "REFER", "BLOCK": "REFER",
                  "DATA_REQUEST": "DATA_REQUEST", "DECLINE": "NON_RENEW"}
CONTROL_METHODS = {"control_premium", "control_tiv"}
CONTRACT_LABEL = {"limit": "Limit", "aop_deductible": "AOP deductible", "named_storm_ded_pct": "Named storm deductible",
                  "named_storm_ded_min": "Named storm minimum", "wind_hail_ded_pct": "Wind/hail deductible", "bi_sublimit": "Business income sublimit",
                  "flood_sublimit": "Flood sublimit", "eq_sublimit": "Earthquake sublimit", "premium": "Premium", "forms": "Forms",
                  "safeguards": "Protective safeguards", "subjectivities": "Subjectivities", "limit_basis": "Limit basis"}
CONTRACT_GROUP = {"limit": "Limits", "limit_basis": "Limits", "aop_deductible": "Deductibles", "named_storm_ded_pct": "Deductibles",
                  "named_storm_ded_min": "Deductibles", "wind_hail_ded_pct": "Deductibles", "bi_sublimit": "Sublimits", "flood_sublimit": "Sublimits",
                  "eq_sublimit": "Sublimits", "premium": "Premium", "forms": "Forms", "safeguards": "Safeguards", "subjectivities": "Subjectivities"}


def d(s: str) -> date:
    return date.fromisoformat(s[:10])


def fmt_contract(f: str, v: Any) -> str | None:
    if v is None:
        return None
    if f.endswith("_pct"):
        return f"{v * 100:.1f}%".replace(".0%", "%")
    if isinstance(v, (int, float)):
        return f"${v:,.0f}"
    if isinstance(v, list):
        if f == "safeguards":
            return f"{len(v)} scheduled"
        return f"{len(v)} items"
    return str(v)


# =============================================================================== contract
def contract_views(rt: "Runtime", acct: str, renewal: bool = False) -> dict[str, dict]:
    pre = "r_" if renewal else ""
    st = rt.contract_stages.get(acct, {})
    out = {}
    q = st.get(f"{pre}quote_accepted")
    if q:
        out["quote"] = contract_stage(rt, acct, q)
    for k in ("binder", "policy"):
        if st.get(f"{pre}{k}"):
            out[k] = contract_stage(rt, acct, f"{pre}{k}")
    if "policy" in out and not renewal:
        e = dict(out["policy"])
        for endt in rt.pas[acct].get("endorsements_applied", []):
            for k, v in endt.get("changes", {}).items():
                if k in e:
                    e[k] = v
        out["endorsed"] = e
    return out


def contract_diffs(views: dict[str, dict], safeguard_labels: dict[str, str]) -> list[dict]:
    rows = []
    fields = ["limit", "limit_basis", "aop_deductible", "named_storm_ded_pct", "named_storm_ded_min", "wind_hail_ded_pct", "bi_sublimit",
              "flood_sublimit", "eq_sublimit", "premium", "forms", "safeguards"]
    for f in fields:
        vals = {k: v.get(f) for k, v in views.items()}
        for pair, a, b in (("quote_binder", "quote", "binder"), ("binder_policy", "binder", "policy")):
            if a not in views or b not in views:
                continue
            va, vb = vals.get(a), vals.get(b)
            if f == "premium":
                continue
            if isinstance(va, list) or isinstance(vb, list):
                if pair == "quote_binder" and (va is None or vb is None):
                    continue
                sa, sb = set(va or []), set(vb or [])
                if sa != sb:
                    missing = sorted(sa - sb)
                    added = sorted(sb - sa)
                    lab = CONTRACT_LABEL[f]
                    desc_a = ", ".join(_sg(x, safeguard_labels) for x in missing) or "—"
                    desc_b = ", ".join(_sg(x, safeguard_labels) for x in added) or "missing"
                    rows.append({"pair": pair, "field": f, "label": lab, "a": desc_a, "b": desc_b, "result": "MISSING" if missing else "ADDED",
                                 "a_obs": views[a]["_obs"].get(f), "b_obs": views[b]["_obs"].get(f), "raw_a": va, "raw_b": vb})
                continue
            if va != vb and not (va is None and vb is None):
                rows.append({"pair": pair, "field": f, "label": CONTRACT_LABEL[f], "a": fmt_contract(f, va) or "none", "b": fmt_contract(f, vb) or "none",
                             "result": "MISSING" if vb is None else "MISMATCH", "a_obs": views[a]["_obs"].get(f), "b_obs": views[b]["_obs"].get(f),
                             "raw_a": va, "raw_b": vb})
    return rows


def _sg(x: str, labels: dict[str, str]) -> str:
    uid, code = x.split("|") if "|" in x else (x, "")
    return f"{code} at {labels.get(uid, uid)}"


# =============================================================================== evaluate
def evaluate_account(rt: "Runtime", acct: str, pass_no: int | None = None) -> None:
    ren = rt.ren[acct]
    if pass_no:
        ren.pass_no = max(ren.pass_no, pass_no)
        ren.pass_dates.setdefault(pass_no, rt.clock)
    if ren.pass_no == 0:
        return
    today = rt.clock_date
    g = guideline_for(today)
    pas = rt.pas.get(acct)
    if not pas or not pas.get("term_start"):
        return
    reg = rt.systems["accounts"][acct]
    snaps = snapshots(rt, acct)
    E0, E1 = snaps["E0"], snaps["E1"]
    if not E0:
        return
    locs = rt.store.account_locations(acct)
    labels = {uid: e.label for uid, e in locs.items()}
    cviews = contract_views(rt, acct)
    exp_terms = dict(cviews.get("endorsed") or cviews.get("policy") or cviews.get("binder") or {})
    exp_terms.setdefault("limit_basis", "blanket")
    has_t1 = any(s.get("wind_tier") == "T1" for s in snaps["current"])
    # ------------------------------------------------ working proposal
    quote = ren.quotes[-1] if ren.quotes else None
    if quote:
        T1 = {**exp_terms, **quote["terms"]}
        proposed = quote["premium"]
        src = f"quote v{quote['version']}"
    else:
        T1 = P.recommended_terms(rt, acct, exp_terms, has_t1)
        proposed = None
        src = "platform-recommended terms"
    target = rt.account_value(acct, "target_premium")
    r = P.compute(rt, acct, E0, E1, exp_terms, T1, proposed or target or 0)
    if proposed is None:
        proposed = target if target else pas["premium"]
        r = P.compute(rt, acct, E0, E1, exp_terms, T1, proposed)
    r00, r10, r11 = r.pop("_runs")
    ren.working = {"terms": P.terms_only(T1), "premium": proposed, "source": src if quote else ("broker target premium on guideline-compliant terms" if target else "expiring premium on guideline-compliant terms (as-is renewal)")}
    ren.rarc = r
    ren.rarc["expiring_terms"] = P.terms_only(exp_terms)
    ren.rarc["proposed_terms"] = P.terms_only(T1)
    # ------------------------------------------------ CAT runs (current = E1,T0; proposed = E1,T1)
    rt.record_cat_run(acct, "CURRENT", E1, exp_terms, r10["cat"])
    rt.record_cat_run(acct, "RENEWAL_PROPOSED", E1, T1, r11["cat"])
    loc_aal = r10["cat"]["loc_aal"]
    total_aal = sum(loc_aal.values()) or 1.0
    rol = r["tp_e1_t1"] / max(1.0, r["tiv_renewal"])
    # ------------------------------------------------ location contexts
    claims = rt.claims.get(acct, [])
    from uwc.ingest.interpret import _loc_by_address
    for c in claims:
        if not c.get("location_uid") and c.get("location_address"):
            c["location_uid"] = _loc_by_address(rt, acct, c["location_address"])
    for rec in rt.recs.get(acct, {}).values():
        if not rec.get("location_uid") and rec.get("location_address"):
            rec["location_uid"] = _loc_by_address(rt, acct, rec["location_address"])
    term_start = pas["term_start"]
    prior_by_uid = {s["location_uid"]: s for s in snaps["prior"]}
    att_rows = {x["location_uid"]: x["loss_cost"] for x in rater.attritional(E1)[1]}
    loc_ctx = []
    uids = [s["location_uid"] for s in snaps["current"]] + [uid for uid, e in locs.items() if e.in_prior and not e.in_current and rt.renewal_sov.get(acct)]
    cur_by_uid = {s["location_uid"]: s for s in snaps["current"]}
    safeguards = exp_terms.get("safeguards") or []
    for uid in uids:
        s = dict(cur_by_uid.get(uid) or prior_by_uid.get(uid) or {})
        e = locs[uid]
        p = prior_by_uid.get(uid, {})
        s["match_status"] = e.match_status
        s["match_method"] = e.match_method
        s["match_score"] = e.match_score
        s["in_cat_run"] = bool(rt.store.field_obs(uid, "cat_input_construction"))
        s["occupancy_prior"] = p.get("occupancy_class") if e.in_prior else None
        s["occupancy_label"] = OCCUPANCY.get(s.get("occupancy_class"), ("—",))[0]
        s["occupancy_prior_label"] = OCCUPANCY.get(s.get("occupancy_prior"), ("—",))[0]
        if s.get("model_rc") and s.get("building_value"):
            s["valuation_ratio"] = s["building_value"] / s["model_rc"]
        pb = p.get("building_value")
        s["value_flat"] = bool(pb and s.get("building_value") and abs(s["building_value"] - pb) < 1 and e.in_current and rt.renewal_sov.get(acct))
        s["cost_trend"] = 0.052
        c_roof = [o for o in rt.store.field_obs(uid, "roof_year") if o.obs_type == "C"]
        s["roof_year_reported"] = c_roof[-1].value if c_roof else None
        s["roof_conflict"] = "roof_year" in s.get("_conflicts", {})
        s["roof_age"] = today.year - s["roof_year"] if s.get("roof_year") else None
        wc = [c for c in claims if c.get("location_uid") == uid and c["cause"] == "water_nonweather" and c["dol"] >= term_start]
        s["water_claims_since_bind"] = len(wc)
        s["water_incurred"] = sum(c["paid"] + c["reserve"] for c in wc)
        s["cat_input_construction_label"] = CONSTRUCTION.get(s.get("cat_input_construction") or 0, ("—",))[0]
        s["construction_label"] = CONSTRUCTION.get(s.get("construction_class") or 0, ("—",))[0]
        s["monitored_text"] = {True: "yes", False: "no (local alarm)", None: "no certificate"}[s.get("burglar_monitored")]
        gaps = []
        for sg in safeguards:
            su, code = sg.split("|") if "|" in sg else (sg, "")
            if su != uid:
                continue
            if code == "P-1" and (s.get("sprinkler_impaired") or (s.get("sprinkler_pct") is not None and s["sprinkler_pct"] < 1)):
                gaps.append(f"P-1 sprinkler: {'impaired' if s.get('sprinkler_impaired') else 'partial protection'}")
            if code == "P-4" and s.get("burglar_monitored") is not True:
                gaps.append(f"P-4 monitored burglar alarm: {s['monitored_text']}")
            if code == "P-5" and s.get("cooking_suppression_verified") is not True:
                gaps.append("P-5 cooking suppression: no current certificate")
        s["safeguard_gaps"] = gaps
        s["safeguard_gap_text"] = "; ".join(gaps)
        vs = s.get("vacancy_since")
        s["vacancy_days"] = (today - d(vs)).days if vs else 0
        s["tiv"] = s.get("tiv") or 0
        s["aal"] = loc_aal.get(uid)
        loc_ctx.append(s)
    # ------------------------------------------------ account context
    since = [c for c in claims if c["dol"] >= term_start]
    fire3 = [c for c in claims if c["cause"] == "fire" and c["dol"] >= f"{today.year - 3}-{today.month:02d}-01"]
    missing_mod = [s for s in loc_ctx if s.get("in_current") and not s.get("roof_year") and (s.get("aal") or 0) > 0]
    appraisal = rt.account_value(acct, "appraisal_date")
    tiv_prior = sum(sum((l[k] for k in ("building", "contents", "stock", "bi"))) for l in E0)
    tiv_cur = sum(sum((l[k] for k in ("building", "contents", "stock", "bi"))) for l in E1)
    zone = zone_update(rt, acct, snaps, pas)
    days_to_expiry = (d(pas["term_end"]) - today).days
    notice = notice_info(reg, pas, today)
    ctx_acct = {
        "renewal_sov_received": bool(rt.renewal_sov.get(acct)), "days_to_expiry": days_to_expiry, "occ_family": reg["occupancy_family"],
        "occ_label": OCCUPANCY.get(reg["occupancy_family"], ("—",))[0], "has_t1": has_t1,
        "missing_modifier_locs": len(missing_mod), "missing_modifier_aal_share": sum(s.get("aal") or 0 for s in missing_mod) / total_aal,
        "max_claim_since_bind": max([c["paid"] + c["reserve"] for c in since] or [0]), "repeat_fire_claims": len(fire3),
        "repeat_fire_sites": len({c.get("location_uid") for c in fire3}), "cash_on_premises": rt.account_value(acct, "cash_on_premises"),
        "has_crime_form": "NS-CR 01 00" in (((quote or {}).get("terms") or {}).get("forms") or exp_terms.get("forms") or []), "appraisal_date": appraisal,
        "appraisal_age_years": (today.year - int(appraisal[:4])) if appraisal else None, "tiv_prior": tiv_prior, "tiv_current": tiv_cur,
        "cooking_certs_provided": any(o.field_code == "hood_cleaning_ok" for o in rt.store.account_obs(acct)),
        **zone,
    }
    uw = USER_BY_ID[reg["underwriter_id"]]
    pricing_ctx = {**r, "uw_min_rarc": AUTHORITY[uw["authority_level"]]["min_rarc"], "tp": r["tp_e1_t1"],
                   "expiring_adequacy": r["expiring_premium"] / r["tp_e0_t0"] if r["tp_e0_t0"] else None}
    if quote:
        terms_ctx = {**P.terms_only(T1), "source": f"quote v{quote['version']}"}
    else:
        req = rt.account_value(acct, "requested_ns_ded_pct")
        base_t = P.terms_only(exp_terms)
        if req is not None:
            base_t["named_storm_ded_pct"] = req
        terms_ctx = {**base_t, "source": "broker-requested terms" if req is not None else "expiring terms — no renewal quote yet"}
    pricing_ctx["has_proposal"] = bool(quote or target)
    # ------------------------------------------------ recs / subjectivities / approvals
    rec_ctx = []
    for rec in rt.recs.get(acct, {}).values():
        linked = [c for c in claims if c.get("linked_rec") == rec["rec_id"]]
        rec_ctx.append({**rec, "days_overdue": max(0, (today - d(rec["due"])).days) if rec["status"] not in ("VERIFIED_CLOSED",) else 0,
                        "linked_incurred": sum(c["paid"] + c["reserve"] for c in linked), "location_label": labels.get(rec.get("location_uid"), "")})
    subj_ctx = []
    bind_date = pas.get("bind_date")
    for sj in pas.get("subjectivities", []):
        subj_ctx.append({**sj, "age_days": (today - d(bind_date)).days if bind_date else 0})
    if ren.r_bound:
        from uwc.fulfilment import renewal_subjectivities
        for sj in renewal_subjectivities(rt, acct):
            subj_ctx.append({**sj, "age_days": (today - d(ren.r_bound["date"])).days})
    appr = approval_ctx(rt, acct)
    diffs = contract_diffs(cviews, labels)
    if ren.r_bound:
        rv = contract_views(rt, acct, renewal=True)
        diffs += [dict(x, renewal=True) for x in contract_diffs(rv, labels)]
    # ------------------------------------------------ run rules
    env_base = {"acct": ctx_acct, "g": g, "pricing": pricing_ctx, "terms": terms_ctx, "exp_terms": P.terms_only(exp_terms)}
    fired: dict[str, dict] = {}
    rule_levels: list[tuple[int, str]] = []
    for rule in rt.rules.values():
        if rule.product != "renewal" or not rule.active(rt.clock) or ren.pass_no not in rule.passes:
            continue
        subjects: list[tuple[str, str, dict]] = []
        if rule.applies_to == "account":
            subjects = [("account", acct, {})]
        elif rule.applies_to == "location":
            subjects = [("location", s["location_uid"], {"loc": s}) for s in loc_ctx]
        elif rule.applies_to == "contract_field":
            subjects = [("contract", f"{acct}:{x['pair']}:{x['field']}" + (":r" if x.get("renewal") else ""), {"diff": x}) for x in diffs]
        elif rule.applies_to == "recommendation":
            subjects = [("recommendation", f"{acct}:{x['rec_id']}", {"rec": x}) for x in rec_ctx]
        elif rule.applies_to == "subjectivity":
            subjects = [("contract", f"{acct}:subj:{i}", {"subj": x}) for i, x in enumerate(subj_ctx)]
        for stype, sid, extra in subjects:
            env = {**env_base, "appr": appr, **extra}
            if stype == "account" and rule.rule_id == "AUTH.APPROVAL_INVALID" and not appr.get("required"):
                continue
            v = eval_rule(rule.code, env)
            if not v:
                continue
            f = build_finding(rt, acct, rule, stype, sid, env, r, rol, loc_aal, att_rows, labels, uw)
            fired[f["key"]] = f
            if rule.referral_level:
                rule_levels.append((rule.referral_level, f"{rule.title} → L{rule.referral_level}"))
    # authority on the working proposal
    max_loc = max([s.get("tiv") or 0 for s in loc_ctx] or [0]) * pas.get("carrier_share", 1.0)
    lvl, reasons = P.authority_required(r, tiv_cur * pas.get("carrier_share", 1.0), max_loc, rule_levels)
    ren.rarc["required_authority_level"] = lvl
    ren.rarc["authority_reasons"] = reasons
    ren.rarc["adequacy_floor"] = g["adequacy_floor"]
    upsert_findings(rt, acct, fired)
    derive_actions(rt, acct, notice)
    ren.notice = notice
    ren.loc_ctx = {s["location_uid"]: s for s in loc_ctx}
    ren.diffs = diffs
    ren.acct_ctx = ctx_acct
    ren.last_eval = rt.clock
    build_narrative(rt, acct)


def build_finding(rt, acct, rule, stype, sid, env, r, rol, loc_aal, att_rows, labels, uw) -> dict:
    loc = env.get("loc") or {}
    impact, method, conf_adj = impact_of(rule.impact, env, r, rol, loc_aal, att_rows, rt, acct)
    ev_obs: list[str] = []
    conflicts: list[str] = []
    for path in rule.evidence:
        obj, _, fld = path.partition(".")
        if obj == "loc" and loc.get("_obs", {}).get(fld):
            ev_obs.append(loc["_obs"][fld])
            conflicts += [x for x in loc.get("_conflicts", {}).get(fld, []) if x != loc["_obs"][fld]]
    diff = env.get("diff")
    if diff:
        ev_obs += [x for x in (diff.get("a_obs"), diff.get("b_obs")) if x]
    if stype == "location":
        ev_obs += [loc["_obs"][f] for f in ("tiv_reported", "building_value") if loc.get("_obs", {}).get(f) and loc["_obs"][f] not in ev_obs][:1]
        if rule.rule_id in ("ROOF.YEAR_CONFLICT",):
            conflicts = loc.get("_conflicts", {}).get("roof_year", [])
            ev_obs = conflicts[:]
        if rule.rule_id == "SEC.HIGH_VALUE_UNMONITORED" and loc["_obs"].get("burglar_monitored"):
            ev_obs.append(loc["_obs"]["burglar_monitored"])
        if rule.rule_id in ("OCC.DRIFT",):
            ev_obs = [o.obs_id for o in rt.store.field_obs(loc["location_uid"], "occupancy_class")]
        if rule.rule_id == "CAT.INPUT_MISMATCH":
            ev_obs = [loc["_obs"][f] for f in ("cat_input_construction", "construction_class") if loc["_obs"].get(f)]
        if rule.rule_id == "FIRE.SPRINKLER_ADEQUACY":
            ev_obs = [o.obs_id for f in ("storage_height_ft", "sprinkler_design_ft", "commodity") for o in rt.store.field_obs(loc["location_uid"], f)]
        if rule.rule_id == "VAC.FIRE_SPRINKLER_OFF" or rule.rule_id == "VAC.THRESHOLD":
            ev_obs = [o.obs_id for f in ("vacancy_pct", "sprinkler_impaired", "vacancy_indicator") for o in rt.store.field_obs(loc["location_uid"], f)]
    if stype == "account":
        for f in ("target_premium", "cash_on_premises", "appraisal_date", "requested_ns_ded_pct"):
            ob = rt.store.field_obs(acct, f)
            if ob and (f in rule.when or rule.family == "pricing" and f == "target_premium"):
                ev_obs.append(ob[-1].obs_id)
    confs = [rt.store.obs[o].confidence for o in ev_obs if o in rt.store.obs]
    conf = round(min(confs) if confs else 0.9, 2) * conf_adj
    subject_label = {"account": rt.systems["accounts"][acct]["name"], "location": loc.get("label", ""), "contract": (diff or {}).get("label") or "Subjectivity",
                     "recommendation": (env.get("rec") or {}).get("rec_id", "")}.get(stype, "")
    if env.get("rec"):
        subject_label = f"{env['rec']['rec_id']} · {env['rec'].get('location_label', '')}"
    key = f"{rule.rule_id}|{sid}"
    return {"key": key, "rule": rule, "subject_type": stype, "subject_id": sid, "subject_label": subject_label,
            "observed": fmt(rule.observed, env), "expected": fmt(rule.expected, env), "impact_usd": round(impact, -2) if impact else 0,
            "impact_method": method, "confidence": round(conf, 2), "evidence": list(dict.fromkeys(ev_obs)), "conflicts": list(dict.fromkeys(conflicts)),
            "action": rule.action}


def impact_of(method: str, env: dict, r: dict, rol: float, loc_aal: dict, att_rows: dict, rt, acct) -> tuple[float, str, float]:
    loc = env.get("loc") or {}
    uid = loc.get("location_uid")
    load = 1 / (1 - rater.EXPENSE - rater.PROFIT)
    if method == "valuation_gap":
        gap = (loc.get("model_rc") or 0) - (loc.get("building_value") or 0)
        return gap * rol, f"Under-insured building value {_m(gap)} × rate on line {rol * 100:.3f}%", 1.0
    if method == "trend_gap":
        gap = (loc.get("building_value") or 0) * loc.get("cost_trend", 0.05)
        return gap * rol, f"Missing cost trend {_m(gap)} × rate on line", 0.9
    if method == "unmodelled_aal":
        a = loc_aal.get(uid, 0) * rater.CAT_MULT * load
        return a, f"CAT load on unmodelled location (AAL {_m(loc_aal.get(uid, 0))} × {rater.CAT_MULT} ÷ (1−expense−profit))", 1.0
    if method == "occupancy_rate_delta":
        from uwc.refdata import OCCUPANCY
        cur = OCCUPANCY.get(loc.get("occupancy_class") or "warehouse")[4]
        pri = OCCUPANCY.get(loc.get("occupancy_prior") or "warehouse")[4]
        base = ((loc.get("building_value") or 0) + (loc.get("contents_value") or 0) + (loc.get("stock_value") or 0)) / 100
        return max(0, (cur - pri)) * base * load, "Attritional rate difference between classes × insured value", 0.95
    if method == "cat_recode_delta":
        a = loc_aal.get(uid, 0)
        coded = loc.get("cat_input_construction") or 3
        res = loc.get("construction_class") or 3
        v1, v0 = CONSTRUCTION[res][3], CONSTRUCTION[coded][3]
        return abs(a - a * v0 / v1) * rater.CAT_MULT * load, "CAT load difference between coded and resolved construction", 0.8
    if method in ("ns_floor_delta", "ns_min_delta"):
        return max(0, r["tp_e1_t0"] - r["tp_e1_t1"]) if r["terms_factor"] < 1 else max(0, r["tp_e1_t0"] * 0.04), "Expected CAT loss retained by the carrier below the guideline deductible (TP at expiring vs floor terms)", 1.0
    if method == "rate_given_away":
        return max(0, r["expected_premium"] - r["proposed_premium"]), "Expected premium (expiring × exposure × terms factor) − proposed", 1.0
    if method == "adequacy_gap":
        g = env["g"]
        return max(0, g["adequacy_floor"] * r["tp_e1_t1"] - r["proposed_premium"]), "Adequacy floor × technical − proposed", 1.0
    if method == "expiring_gap":
        g = env["g"]
        return max(0, g["adequacy_floor"] * r["tp_e0_t0"] - r["expiring_premium"]), "Adequacy floor × today's technical on expiring exposure − expiring", 1.0
    if method == "contract_delta":
        x = env["diff"]
        a, b = x.get("raw_a"), x.get("raw_b")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if x["field"].endswith("sublimit") or x["field"] == "limit":
                return max(0, b - a) * 0.012, f"Over-granted limit {_m(b - a)} × modelled probability of reaching it (1.2%)", 0.85
            if "ded" in x["field"]:
                return max(0, a - b) * 0.3, "Deductible reduction × expected claim frequency (0.3)", 0.85
        if x["field"] == "named_storm_ded_min" and b is None:
            return r["tp_e1_t0"] * 0.035, "Expected named-storm loss below the lost minimum (model rerun)", 0.85
        return r["expiring_premium"] * 0.05, "Premium share exposed to the missing form / safeguard", 0.8
    if method == "repeat_loss":
        return loc.get("water_incurred", 0), "Repeat water incurred since bind (expected to recur without controls)", 0.9
    if method == "repeat_loss_account":
        acctc = env["acct"]
        fires = [c for c in rt.claims.get(acct, []) if c["cause"] == "fire"]
        return sum(c["paid"] + c["reserve"] for c in fires) / 3, "Average annual fire incurred over 3 years", 0.9
    if method == "rec_loss_uplift":
        rec = env.get("rec") or {}
        base = att_rows.get(rec.get("location_uid"), 0) * load
        return base * 0.25, "25% attritional uplift while deficiency is open", 0.8
    if method == "linked_claims":
        return (env.get("rec") or {}).get("linked_incurred", 0), "Incurred on claims linked to the recommendation", 1.0
    if method == "fire_uplift":
        return att_rows.get(uid, 0) * load * 0.8, "80% attritional fire-loss uplift until corrected", 0.85
    if method == "theft_expected":
        return (loc.get("stock_value") or 0) * 0.004, "Expected theft loss 0.4% of stock at this crime level", 0.8
    if method == "accumulation_charge":
        return env["acct"].get("zone_increase", 0) * 0.015, "Capital charge 1.5% on added 1-in-250 zone PML", 0.8
    if method == "dq_uncertainty":
        return env["acct"].get("missing_modifier_aal_share", 0) * sum(loc_aal.values()) * 0.2 * rater.CAT_MULT * load, "20% CAT load uncertainty on locations missing secondary modifiers", 0.7
    if method == "control_premium":
        return r["expiring_premium"], "control: premium written outside approved terms / authority", 1.0
    if method == "control_tiv":
        return (loc.get("tiv") or 0) * rt.pas[acct].get("carrier_share", 1.0), "control: insured value at stake", 1.0
    return 0.0, "not quantified", 1.0


def _m(x: float) -> str:
    return f"${x / 1e6:,.1f}M" if abs(x) >= 1e6 else f"${x:,.0f}"


def upsert_findings(rt, acct, fired: dict[str, dict]):
    ren = rt.ren[acct]
    prem = rt.pas[acct]["premium"]
    thr = max(5000, 0.02 * prem)
    for key, f in fired.items():
        rule = f["rule"]
        control = f["impact_method"].startswith("control")
        econ = 0 if control else f["impact_usd"]
        material = (econ * f["confidence"] >= thr) or rule.severity == "CRITICAL" or (rule.outcome in ("REFER", "BLOCK", "DECLINE", "TERM_BREACH", "CONDITION") and rule.severity == "HIGH")
        fid = ren.finding_ids.get(key) or f"fnd_{hashlib.md5(key.encode()).hexdigest()[:10]}"
        ren.finding_ids[key] = fid
        cur = ren.findings.get(fid)
        base = {
            "finding_id": fid, "account_id": acct, "subject_type": f["subject_type"], "subject_id": f["subject_id"], "subject_label": f["subject_label"],
            "rule_id": rule.rule_id, "rule_version": rule.version, "family": rule.family, "title": rule.title, "description": rule.description or rule.title,
            "severity": rule.severity, "outcome": rule.outcome, "observed": f["observed"], "expected": f["expected"], "impact_usd": f["impact_usd"],
            "impact_method": f["impact_method"], "confidence": f["confidence"], "materiality_score": round(econ * f["confidence"]), "material": material,
            "evidence_obs_ids": f["evidence"], "conflicting_obs_ids": f["conflicts"], "source": rule.source or f"Anaira standard library · {rule.family}",
            "action": f["action"] or OUTCOME_ACTION.get(rule.outcome), "control": control,
        }
        if cur:
            cur.update(base)
            if cur["status"] == "RESOLVED":
                dec = (cur.get("disposition") or {}).get("decision")
                cur["status"] = {"ACCEPT": "ACCEPTED", "REJECT": "REJECTED", "DEFER": "DEFERRED"}.get(dec, "OPEN")
        else:
            base.update({"status": "OPEN", "disposition": None, "pass": ren.pass_no, "created_at": rt.clock, "critique": critique(rt, base)})
            ren.findings[fid] = base
            rt.log(acct, "engine", "15" if ren.pass_no < 3 else "11", f"Finding: {rule.title}", f"{base['subject_label']} — {base['observed']}", "Control engine", finding_ids=[fid])
            rt.new_findings_counter += 1
    for fid, cur in ren.findings.items():
        key = next((k for k, v in ren.finding_ids.items() if v == fid), None)
        if key not in fired and cur["status"] in ("OPEN", "ACCEPTED", "DEFERRED"):
            cur["status"] = "RESOLVED"
            cur["resolved_at"] = rt.clock


def critique(rt, f: dict) -> dict:
    """Deterministic critique pass: challenge weak evidence before the finding reaches the underwriter."""
    obs = [rt.store.obs[o] for o in f["evidence_obs_ids"] if o in rt.store.obs]
    if f["confidence"] < 0.75:
        return {"verdict": "CHALLENGED", "note": f"Confidence {f['confidence']:.2f} (evidence × impact-model uncertainty) — verify the estimate before acting."}
    if f["severity"] in ("HIGH", "CRITICAL") and obs and all(o.obs_type in ("C", "N") and o.source_family == "Broker / insured" for o in obs):
        return {"verdict": "CHALLENGED", "note": "Rests only on broker-reported evidence; request verification (engineering or certificate)."}
    if "fallback" in f["impact_method"]:
        return {"verdict": "CHALLENGED", "note": "Impact estimated with elasticity fallback — rater not callable."}
    types = sorted({o.obs_type for o in obs})
    return {"verdict": "UPHELD", "note": f"Evidence types {', '.join(types) or 'system'}; rule {f['rule_id']} v{f['rule_version']} re-evaluated with no counter-evidence."}


def derive_actions(rt, acct, notice):
    ren = rt.ren[acct]
    open_mat = [f for f in ren.findings.values() if f["material"] and f["status"] in ("OPEN", "ACCEPTED", "DEFERRED")]
    reg = rt.systems["accounts"][acct]
    owner = USER_BY_ID[reg["underwriter_id"]]["name"]
    by: dict[str, list[dict]] = {}
    for f in open_mat:
        a = f.get("action")
        if not a:
            if f["family"] in ("valuation", "pricing"):
                a = "REPRICE"
            else:
                continue
        by.setdefault(a, []).append(f)
    if "NON_RENEW" in by and notice["required"]:
        by.setdefault("CONDITIONAL_RENEWAL_NOTICE", []).extend(by["NON_RENEW"])
    order = ["NON_RENEW", "CONDITIONAL_RENEWAL_NOTICE", "REFER", "REPRICE", "RESTRUCTURE", "CONDITION", "ENDORSEMENT_CORRECTION", "DATA_REQUEST"]
    titles = {"NON_RENEW": "Non-renew (class declined)", "CONDITIONAL_RENEWAL_NOTICE": "Issue statutory notice", "REFER": "Refer to senior authority",
              "REPRICE": "Reprice to technical", "RESTRUCTURE": "Restructure terms", "CONDITION": "Condition renewal", "ENDORSEMENT_CORRECTION": "Correct issued policy by endorsement",
              "DATA_REQUEST": "Request missing data from broker"}
    exp = rt.pas[acct]["term_end"]
    actions = []
    for a in order:
        fs = by.get(a)
        if not fs:
            continue
        due = notice["latest_notice_date"] if a in ("NON_RENEW", "CONDITIONAL_RENEWAL_NOTICE") and notice["latest_notice_date"] else _minus(exp, 60 if a != "DATA_REQUEST" else 75)
        prev = next((x for x in ren.actions if x["type"] == a), None)
        actions.append({"action_id": f"act_{acct}_{a.lower()}", "account_id": acct, "type": a, "title": titles[a],
                        "detail": "; ".join(sorted({f["title"] for f in fs}))[:300], "finding_ids": [f["finding_id"] for f in fs], "owner": owner,
                        "due": due, "status": prev["status"] if prev else "PROPOSED",
                        "impact_usd": sum(0 if f["control"] else f["impact_usd"] for f in fs)})
    ren.actions = actions
    ren.recommended_actions = [x["type"] for x in actions] or ["MAINTAIN"]
    # integrity score
    score = 100.0
    for f in ren.findings.values():
        if f["status"] in ("RESOLVED", "REJECTED"):
            continue
        score -= SEV_PENALTY[f["severity"]] * (1 if f["material"] else 0.3)
    ren.integrity = max(5.0, round(score))
    if ren.status in ("NOT_STARTED", "FAST_TRACK", "ACTION_REQUIRED"):
        ren.status = "ACTION_REQUIRED" if actions else "FAST_TRACK"
        if "NON_RENEW" in ren.recommended_actions and ren.status == "ACTION_REQUIRED":
            ren.status = "ACTION_REQUIRED"


def _minus(s: str, n: int) -> str:
    from datetime import timedelta
    return (d(s) - timedelta(days=n)).isoformat()


def notice_info(reg, pas, today) -> dict:
    st = reg["hq_state"]
    days = NOTICE_DAYS.get(st) if reg["admitted"] else None
    latest = None
    rem = None
    if days:
        from datetime import timedelta
        latest = (d(pas["term_end"]) - timedelta(days=days)).isoformat()
        rem = (d(latest) - today).days
    return {"required": bool(days), "state": st, "admitted": reg["admitted"], "days_required": days, "latest_notice_date": latest,
            "days_remaining": rem, "rule_ref": NOTICE_REF if days else "Surplus lines — statutory notice rules generally do not apply (verify)"}


def approval_ctx(rt, acct) -> dict:
    """Prior-term: was a required referral approved for the exact terms bound?"""
    pas = rt.pas[acct]
    quotes = pas.get("quotes", [])
    approvals = pas.get("approvals", [])
    bound = next((q for q in quotes if q["status"] == "ACCEPTED"), None)
    if not bound or not approvals:
        return {"required": False}
    appr = approvals[-1]
    av = appr["quote_version"]
    aq = next((q for q in quotes if q["version"] == av), None)
    same = aq is not None and P.terms_hash(aq["premium"], aq["terms"]) == P.terms_hash(bound["premium"], bound["terms"])
    change = ""
    if aq and not same:
        diffs = [k for k in P.TERM_KEYS if aq["terms"].get(k) != bound["terms"].get(k)]
        change = ", ".join(f"{CONTRACT_LABEL.get(k, k)} {fmt_contract(k, aq['terms'].get(k))} → {fmt_contract(k, bound['terms'].get(k))}" for k in diffs)
    return {"required": True, "valid_for_bound": same, "approved_version": av, "bound_version": bound["version"], "change": change or "terms changed"}


def zone_update(rt, acct, snaps, pas) -> dict:
    share = pas.get("carrier_share", 1.0)
    contrib_prior: dict[str, float] = {}
    contrib_cur: dict[str, float] = {}
    for key, states in (("prior", snaps["prior"]), ("current", snaps["current"])):
        for s in states:
            z = s.get("cat_zone")
            if not z or z not in ZONES:
                continue
            f = PML_FACTOR.get(ZONES[z][1], 0.1)
            val = (s.get("tiv") or 0) * share * f
            (contrib_prior if key == "prior" else contrib_cur)[z] = (contrib_prior if key == "prior" else contrib_cur).get(z, 0) + val
    rt.zone_contrib[acct] = {"prior": contrib_prior, "current": contrib_cur}
    best = {"zone_util_post": 0.0, "zone_increase": 0.0, "zone_name": None, "zone_id": None}
    for z in set(contrib_prior) | set(contrib_cur):
        post = rt.zone_total(z, "current")
        util = post / ZONES[z][5]
        inc = contrib_cur.get(z, 0) - contrib_prior.get(z, 0)
        if util > best["zone_util_post"]:
            best = {"zone_util_post": util, "zone_increase": inc, "zone_name": ZONES[z][0], "zone_id": z, "zone_increase_share": inc / ZONES[z][5]}
    best.setdefault("zone_increase_share", 0.0)
    return best


def build_narrative(rt, acct):
    ren = rt.ren[acct]
    reg = rt.systems["accounts"][acct]
    pas = rt.pas[acct]
    r = ren.rarc or {}
    mats = sorted([f for f in ren.findings.values() if f["material"] and f["status"] != "RESOLVED"], key=lambda f: (-SEV_PENALTY[f["severity"]], -f["impact_usd"]))
    econ = sum(f["impact_usd"] for f in mats if not f["control"])
    days = (d(pas["term_end"]) - rt.clock_date).days
    lines = []
    if not mats:
        lines.append(f"**{reg['name']}** renews {pas['term_end']} (T-{days}). No material change against the expiring position — "
                     f"adequacy {r.get('adequacy', 0) * 100:.0f}% of technical, RARC {r.get('rarc', 0) * 100:+.1f}%. Recommended: **fast-track / maintain**.")
    else:
        lines.append(f"**{reg['name']}** renews {pas['term_end']} (T-{days}). {len(mats)} material findings; economic impact **${econ:,.0f}**.")
        if r:
            lines.append(f"- Pricing: headline {r['headline_change'] * 100:+.1f}% but like-for-like RARC **{r['rarc'] * 100:+.1f}%** "
                         f"(exposure factor {r['exposure_factor']:.3f}, terms factor {r['terms_factor']:.3f}); adequacy {r['adequacy'] * 100:.1f}% of technical.")
        for f in mats[:7]:
            lines.append(f"- {f['title']}: {f['observed']} [F:{f['finding_id']}]")
        lines.append(f"Recommended: **{' + '.join(a.replace('_', ' ').lower() for a in ren.recommended_actions)}**. Underwriter decides.")
    up = sum(1 for f in mats if (f.get("critique") or {}).get("verdict") == "UPHELD")
    ch = sum(1 for f in mats if (f.get("critique") or {}).get("verdict") == "CHALLENGED")
    head = [l for l in lines if not l.startswith("- ")]
    bullets = [l for l in lines if l.startswith("- ")]
    text = head[0] + ("\n\n" + "\n".join(bullets) if bullets else "") + ("\n\n" + "\n\n".join(head[1:]) if len(head) > 1 else "")
    ren.narrative = {"text": text, "generated_by": "template", "model": None,
                     "critique": {"summary": f"{up} upheld · {ch} challenged", "upheld": up, "challenged": ch}}

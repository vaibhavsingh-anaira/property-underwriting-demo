"""Decision Assurance engine (REAL). Stage 1 builds the decision pack from the evidence ledger; stage 2 checks an
intended action independently against evidence, pricing, guidelines, appetite and authority.

Inputs are resolved observations only (uwc.engine.views.location_state over rt.store), the versioned rules in
rules/*.yaml (product: decision), the guidelines in force, the new-business authority matrix and the portfolio.
Pricing calls the mock rater (uwc.mocks.rater, which runs MockCat) — the only stand-in on this path."""
from __future__ import annotations

import statistics
from datetime import date
from typing import Any

from uwc.engine.rules import evaluate, fmt
from uwc.engine.views import VALUE_FIELDS, exposure_row, location_state
from uwc.ledger.fields import display, label as flabel
from uwc.mocks import rater
from uwc.refdata import CONSTRUCTION, GUIDELINE_PAGES, OCCUPANCY, PPC_FACTOR, USER_BY_ID, ZONES, guideline_for

from .ingest import years_covered
from .model import (AUTH_DOC, CONTRA_FIELDS, DIMENSIONS, GUIDE_DOC, HAIL_ZONES, HAZARD_RANK, NB_AUTHORITY, NB_DOC, NB_SECTION_PAGE, NB_STANDARDS,
                    PML_FACTOR, REQUIRED_LOC_FIELDS, ADDON_FIELDS, aop_min, h8, level_for_dev, money, pct, st)

RANK = {"FAIL": 3, "FLAG": 2, "CONDITION": 1, "PASS": 0}
APPROVERS = {2: "u_daniel", 3: "u_priya", 4: "u_robert"}


def G(asof: str) -> dict:
    g = dict(guideline_for(date.fromisoformat(asof[:10])))
    g.update({k: v for k, v in NB_STANDARDS.items() if not isinstance(v, list)})
    return g


def year(d: str) -> int:
    return int(d[:4])


# ============================================================================ resolved state
def loc_states(rt, cid: str) -> list[dict]:
    out = []
    for uid in rt.store.account_locations(cid):
        s = location_state(rt, cid, uid)
        s["tiv"] = sum(s.get(k) or 0 for k in ("building_value", "contents_value", "stock_value", "bi_value")) or s.get("tiv_reported") or 0
        out.append(s)
    return out


def acct(rt, cid: str, f: str, default=None):
    obs = rt.store.field_obs(cid, f)
    return obs[-1].value if obs else default


def acct_obs(rt, cid: str, f: str):
    obs = rt.store.field_obs(cid, f)
    return obs[-1] if obs else None


def claims(rt, cid: str) -> list[dict]:
    by: dict[str, dict] = {}
    for o in rt.store.account_obs(cid):
        if o.subject_type == "claim":
            x = by.setdefault(o.subject_id, {"claim_id": o.subject_id.split(":")[-1], "obs": {}})
            x[o.field_code] = o.value
            x["obs"][o.field_code] = o.obs_id
    return sorted(by.values(), key=lambda x: x.get("date_of_loss") or "")


def loss_run_years(rt, cid: str) -> float:
    periods = [o.value for o in rt.store.field_obs(cid, "loss_run_period")]
    return years_covered(periods, "") if periods else 0.0


def classification(rt, cid: str, states: list[dict]) -> dict:
    ev = []
    for o in rt.store.field_obs(cid, "operations_class"):
        ev.append({"class": o.value, "source": o.source_label, "obs_id": o.obs_id, "confidence": o.confidence})
    for s in states:
        for oid in [x for x in rt.store.by_subject.get((s["location_uid"], "occupancy_class"), [])]:
            o = rt.store.obs[oid]
            ev.append({"class": o.value, "source": f"{o.source_label} · {s['label']}", "obs_id": o.obs_id, "confidence": o.confidence})
    ev = [e for e in ev if e["class"] and e["confidence"] >= 0.8]
    gov = max(ev, key=lambda e: (HAZARD_RANK.get(e["class"], 0), e["confidence"]))["class"] if ev else None
    return {"governing": gov, "label": OCCUPANCY.get(gov, ("—",))[0], "evidence": ev,
            "classes": sorted({e["class"] for e in ev}, key=lambda k: -HAZARD_RANK.get(k, 0))}


# ============================================================================ pricing (mock rater + MockCat)
def rterms(a: dict) -> dict:
    return {"aop_deductible": a.get("aop"), "named_storm_ded_pct": a.get("ns_pct"), "named_storm_ded_min": a.get("ns_min"), "wind_hail_ded_pct": a.get("wh_pct")}


def _rows(states: list[dict], override: dict | None = None) -> list[dict]:
    rows = []
    for s in states:
        s2 = dict(s)
        s2.update((override or {}).get(s["location_uid"], {}))
        r = exposure_row(s2)
        if s2.get("governing_occ"):
            r["occupancy"] = s2["governing_occ"]
        rows.append(r)
    return rows


def manuscript_load(states: list[dict], line: float) -> float:
    """Expected annual loss given back by deleting the water exclusion (surface water / surge in SFHA, other water elsewhere)."""
    el = sum(s["tiv"] * (0.0021 if s.get("flood_zone") in ("AE", "VE") else 0.0002) for s in states) * line
    return el / (1 - rater.EXPENSE - rater.PROFIT)


def price(rt, c: dict, states: list[dict], a: dict, override: dict | None = None, gov: str | None = None) -> dict:
    line = a.get("line") or 1.0
    rows = _rows(states, override)
    if gov and gov in ("scrap",):
        for r in rows:
            if r["occupancy"] in ("warehouse", "manufacturing"):
                r["occupancy"] = gov
    sched = c.get("sched_mod", 1.0)
    base = rater.technical(rows, rterms(a), share=line, account_mod=sched)
    att = base["components"][0]["value"] / sched
    cl = [x for x in claims(rt, c["case_id"]) if (x.get("cause") or "").lower() not in ("hurricane", "flood")]
    yrs = loss_run_years(rt, c["case_id"]) or 0
    exp_e = att / line * yrs
    act_l = sum(x.get("incurred") or 0 for x in cl)
    z = min(0.35, 0.07 * yrs)
    emod = max(0.9, min(1.3, 1 + z * (min(4.0, act_l / exp_e) - 1))) if exp_e else 1.0
    r = rater.technical(rows, rterms(a), share=line, account_mod=sched * emod)
    ms = manuscript_load(states, line) if a.get("manuscript") == "full" else 0.0
    tech = r["technical_premium"] + ms
    oep250 = next((x["loss"] for x in r["cat"]["oep"] if x["rp"] == 250), 0)
    per_loc = []
    for s, row in zip(states, rows):
        occ = OCCUPANCY.get(row["occupancy"] or "warehouse", OCCUPANCY["warehouse"])
        per_loc.append({"location_uid": s["location_uid"], "label": s["label"], "class": occ[0], "base_rate": occ[4],
                        "construction_factor": CONSTRUCTION.get(row["construction"] or 3)[1], "ppc_factor": PPC_FACTOR.get(row["ppc"] or 5, 1.0),
                        "sprinkler_factor": rater._sprinkler_factor(row["sprinkler_pct"]), "roof_factor": rater._age_factor(row["roof_year"], row["year_built"]),
                        "aal": round(r["cat"]["loc_aal"].get(s["location_uid"], 0)), "tiv": s["tiv"]})
    comps = [{"component": x["component"], "value": round(x["value"])} for x in r["components"]]
    if ms:
        comps.append({"component": "Manuscript give-back (water exclusion deleted)", "value": round(ms)})
    return {"technical": round(tech), "components": comps, "aal": round(r["aal"]), "oep_250": round(oep250), "per_loc": per_loc,
            "modifiers": [{"label": "Schedule rating", "value": sched}, {"label": f"Experience ({yrs:g} yrs, credibility {z:.2f})", "value": round(emod, 3)}],
            "exp_mod": round(emod, 3), "sched_mod": sched, "manuscript_load": round(ms), "model": rater.MODEL_VERSION, "line": line,
            "attritional_expected": round(att)}


def band(tech: float) -> tuple[float, float]:
    b = NB_STANDARDS["suggested_band"]
    step = 5000 if tech >= 250_000 else 1000 if tech >= 25_000 else 100
    return round(tech * (1 - b) / step) * step, round(tech * (1 + b) / step) * step


# ============================================================================ portfolio
def nb_zone_contrib(rt, exclude: str | None = None) -> dict:
    tot: dict[str, float] = {}
    for cid, c in st(rt).cases.items():
        if cid == exclude or not c.get("bound"):
            continue
        for z, v in c["bound"].get("zone_contrib", {}).items():
            tot[z] = tot.get(z, 0) + v
    return tot


def zone_contrib(states: list[dict], line: float) -> dict:
    out: dict[str, float] = {}
    for s in states:
        z = s.get("cat_zone")
        if z in ZONES:
            out[z] = out.get(z, 0) + s["tiv"] * line * PML_FACTOR.get(ZONES[z][1], 0.1)
    return out


def portfolio(rt, cid: str, states: list[dict], line: float) -> dict:
    mine = zone_contrib(states, line)
    nb = nb_zone_contrib(rt, exclude=cid)
    zones = []
    for z, v in mine.items():
        name, peril, *_rest = ZONES[z]
        thr = ZONES[z][5]
        before = rt.zone_total(z, "prior") + nb.get(z, 0)
        zones.append({"zone_id": z, "name": name, "peril": peril, "threshold": thr, "before": round(before), "after": round(before + v),
                      "util_before": before / thr, "util_after": (before + v) / thr, "increase": round(v),
                      "max_line": max(0.0, min(1.0, (thr * 0.9 - before) / (v / line))) if v else 1.0})
    zones.sort(key=lambda z: -z["util_after"])
    top = zones[0] if zones else None
    return {"zones": zones, "zone_name": top["name"] if top else None, "zone_util_before": top["util_before"] if top else 0.0,
            "zone_util_after": top["util_after"] if top else 0.0, "zone_increase": top["increase"] if top else 0.0,
            "max_line": top["max_line"] if top else 1.0}


# ============================================================================ environment for rules
def loc_env(s: dict, asof: str, rt, cid: str) -> dict:
    ry = s.get("roof_year")
    age = year(asof) - int(ry) if ry else None
    rc = s.get("model_rc")
    miss = [lab for f, lab in REQUIRED_LOC_FIELDS if s.get(f) in (None, "")] + [lab for f, lab in ADDON_FIELDS.get(s.get("occupancy_class"), []) if s.get(f) in (None, "")]
    spr_o = rt.store.obs.get(s["_obs"].get("sprinkler_pct")) if s.get("_obs", {}).get("sprinkler_pct") else None
    rc_ok = (s.get("roof_condition_verified") or "").split(" ")[0] in ("Good", "Fair")
    occ = s.get("occupancy_class")
    return {**{k: v for k, v in s.items() if not k.startswith("_")}, "roof_age": age, "hail_zone": s.get("cat_zone") in HAIL_ZONES,
            "roof_mitigated": bool(s.get("roof_replacement_planned")) or rc_ok, "valuation_ratio": (s.get("building_value") or 0) / rc if rc else None,
            "missing_cope": len(miss), "missing_cope_text": ", ".join(miss) or "none", "occ_hazard": HAZARD_RANK.get(occ, 3),
            "occ_label": OCCUPANCY.get(occ, ("—",))[0], "sprinkler_source": (spr_o.source_label if spr_o else "—")}


def case_env(rt, c: dict, states: list[dict], cls: dict, contras: list[dict], asof: str, px: dict | None = None) -> dict:
    tiv = sum(s["tiv"] for s in states)
    open_c = [k for k in c.get("conditions", []) if k["status"] == "OPEN" and k.get("kind") == "evidence"]
    mat = [x for x in contras if x["status"] == "OPEN" and x["material"]]
    low = []
    for s in states:
        for f in ("occupancy_class", "construction_class", "sprinkler_pct"):
            o = rt.store.obs.get(s["_obs"].get(f)) if s["_obs"].get(f) else None
            if o and o.confidence < 0.85:
                low.append(f"{flabel(f)} at {s['label']} ({o.confidence:.0%})")
    ms = acct(rt, c["case_id"], "manuscript_clause")
    peer = peer_stats(rt, c, cls["governing"], tiv, px)
    return {"tiv": tiv, "max_loc_tiv": max((s["tiv"] for s in states), default=0), "loss_run_years": loss_run_years(rt, c["case_id"]),
            "has_inspection": any(d.get("role") in ("inspection", "survey") for d in c.get("docs", [])), "governing_class": cls["governing"], "governing_label": cls["label"],
            "class_evidence": "; ".join(sorted({e["source"].split(" → ")[0] for e in cls["evidence"] if e["class"] == cls["governing"]})) or "—",
            "has_t1": any(s.get("wind_tier") == "T1" for s in states), "aop_min": aop_min(tiv), "open_conditions": len(open_c),
            "open_conditions_text": "; ".join(k["text"] for k in open_c) or "—", "open_material_contradictions": len(mat),
            "open_contradiction_impact": sum(x["impact_usd"] for x in mat), "low_conf_fields": len(low), "low_conf_text": "; ".join(low) or "—",
            "manuscript_text": ms or "No manuscript wording", **peer, "n_locations": len(states)}


def peer_stats(rt, c: dict, cls: str | None, tiv: float, px: dict | None) -> dict:
    rates = []
    for oc in st(rt).cases.values():
        p = oc.get("pack") or {}
        if oc["case_id"] != c["case_id"] and p.get("governing_class") == cls and p.get("pricing", {}).get("technical") and p.get("tiv"):
            rates.append(_att_rate(p["pricing"], p["tiv"]))
    if not px or not tiv or len(rates) < 4:
        return {"peer_rate_z": 0.0, "rate_per_100": round(_att_rate(px, tiv), 3) if px and tiv else None, "peer_rate_median": None, "peer_n": len(rates)}
    mine = _att_rate(px, tiv)
    med = statistics.median(rates)
    sd = statistics.pstdev(rates) or 1e-9
    return {"peer_rate_z": round((mine - med) / sd, 2), "rate_per_100": round(mine, 3), "peer_rate_median": round(med, 3), "peer_n": len(rates)}


def _att_rate(px: dict, tiv: float) -> float:
    """Non-catastrophe rate per $100 TIV (peer comparison excludes CAT, which is location-driven)."""
    cat = next((x["value"] for x in px.get("components", []) if x["component"].startswith("CAT")), 0)
    return (px["technical"] - cat / (1 - rater.EXPENSE - rater.PROFIT)) / tiv * 100 / (px.get("line") or 1.0)


RULE_EVIDENCE = {"DA.PROT.PARTIAL_SPRINKLER": ["sprinkler_pct"], "DA.PROT.STORAGE_ABOVE_DESIGN": ["storage_height_ft", "sprinkler_design_ft", "commodity"],
                 "DA.ROOF.AGE": ["roof_year", "roof_replacement_planned", "roof_condition_verified"], "DA.VAL.RC_RATIO": ["building_value", "model_rc"],
                 "DA.CAT.NS_DED_FLOOR": ["wind_tier"], "DA.TERMS.HAIL_DED": ["cat_zone"], "DA.ACCUM.ZONE": ["cat_zone"], "DA.DOC.COPE_MISSING": ["occupancy_raw", "construction_raw"],
                 "DA.APPETITE.PROHIBITED": ["@operations_class", "@operations_description", "occupancy_class"], "DA.DOC.LOSS_RUNS": ["@loss_run_period"],
                 "DA.DOC.LOSS_RUNS_BIND": ["@loss_run_period"], "DA.T2.MANUSCRIPT": ["@manuscript_clause"], "DA.T2.RATIONALE_EVIDENCE": ["@loss_run_period"],
                 "DA.T2.CONFLICT_UNRESOLVED": ["sprinkler_pct", "occupancy_class", "construction_class", "roof_year"], "DA.T2.OVERRIDE_EVIDENCE": ["sprinkler_design_ft", "in_rack_claimed", "@operations_class"],
                 "DA.T2.LOW_CONFIDENCE": ["occupancy_class", "construction_class"], "DA.CAT.NS_MIN": ["wind_tier"], "DA.DOC.INSPECTION": ["tiv_reported"]}


def evidence_ids(rt, cid: str, rule_id: str, subject_id: str | None) -> list[str]:
    out = []
    uids = [subject_id] if subject_id else list(rt.store.account_locations(cid))
    for f in RULE_EVIDENCE.get(rule_id, []):
        if f.startswith("@"):
            out += rt.store.by_subject.get((cid, f[1:]), [])
        else:
            for u in uids:
                out += rt.store.by_subject.get((u, f), [])
    return out[:12]


def rules_for(rt, stage: str, asof: str):
    return [r for r in rt.rules.values() if r.product == "decision" and r.active(asof[:10]) and (r.scope.get("stage") in (stage, "both"))]


def run_rules(rt, stage: str, asof: str, env: dict, locs: list[dict]) -> list[dict]:
    out = []
    for r in rules_for(rt, stage, asof):
        subjects = [(s, {**env, "loc": s}) for s in locs] if r.applies_to == "location" else [(None, env)]
        any_applicable = False
        for s, e in subjects:
            v = evaluate(r.code, e)
            if v is None:
                continue
            any_applicable = True
            if v:
                out.append({"rule": r, "subject_id": s["location_uid"] if s else None, "subject_label": s["label"] if s else "Submission",
                            "observed": fmt(r.observed, e), "expected": fmt(r.expected, e), "fired": True})
        if not any(x["rule"].rule_id == r.rule_id for x in out):
            out.append({"rule": r, "subject_id": None, "subject_label": "Submission" if r.applies_to != "location" else f"{len(locs)} location(s)",
                        "observed": "Not triggered" if any_applicable else "Not applicable (no data)", "expected": fmt(r.expected, env), "fired": False,
                        "applicable": any_applicable})
    return out


def citation(src: str) -> dict:
    import re
    m = re.search(r"(NB§\d+\.\d+)", src or "")
    if m:
        return {"label": m.group(1), "doc_id": NB_DOC, "page": NB_SECTION_PAGE.get(m.group(1), 1)}
    m = re.search(r"§(\d+\.\d+)", src or "")
    if m and f"§{m.group(1)}" in GUIDELINE_PAGES:
        return {"label": f"Guidelines §{m.group(1)}", "doc_id": GUIDE_DOC, "page": GUIDELINE_PAGES[f"§{m.group(1)}"] + 1}
    return {"label": src, "doc_id": None, "page": None}


# ============================================================================ contradictions & missing information
def _close(f: str, a, b) -> bool:
    tol = CONTRA_FIELDS[f]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if f in ("sqft",):
            return abs(a - b) / max(abs(a), abs(b), 1) <= tol
        if f == "sprinkler_pct":
            return abs(a - b) < tol
        return abs(a - b) < max(tol, 1) if tol else a == b
    return a == b


def contradictions(rt, c: dict, states: list[dict], base_tech: float, act: dict) -> list[dict]:
    prev = {x["contradiction_id"]: x for x in c.get("contradictions", [])}
    out = []
    thr = max(NB_STANDARDS["materiality_floor"], NB_STANDARDS["materiality_pct"] * base_tech)
    for s in states:
        uid = s["location_uid"]
        for f in CONTRA_FIELDS:
            obs = [o for o in rt.store.field_obs(uid, f) if o.value is not None and (o.obs_type != "N" or f in ("occupancy_class", "construction_class", "sprinkler_pct"))]
            if f in VALUE_FIELDS:
                continue
            by_src: dict[str, Any] = {}
            for o in obs:
                by_src[o.doc_id or o.source_label] = o
            srcs = list(by_src.values())
            win = rt.store.obs.get(s["_obs"].get(f)) or (srcs[0] if srcs else None)
            if not win:
                continue
            others = [o for o in srcs if o.obs_id != win.obs_id and not _close(f, o.value, win.value)]
            if not others:
                continue
            b = max(others, key=lambda o: abs(o.value - win.value) if isinstance(o.value, (int, float)) and isinstance(win.value, (int, float)) else 1)
            a = win
            alt = b.value
            try:
                t_alt = price(rt, c, states, act, override={uid: {f: alt}})["technical"]
            except Exception:  # noqa: BLE001
                t_alt = base_tech
            impact = abs(base_tech - t_alt)
            cid_ = f"ctr_{h8(c['case_id'], uid, f)}"
            p = prev.get(cid_, {})
            out.append({"contradiction_id": cid_, "location_uid": uid, "location": s["label"], "field": f, "field_label": flabel(f),
                        "resolved": _side(win or a, f), "other": _side(b, f), "sources": [_side(o, f) for o in srcs],
                        "impact_usd": round(impact), "impact_note": f"Rating on {display(f, alt)} instead of {display(f, (win or a).value)} moves technical by {money(impact)}",
                        "material": impact >= thr or f in ("occupancy_class",), "policy": _policy(f), "status": p.get("status", "OPEN"),
                        "resolution": p.get("resolution"), "adverse_resolved": (t_alt < base_tech)})
    return out


def _side(o, f: str) -> dict:
    return {"obs_id": o.obs_id, "value": display(f, o.value), "source": o.source_label, "obs_type": o.obs_type, "doc_id": o.doc_id, "anchor": o.anchor,
            "confidence": round(o.confidence, 2)}


def _policy(f: str) -> str:
    from uwc.ledger.fields import POLICY_EXPLAINER, policy_of
    return POLICY_EXPLAINER.get(policy_of(f), "Most recent observation")


def missing_info(rt, c: dict, states: list[dict], fired: list[dict]) -> list[dict]:
    reqs = {i for r in c.get("requests", []) for i in r["items"]}
    out = []
    for f in fired:
        r = f["rule"]
        if f["fired"] and r.outcome in ("DATA_REQUEST",) or (f["fired"] and r.scope.get("request") and r.outcome in ("CONDITION", "PRICE_ADJUST")):
            item = r.scope.get("request") or f"{r.title} — {f['subject_label']}"
            if r.rule_id == "DA.DOC.COPE_MISSING":
                item = f"Complete COPE for {f['subject_label']}: {f['observed'].split(': ', 1)[-1]}"
            if r.rule_id == "DA.ROOF.AGE":
                item = f"Roof replacement schedule — {f['subject_label']}"
            out.append({"item": item, "why": f"{r.rule_id} · {f['observed']}", "rule_id": r.rule_id, "blocking": r.outcome == "DATA_REQUEST" and r.rule_id.startswith("DA.DOC.LOSS"),
                        "status": "REQUESTED" if any(item.split(" — ")[0].lower() in x.lower() for x in reqs) else "OPEN"})
    for m in rt.store.field_obs(c["case_id"], "missing_document"):
        out.append({"item": m.value, "why": "Broker email: to follow", "rule_id": None, "blocking": False, "status": "REQUESTED" if reqs else "OPEN", "obs_id": m.obs_id})
    seen, uniq = set(), []
    for x in out:
        if x["item"] not in seen:
            seen.add(x["item"])
            uniq.append(x)
    return uniq


# ============================================================================ actions
def suggested_action(rt, c: dict, states: list[dict], cls: dict) -> dict:
    tiv = sum(s["tiv"] for s in states)
    a = {"type": "QUOTE", "aop": aop_min(tiv), "line": 1.0, "limit": tiv, "manuscript": None}
    if any(s.get("wind_tier") == "T1" for s in states):
        g = G(c.get("received") or "2026-08-01")
        a.update(ns_pct=g["wind_ded_floor_pct_t1"], ns_min=g["ns_min_floor"])
    if any(s.get("cat_zone") in HAIL_ZONES for s in states):
        a["wh_pct"] = NB_STANDARDS["hail_ded_pct_min"]
    return a


def normalize(rt, c: dict, raw: dict, states: list[dict] | None = None) -> dict:
    states = states if states is not None else loc_states(rt, c["case_id"])
    cls = classification(rt, c["case_id"], states)
    sug = suggested_action(rt, c, states, cls)
    a = {**sug, **{k: v for k, v in raw.items() if v is not None and k not in ("premium", "dev")}}
    a["type"] = (raw.get("type") or "QUOTE").upper()
    line = float(a.get("line") or 1.0)
    a["line"] = line
    tiv = sum(s["tiv"] for s in states)
    if raw.get("limit") in (None, "", 0):
        a["limit"] = round(tiv * line)
    tech = price(rt, c, states, a, gov=cls["governing"])["technical"]
    if raw.get("premium"):
        a["premium"] = float(raw["premium"])
    else:
        step = 1000 if tech >= 50_000 else 100
        a["premium"] = round(tech * (1 + float(raw.get("dev") or 0)) / step) * step
    a["rationale"] = (raw.get("rationale") or "").strip()
    return a


# ============================================================================ Stage 1 — decision pack
def build_pack(rt, cid: str, asof: str | None = None) -> dict:
    c = st(rt).cases[cid]
    asof = asof or rt.clock
    states = loc_states(rt, cid)
    if not states:
        return {}
    cls = classification(rt, cid, states)
    g = G(asof)
    sug = suggested_action(rt, c, states, cls)
    px = price(rt, c, states, sug, gov=cls["governing"])
    lo, hi = band(px["technical"])
    tiv = sum(s["tiv"] for s in states)
    contras = contradictions(rt, c, states, px["technical"], sug)
    c["contradictions"] = contras
    pf = portfolio(rt, cid, states, 1.0)
    uw = USER_BY_ID[c["uw"]]
    lvl = uw["authority_level"]
    env = {"case": case_env(rt, c, states, cls, contras, asof, px), "g": g, "pf": pf, "px": {"technical": px["technical"], "band_low": lo, "band_high": hi},
           "act": {**sug, "premium": px["technical"], "dev": 0.0}, "auth": {"level": lvl, **NB_AUTHORITY[lvl]}}
    locs = [loc_env(s, asof, rt, cid) for s in states]
    res = run_rules(rt, "pack", asof, env, locs)
    fired = [f for f in res if f["fired"]]
    sug_p = {**sug, "premium": px["technical"]}
    for f in fired:
        f["impact_usd"] = impact(rt, c, states, f, sug_p, px, env)
    # authority & referral requirements
    reqs = []
    for f in fired:
        r = f["rule"]
        if r.referral_level:
            reqs.append({"requirement": f"{r.title} — {f['subject_label']}", "level": r.referral_level, "rule_id": r.rule_id, "within": r.referral_level <= lvl,
                         "source": r.source})
    for k, lab, val in (("max_account_tiv", "Account TIV", tiv), ("max_loc_tiv", "Largest location TIV", env["case"]["max_loc_tiv"]), ("max_premium", "Premium at technical", px["technical"])):
        need = next((L for L in (1, 2, 3, 4) if val <= NB_AUTHORITY[L][k]), 4)
        reqs.append({"requirement": f"{lab} {money(val, False)}", "level": need, "rule_id": None, "within": need <= lvl, "source": "NB Standards NB§3.2"})
    reqs.append({"requirement": f"Pricing deviation authority ±{NB_AUTHORITY[lvl]['max_price_dev'] * 100:.0f}% at L{lvl} ({money(px['technical'] * (1 - NB_AUTHORITY[lvl]['max_price_dev']))}–{money(px['technical'] * (1 + NB_AUTHORITY[lvl]['max_price_dev']))})",
                 "level": lvl, "rule_id": "DA.PRICE.DEVIATION", "within": True, "source": "NB Standards NB§3.2"})
    need_lvl = max([r_["level"] for r_ in reqs] + [1])
    # draft recommendation
    outc = {f["rule"].outcome for f in fired}
    open_contra = [x for x in contras if x["status"] == "OPEN" and x["material"]]
    miss = missing_info(rt, c, states, res)
    conds = [f for f in fired if f["rule"].outcome == "CONDITION"]
    refers = [r_ for r_ in reqs if not r_["within"]]
    if "DECLINE" in outc:
        draft, why = "DECLINE", "Declined class evidenced; an exception needs Level 4."
    elif refers and conds:
        draft, why = "REFER_CONDITIONAL_QUOTE", "Referral required; quote conditionally once resolved."
    elif refers:
        draft, why = "REFER", "Outside the underwriter's authority on the evidence."
    elif any(m["blocking"] for m in miss):
        draft, why = "REQUEST_INFO", "Required documents outstanding; quote only, no bind."
    elif conds:
        draft, why = "QUOTE_SUBJECT_TO", "Quote subject to pre-bind conditions."
    else:
        draft, why = "QUOTE", "No material issue; quote within the suggested range."
    before = ([f"Resolve contradiction: {x['field_label']} at {x['location']} ({x['resolved']['value']} vs {x['other']['value']})" for x in open_contra]
              + [f"{f['rule'].scope.get('condition') or f['rule'].title} — {f['subject_label']}" for f in conds]
              + [f"Referral to L{r_['level']}: {r_['requirement']}" for r_ in refers]
              + [f"Obtain: {m['item']}" for m in miss if m["status"] == "OPEN" and m["rule_id"] != "DA.ROOF.AGE"])
    factors = sorted([{"title": f["rule"].title, "subject": f["subject_label"], "subject_id": f["subject_id"], "observed": f["observed"], "expected": f["expected"], "rule_id": f["rule"].rule_id,
                       "rule_version": f["rule"].version, "severity": f["rule"].severity, "outcome": f["rule"].outcome, "impact_usd": f["impact_usd"], "citation": citation(f["rule"].source),
                       "source": f["rule"].source, "tier": f["rule"].scope.get("tier", 1), "family": f["rule"].family,
                       "evidence_obs_ids": evidence_ids(rt, cid, f["rule"].rule_id, f["subject_id"])} for f in fired],
                     key=lambda x: (-{"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}[x["severity"]], -x["impact_usd"]))
    for x in open_contra:
        factors.append({"title": f"Contradiction — {x['field_label']}", "subject": x["location"], "subject_id": x["location_uid"], "observed": f"{x['resolved']['source']}: {x['resolved']['value']} · {x['other']['source']}: {x['other']['value']}",
                        "expected": "One value, chosen by the resolution policy or the underwriter", "rule_id": None, "rule_version": 0, "severity": "HIGH", "outcome": "FLAG", "impact_usd": x["impact_usd"],
                        "citation": {"label": "Evidence resolution policy", "doc_id": None, "page": None}, "source": x["policy"], "tier": 2, "family": "data_integrity",
                        "evidence_obs_ids": [x["resolved"]["obs_id"], x["other"]["obs_id"]]})
    cl = claims(rt, cid)
    guides = [{"rule_id": f["rule"].rule_id, "title": f["rule"].title, "result": f["rule"].outcome if f["fired"] else ("PASS" if f.get("applicable", True) else "N/A"),
               "subject": f["subject_label"], "observed": f["observed"], "citation": citation(f["rule"].source), "tier": f["rule"].scope.get("tier", 1),
               "version": f["rule"].version} for f in res]
    n_obs = sum(1 for o in rt.store.account_obs(cid) if o.anchor)
    ndocs = len(c.get("docs", []))
    pack = {
        "built_at": asof, "tiv": tiv, "governing_class": cls["governing"], "classification": cls, "states": states, "suggested": sug,
        "pricing": {**px, "band_low": lo, "band_high": hi, "prior_premium": acct(rt, cid, "prior_premium"), "target_premium": acct(rt, cid, "target_premium"),
                    "bind_offer": acct(rt, cid, "bind_offer")},
        "portfolio": pf, "contradictions": contras, "missing": miss, "factors": factors, "guidelines": guides, "requirements": reqs, "required_level": need_lvl,
        "draft": {"action": draft, "why": why, "before_final": before, "premium_range": [lo, hi]}, "claims": cl, "loss_run_years": loss_run_years(rt, cid),
        "evidence": {"facts": n_obs, "documents": ndocs, "sources": sorted({o.source_family for o in rt.store.account_obs(cid)})},
        "prep": prep_hours(len(states), ndocs, len(contras), len(miss)),
        "auto_prepared": all(m["rule_id"] != "DA.DOC.COPE_MISSING" for m in miss) and not env["case"]["low_conf_fields"],
        "env_case": {k: v for k, v in env["case"].items()}, "fired_rules": [f["rule"].rule_id for f in fired],
    }
    c["pack"] = pack
    for f in fired:
        s_ = st(rt).stats.setdefault(f["rule"].rule_id, {"fired": set(), "accepted": 0, "rejected": 0, "confirmed": 0, "not_confirmed": 0})
        s_["fired"].add(cid)
    return pack


def prep_hours(nloc: int, ndocs: int, ncontra: int, nmiss: int) -> dict:
    manual = 2.0 + 0.35 * nloc + 0.3 * ndocs + 0.25 * ncontra + 0.2 * nmiss
    platform = 0.5 + 0.1 * ncontra
    return {"manual": round(manual, 2), "platform": round(platform, 2), "saved": round(manual - platform, 2),
            "method": "Manual assembly estimate 2.0h + 0.35h/location + 0.3h/document + 0.25h/contradiction + 0.2h/missing item; review with pack 0.5h + 0.1h/contradiction"}


# ============================================================================ impact of a fired check ($, premium-equivalent)
def impact(rt, c: dict, states: list[dict], f: dict, a: dict, px: dict, env: dict) -> int:
    r = f["rule"]
    m = r.impact
    tech = px["technical"]
    try:
        if m == "price_shortfall":
            return int(max(0, tech * (1 - env["auth"]["max_price_dev"]) - a["premium"]))
        if m == "range_gap":
            return int(max(0, env["px"]["band_low"] - a["premium"], a["premium"] - env["px"]["band_high"]))
        if m == "risk_cost":
            return int(tech)
        if m == "cat_load":
            return int(next((x["value"] for x in px["components"] if x["component"].startswith("CAT")), 0))
        if m == "manuscript_load":
            return int(manuscript_load(states, a.get("line") or 1.0))
        if m == "terms_delta":
            fix = dict(a)
            g = env["g"]
            if r.rule_id == "DA.CAT.NS_DED_FLOOR":
                fix["ns_pct"] = g["wind_ded_floor_pct_t1"]
            elif r.rule_id == "DA.CAT.NS_MIN":
                fix["ns_min"] = g["ns_min_floor"]
            elif r.rule_id == "DA.TERMS.AOP_MIN":
                fix["aop"] = env["case"]["aop_min"]
            elif r.rule_id == "DA.TERMS.HAIL_DED":
                fix["wh_pct"] = g["hail_ded_pct_min"]
            return int(max(0, tech - price(rt, c, states, fix)["technical"]))
        if m == "protection_delta" and f["subject_id"]:
            s = next(x for x in states if x["location_uid"] == f["subject_id"])
            if r.rule_id == "DA.PROT.PARTIAL_SPRINKLER":
                alt = {f["subject_id"]: {"sprinkler_pct": 1.0}}
                return int(max(0, tech - price(rt, c, states, a, override=alt)["technical"]))
            alt = {f["subject_id"]: {"sprinkler_pct": min(s.get("sprinkler_pct") or 0, 0.5)}}
            return int(max(0, price(rt, c, states, a, override=alt)["technical"] - tech))
        if m == "roof_delta" and f["subject_id"]:
            alt = {f["subject_id"]: {"roof_year": year(rt.clock) - 5}}
            return int(max(0, tech - price(rt, c, states, a, override=alt)["technical"]))
        if m == "valuation_gap" and f["subject_id"]:
            s = next(x for x in states if x["location_uid"] == f["subject_id"])
            return int(max(0, ((s.get("model_rc") or 0) - (s.get("building_value") or 0)) * tech / max(1, sum(x["tiv"] for x in states))))
        if m == "contradiction_impact":
            return int(env["case"]["open_contradiction_impact"])
    except (StopIteration, KeyError, TypeError):
        return 0
    return 0


# ============================================================================ Stage 2 — assurance of an intended action
def act_env(rt, c: dict, a: dict, px: dict) -> dict:
    ovs = list(c.get("overrides", {}).values())
    unev, contra, texts = 0, 0, []
    for o in ovs:
        ev = override_evidence(rt, c, o)
        o["evidence_check"] = ev
        if ev["needs"] and not ev["found"]:
            unev += 1
            texts.append(f"{o['rule_id']}: '{o['reason']}' — relies on {ev['needs']}, none on file")
        if ev["contrary"]:
            contra += 1
            texts.append(f"{o['rule_id']}: '{o['reason']}' — contrary to {ev['contrary']}")
    tech = px["technical"]
    rat = a.get("rationale") or ""
    return {**a, "dev": (a["premium"] / tech - 1) if tech else 0.0, "has_rationale": len(rat) >= 12, "overrides": len(ovs), "override_unevidenced": unev,
            "override_contrary": contra, "override_text": " · ".join(texts) or "—", "rationale_cites_losses": any(w in rat.lower() for w in ("loss history", "loss record", "clean", "loss-free"))}


OVR_NEEDS = [("in-rack", "an in-rack sprinkler contractor letter or survey", ("in_rack_claimed",), ("Verification survey",)),
             ("recoat", "a roofing contractor invoice or roof survey", ("roof_replacement_planned", "roof_condition_verified"), ()),
             ("replaced", "a roofing contractor invoice or roof survey", ("roof_replacement_planned", "roof_condition_verified"), ())]


def override_evidence(rt, c: dict, o: dict) -> dict:
    reason = o["reason"].lower()
    needs, found = None, False
    for kw, what, fields, doc_types in OVR_NEEDS:
        if kw in reason:
            needs = what
            for uid in rt.store.account_locations(c["case_id"]):
                if any(rt.store.field_obs(uid, f) for f in fields):
                    found = True
            if any(d.get("doc_type") in doc_types for d in c.get("docs", [])):
                found = True
    contrary = None
    if o["rule_id"] == "DA.APPETITE.PROHIBITED":
        cls = (c.get("pack") or {}).get("classification") or {}
        srcs = sorted({e["source"].split(" → ")[0] for e in cls.get("evidence", []) if e["class"] == cls.get("governing")})
        contrary = "the operations evidenced in " + ", ".join(srcs) if srcs else None
    if o["rule_id"] == "DA.PROT.STORAGE_ABOVE_DESIGN":
        v = [ob for uid in rt.store.account_locations(c["case_id"]) for ob in rt.store.field_obs(uid, "sprinkler_design_ft") if ob.obs_type == "V"]
        if v and not found:
            contrary = f"verified design basis {v[-1].value:.0f} ft ({v[-1].source_label})"
    return {"needs": needs, "found": found, "contrary": contrary}


def level_of(rule, f: dict, env: dict, uw_level: int) -> int:
    k = rule.scope.get("level")
    a, case = env["act"], env["case"]
    if k == "price_dev":
        return min(4, level_for_dev(a["dev"]))
    if k == "tiv":
        return next((L for L in (1, 2, 3, 4) if a["limit"] <= NB_AUTHORITY[L]["max_account_tiv"] and case["max_loc_tiv"] * a["line"] <= NB_AUTHORITY[L]["max_loc_tiv"]), 4)
    if k == "premium":
        return next((L for L in (1, 2, 3, 4) if a["premium"] <= NB_AUTHORITY[L]["max_premium"]), 4)
    if k == "override":
        return min(4, max(uw_level + 1, 2))
    return rule.referral_level or 0


def envelope_ok(env_: dict, a: dict) -> tuple[bool, str]:
    why = []
    if env_.get("min_premium") and a["premium"] < env_["min_premium"] - 0.5:
        why.append(f"premium {money(a['premium'])} below approved minimum {money(env_['min_premium'])}")
    if env_.get("min_aop") and (a.get("aop") or 0) < env_["min_aop"]:
        why.append(f"AOP {money(a.get('aop'))} below approved {money(env_['min_aop'])}")
    if env_.get("max_line") and a["line"] > env_["max_line"] + 1e-9:
        why.append(f"line {a['line'] * 100:.0f}% above approved {env_['max_line'] * 100:.0f}%")
    if env_.get("min_ns_pct") and (a.get("ns_pct") or 0) < env_["min_ns_pct"] - 1e-9:
        why.append("named storm below approved")
    if "manuscript" in env_ and (a.get("manuscript") or None) not in (env_["manuscript"], None):
        why.append(f"manuscript '{a.get('manuscript')}' vs approved '{env_['manuscript']}'")
    if env_.get("max_limit") and a["limit"] > env_["max_limit"]:
        why.append("limit above approved")
    return (not why), "; ".join(why)


def assure(rt, cid: str, a: dict, asof: str | None = None, uid: str | None = None) -> dict:
    """Run tier 1 + tier 2 on an intended action and derive the tier-3 human requirements. Pure: does not record."""
    from . import flow as FL
    c = st(rt).cases[cid]
    asof = asof or rt.clock
    pack = build_pack(rt, cid, asof)
    states = pack["states"]
    cls = pack["classification"]
    uid = uid or a.get("by") or c["uw"]
    uw_level = USER_BY_ID[uid]["authority_level"]
    px = price(rt, c, states, a, gov=cls["governing"])
    lo, hi = band(px["technical"])
    g = G(asof)
    pf = portfolio(rt, cid, states, a["line"])
    FL.refresh_conditions(rt, cid, asof, a)
    env = {"case": case_env(rt, c, states, cls, pack["contradictions"], asof, px), "g": g, "pf": pf,
           "px": {"technical": px["technical"], "band_low": lo, "band_high": hi, "oep_250": px["oep_250"]},
           "auth": {"level": uw_level, **NB_AUTHORITY[uw_level]}}
    env["act"] = act_env(rt, c, a, px)
    locs = [loc_env(s, asof, rt, cid) for s in states]
    res = run_rules(rt, "action", asof, env, locs)
    checks = []
    for f in res:
        r = f["rule"]
        dim = r.scope.get("dimension", "guidelines")
        tier = r.scope.get("tier", 1)
        base = {"check_id": f"{r.rule_id}|{f['subject_id'] or 'case'}", "rule_id": r.rule_id, "rule_version": r.version, "tier": tier, "dimension": dim,
                "title": r.title, "subject": f["subject_label"], "subject_id": f["subject_id"], "observed": f["observed"], "expected": f["expected"],
                "source": r.source, "citation": citation(r.source), "severity": r.severity, "outcome": r.outcome if f["fired"] else "PASS", "level": 0,
                "impact_usd": 0, "covered_by": None, "overridden": None, "note": None, "family": r.family,
                "evidence_obs_ids": evidence_ids(rt, cid, r.rule_id, f["subject_id"]) if f["fired"] else []}
        if not f["fired"]:
            base["result"] = "PASS" if f.get("applicable", True) else "N/A"
            checks.append(base)
            continue
        base["impact_usd"] = impact(rt, c, states, f, a, px, env)
        lvl = level_of(r, f, env, uw_level)
        base["level"] = lvl
        out = r.outcome
        result = {"FLAG": "FLAG", "PRICE_ADJUST": "FLAG", "DATA_REQUEST": "FLAG", "CONDITION": "CONDITION"}.get(out, "FAIL")
        if result == "FAIL" and out in ("REFER", "TERM_BREACH", "DECLINE") and lvl and lvl <= uw_level and out != "DECLINE":
            result, base["note"] = "PASS", f"Within {USER_BY_ID[uid]['name']}'s authority (L{uw_level})"
        ov = c.get("overrides", {}).get(f"{r.rule_id}|{f['subject_id'] or 'case'}") or c.get("overrides", {}).get(f"{r.rule_id}|case")
        if ov:
            base["overridden"] = ov
            need = max(lvl, 2) if out in ("REFER", "DECLINE", "BLOCK") else lvl
            if result in ("FAIL", "CONDITION") and need and need > uw_level:
                result, base["note"] = "FAIL", f"Override recorded by {ov['by_name']} (L{uw_level}); overriding this control needs L{need}"
                base["level"] = need
            else:
                result, base["note"] = "FLAG", f"Overridden by {ov['by_name']}: {ov['reason']}"
        if result == "FAIL" and r.scope.get("coverable", True):
            ref = FL.covering_approval(rt, c, r.rule_id, base["level"], a)
            if ref:
                base["covered_by"] = {"referral_id": ref["referral_id"], "approver": ref["approver"], "level": ref["approver_level"], "at": ref["decided_at"]}
                result = "FLAG" if r.scope.get("flag_when_approved") else "PASS"
                base["note"] = f"Approved by {ref['approver']} (L{ref['approver_level']}) on {ref['decided_at']} · action within the approved envelope"
            else:
                inv = FL.invalid_approval(rt, c, r.rule_id, a)
                if inv:
                    base["note"] = f"Approval {inv['referral_id']} does not cover this action: {inv['why']}"
        base["result"] = result
        checks.append(base)
    # remaining conditions (pre-bind)
    conds = [{"text": f"{ch['subject']}: {next((r.scope.get('condition') for r in rt.rules.values() if r.rule_id == ch['rule_id']), ch['expected'])}", "source": ch["rule_id"],
              "status": "OPEN", "due": "Before bind", "rule_id": ch["rule_id"], "subject_id": ch["subject_id"]} for ch in checks if ch["result"] == "CONDITION"]
    conds += [{"text": k["text"], "source": k["source"], "status": k["status"], "due": k["due"], "evidence": k.get("evidence")} for k in c.get("conditions", []) if k.get("kind") == "evidence"]
    dims = []
    for key, lab in DIMENSIONS:
        cs = [ch for ch in checks if ch["dimension"] == key and ch["result"] != "N/A"]
        worst = max((RANK[ch["result"]] for ch in cs), default=0)
        res_ = {3: "FAIL", 2: "FLAG", 1: "PASS", 0: "PASS"}[worst]
        dims.append({"key": key, "label": lab, "result": res_, "checks": len(cs), "issues": sum(1 for ch in cs if ch["result"] in ("FAIL", "FLAG")),
                     "summary": _dim_summary(key, cs, env)})
    fails = [ch for ch in checks if ch["result"] == "FAIL"]
    flags = [ch for ch in checks if ch["result"] == "FLAG"]
    open_conds = [k for k in conds if k["status"] == "OPEN"]
    verdict = "REFER_HOLD" if fails else "PASS_WITH_FLAGS" if (flags or open_conds) else "PASS"
    req_level = max([ch["level"] for ch in fails] + [uw_level if verdict != "REFER_HOLD" else 0])
    blocked = [ch for ch in fails if not next(r for r in rt.rules.values() if r.rule_id == ch["rule_id"]).scope.get("coverable", True)]
    if verdict == "REFER_HOLD":
        if blocked and not [ch for ch in fails if ch not in blocked]:
            owner = {"user_id": uid, "name": USER_BY_ID[uid]["name"], "level": uw_level, "why": "Hold: resolve the blocking items, then resubmit"}
        else:
            ap = APPROVERS.get(max(2, min(4, req_level)), "u_robert")
            owner = {"user_id": ap, "name": USER_BY_ID[ap]["name"], "level": USER_BY_ID[ap]["authority_level"], "why": f"Referral to L{max(2, req_level)}"}
    else:
        owner = {"user_id": uid, "name": USER_BY_ID[uid]["name"], "level": uw_level, "why": "Within authority — the underwriter decides"}
    tier3 = []
    if any(ch["overridden"] for ch in checks):
        tier3.append("Material override of an engine control")
    if env["case"]["open_material_contradictions"]:
        tier3.append("Unresolved ambiguity in the evidence")
    if a.get("manuscript"):
        tier3.append("Complex coverage — manuscript wording")
    if any(ch["severity"] == "CRITICAL" and ch["result"] != "PASS" for ch in checks) or a["limit"] >= g["large_limit"]:
        tier3.append("High severity / large limit")
    tier3.append("Final commitment (quote, bind or decline) is a human decision")
    exposure = sum(ch["impact_usd"] for ch in checks if ch["result"] in ("FAIL", "FLAG"))
    dev = env["act"]["dev"]
    summ = (f"{a['type'].title()} at {money(a['premium'])} ({pct(dev, True)} vs technical {money(px['technical'])}; permitted ±{NB_AUTHORITY[uw_level]['max_price_dev'] * 100:.0f}% at L{uw_level}): "
            f"{ {'PASS': 'Pass', 'PASS_WITH_FLAGS': 'Pass with flags', 'REFER_HOLD': 'Refer / hold'}[verdict]}"
            + (f" · {len(fails)} fail" if fails else "") + (f" · {len(flags)} flag(s)" if flags else "") + (f" · {len(open_conds)} condition(s) before bind" if open_conds else ""))
    return {"verdict": verdict, "dimensions": dims, "checks": sorted(checks, key=lambda ch: (-RANK.get(ch["result"], -1), ch["tier"], ch["rule_id"])), "conditions": conds,
            "required_level": req_level, "owner": owner, "tier3": tier3, "technical": px["technical"], "deviation": dev,
            "permitted_dev": NB_AUTHORITY[uw_level]["max_price_dev"], "band": [lo, hi], "pricing": px, "portfolio": pf, "exposure_usd": exposure, "summary": summ,
            "run_at": asof, "uw_level": uw_level, "counts": {"tier1": sum(1 for ch in checks if ch["tier"] == 1 and ch["result"] != "N/A"),
                                                            "tier2": sum(1 for ch in checks if ch["tier"] == 2 and ch["result"] != "N/A"),
                                                            "fail": len(fails), "flag": len(flags), "pass": sum(1 for ch in checks if ch["result"] == "PASS")}}


def _dim_summary(key: str, cs: list[dict], env: dict) -> str:
    bad = [ch for ch in cs if ch["result"] in ("FAIL", "FLAG")]
    if key == "pricing":
        a = env["act"]
        return f"{pct(a['dev'], True)} vs technical {money(env['px']['technical'])} · permitted ±{env['auth']['max_price_dev'] * 100:.0f}%"
    if key == "authority" and not bad:
        return f"Within L{env['auth']['level']} or covered by approval"
    if not bad:
        return f"{len(cs)} checks pass"
    return "; ".join(sorted({ch["title"] for ch in bad}))[:180]

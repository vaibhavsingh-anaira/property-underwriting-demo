"""Resolved views over the ledger: location state, exposure snapshots, contract stages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from uwc.ledger.fields import POLICY_EXPLAINER, display, label, policy_of, resolve

if TYPE_CHECKING:
    from uwc.runtime import Runtime

# fields whose change over time is a real risk change (as-of-bind for E0); everything else uses best current knowledge
DYNAMIC = {"occupancy_class", "storage_height_ft", "commodity", "vacancy_pct", "sprinkler_impaired"}
VALUE_FIELDS = ("building_value", "contents_value", "stock_value", "bi_value", "tiv_reported")
CONTRACT_FIELDS = ("limit", "limit_basis", "aop_deductible", "named_storm_ded_pct", "named_storm_ded_min", "wind_hail_ded_pct",
                   "bi_sublimit", "flood_sublimit", "eq_sublimit", "premium", "forms", "safeguards", "subjectivities")


def resolved(rt: "Runtime", uid: str, field: str, as_of: str | None = None, term: str | None = None):
    obs = rt.store.field_obs(uid, field, as_of=as_of)
    if term:
        obs = [o for o in obs if o.term == term]
    pol = policy_of(field)
    if field in VALUE_FIELDS and term == "prior":
        s = [o for o in obs if o.obs_type == "S"]
        if s:
            return s[-1], False, obs
    w, conflict = resolve(obs, pol)
    return w, conflict, obs


def location_state(rt: "Runtime", acct: str, uid: str, term: str = "current", as_of_dynamic: str | None = None) -> dict[str, Any]:
    """Flat dict of resolved values (+ `_obs` field→obs_id, `_conflicts`) used by rules, rater and UI."""
    ent = rt.store.account_locations(acct)[uid]
    out: dict[str, Any] = {"location_uid": uid, "label": ent.label, "address": ent.address, "city": ent.city, "state": ent.state,
                           "match_status": ent.match_status, "in_prior": ent.in_prior, "in_current": ent.in_current, "_obs": {}, "_conflicts": {}}
    for f in rt.store.subject_fields(uid):
        if f in VALUE_FIELDS:
            continue
        w, conflict, obs = resolved(rt, uid, f, as_of=as_of_dynamic if f in DYNAMIC else None)
        if w is None:
            continue
        out[f] = w.value
        out["_obs"][f] = w.obs_id
        if conflict:
            out["_conflicts"][f] = [o.obs_id for o in obs]
    vterm = term
    has_term = any(rt.store.field_obs(uid, f) and any(o.term == vterm for o in rt.store.field_obs(uid, f)) for f in VALUE_FIELDS)
    if term == "current" and not has_term:
        vterm = "prior"          # no renewal SOV yet: carry expiring values forward
        out["_values_carried"] = True
    for f in VALUE_FIELDS:
        w, _, _ = resolved(rt, uid, f, term=vterm)
        out[f] = w.value if w else None
        if w:
            out["_obs"][f] = w.obs_id
    comps = [out.get(k) or 0 for k in ("building_value", "contents_value", "stock_value", "bi_value")]
    out["tiv"] = sum(comps) if any(comps) else (out.get("tiv_reported") or 0)
    return out


def exposure_row(s: dict) -> dict:
    return dict(location_uid=s["location_uid"], label=s["label"], lat=s.get("lat"), lon=s.get("lon"), zone=s.get("cat_zone"), state=s.get("state"),
                construction=s.get("construction_class"), year_built=s.get("year_built"), roof_year=s.get("roof_year"),
                stories=s.get("stories"), wind_tier=s.get("wind_tier"), flood_zone=s.get("flood_zone"), wildfire=s.get("wildfire_score"),
                occupancy=s.get("occupancy_class"), ppc=s.get("ppc"), sprinkler_pct=s.get("sprinkler_pct"),
                geocode_level=s.get("geocode_level"), building=s.get("building_value") or 0, contents=s.get("contents_value") or 0,
                stock=s.get("stock_value") or 0, bi=s.get("bi_value") or 0)


def snapshots(rt: "Runtime", acct: str) -> dict:
    """E0 = expiring exposure (as-bound values, as-of-bind dynamic risk factors); E1 = renewal exposure."""
    pas = rt.pas.get(acct, {})
    term_start = pas.get("term_start")
    locs = rt.store.account_locations(acct)
    prior_states, cur_states = [], []
    for uid, e in locs.items():
        if e.in_prior:
            prior_states.append(location_state(rt, acct, uid, term="prior", as_of_dynamic=term_start))
        if e.in_current or (not rt.renewal_sov.get(acct) and e.in_prior):
            cur_states.append(location_state(rt, acct, uid, term="current"))
    return {"prior": prior_states, "current": cur_states, "E0": [exposure_row(s) for s in prior_states],
            "E1": [exposure_row(s) for s in cur_states]}


def contract_stage(rt: "Runtime", acct: str, stage: str) -> dict:
    sid = f"{acct}:{stage}"
    out: dict[str, Any] = {"_obs": {}}
    for f in CONTRACT_FIELDS:
        obs = rt.store.field_obs(sid, f)
        c = [o for o in obs if o.obs_type == "C"] or obs
        if c:
            out[f] = c[-1].value
            out["_obs"][f] = c[-1].obs_id
    return out


def resolved_field_payload(rt: "Runtime", subject_id: str, field: str) -> dict:
    obs = rt.store.field_obs(subject_id, field)
    pol = policy_of(field)
    w, conflict = resolve(obs, pol)
    return {"field_code": field, "label": label(field), "value": w.value if w else None, "value_display": display(field, w.value if w else None),
            "resolved_obs_id": w.obs_id if w else None, "policy": pol, "policy_explainer": POLICY_EXPLAINER.get(pol, ""), "conflict": conflict,
            "observations": [rt.obs_payload(o, w) for o in obs]}

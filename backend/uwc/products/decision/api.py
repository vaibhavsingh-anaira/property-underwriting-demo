"""HTTP endpoints for Decision Assurance (/api/decision/...). Handlers import RT and LOCK from uwc.api lazily."""
from __future__ import annotations

import statistics
import tempfile
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Body, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from uwc.ledger.fields import display, label as flabel
from uwc.refdata import OCCUPANCY, USER_BY_ID, ZONES

from .model import (ACTION_LABEL, DIMENSIONS, NB_AUTHORITY, NB_STANDARDS, PIPE, STAGE_NAME, VERDICT_LABEL, DState, money, st)

router = APIRouter(prefix="/api/decision")


def _rt():
    from uwc.api import LOCK, RT
    from . import ensure
    ensure(RT)
    return RT, LOCK


def _uid(x: str | None) -> str:
    from uwc.api import uid_of
    return uid_of(x)


def _case(rt, cid: str) -> dict:
    c = st(rt).cases.get(cid)
    if not c:
        raise HTTPException(404, "case not found")
    return c


def _err(fn):
    try:
        return fn()
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except (ValueError, KeyError, StopIteration) as e:
        raise HTTPException(409, str(e))


# ============================================================================ serializers
LOC_FIELDS = ["occupancy_class", "construction_class", "year_built", "stories", "sqft", "roof_year", "roof_type", "sprinkler_pct", "fire_alarm", "ppc",
              "storage_height_ft", "sprinkler_design_ft", "commodity", "building_value", "contents_value", "stock_value", "bi_value", "cat_zone", "wind_tier",
              "flood_zone", "model_rc", "roof_replacement_planned", "roof_condition_verified", "in_rack_claimed"]
ACCT_FIELDS = ["named_insured", "fein", "naics", "company_naics", "years_in_business", "operations_description", "effective_date", "limit_requested",
               "prior_carrier", "prior_premium", "target_premium", "bind_offer", "loss_run_period", "loss_count_declared", "manuscript_clause", "quote_needed_by"]


def _fact(rt, sid: str, f: str, winner_id: str | None = None) -> dict | None:
    obs = rt.store.field_obs(sid, f)
    if f in ("building_value", "contents_value", "stock_value", "bi_value"):
        obs = [o for o in obs if o.term == "current"] or obs
    if not obs:
        return None
    w = rt.store.obs.get(winner_id) if winner_id else None
    if not w or w.field_code != f:
        from uwc.ledger.fields import policy_of, resolve
        w, _ = resolve(obs, policy_of(f))
        w = w or obs[-1]
    vals = {display(f, o.value) for o in obs if o.value is not None}
    v = w.value
    disp = ZONES[v][0] if f == "cat_zone" and v in ZONES else display(f, v) if not isinstance(v, list) else ", ".join(map(str, v))
    return {"field": f, "label": flabel(f), "value": disp, "obs_id": w.obs_id, "source": w.source_label, "obs_type": w.obs_type, "confidence": round(w.confidence, 2),
            "sources": len({o.doc_id or o.source_label for o in obs}), "conflict": len(vals) > 1 and f not in ("loss_run_period",)}


def facts_payload(rt, c: dict) -> dict:
    p = c.get("pack") or {}
    locs = []
    for s in p.get("states", []):
        rows = [x for x in (_fact(rt, s["location_uid"], f, s["_obs"].get(f)) for f in LOC_FIELDS) if x]
        locs.append({"location_uid": s["location_uid"], "label": s["label"], "address": f"{s['address']}, {s['city']}, {s['state']}", "tiv": s["tiv"],
                     "occupancy": OCCUPANCY.get(s.get("occupancy_class"), (s.get("occupancy_raw") or "—",))[0], "facts": rows,
                     "lat": s.get("lat"), "lon": s.get("lon")})
    acct = [x for x in (_fact(rt, c["case_id"], f) for f in ACCT_FIELDS) if x]
    return {"account": acct, "locations": locs}


def assurance_payload(res: dict | None) -> dict | None:
    if not res:
        return None
    keep = ("assurance_id", "action_id", "action_version", "action_type", "premium", "verdict", "dimensions", "checks", "conditions", "required_level", "owner",
            "tier3", "technical", "deviation", "permitted_dev", "band", "exposure_usd", "summary", "run_at", "uw_level", "counts", "rerun")
    out = {k: res.get(k) for k in keep}
    out["checks"] = [{k: v for k, v in ch.items()} for ch in res["checks"] if ch["result"] != "N/A"]
    out["portfolio"] = res.get("portfolio")
    out["pricing"] = {k: res["pricing"].get(k) for k in ("technical", "components", "aal", "oep_250", "modifiers", "line", "manuscript_load")} if res.get("pricing") else None
    return out


def pack_payload(p: dict | None) -> dict | None:
    if not p:
        return None
    out = {k: v for k, v in p.items() if k not in ("states", "env_case", "classification")}
    cl = p.get("classification") or {}
    out["classification"] = {"governing": cl.get("governing"), "label": cl.get("label"), "evidence": cl.get("evidence", []),
                             "classes": [{"key": k, "label": OCCUPANCY.get(k, (k,))[0]} for k in cl.get("classes", [])]}
    return out


def referral_payload(rt, rid: str) -> dict:
    r = dict(st(rt).referrals[rid])
    c = st(rt).cases[r["case_id"]]
    r["href"] = f"/decision/cases/{r['case_id']}"
    r["scenario"] = c.get("scenario")
    r["envelope_text"] = _env(r["envelope"])
    return r


def _env(e: dict) -> str:
    from .flow import _env_text
    return _env_text(e or {})


def stage_reached(c: dict) -> int:
    if c.get("outcome"):
        return 10
    if c.get("decision"):
        return 9
    if c["assurances"]:
        return 8
    if c["actions"]:
        return 6
    if c["judged"]:
        return 5
    if c.get("pack"):
        return 4
    if c["received"]:
        return 2
    return 0


def queue_item(rt, c: dict) -> dict:
    from .stages import case_exposure
    from .flow import plus
    p = c.get("pack") or {}
    a = c["actions"][-1] if c["actions"] else None
    res = c["assurances"][-1] if c["assurances"] else None
    s = st(rt)
    qb = None
    if c["received"]:
        qbo = rt.store.field_obs(c["case_id"], "quote_needed_by")
        qb = qbo[-1].value if qbo else plus(c["received"], 14)
    open_statuses = ("PREPARED", "IN_REVIEW", "READY", "HOLD", "REFERRED", "APPROVED")
    sla = (date.fromisoformat(qb) - date.fromisoformat(rt.clock)).days if qb and c["status"] in open_statuses else None
    return {"case_id": c["case_id"], "insured": c["insured"], "short": c["short"], "scenario": c.get("scenario"), "title": c["title"] if c.get("scenario") else None,
            "broker": c["broker"], "underwriter": USER_BY_ID[c["uw"]]["name"], "underwriter_id": c["uw"], "segment": c["segment"], "state": c["state"],
            "class_label": (p.get("classification") or {}).get("label"), "tiv": p.get("tiv"), "received": c["received"], "expected": c["arrive"], "effective": c["effective"],
            "quote_by": qb, "sla_days": sla, "status": c["status"], "stage": stage_reached(c), "draft": (p.get("draft") or {}).get("action"),
            "verdict": res["verdict"] if res else None, "technical": (p.get("pricing") or {}).get("technical"), "premium": a["premium"] if a else None,
            "deviation": res["deviation"] if res else None, "contradictions": sum(1 for x in c.get("contradictions", []) if x["status"] == "OPEN"),
            "missing": sum(1 for m in p.get("missing", []) if m["status"] == "OPEN"), "referral_pending": any(s.referrals[r]["status"] == "PENDING" for r in c["referrals"]),
            "exposure": case_exposure(rt, c)["total"], "auto_prepared": p.get("auto_prepared"), "hero": c["kind"] == "hero"}


def case_payload(rt, c: dict) -> dict:
    from uwc.api import doc_meta
    from .stages import case_exposure
    s = st(rt)
    res = c["assurances"][-1] if c["assurances"] else None
    pend = sorted([{"date": e["date"], "title": e["title"], "type": e["type"]} for e in rt.dynamic if not e.get("done") and e.get("case_id") == c["case_id"]], key=lambda e: e["date"])
    subj = []
    if c.get("quote"):
        fired = {(f["rule_id"], f.get("subject_id")) for f in (c.get("pack") or {}).get("factors", [])}
        for sj in c["quote"].get("subjectivities", []):
            done = (sj.get("rule_id"), sj.get("subject_id")) not in fired if sj.get("rule_id") else any(k["text"] == sj["text"] and k["status"] == "CLEARED" for k in c["conditions"])
            subj.append({**sj, "status": "CLEARED" if done else "OPEN"})
    return {**queue_item(rt, c), "contact": c["contact"], "uw_level": USER_BY_ID[c["uw"]]["authority_level"], "clock": rt.clock,
            "pack": pack_payload(c.get("pack")), "facts": facts_payload(rt, c) if c.get("pack") else None,
            "actions": c["actions"], "assurance": assurance_payload(res),
            "assurances": [{"assurance_id": x["assurance_id"], "action_version": x["action_version"], "action_type": x["action_type"], "premium": x["premium"], "verdict": x["verdict"],
                            "run_at": x["run_at"], "deviation": x["deviation"], "fails": x["counts"]["fail"], "flags": x["counts"]["flag"], "summary": x["summary"], "rerun": x.get("rerun")} for x in c["assurances"]],
            "referrals": [referral_payload(rt, r) for r in c["referrals"]], "conditions": c["conditions"], "requests": c["requests"], "overrides": list(c["overrides"].values()),
            "decision": c.get("decision"), "quote": {**c["quote"], "subjectivities": subj} if c.get("quote") else None, "bound": {k: v for k, v in (c.get("bound") or {}).items() if k != "zone_contrib"} or None,
            "outcome": c.get("outcome"), "feedback": c.get("feedback", []), "exposure_detail": case_exposure(rt, c), "surveys": c.get("surveys", []),
            "documents": sorted([doc_meta(rt.store.docs[d["doc_id"]]) for d in c["docs"] if d["doc_id"] in rt.store.docs], key=lambda d: d["received_at"], reverse=True),
            "timeline": list(reversed(c["timeline"])), "pending": pend, "authority": {str(k): v for k, v in NB_AUTHORITY.items()}}


# ============================================================================ dashboard
def dashboard(rt) -> dict:
    from .stages import case_exposure
    s = st(rt)
    cs = [c for c in s.cases.values() if c["received"]]
    packs = [c for c in cs if c.get("pack")]
    last = [c["assurances"][-1]["verdict"] for c in cs if c["assurances"]]
    ex = [case_exposure(rt, c) for c in cs]
    intercepted = [c for c in cs if any(x["verdict"] == "REFER_HOLD" for x in c["assurances"]) and (c["status"] == "DECLINED" or (c["actions"] and c["actions"][-1]["action_id"] != next(x for x in c["assurances"] if x["verdict"] == "REFER_HOLD")["action_id"]))]
    errors = sum(next(x for x in c["assurances"] if x["verdict"] == "REFER_HOLD")["counts"]["fail"] for c in intercepted) + sum(1 for c in cs for x in c.get("contradictions", []) if x["status"] == "RESOLVED" and x.get("adverse_resolved") and x["material"])
    ttd = [(date.fromisoformat(c["decision"]["at"]) - date.fromisoformat(c["received"])).days for c in cs if c.get("decision")]
    funnel = [{"code": code, "name": STAGE_NAME[code], "count": sum(1 for c in cs if stage_reached(c) >= int(code) or (code == "03" and c.get("pack")) or (code == "07" and c["assurances"]))} for code, *_ in PIPE]
    funnel[0]["count"] = len(cs)
    tiers = {1: {"checks": 0, "fired": 0}, 2: {"checks": 0, "fired": 0}}
    issues: dict[str, dict] = {}
    for c in cs:
        seen = set()
        for x in c["assurances"][:1]:
            for ch in x["checks"]:
                if ch["result"] == "N/A":
                    continue
                tiers[ch["tier"]]["checks"] += 1
                if ch["result"] in ("FAIL", "FLAG", "CONDITION") or ch.get("covered_by"):
                    tiers[ch["tier"]]["fired"] += 1
                    k = ch["rule_id"]
                    if k not in seen:
                        seen.add(k)
                        it = issues.setdefault(k, {"rule_id": k, "title": ch["title"], "tier": ch["tier"], "dimension": ch["dimension"], "cases": 0, "impact_usd": 0})
                        it["cases"] += 1
                        it["impact_usd"] += ch["impact_usd"]
        for f in (c.get("pack") or {}).get("factors", []):
            if f["rule_id"] and f["rule_id"] not in seen:
                seen.add(f["rule_id"])
                it = issues.setdefault(f["rule_id"], {"rule_id": f["rule_id"], "title": f["title"], "tier": f["tier"], "dimension": "pack", "cases": 0, "impact_usd": 0})
                it["cases"] += 1
                it["impact_usd"] += f["impact_usd"]
    tier3 = sum(1 for r in s.referrals.values()) + sum(1 for c in cs if c.get("decision"))
    uw: dict[str, dict] = {}
    for c in cs:
        u = uw.setdefault(c["uw"], {"user_id": c["uw"], "name": USER_BY_ID[c["uw"]]["name"], "level": USER_BY_ID[c["uw"]]["authority_level"], "cases": 0, "pass": 0, "flags": 0, "refer": 0,
                                    "overrides": 0, "_dev": [], "bound": 0})
        u["cases"] += 1
        if c["assurances"]:
            v = c["assurances"][0]["verdict"]
            u["pass" if v == "PASS" else "flags" if v == "PASS_WITH_FLAGS" else "refer"] += 1
            u["_dev"].append(c["assurances"][0]["deviation"])
        u["overrides"] += len(c["overrides"])
        u["bound"] += 1 if c.get("bound") else 0
    for u in uw.values():
        u["avg_dev"] = sum(u["_dev"]) / len(u["_dev"]) if u["_dev"] else None
        del u["_dev"]
    br: dict[str, dict] = {}
    for c in cs:
        b = br.setdefault(c["broker"], {"broker": c["broker"], "cases": 0, "contradictions": 0, "missing": 0, "refer": 0, "quoted": 0, "bound": 0, "premium": 0})
        b["cases"] += 1
        b["contradictions"] += len(c.get("contradictions", []))
        b["missing"] += len((c.get("pack") or {}).get("missing", []))
        b["refer"] += 1 if any(x["verdict"] == "REFER_HOLD" for x in c["assurances"]) else 0
        b["quoted"] += 1 if c.get("quote") else 0
        b["bound"] += 1 if c.get("bound") else 0
        b["premium"] += (c.get("bound") or {}).get("premium", 0)
    seg: dict[str, dict] = {}
    for c in cs:
        g = seg.setdefault(c["segment"], {"segment": c["segment"], "cases": 0, "refer": 0, "bound": 0, "premium": 0, "tiv": 0})
        g["cases"] += 1
        g["refer"] += 1 if any(x["verdict"] == "REFER_HOLD" for x in c["assurances"]) else 0
        g["bound"] += 1 if c.get("bound") else 0
        g["premium"] += (c.get("bound") or {}).get("premium", 0)
        g["tiv"] += (c.get("pack") or {}).get("tiv", 0)
    # outcome feedback
    fb = [f for c in cs for f in c.get("feedback", [])]
    scored = [f for f in fb if f.get("outcome")]
    ovs = [f for f in fb if f["overridden"]]
    bound = [c for c in cs if c.get("bound")]
    with_out = [c for c in bound if c.get("outcome")]
    flagged = [c for c in with_out if c.get("feedback")]
    clean = [c for c in with_out if not c.get("feedback")]
    lr = lambda xs: (sum((c["outcome"]["loss"] or {}).get("incurred", 0) for c in xs if c["outcome"]["loss"] and not c["outcome"]["loss"]["excluded"]) / sum(c["bound"]["premium"] for c in xs)) if xs else None
    rules = []
    for rid, s_ in sorted(s.stats.items()):
        tot = s_["accepted"] + s_["rejected"]
        r = rt.rules.get(rid)
        rules.append({"rule_id": rid, "title": r.title if r else rid, "tier": r.scope.get("tier", 1) if r else 1, "fired": len(s_["fired"]), "accepted": s_["accepted"], "rejected": s_["rejected"],
                      "confirmed": s_["confirmed"], "not_confirmed": s_["not_confirmed"], "precision": (s_["accepted"] / tot) if tot else None})
    # portfolio fit
    from .engine import nb_zone_contrib
    nbz = nb_zone_contrib(rt)
    zones = []
    for z, (name, peril, *_r) in ZONES.items():
        thr = ZONES[z][5]
        inf = rt.zone_total(z, "prior")
        zones.append({"zone_id": z, "name": name, "peril": peril, "threshold": thr, "in_force": inf, "nb_bound": nbz.get(z, 0), "util": (inf + nbz.get(z, 0)) / thr, "util_in_force": inf / thr})
    zones.sort(key=lambda z: -z["util"])
    mix: dict[str, dict] = {}
    for c in bound:
        k = (c.get("pack") or {}).get("classification", {}).get("label") or "—"
        m = mix.setdefault(k, {"class": k, "bound": 0, "premium": 0})
        m["bound"] += 1
        m["premium"] += c["bound"]["premium"]
    return {
        "as_of": rt.clock, "cases": len(s.cases), "prepared": len(packs), "expected": sum(1 for c in s.cases.values() if not c["received"]),
        "auto_prepared": sum(1 for c in packs if c["pack"].get("auto_prepared")), "assured": sum(1 for c in cs if c["assurances"]),
        "verdicts": {"PASS": last.count("PASS"), "PASS_WITH_FLAGS": last.count("PASS_WITH_FLAGS"), "REFER_HOLD": last.count("REFER_HOLD")},
        "first_verdicts": {v: sum(1 for c in cs if c["assurances"] and c["assurances"][0]["verdict"] == v) for v in ("PASS", "PASS_WITH_FLAGS", "REFER_HOLD")},
        "exposure": {"total": sum(e["total"] for e in ex), "preparation": sum(e["preparation"] for e in ex), "assurance": sum(e["assurance"] for e in ex),
                     "loss_avoided": sum(e["loss_avoided"] for e in ex), "cases": sum(1 for e in ex if e["total"]),
                     "by_case": sorted([{"case_id": c["case_id"], "insured": c["short"], "scenario": c.get("scenario"), **e} for c, e in zip(cs, ex) if e["total"]], key=lambda x: -x["total"])[:8]},
        "errors_intercepted": errors, "commitments_changed": len(intercepted),
        "hours_saved": round(sum(c["pack"]["prep"]["saved"] for c in packs), 1), "hours_manual": round(sum(c["pack"]["prep"]["manual"] for c in packs), 1),
        "median_days_to_decision": statistics.median(ttd) if ttd else None, "decided": len(ttd),
        "funnel": funnel, "tiers": {"tier1": tiers[1], "tier2": tiers[2], "tier3": {"human_decisions": tier3, "referrals": len(s.referrals)}},
        "by_underwriter": sorted(uw.values(), key=lambda u: -u["cases"]), "by_broker": sorted(br.values(), key=lambda b: -b["cases"]),
        "by_segment": sorted(seg.values(), key=lambda g: -g["cases"]), "top_issues": sorted(issues.values(), key=lambda x: (-x["cases"], -x["impact_usd"]))[:10],
        "feedback": {"flags": len(fb), "overrides": len(ovs), "override_rate": len(ovs) / len(fb) if fb else None, "scored": len(scored),
                     "confirmed": sum(1 for f in scored if f["outcome"] == "CONFIRMED"), "overrides_confirmed": sum(1 for f in ovs if f.get("outcome") == "CONFIRMED"),
                     "bound": len(bound), "with_outcome": len(with_out), "loss_ratio_flagged": lr(flagged), "loss_ratio_clean": lr(clean),
                     "losses": sum(1 for c in with_out if c["outcome"]["loss"]), "rules": rules},
        "portfolio": {"zones": zones[:8], "mix": sorted(mix.values(), key=lambda m: -m["premium"])},
        "bound_premium": sum(c["bound"]["premium"] for c in bound), "quoted": sum(1 for c in cs if c.get("quote")), "bound": len(bound),
    }


# ============================================================================ routes
@router.get("/dashboard")
def get_dashboard():
    rt, lock = _rt()
    with lock:
        return dashboard(rt)


@router.get("/cases")
def get_cases():
    rt, lock = _rt()
    with lock:
        s = st(rt)
        return [queue_item(rt, s.cases[k]) for k in s.cases]


@router.get("/cases/{cid}")
def get_case(cid: str):
    rt, lock = _rt()
    with lock:
        return case_payload(rt, _case(rt, cid))


@router.post("/cases/{cid}/contradictions/{ctr}/resolve")
def post_resolve(cid: str, ctr: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        _case(rt, cid)
        _err(lambda: FL.resolve_contradiction(rt, cid, ctr, b.get("choice", "resolved"), b.get("note", ""), _uid(x_user_id), rt.clock))
        return case_payload(rt, _case(rt, cid))


@router.post("/cases/{cid}/requests")
def post_request(cid: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        _case(rt, cid)
        if not b.get("items"):
            raise HTTPException(400, "items required")
        _err(lambda: FL.request_info(rt, cid, b["items"], _uid(x_user_id), rt.clock))
        return case_payload(rt, _case(rt, cid))


@router.post("/cases/{cid}/inspection")
def post_inspection(cid: str, b: dict = Body(default={}), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        _case(rt, cid)
        _err(lambda: FL.order_inspection(rt, cid, _uid(x_user_id), rt.clock, b.get("scope") or "Verification survey"))
        return case_payload(rt, _case(rt, cid))


@router.post("/cases/{cid}/overrides")
def post_override(cid: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        _case(rt, cid)
        if not (b.get("reason") or "").strip():
            raise HTTPException(400, "An override needs a reason")
        FL.override(rt, cid, b["rule_id"], b.get("subject_id"), b["reason"].strip(), _uid(x_user_id), rt.clock)
        return case_payload(rt, _case(rt, cid))


@router.post("/cases/{cid}/prerefer")
def post_prerefer(cid: str, b: dict = Body(default={}), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        _case(rt, cid)
        _err(lambda: FL.prerefer(rt, cid, b.get("note", ""), _uid(x_user_id), rt.clock))
        return case_payload(rt, _case(rt, cid))


@router.post("/cases/{cid}/assure/preview")
def post_preview(cid: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import engine as E
    rt, lock = _rt()
    with lock:
        c = _case(rt, cid)
        if not c.get("pack"):
            raise HTTPException(409, "The decision pack is not ready")
        uid = _uid(x_user_id)
        a = _err(lambda: E.normalize(rt, c, b))
        a.update(by=uid, by_name=USER_BY_ID[uid]["name"], at=rt.clock, action_id="preview", version=len(c["actions"]) + 1)
        return {"action": a, "assurance": assurance_payload(_err(lambda: E.assure(rt, cid, a, rt.clock, uid)))}


@router.post("/cases/{cid}/actions")
def post_action(cid: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        c = _case(rt, cid)
        if not c.get("pack"):
            raise HTTPException(409, "The decision pack is not ready")
        if c["status"] in ("BOUND", "DECLINED", "LOST"):
            raise HTTPException(409, f"Case is {c['status'].lower()}")
        _err(lambda: FL.submit_action(rt, cid, b, _uid(x_user_id), rt.clock))
        return case_payload(rt, c)


@router.post("/cases/{cid}/route")
def post_route(cid: str, b: dict = Body(default={}), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        c = _case(rt, cid)
        msg = _err(lambda: FL.route(rt, cid, _uid(x_user_id), rt.clock, b.get("note", "")))
        return {"message": msg, "case": case_payload(rt, c)}


@router.post("/cases/{cid}/decision")
def post_decision(cid: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        c = _case(rt, cid)
        d = (b.get("decision") or "").upper()
        if d not in ("COMMIT", "DECLINE"):
            raise HTTPException(400, "decision must be COMMIT or DECLINE")
        msg = _err(lambda: FL.final_decision(rt, cid, d, _uid(x_user_id), rt.clock, b.get("note", "")))
        return {"message": msg, "case": case_payload(rt, c)}


@router.post("/cases/{cid}/bind")
def post_bind(cid: str, x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        c = _case(rt, cid)
        msg = _err(lambda: FL.bind(rt, cid, _uid(x_user_id), rt.clock))
        return {"message": msg, "case": case_payload(rt, c)}


@router.get("/referrals")
def get_referrals():
    rt, lock = _rt()
    with lock:
        return sorted([referral_payload(rt, r) for r in st(rt).referrals], key=lambda r: (r["status"] != "PENDING", r["requested_at"]), reverse=False)


@router.post("/referrals/{rid}/decision")
def post_ref_decision(rid: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import flow as FL
    rt, lock = _rt()
    with lock:
        if rid not in st(rt).referrals:
            raise HTTPException(404, "referral not found")
        d = (b.get("decision") or "").upper()
        if d not in ("APPROVE", "DECLINE"):
            raise HTTPException(400, "decision must be APPROVE or DECLINE")
        conds = [x.strip() for x in (b.get("conditions") or []) if x and x.strip()]
        env = {k: v for k, v in (b.get("envelope") or {}).items() if v not in (None, "")} or None
        _err(lambda: FL.decide_referral(rt, rid, d, conds, env, b.get("note", ""), _uid(x_user_id), rt.clock))
        return referral_payload(rt, rid)


@router.get("/assurance-log")
def get_log():
    rt, lock = _rt()
    with lock:
        s = st(rt)
        return [{**x, "insured": s.cases[x["case_id"]]["short"], "scenario": s.cases[x["case_id"]].get("scenario"), "underwriter": USER_BY_ID[x["uw"]]["name"]} for x in reversed(s.assurance_log)]


# ============================================================================ sandbox — your own files through the real Stage 1 + Stage 2
class _Sandbox:
    """A throwaway runtime for uploaded files: its own ledger, the live rules, the live portfolio."""

    def __init__(self, rt):
        from uwc.ledger.store import Store
        self.store = Store()
        self.email_highlights = {}
        self.rules = rt.rules
        self.clock = rt.clock
        self.decision = DState(built=True)
        self._rt = rt
        self.outbox, self.dynamic = [], []

    def zone_total(self, z, which):
        return self._rt.zone_total(z, which)


_SB: dict[str, _Sandbox] = {}


@router.post("/sandbox")
async def sandbox(sov: UploadFile = File(...), application: UploadFile | None = File(None), x_user_id: str | None = Header(None)):
    from uwc.sandbox import _to_xlsx
    from . import engine as E
    from . import flow as FL
    from . import ingest as N
    rt, lock = _rt()
    if not sov.filename.lower().endswith((".xlsx", ".csv")):
        raise HTTPException(400, "Upload the schedule as .xlsx or .csv")
    if application and not application.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "The application must be a PDF")
    sov_path = _to_xlsx(sov.filename, await sov.read())
    app_path = None
    if application:
        app_path = Path(tempfile.mkdtemp()) / "application.pdf"
        app_path.write_bytes(await application.read())
    with lock:
        sb = _Sandbox(rt)
        uid = _uid(x_user_id)
        cid = "sb_" + uuid.uuid4().hex[:8]
        c = FL.new_case(cid, {"title": "Your submission", "insured": sov.filename, "short": Path(sov.filename).stem, "broker": "—", "contact": "—", "uw": uid, "state": "—",
                              "segment": "—", "arrive": rt.clock, "effective": rt.clock, "script": {}, "kind": "sandbox", "naics": None, "years": None})
        sb.decision.cases[cid] = c
        try:
            d_sov = {"doc_id": f"{cid}_sov", "title": sov.filename, "abs_path": str(sov_path), "doc_type": "SOV"}
            n = N.ingest_sov(sb, cid, d_sov, rt.clock)
            if not n:
                raise ValueError("No location rows found (the parser needs a header band with at least six recognised columns)")
            c["docs"].append({"doc_id": d_sov["doc_id"], "role": "sov", "doc_type": "SOV", "title": sov.filename, "received_at": rt.clock})
            if app_path:
                d_app = {"doc_id": f"{cid}_app", "title": application.filename, "abs_path": str(app_path), "doc_type": "ACORD application"}
                N.ingest_application(sb, cid, d_app, rt.clock)
                c["docs"].append({"doc_id": d_app["doc_id"], "role": "application", "doc_type": "ACORD application", "title": application.filename, "received_at": rt.clock})
            FL.enrich(sb, cid, rt.clock, persist=False)
            c["received"] = rt.clock
            E.build_pack(sb, cid, rt.clock)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(422, f"Could not read the files: {e}")
        _SB[cid] = sb
        while len(_SB) > 20:
            _SB.pop(next(iter(_SB)))
        return _sb_payload(sb, cid, sov.filename, application.filename if application else None)


def _sb_payload(sb, cid: str, sov_name: str, app_name: str | None) -> dict:
    c = sb.decision.cases[cid]
    p = c["pack"]
    out = {"token": cid, "sov": sov_name, "application": app_name, "pack": pack_payload(p), "facts": facts_payload(sb, c),
            "issues": sb.store.doc_issues.get(f"{cid}_sov", []), "observations": len(sb.store.obs),
            "real": ["SOV parser (header band, synonyms, $000s, totals, hidden rows/columns)", "ACORD 125/140 application field map (PDF layout extraction)" if app_name else None,
                     "Contradictions between the two files, priced by re-rating", "Tier-1 guideline, appetite, protection, roof and authority rules (the live rule library)",
                     "Tier-2 critique and the verdict on your intended action"] if True else [],
            "not_real": ["Technical price and CAT: the mock rater and MockCat (no carrier rater connected)", "Hazard zones from a city reference table (no geocoder connected) — unknown cities get no CAT zone",
                         "Loss runs and inspection: not uploaded, so the loss-run and inspection requirements show as missing"]}
    out["real"] = [x for x in out["real"] if x]
    return out


@router.post("/sandbox/{token}/assure")
def sandbox_assure(token: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    from . import engine as E
    rt, lock = _rt()
    sb = _SB.get(token)
    if not sb:
        raise HTTPException(404, "Sandbox session expired — upload again")
    with lock:
        c = sb.decision.cases[token]
        uid = _uid(x_user_id)
        c["uw"] = uid
        a = _err(lambda: E.normalize(sb, c, b))
        a.update(by=uid, by_name=USER_BY_ID[uid]["name"], at=sb.clock, action_id="sandbox", version=1)
        return {"action": a, "assurance": assurance_payload(_err(lambda: E.assure(sb, token, a, sb.clock, uid)))}


@router.get("/sandbox/samples/{name}")
def sandbox_sample(name: str):
    from uwc.runtime import RUNTIME_DOCS
    files = {"sov": ("nb_d1_sov.xlsx", "sample_SOV_Halvorsen.xlsx"), "application": ("nb_d1_app.pdf", "sample_ACORD_application_Halvorsen.pdf")}
    if name not in files:
        raise HTTPException(404, "unknown sample")
    p = RUNTIME_DOCS / files[name][0]
    if not p.exists():
        raise HTTPException(404, "sample not generated yet")
    return FileResponse(p, filename=files[name][1])

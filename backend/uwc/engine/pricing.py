"""RARC decomposition (blueprint §10.3) and authority requirement (§11.3).

    TP(E0,T0) = technical on expiring exposure, expiring terms (today's model)
    TP(E1,T0) = technical on renewal exposure, expiring terms
    TP(E1,T1) = technical on renewal exposure, proposed terms
    exposure_factor = TP(E1,T0)/TP(E0,T0);  terms_factor = TP(E1,T1)/TP(E1,T0)
    expected = expiring × exposure_factor × terms_factor;  RARC = proposed/expected − 1
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from uwc.mocks import rater
from uwc.refdata import AUTHORITY, guideline_for

if TYPE_CHECKING:
    from uwc.runtime import Runtime

TERM_KEYS = ("aop_deductible", "named_storm_ded_pct", "named_storm_ded_min", "wind_hail_ded_pct", "bi_sublimit", "flood_sublimit", "eq_sublimit")


def terms_only(t: dict) -> dict:
    return {k: t.get(k) for k in TERM_KEYS}


def terms_hash(premium: float, t: dict) -> str:
    return hashlib.sha1(json.dumps({"p": round(premium), **terms_only(t)}, sort_keys=True).encode()).hexdigest()[:10]


def recommended_terms(rt: "Runtime", acct: str, exp_terms: dict, has_t1: bool) -> dict:
    g = guideline_for(rt.clock_date)
    t = dict(exp_terms)
    if has_t1 and t.get("named_storm_ded_pct") is not None:
        t["named_storm_ded_pct"] = max(t["named_storm_ded_pct"], g["wind_ded_floor_pct_t1"])
        t["named_storm_ded_min"] = max(t.get("named_storm_ded_min") or 0, g["ns_min_floor"])
    return t


def rate_kw(rt: "Runtime", acct: str, terms: dict) -> dict:
    pas = rt.pas[acct]
    return dict(share=pas.get("carrier_share", 1.0), attach=pas.get("layer_attach") or 0.0, layer_limit=pas.get("layer_limit"),
                loss_limit=terms.get("limit") if terms.get("limit_basis") == "loss_limit" else None,
                account_mod=rt.systems["rater"][acct]["account_mod"])


def compute(rt: "Runtime", acct: str, E0: list[dict], E1: list[dict], T0: dict, T1: dict, proposed: float) -> dict:
    kw = rate_kw(rt, acct, T0)
    r00 = rater.technical(E0, T0, **kw)
    r10 = rater.technical(E1, T0, **kw)
    r11 = rater.technical(E1, T1, **rate_kw(rt, acct, T1))
    pas = rt.pas[acct]
    expiring = pas["premium"]
    tp00, tp10, tp11 = r00["technical_premium"], r10["technical_premium"], r11["technical_premium"]
    ef = tp10 / tp00 if tp00 else 1.0
    tf = tp11 / tp10 if tp10 else 1.0
    expected = expiring * ef * tf
    rarc = proposed / expected - 1 if expected else 0.0
    b0, b1 = pas.get("brokerage_prior", 0.15), pas.get("brokerage_proposed", 0.15)
    rarc_net = (proposed * (1 - b1)) / (expected * (1 - b0)) - 1 if expected else 0.0
    breakdown = []
    for c00, c10, c11 in zip(r00["components"], r10["components"], r11["components"]):
        breakdown.append({"component": c00["component"], "e0t0": round(c00["value"]), "e1t0": round(c10["value"]), "e1t1": round(c11["value"])})
    breakdown.append({"component": "Technical premium", "e0t0": round(tp00), "e1t0": round(tp10), "e1t1": round(tp11)})
    tp_bind = rt.systems["rater"][acct]["tp_at_bind"]
    return {
        "expiring_premium": expiring, "tp_e0_t0": tp00, "tp_e1_t0": tp10, "tp_e1_t1": tp11, "exposure_factor": ef, "terms_factor": tf,
        "expected_premium": expected, "proposed_premium": proposed, "headline_change": proposed / expiring - 1 if expiring else 0.0,
        "rarc": rarc, "adequacy": proposed / tp11 if tp11 else None, "price_deviation": proposed / tp11 - 1 if tp11 else 0.0,
        "model_version": rater.MODEL_VERSION, "method": "model_rerun",
        "model_drift": {"tp_at_bind": tp_bind, "tp_today_e0t0": tp00, "drift": tp00 / tp_bind - 1 if tp_bind else 0.0},
        "net": {"brokerage_expiring": b0, "brokerage_proposed": b1, "rarc_net": rarc_net},
        "breakdown": breakdown, "tiv_expiring": sum(l["building"] + l["contents"] + l["stock"] + l["bi"] for l in E0),
        "tiv_renewal": sum(l["building"] + l["contents"] + l["stock"] + l["bi"] for l in E1),
        "_runs": (r00, r10, r11),
    }


def authority_required(r: dict, tiv: float, max_loc_tiv: float, rule_levels: list[tuple[int, str]]) -> tuple[int, list[str]]:
    level, reasons = 1, []
    for lvl in (1, 2, 3, 4):
        a = AUTHORITY[lvl]
        why = []
        if r["rarc"] < a["min_rarc"]:
            why.append(f"RARC {r['rarc'] * 100:.1f}% below L{lvl} floor {a['min_rarc'] * 100:.0f}%")
        if -r["price_deviation"] > a["max_price_dev"]:
            why.append(f"price deviation {r['price_deviation'] * 100:+.1f}% beyond ±{a['max_price_dev'] * 100:.0f}%")
        if tiv > a["max_account_tiv"]:
            why.append(f"account TIV ${tiv / 1e6:,.0f}M above L{lvl} ${a['max_account_tiv'] / 1e6:,.0f}M")
        if max_loc_tiv > a["max_loc_tiv"]:
            why.append(f"location TIV ${max_loc_tiv / 1e6:,.0f}M above L{lvl} ${a['max_loc_tiv'] / 1e6:,.0f}M")
        if r["proposed_premium"] > a["max_premium"]:
            why.append(f"premium above L{lvl} maximum")
        if not why:
            level = lvl
            break
        reasons = why
        level = lvl + 1
    level = min(level, 4)
    reasons = reasons if level > 1 else []
    for lvl, why in rule_levels:
        if lvl > level:
            level = lvl
        if lvl > 1 and why not in reasons:
            reasons.append(why)
    return level, reasons

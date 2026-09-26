"""Mock rater — stand-in for the carrier's rating service / hx behind `RaterPort`.

technical premium = (attritional loss cost × AOP deductible credit + CAT load)
                    / (1 − expense − profit) × account modifier

The CAT load comes from MockCat (AAL × risk multiplier) run on the same
exposure and terms, so deductible and sublimit changes flow through both.
"""
from __future__ import annotations

from uwc.mocks import cat as catmodel
from uwc.refdata import CONSTRUCTION, OCCUPANCY, PPC_FACTOR

MODEL_VERSION = "NS-PROP-RATER v8.0 (mock)"
PRIOR_MODEL_VERSION = "NS-PROP-RATER v7.2 (mock)"
EXPENSE = 0.30
PROFIT = 0.06
CAT_MULT = 1.6


def _sprinkler_factor(p: float | None) -> float:
    p = p or 0
    return 0.75 if p >= 0.9 else 0.9 if p >= 0.5 else 1.15


def _age_factor(roof_year: int | None, year_built: int | None, as_of: int = 2026) -> float:
    ry = roof_year or year_built or 1990
    age = as_of - ry
    return 1.12 if age > 20 else 1.05 if age > 15 else 1.0


def attritional(exposure: list[dict], version: str = MODEL_VERSION) -> tuple[float, list[dict]]:
    drift = 0.97 if version == PRIOR_MODEL_VERSION else 1.0
    total = 0.0
    rows = []
    for l in exposure:
        occ = OCCUPANCY.get(l.get("occupancy") or "warehouse", OCCUPANCY["warehouse"])
        base = occ[4] * drift
        c = CONSTRUCTION.get(l.get("construction") or 3)[1]
        ppc = PPC_FACTOR.get(l.get("ppc") or 5, 1.0)
        spr = _sprinkler_factor(l.get("sprinkler_pct"))
        age = _age_factor(l.get("roof_year"), l.get("year_built"))
        pd = (l.get("building") or 0) + (l.get("contents") or 0) + (l.get("stock") or 0)
        bi = l.get("bi") or 0
        lc = pd / 100 * base * c * ppc * spr * age + bi / 100 * base * 0.35
        total += lc
        rows.append({"location_uid": l["location_uid"], "loss_cost": lc})
    return total, rows


def aop_credit(aop: float | None) -> float:
    aop = aop or 25_000
    return max(0.70, min(1.15, (aop / 25_000) ** -0.10))


def technical(exposure: list[dict], terms: dict, share: float = 1.0, attach: float = 0.0,
              layer_limit: float | None = None, loss_limit: float | None = None,
              account_mod: float = 1.0, version: str = MODEL_VERSION) -> dict:
    att, _ = attritional(exposure, version)
    att *= aop_credit(terms.get("aop_deductible"))
    if attach > 0:
        att *= 0.06          # attritional largely retained below attachment
    att *= share
    cat = catmodel.run(exposure, terms, share=share, attach=attach, layer_limit=layer_limit, loss_limit=loss_limit)
    cat_load = cat["aal_total"] * CAT_MULT * (0.97 if version == PRIOR_MODEL_VERSION else 1.0)
    loss_cost = att + cat_load
    gross = loss_cost / (1 - EXPENSE - PROFIT) * account_mod
    expense = gross * EXPENSE
    profit = gross - expense - loss_cost * account_mod
    return {
        "model_version": version,
        "technical_premium": gross,
        "components": [
            {"component": "Attritional loss cost", "value": att * account_mod},
            {"component": "CAT load (AAL × 1.6)", "value": cat_load * account_mod},
            {"component": "Expense load (30%)", "value": expense},
            {"component": "Profit & capital load", "value": profit},
        ],
        "aal": cat["aal_total"],
        "cat": cat,
    }

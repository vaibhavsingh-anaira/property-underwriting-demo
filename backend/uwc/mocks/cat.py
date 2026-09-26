"""MockCat — stand-in for Moody's RMS / Verisk behind `CatModelPort`.

Event-based so that financial terms behave like a real model:
  * a seeded stochastic catalogue per (zone, peril) with annual rates;
  * locations in the same zone are hit by the same events (correlation →
    accumulation, tail);
  * per-location occurrence deductibles (named-storm %, min), account sublimits,
    loss limit, layer attachment/limit and carrier share are applied per event;
  * outputs: ELT, AAL by peril / location, OEP (analytic Poisson) and AEP
    (simulated years), data-quality flags.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

from uwc.refdata import CONSTRUCTION, ZONE_PERIL_RATES

MODEL_VERSION = "MockCat 3.1 (stand-in for Moody's RMS / Verisk)"
RPS = [10, 25, 50, 100, 250, 500, 1000]

EVENTS_PER_BUCKET = 240
FREQ = {"HU": 0.20, "SCS": 2.2, "FL": 0.25, "EQ": 0.08, "WF": 0.12}
EQ_VULN = {1: 0.8, 2: 1.45, 3: 0.95, 4: 1.25, 5: 0.9, 6: 0.85}


def _h(*parts: Any) -> float:
    s = "|".join(str(p) for p in parts).encode()
    return int(hashlib.blake2b(s, digest_size=8).hexdigest(), 16) / 2**64


@dataclass
class Event:
    event_id: int
    bucket: str
    peril: str
    rate: float
    dr: float           # reference damage ratio


@lru_cache(maxsize=None)
def catalogue(bucket: str, peril: str) -> tuple[Event, ...]:
    """Seeded catalogue whose rate-weighted damage equals the bucket's AAL ratio."""
    zone = None if bucket.startswith("ST-") else bucket
    target = ZONE_PERIL_RATES.get(zone, ZONE_PERIL_RATES[None]).get(peril)
    if not target:
        return ()
    rng = np.random.default_rng(int(_h(bucket, peril) * 1e9))
    lam = FREQ[peril] / EVENTS_PER_BUCKET
    alpha = {"HU": 1.35, "SCS": 2.2, "FL": 1.6, "EQ": 1.1, "WF": 1.3}[peril]
    raw = rng.pareto(alpha, EVENTS_PER_BUCKET) + 0.05
    raw = raw / raw.mean()
    dr = raw * (target / FREQ[peril])
    dr = np.minimum(dr, 0.85)
    dr = dr * (target / (lam * dr.sum()))       # re-normalise after capping
    dr = np.minimum(dr, 0.9)
    base = int(_h('evid', bucket, peril) * 900) * 1000
    return tuple(Event(event_id=100000 + base + i, bucket=bucket, peril=peril, rate=lam, dr=float(dr[i])) for i in range(EVENTS_PER_BUCKET))


def bucket_of(loc: dict) -> str:
    return loc.get("zone") or f"ST-{loc.get('state', 'XX')}"


def vulnerability(loc: dict, peril: str, as_of_year: int = 2026) -> float:
    c = loc.get("construction") or 3
    yb = loc.get("year_built") or 1985
    roof_age = as_of_year - (loc.get("roof_year") or yb)
    if peril == "HU":
        v = CONSTRUCTION[c][3] * (1 + 0.02 * max(0, roof_age - 10))
        v *= 1.15 if yb < 1995 else 0.9 if yb >= 2002 else 1.0
        v *= 0.9 if (loc.get("stories") or 1) >= 5 else 1.0
        v *= 1.1 if loc.get("wind_tier") == "T1" else 1.0
    elif peril == "SCS":
        v = CONSTRUCTION[c][3] * (1 + 0.045 * max(0, roof_age - 8))
    elif peril == "EQ":
        v = EQ_VULN.get(c, 1.0) * (1.2 if yb < 1980 else 0.85 if yb >= 2000 else 1.0)
    elif peril == "WF":
        v = (loc.get("wildfire") or 5) / 40
    elif peril == "FL":
        v = {"VE": 1.6, "AE": 1.0, "A": 0.9, "X": 0.15}.get(loc.get("flood_zone") or "X", 0.15)
    else:
        v = 1.0
    return float(v)


def _loc_tiv(loc: dict) -> tuple[float, float]:
    pd = (loc.get("building") or 0) + (loc.get("contents") or 0) + (loc.get("stock") or 0)
    return pd, (loc.get("bi") or 0)


def _spatial(bucket: str, peril: str, uid: str, m: int) -> np.ndarray:
    rng = np.random.default_rng(int(_h("sp", bucket, peril, uid) * 1e9))
    return 0.45 + 1.1 * rng.random(m)


_CACHE: dict[str, dict] = {}


def run(exposure: list[dict], terms: dict, share: float = 1.0, attach: float = 0.0,
        layer_limit: float | None = None, loss_limit: float | None = None, years: int = 4000, seed: int = 7) -> dict:
    """Run the model. `exposure` rows carry location_uid, label, zone, state, construction, year_built,
    roof_year, stories, wind_tier, flood_zone, wildfire, building, contents, stock, bi."""
    import json as _json
    key = _json.dumps([exposure, terms, share, attach, layer_limit, loss_limit], sort_keys=True, default=str)
    if key in _CACHE:
        return _CACHE[key]
    buckets: dict[tuple[str, str], list[dict]] = {}
    for loc in exposure:
        zone_rates = ZONE_PERIL_RATES.get(loc.get("zone"), ZONE_PERIL_RATES[None])
        for peril in zone_rates:
            buckets.setdefault((bucket_of(loc), peril), []).append(loc)

    ns_pct = terms.get("named_storm_ded_pct")
    ns_min = terms.get("named_storm_ded_min") or 0
    wh_pct = terms.get("wind_hail_ded_pct")
    aop = terms.get("aop_deductible") or 25_000
    flood_sub = terms.get("flood_sublimit")
    eq_sub = terms.get("eq_sublimit")
    bi_sub = terms.get("bi_sublimit")

    elt: list[dict] = []
    loc_aal: dict[str, float] = {l["location_uid"]: 0.0 for l in exposure}
    peril_aal: dict[str, float] = {}
    gross_aal = 0.0
    for (bucket, peril), locs in buckets.items():
        cat = catalogue(bucket, peril)
        if not cat:
            continue
        m, n = len(cat), len(locs)
        ev_dr = np.array([e.dr for e in cat])
        ev_rate = np.array([e.rate for e in cat])
        pd = np.array([_loc_tiv(l)[0] for l in locs])
        bi = np.array([_loc_tiv(l)[1] for l in locs])
        vul = np.array([vulnerability(l, peril) for l in locs])
        # spatial variation keyed by physical position (not by identifier) so results are reproducible across systems
        S = np.stack([_spatial(bucket, peril, f"{round(l.get('lat') or 0, 4)},{round(l.get('lon') or 0, 4)}" if l.get("lat") else l["label"], m) for l in locs], axis=1)
        dr = np.minimum(0.95, ev_dr[:, None] * S * vul[None, :])
        gu_pd = dr * pd[None, :]
        gu_bi = np.minimum(bi[None, :], bi[None, :] * np.minimum(1.0, dr * 1.8))
        gu = gu_pd + gu_bi
        tot = pd + bi
        if peril == "HU" and ns_pct:
            ded = np.maximum(ns_pct * tot, ns_min)
        elif peril in ("HU", "SCS") and wh_pct:
            ded = wh_pct * tot
        elif peril == "EQ":
            ded = 0.05 * tot
        else:
            ded = np.full(n, float(aop))
        net = np.maximum(0.0, gu - ded[None, :])
        with np.errstate(divide="ignore", invalid="ignore"):
            frac_bi = np.where(gu > 0, gu_bi / gu, 0.0)
        bi_net = (net * frac_bi).sum(axis=1)
        gross_aal += float((ev_rate * gu.sum(axis=1)).sum())
        occ = net.sum(axis=1)
        if bi_sub is not None:
            occ = occ - np.maximum(0.0, bi_net - bi_sub)
        if peril == "FL" and flood_sub is not None:
            occ = np.minimum(occ, flood_sub)
        if peril == "EQ" and eq_sub is not None:
            occ = np.minimum(occ, eq_sub)
        if loss_limit:
            occ = np.minimum(occ, loss_limit)
        layer = np.maximum(0.0, occ - attach)
        if layer_limit is not None:
            layer = np.minimum(layer, layer_limit)
        loss = layer * share
        rowsum = net.sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            scale = np.where(rowsum > 0, loss / rowsum, 0.0)
        alloc = (net * scale[:, None] * ev_rate[:, None]).sum(axis=0)
        for j, l in enumerate(locs):
            loc_aal[l["location_uid"]] += float(alloc[j])
        expo = float(tot.sum() * share)
        for i in np.nonzero(loss > 0)[0]:
            elt.append({"EventID": cat[i].event_id, "Peril": peril, "Region": bucket, "Rate": float(ev_rate[i]),
                        "MeanLoss": float(loss[i]), "SDev": float(loss[i] * 0.35), "ExposureValue": expo})
        peril_aal[peril] = peril_aal.get(peril, 0.0) + float((ev_rate * loss).sum())

    aal = sum(peril_aal.values())
    losses = np.array([e["MeanLoss"] for e in elt]) if elt else np.zeros(0)
    rates = np.array([e["Rate"] for e in elt]) if elt else np.zeros(0)
    order = np.argsort(-losses)
    cum = np.cumsum(rates[order]) if len(order) else np.zeros(0)
    oep = []
    for rp in RPS:
        need = -math.log(1 - 1 / rp)
        idx = int(np.searchsorted(cum, need)) if len(cum) else 0
        oep.append({"rp": rp, "loss": float(losses[order][idx]) if len(cum) and idx < len(cum) else 0.0})
    aep = []
    if elt:
        rng = np.random.default_rng(seed)
        counts = rng.poisson(rates[None, :], size=(years, len(rates))).astype(np.float32)
        annual = np.sort(counts @ losses.astype(np.float32))
        for rp in RPS:
            aep.append({"rp": rp, "loss": float(annual[int(len(annual) * (1 - 1 / rp))])})
    else:
        aep = [{"rp": rp, "loss": 0.0} for rp in RPS]
    out = {
        "model_version": MODEL_VERSION,
        "aal_total": aal,
        "aal_gross_ground_up": gross_aal,
        "aal_by_peril": peril_aal,
        "loc_aal": loc_aal,
        "oep": oep,
        "aep": aep,
        "elt": sorted(elt, key=lambda e: -e["MeanLoss"]),
    }
    _CACHE[key] = out
    return out


def dq_flags(exposure: list[dict]) -> list[dict]:
    out = []
    for l in exposure:
        lbl = l.get("label", l["location_uid"])
        if not l.get("year_built"):
            out.append({"location_uid": l["location_uid"], "label": lbl, "field": "YearBuilt", "issue": "Missing year built", "impact": "HIGH"})
        if not l.get("roof_year"):
            out.append({"location_uid": l["location_uid"], "label": lbl, "field": "RoofYear", "issue": "Missing roof year (secondary modifier)", "impact": "MEDIUM"})
        if l.get("geocode_level") and l["geocode_level"] != "rooftop":
            out.append({"location_uid": l["location_uid"], "label": lbl, "field": "GeocodeLevel", "issue": f"Geocode at {l['geocode_level']} level", "impact": "HIGH"})
        if not l.get("construction"):
            out.append({"location_uid": l["location_uid"], "label": lbl, "field": "ConstructionCode", "issue": "Unknown construction", "impact": "HIGH"})
        if not l.get("stories"):
            out.append({"location_uid": l["location_uid"], "label": lbl, "field": "NumberOfStoreys", "issue": "Missing stories", "impact": "LOW"})
    return out

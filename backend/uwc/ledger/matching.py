"""Location matching across years (blueprint §8). Stops at the first confident rung:

  1. carrier location ID (exact)
  2. broker loc no + address similarity ≥ 0.9
  3. standardised address (exact)
  4. parcel / footprint ID (not available in demo data)
  5. geocode within 30 m + construction/stories/area similar
  6. fuzzy address + same value band  → proposed only (needs human confirmation)
"""
from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

ABBR = {"avenue": "ave", "street": "st", "road": "rd", "drive": "dr", "boulevard": "blvd", "parkway": "pkwy", "lane": "ln",
        "court": "ct", "circle": "cir", "east": "e", "west": "w", "north": "n", "south": "s"}


def std_address(a: str | None) -> str:
    if not a:
        return ""
    t = re.sub(r"[.,#]", " ", a.lower())
    t = re.sub(r"\b(bldg|building|suite|ste|unit)\s*\w+", " ", t)
    words = [ABBR.get(w, w) for w in t.split()]
    return " ".join(words)


def _num(a: str) -> int | None:
    m = re.match(r"\s*(\d+)", a or "")
    return int(m.group(1)) if m else None


def sim(a: str, b: str) -> float:
    """Address similarity; house numbers must agree (±4 tolerated for fuzzy typos) or the score is capped."""
    s = SequenceMatcher(None, std_address(a), std_address(b)).ratio()
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None and na != nb:
        s = min(s, 0.74) if abs(na - nb) <= 4 else min(s, 0.5)
    return s


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return 1e9
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def match_rows(prior: list[dict], current: list[dict]) -> list[dict]:
    """prior: [{uid, loc_no, address, city, carrier_loc_id, lat, lon, sqft, tiv, construction, stories}]
    current: [{idx, loc_no, address, city, carrier_loc_id, lat, lon, sqft, tiv, construction, stories}]
    Returns one decision per current row: {idx, uid|None, status, method, score, proposed_uid}
    plus decisions for unmatched prior rows (status DELETED / MERGED)."""
    used: set[str] = set()
    decisions: list[dict] = []
    by_std = {}
    for p in prior:
        by_std.setdefault((std_address(p["address"]), (p.get("city") or "").lower()), []).append(p)
    for c in current:
        d = {"idx": c["idx"], "uid": None, "status": "NEW", "method": None, "score": None, "proposed_uid": None}
        cand = None
        # 1 carrier loc id
        if c.get("carrier_loc_id"):
            cand = next((p for p in prior if p.get("carrier_loc_id") == c["carrier_loc_id"] and p["uid"] not in used), None)
            if cand:
                d.update(uid=cand["uid"], status="MATCHED", method="carrier_loc_id", score=1.0)
        # 2 broker loc no + address
        if not cand and c.get("loc_no"):
            for p in prior:
                if p["uid"] in used or not p.get("loc_no"):
                    continue
                if str(p["loc_no"]).lstrip("0") == str(c["loc_no"]).lstrip("0"):
                    s = sim(p["address"], c["address"])
                    if s >= 0.9:
                        cand = p
                        d.update(uid=p["uid"], status="MATCHED", method="broker_loc_no+address", score=round(s, 3))
                        break
        # 3 standardised address
        if not cand:
            key = (std_address(c["address"]), (c.get("city") or "").lower())
            for p in by_std.get(key, []):
                if p["uid"] not in used:
                    cand = p
                    d.update(uid=p["uid"], status="MATCHED", method="std_address", score=0.98)
                    break
        # 5 geocode within 30 m + attributes
        if not cand:
            for p in prior:
                if p["uid"] in used:
                    continue
                dist = haversine_m(p.get("lat"), p.get("lon"), c.get("lat"), c.get("lon"))
                if dist <= 30 and _similar_attrs(p, c):
                    cand = p
                    d.update(uid=p["uid"], status="MATCHED", method="geocode_30m+attributes", score=round(max(0.8, 1 - dist / 150), 3))
                    break
        if cand:
            used.add(cand["uid"])
        decisions.append(d)
    # 6 fuzzy → proposed (second phase, only for rows still unmatched after exact rungs)
    for d in decisions:
        if d["status"] != "NEW":
            continue
        c = next(x for x in current if x["idx"] == d["idx"])
        best, best_s = None, 0.0
        for p in prior:
            if p["uid"] in used or (p.get("city") or "").lower() != (c.get("city") or "").lower():
                continue
            s = sim(p["address"], c["address"])
            if s > best_s:
                best, best_s = p, s
        if best and best_s >= 0.72 and _value_band(best, c):
            used.add(best["uid"])
            d.update(uid=best["uid"], status="AMBIGUOUS", method="fuzzy_address+value_band", score=round(best_s, 3), proposed_uid=best["uid"])
    # merges: unmatched prior whose area fits into a matched current row together with its matched prior
    unmatched = [p for p in prior if p["uid"] not in used]
    for p in unmatched:
        merged = None
        for d in decisions:
            if d["status"] != "MATCHED" or not d["uid"]:
                continue
            c = next(x for x in current if x["idx"] == d["idx"])
            a = next(x for x in prior if x["uid"] == d["uid"])
            if c.get("sqft") and a.get("sqft") and p.get("sqft") and abs((a["sqft"] + p["sqft"]) - c["sqft"]) / c["sqft"] < 0.08 \
                    and (haversine_m(a.get("lat"), a.get("lon"), p.get("lat"), p.get("lon")) < 400):
                merged = d
                break
        if merged:
            decisions.append({"idx": None, "uid": p["uid"], "status": "MERGED", "method": "area_sum_within_8%+proximity", "score": 0.9, "merged_into": merged["uid"]})
            merged["merged_from"] = merged.get("merged_from", []) + [p["uid"]]
        else:
            decisions.append({"idx": None, "uid": p["uid"], "status": "DELETED", "method": "not_in_renewal_sov", "score": None})
    return decisions


def _similar_attrs(p: dict, c: dict) -> bool:
    ok = 0
    if p.get("stories") and c.get("stories") and p["stories"] == c["stories"]:
        ok += 1
    if p.get("construction") and c.get("construction") and p["construction"] == c["construction"]:
        ok += 1
    if p.get("sqft") and c.get("sqft") and abs(p["sqft"] - c["sqft"]) / max(p["sqft"], 1) < 0.1:
        ok += 1
    return ok >= 2


def _value_band(p: dict, c: dict) -> bool:
    if not p.get("tiv") or not c.get("tiv"):
        return True
    return 0.7 <= c["tiv"] / p["tiv"] <= 1.4

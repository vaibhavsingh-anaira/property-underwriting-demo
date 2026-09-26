"""Real mode: run your own statement of values through the product's parser, matcher and data-quality
controls. Nothing here is scripted — the same code that reads the demo SOVs reads yours.

Pricing, CAT and contract checks need a carrier rater, CAT model and policy system, so they are not run
here (they are stand-ins in the demo). The response says so explicitly.
"""
from __future__ import annotations

import csv
import io
import tempfile
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from uwc.ingest.sov import map_construction, map_occupancy, map_sprinkler, parse_sov
from uwc.ledger.matching import match_rows
from uwc.refdata import CONSTRUCTION, OCCUPANCY

RC_RANGE = (60, 1200)  # $/sq ft building replacement cost considered plausible for commercial property


def _to_xlsx(name: str, data: bytes) -> Path:
    tmp = Path(tempfile.mkdtemp()) / (Path(name).stem + ".xlsx")
    if name.lower().endswith(".csv"):
        wb = Workbook()
        ws = wb.active
        for row in csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace"))):
            ws.append([_num(c) for c in row])
        wb.save(tmp)
    else:
        tmp.write_bytes(data)
    return tmp


def _num(s: str):
    t = s.replace(",", "").replace("$", "").strip()
    try:
        return float(t) if "." in t else int(t)
    except ValueError:
        return s


def _rows(p) -> list[dict]:
    out = []
    for i, row in enumerate(p.rows):
        g = lambda f: row.get(f, (None, None))[0]
        cell = lambda f: row.get(f, (None, None))[1]
        occ, occ_c = map_occupancy(g("occupancy_raw"))
        cons, cons_c = map_construction(g("construction_raw"))
        vals = [g(k) or 0 for k in ("building_value", "contents_value", "stock_value", "bi_value")]
        tiv = g("tiv_reported") or sum(vals)
        out.append({"idx": i, "row": row.get("_row"), "loc_no": g("loc_no"), "name": g("location_name"), "address": g("address"), "city": g("city"), "state": g("state"),
                    "occupancy_raw": g("occupancy_raw"), "occupancy": OCCUPANCY[occ][0] if occ in OCCUPANCY else None, "occupancy_conf": occ_c,
                    "construction_raw": g("construction_raw"), "construction": CONSTRUCTION[cons][0] if cons in CONSTRUCTION else None, "construction_conf": cons_c,
                    "construction_class": cons, "year_built": g("year_built"), "stories": g("stories"), "sqft": g("sqft"), "roof_year": g("roof_year"),
                    "sprinkler": map_sprinkler(g("sprinkler")), "building_value": g("building_value"), "tiv": tiv, "cell_address": cell("address"), "cell_tiv": cell("tiv_reported")})
    return out


def _checks(rows: list[dict]) -> list[dict]:
    yr = date.today().year
    out = []
    for r in rows:
        def add(code, sev, msg):
            out.append({"row": r["row"], "location": r["name"] or r["address"], "code": code, "severity": sev, "message": msg})
        for f, lab in (("occupancy", "occupancy"), ("construction", "construction"), ("year_built", "year built"), ("sqft", "floor area"), ("roof_year", "roof year"), ("sprinkler", "sprinkler protection")):
            if r.get(f) in (None, "") and f in ("occupancy", "construction") and r.get(f + "_raw"):
                add("UNMAPPED_" + f.upper(), "HIGH", f"{lab.capitalize()} '{r[f + '_raw']}' not recognised — needs a human mapping before modelling")
            elif r.get(f) in (None, ""):
                add("MISSING_" + f.upper(), "HIGH" if f in ("occupancy", "construction") else "MEDIUM", f"Missing {lab} — CAT model will use a default")
        if r["occupancy_raw"] and r["occupancy_conf"] and r["occupancy_conf"] < 0.8:
            add("OCC_LOW_CONF", "MEDIUM", f"Occupancy '{r['occupancy_raw']}' mapped to {r['occupancy']} with low confidence ({r['occupancy_conf']:.0%})")
        if r["construction_raw"] and r["construction_conf"] and r["construction_conf"] < 0.8:
            add("CONS_LOW_CONF", "MEDIUM", f"Construction '{r['construction_raw']}' mapped to {r['construction']} with low confidence")
        if r["sqft"] and r["building_value"]:
            rc = r["building_value"] / r["sqft"]
            if not RC_RANGE[0] <= rc <= RC_RANGE[1]:
                add("RC_OUTLIER", "HIGH", f"Building value ${rc:,.0f}/sq ft is outside the plausible {RC_RANGE[0]}–{RC_RANGE[1]} range — check valuation or units")
        if r["roof_year"] and isinstance(r["roof_year"], (int, float)) and yr - r["roof_year"] > 20:
            add("ROOF_AGE", "MEDIUM", f"Roof {int(yr - r['roof_year'])} years old")
        if r["year_built"] and isinstance(r["year_built"], (int, float)) and r["roof_year"] and r["roof_year"] < r["year_built"]:
            add("ROOF_BEFORE_BUILT", "HIGH", "Roof year earlier than year built")
    return out


def analyse(renewal: tuple[str, bytes], expiring: tuple[str, bytes] | None = None) -> dict:
    cur = parse_sov(_to_xlsx(*renewal))
    cur_rows = _rows(cur)
    res = {"file": renewal[0], "sheet": cur.sheet, "header_row": cur.header_row, "scale": cur.scale, "columns": cur.columns, "parser": cur.method,
           "parser_issues": cur.issues, "rows": cur_rows, "checks": _checks(cur_rows), "tiv": sum(r["tiv"] or 0 for r in cur_rows),
           "not_run": ["Technical price and RARC split (needs the carrier's rater)", "CAT modelling (needs the carrier's CAT model)",
                       "Contract checks (need quote/binder/policy documents)", "Geocoding and hazard enrichment (vendor feeds are mocked in the demo)"]}
    if expiring:
        pri = parse_sov(_to_xlsx(*expiring))
        pri_rows = _rows(pri)
        prior = [{"uid": f"p{r['idx']}", "loc_no": str(r["loc_no"]) if r["loc_no"] is not None else None, "address": str(r["address"] or ""), "city": str(r["city"] or ""),
                  "carrier_loc_id": None, "lat": None, "lon": None, "sqft": r["sqft"], "tiv": r["tiv"], "construction": r["construction_class"], "stories": r["stories"]} for r in pri_rows]
        current = [{"idx": r["idx"], "loc_no": r["loc_no"], "address": str(r["address"] or ""), "city": str(r["city"] or ""), "carrier_loc_id": None, "lat": None, "lon": None,
                    "sqft": r["sqft"], "tiv": r["tiv"], "construction": r["construction_class"], "stories": r["stories"]} for r in cur_rows]
        by_uid = {p["uid"]: r for p, r in zip(prior, pri_rows)}
        matches = []
        for d in match_rows(prior, current):
            c = cur_rows[d["idx"]] if d["idx"] is not None else None
            p = by_uid.get(d.get("uid") or d.get("proposed_uid") or "")
            matches.append({"status": d["status"], "method": d["method"], "score": d["score"],
                            "renewal": (c["name"] or c["address"]) if c else None, "expiring": (p["name"] or p["address"]) if p else None,
                            "tiv_expiring": p["tiv"] if p else None, "tiv_renewal": c["tiv"] if c else None})
        res["expiring"] = {"file": expiring[0], "rows": len(pri_rows), "tiv": sum(r["tiv"] or 0 for r in pri_rows), "parser_issues": pri.issues}
        res["matches"] = matches
    return res

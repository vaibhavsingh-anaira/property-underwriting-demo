"""Your data (real): an uploaded bordereau through the real mapper, validator and authority rules, against a demo
BAA or an uploaded BAA PDF in the same layout. Nothing is stored in the demo state."""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import baa as B
from . import bordereau as BX
from . import core as C
from . import engine as E
from .refdata import COVERHOLDERS


def _detect(path: Path) -> str:
    _s, grid = BX._read(path)
    best = ("risk", 0)
    for kind in ("risk", "premium", "claims"):
        f = BX.FIELDSETS[kind]
        hits = max((sum(1 for v in row if v is not None and BX.match_header(str(v), f, fuzzy=False)[0]) for row in grid[:15]), default=0)
        uniq = {"risk": ("tiv", "limit", "construction"), "premium": ("commission_pct", "net_premium"), "claims": ("claim_ref", "incurred", "date_of_loss")}[kind]
        bonus = sum(1 for row in grid[:15] for v in row if v is not None and BX.match_header(str(v), f, fuzzy=False)[0] in uniq)
        if hits + 3 * bonus > best[1]:
            best = (kind, hits + 3 * bonus)
    return best[0]


def analyse(rt, filename: str, data: bytes, authority: str | None, pdf: bytes | None) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="da_sandbox_"))
    path = tmp / Path(filename).name
    path.write_bytes(data)
    kind = _detect(path)
    notes = []
    if pdf:
        pp = tmp / "baa.pdf"
        pp.write_bytes(pdf)
        parsed = B.parse(pp, "sandbox_baa")
        version = {"version": 0, "doc_id": None, "kind": "BAA", "number": 0, "effective": parsed["terms"].get("period_start") or "2000-01-01", "terms": parsed["terms"], "anchors": {}}
        src = f"Uploaded agreement ({len(parsed['anchors'])} terms read)"
        if len(parsed["anchors"]) < 10:
            notes.append("Few terms were recognised in the uploaded agreement — it must follow the demo BAA layout (labels, section tables).")
    else:
        ch = authority if authority in COVERHOLDERS else "ch_meridian"
        terms, _a, _v = E.authority(rt.delegated, ch, rt.clock)
        version = {"version": 0, "doc_id": None, "kind": "BAA", "number": 0, "effective": "2000-01-01", "terms": terms, "anchors": {}}
        src = f"{COVERHOLDERS[ch]['name']} — {COVERHOLDERS[ch]['agreement']} as endorsed today"
    st = {"authority": {"sandbox": [version]}, "zone_map": {"sandbox": {}}, "annual_premium": {}, "referrals": [], "_auth_cache": {}}
    p = BX.parse_file(path, kind)
    out = {"filename": filename, "kind": kind, "sheet": p["sheet"], "header_row": p["header_row"], "mapping": p["mapping"], "missing": [BX.FIELDSETS[kind][f][0] for f in p["missing"]],
           "issues": p["issues"][:400], "issue_count": len(p["issues"]), "stats": p["stats"], "authority_source": src, "rows": [], "summary": None, "notes": notes, "method": p["method"]}
    if kind != "risk":
        out["notes"].append(f"This looks like a {kind} bordereau: mapping and validation ran; authority checks need a risk bordereau (or a combined risk & premium file).")
        return out
    prem = BX.parse_file(path, "premium")
    pmap = {r["_r"]: r for r in prem["rows"]} if "commission_pct" in (prem.get("columns") or {}) else {}

    class _RT:
        clock = rt.clock
        rules = rt.rules
    fake = _RT()
    res_rows, fam, tied, comm = [], {}, 0.0, 0.0
    n_ex = 0
    for r in p["rows"]:
        if r.get("_duplicate_of") or not r.get("certificate_ref"):
            continue
        row = C._canonical("sandbox", (r.get("written_date") or rt.clock)[:7], r, p, "sandbox")
        row["row_id"] = f"sandbox|{r['_r']}"
        pr = pmap.get(r["_r"])
        if pr:
            row["prem"] = {"doc_id": "sandbox", "sheet": prem["sheet"], "r": pr["_r"], "cells": pr["_cells"], **{k: pr.get(k) for k in ("commission_pct", "commission_amount", "net_premium", "taxes")}}
            row["commission_pct"] = pr.get("commission_pct")
        checks = E.check_row(st, fake, row)
        fired = []
        for c in checks:
            if c["result"] in ("PASS", "NA"):
                continue
            ref = E.reconcile_referral(st, fake, row, c["rule_id"]) if c["result"] == "REFER" else None
            fired.append({"check": c["check"], "title": c["title"], "family": c["family"], "result": c["result"], "written": c["written"], "authority": c["authority"],
                          "delta": c["delta"], "impact_usd": c["impact_usd"], "cell": (c.get("anchor_written") or {}).get("cell"),
                          "referral": "reference on file — needs the carrier referral system to verify" if ref and row.get("referral_ref") else ("none on the bordereau" if ref else None)})
            fam[c["family"]] = fam.get(c["family"], 0) + 1
            if c["family"] == "commission":
                comm += c["impact_usd"]
        na = [c["rule_id"] for c in checks if c["result"] == "NA"]
        if fired:
            n_ex += 1
            tied += abs(row.get("gross_premium") or 0)
        res_rows.append({"row": r["_r"], "certificate_ref": row["certificate_ref"], "insured": row.get("insured_name"), "txn": row.get("transaction_type"), "tiv": row.get("tiv"),
                         "limit": row.get("limit"), "premium": row.get("gross_premium"), "exceptions": fired, "not_checked": len(na)})
    out["rows"] = res_rows[:500]
    out["summary"] = {"rows": len(res_rows), "with_exceptions": n_ex, "rate": n_ex / len(res_rows) if res_rows else 0, "by_family": [{"family": k, "label": E.FAMILY_LABEL.get(k, k), "count": v} for k, v in
                                                                                                        sorted(fam.items(), key=lambda kv: -kv[1])],
                      "premium_tied": tied, "commission_discrepancy": comm, "not_checked": sum(1 for x in res_rows if x["not_checked"])}
    out["notes"] += ["Referral approvals can only be verified against the carrier's referral system; here any referral trigger without a reference is reported as missing.",
                     "Zone aggregates need the carrier's exposure return and CAT zone feed; claims controls need the claims bordereau and the policy register."]
    return out

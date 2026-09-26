"""Documents produced while the demo runs (renewal quotes, binders, policies, CAT outputs, vendor payloads).
Same layouts as the generator so the same extractor reads them back."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from uwc.config import CARRIER
from uwc.refdata import FORMS, SAFEGUARD_CODES
from uwc.world.pdfkit import Pdf, money, pctf


def _pairs(t: dict) -> list[tuple[str, str]]:
    return [
        ("Limit of insurance", money(t.get("limit"))), ("Limit basis", {"blanket": "Blanket", "scheduled": "Scheduled", "loss_limit": "Loss limit"}.get(t.get("limit_basis") or "blanket")),
        ("AOP deductible", money(t.get("aop_deductible"))),
        ("Named storm deductible", pctf(t.get("named_storm_ded_pct")) + (" per location" if t.get("named_storm_ded_pct") else "")),
        ("Named storm minimum", money(t.get("named_storm_ded_min"))), ("Wind/hail deductible", pctf(t.get("wind_hail_ded_pct"))),
        ("Business income sublimit", money(t["bi_sublimit"]) if t.get("bi_sublimit") else "Included in limit"),
        ("Flood sublimit", money(t["flood_sublimit"]) if t.get("flood_sublimit") else "Not covered"),
        ("Earthquake sublimit", money(t["eq_sublimit"]) if t.get("eq_sublimit") else "Not covered"),
    ]


def render_contract(kind: str, path: Path, *, name: str, broker: str, ref: str, date: str, term: tuple[str, str], premium: float, terms: dict,
                    forms: list[str], safeguards: list[tuple[str, str, str]], subjectivities: list[dict], version: int | None = None,
                    prepared_by: str = "", share: float = 1.0, layer: str = "Primary"):
    title = {"quote": f"Property Quotation v{version}", "binder": "Binder of Insurance", "policy": "Commercial Property Declarations"}[kind]
    p = Pdf(path, "carrier", title, ref)
    p.title(title if kind != "quote" else f"Property Quotation — version {version}",
            f"{'Issued' if kind != 'binder' else 'Bound'} {date}" + (f" · prepared by {prepared_by}" if prepared_by else "") + f" · {CARRIER}")
    head = [("Named insured", name), ("Policy period" if kind != "quote" else "Proposed period", f"{term[0]} to {term[1]}"), ("Producer", broker),
            ({"quote": "Quoted premium", "binder": "Bound premium", "policy": "Total premium"}[kind], money(premium)),
            ("Carrier share", f"{share * 100:.0f}%"), ("Layer", layer)]
    if kind == "quote":
        head.insert(0, ("Quote version", str(version)))
    elif kind == "binder":
        head.insert(0, ("Binder number", ref))
    else:
        head.insert(0, ("Policy number", ref))
    p.kv(head)
    p.section("Quoted terms" if kind == "quote" else "Bound terms" if kind == "binder" else "Limits and deductibles")
    p.kv(_pairs(terms))
    p.section("Forms and endorsements")
    p.table(["Form", "Edition", "Title"], [(f, "10 12" if not f.startswith("NS") else "01 25", FORMS.get(f, "")) for f in forms], [90, 60, 350])
    if safeguards:
        p.section("Protective safeguards schedule (CP 04 11)")
        p.table(["Loc", "Address", "Symbol", "Protective device or service"], [(a, b, c, SAFEGUARD_CODES.get(c, "")) for a, b, c in safeguards], [40, 190, 50, 220])
    if subjectivities:
        p.section("Subjectivities")
        if kind == "binder":
            p.table(["Subjectivity", "Due", "Status at bind"], [(s["text"], s["due"], "Outstanding") for s in subjectivities], [330, 80, 90])
        else:
            p.table(["Subjectivity", "Due"], [(s["text"], s["due"]) for s in subjectivities], [400, 100])
    p.signature("Underwriter" if kind != "policy" else "Authorized representative", CARRIER, date)
    p.save()


def write_cat_files(base: Path, acct_name: str, policy_no: str, snapshot: str, run_date: str, exposure: list[dict], terms: dict, res: dict):
    from uwc.refdata import CONSTRUCTION, OCCUPANCY
    ex, elt, ep = base.with_name(base.name + "_exposure.csv"), base.with_name(base.name + "_elt.csv"), base.with_name(base.name + "_ep.json")
    with ex.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["AccNumber", "LocNumber", "LocName", "OccupancyCode", "ConstructionCode", "YearBuilt", "NumberOfStoreys", "RoofYear",
                    "BuildingTIV", "ContentsTIV", "OtherTIV", "BITIV", "CatZone", "WindTier", "LocDedType", "LocDed1Building"])
        for i, l in enumerate(exposure, 1):
            w.writerow([policy_no, i, l["label"], OCCUPANCY.get(l.get("occupancy") or "warehouse")[3], CONSTRUCTION.get(l.get("construction") or 3)[2],
                        l.get("year_built") or "", l.get("stories") or "", l.get("roof_year") or "", round(l["building"]), round(l["contents"]),
                        round(l["stock"]), round(l["bi"]), l.get("zone") or "", l.get("wind_tier") or "",
                        "NS%" if terms.get("named_storm_ded_pct") else "AOP", terms.get("named_storm_ded_pct") or terms.get("aop_deductible")])
    with elt.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["EventID", "Peril", "Region", "Rate", "MeanLoss", "SDev", "ExposureValue"])
        for r in res["elt"][:1500]:
            w.writerow([r["EventID"], r["Peril"], r["Region"], f"{r['Rate']:.6f}", round(r["MeanLoss"]), round(r["SDev"]), round(r["ExposureValue"])])
    ep.write_text(json.dumps({"account": acct_name, "run_date": run_date, "model_version": res["model_version"], "snapshot": snapshot,
                              "basis": "Carrier share, net of deductibles", "aal_total": round(res["aal_total"]),
                              "aal_by_peril": {k: round(v) for k, v in res["aal_by_peril"].items()},
                              "location_aal": {k: round(v) for k, v in res["loc_aal"].items()},
                              "oep": [{"rp": x["rp"], "loss": round(x["loss"])} for x in res["oep"]],
                              "aep": [{"rp": x["rp"], "loss": round(x["loss"])} for x in res["aep"]]}, indent=2))
    return ex, elt, ep

"""Binding authority agreements and endorsements: rendered with the shared PDF kit, then read back
by the real layout extractor into a versioned authority contract. Every term keeps the page and
bounding box it was read from, so a breach can show the exact clause next to the bordereau cell."""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from uwc.ingest import pdf_extract as PX
from uwc.ingest.interpret import pdf_anchor
from uwc.world.pdfkit import Pdf

from .refdata import CARRIER, CLASSES, CONSTRUCTION, DED_FACTORS, OUT_OF_SCHEDULE, TIER_FACTOR

METHOD = PX.METHOD + " · BAA term map v1"

# label on the page -> (term key, kind)
BAA_KV = {
    "Agreement number": ("agreement_no", "text"), "Unique market reference (UMR)": ("umr", "text"), "Coverholder": ("coverholder", "text"),
    "Coverholder PIN": ("pin", "text"), "Program": ("program", "text"), "Carrier": ("carrier", "text"), "Placing broker": ("broker", "text"),
    "Authority period": ("period", "period"), "Reporting standard": ("reporting_standard", "text"), "Bordereau frequency": ("frequency", "text"),
    "Bordereau due": ("bordereau_due_days", "days"), "Maximum limit any one risk": ("max_limit", "money"), "Gross premium income limit": ("gpi_limit", "money"),
    "Commission": ("commission_pct", "pct"), "Premium tolerance below rated premium": ("tolerance_low", "pct"),
    "Premium tolerance above rated premium": ("tolerance_high", "pct"), "Minimum named storm deductible (Tier 1)": ("ns_min_tier1", "pct"),
    "Minimum named storm deductible (Tier 2)": ("ns_min_tier2", "pct"), "Large loss notification threshold": ("large_loss_threshold", "money"),
    "Large loss notification period": ("large_loss_days", "days"), "Claims settlement authority": ("claims_authority", "money"),
    "TIV any one location exceeding": ("ref_tiv_any", "money"), "TIV in a Tier 1 county exceeding": ("ref_tiv_tier1", "money"),
    "Year built earlier than": ("ref_year_built", "int"), "Premium below rated range": ("ref_premium", "text"),
    "Endorsement number": ("endorsement_no", "int"), "Effective date": ("effective", "date"), "Date issued": ("issued", "date"),
}
TERM_LABEL = {v[0]: k for k, v in BAA_KV.items()}
T_CLASSES = ["Code", "Class", "Base rate per $100", "Status"]
T_CONSTR = ["Construction", "ISO class", "Factor"]
T_TERR = ["State", "County", "Tier", "Factor", "Status"]
T_MINDED = ["TIV from", "TIV to", "Minimum AOP deductible"]
T_DEDF = ["AOP deductible", "Rating factor"]
T_EXCL = ["Ref", "Prohibited risk", "Class code"]
T_AGG = ["Zone", "Zone name", "Peril", "Aggregate TIV limit", "Warning at", "Status"]
TABLES = [T_CLASSES, T_CONSTR, T_TERR, T_MINDED, T_DEDF, T_EXCL, T_AGG]


def dmy(d: str) -> str:
    return date.fromisoformat(d).strftime("%d %b %Y")


def usd(x) -> str:
    return "—" if x is None else f"${x:,.0f}"


def pctf(x) -> str:
    return f"{x * 100:.1f}%".replace(".0%", "%")


# ============================================================================ render
def render_baa(path: Path, cfg: dict, agg_limits: dict[str, float]):
    p = Pdf(path, "carrier", "Binding Authority Agreement", cfg["agreement"])
    p.title("Binding Authority Agreement", f"Commercial property · {cfg['program']} · {CARRIER}")
    p.kv([("Agreement number", cfg["agreement"]), ("Unique market reference (UMR)", cfg["umr"]), ("Coverholder", cfg["name"]),
          ("Coverholder PIN", cfg["pin"]), ("Program", cfg["program"]), ("Carrier", CARRIER), ("Placing broker", cfg["broker"]),
          ("Authority period", f"{dmy(cfg['period'][0])} to {dmy(cfg['period'][1])}"), ("Reporting standard", "Lloyd's CRS v5.2"),
          ("Bordereau frequency", "Monthly (risk, premium, claims)"), ("Bordereau due", "15 days after month end")], cols=1, label_w=200)
    p.para("The Coverholder may bind risks on behalf of the Carrier only within the classes, territories, limits, deductibles and rating set out "
           "below. Any risk outside these terms requires the Carrier's prior written approval, evidenced by a referral reference reported on the bordereau.",
           size=8.5, color="#444444")
    p.section("1. Schedule of classes and rating")
    rows = [(c, CLASSES[c][0], f"{CLASSES[c][1]:.3f}", s) for c, s in cfg["classes"].items()]
    p.table(T_CLASSES, rows, [50, 240, 120, 100])
    p.table(T_CONSTR, [(CONSTRUCTION[i][0], f"ISO {i}", f"{CONSTRUCTION[i][1]:.2f}") for i in (1, 2, 3, 4, 5, 6)], [240, 120, 150])
    p.table(T_DEDF, [(usd(d), f"{f:.2f}") for d, f in DED_FACTORS], [240, 270])
    p.para("Rated premium = TIV ÷ 100 × base rate × construction factor × territory factor × deductible factor. The written premium must fall "
           "within the tolerances in section 3 of the rated premium.", size=8.5, color="#444444")
    p.section("2. Territories")
    p.table(T_TERR, [(s, c, t, f"{TIER_FACTOR[t]:.2f}" if st != "Excluded" else "—", st) for s, c, _city, _z, t, _zone, st, _w in cfg["territories"]
                     if not (cfg.get("endorsement", {}).get("territories_add") and s in {x[0] for x in cfg["endorsement"]["territories_add"]})],
            [60, 160, 90, 80, 120])
    p.section("3. Limits, deductibles and commission")
    kv = [("Maximum limit any one risk", usd(cfg["max_limit"])), ("Gross premium income limit", usd(cfg["gpi_limit"])),
          ("Commission", f"{pctf(cfg['commission'])} of gross premium"), ("Premium tolerance below rated premium", pctf(cfg["tolerance"][0])),
          ("Premium tolerance above rated premium", pctf(cfg["tolerance"][1]))]
    for tier in ("Tier 1", "Tier 2"):
        if cfg["ns_min"].get(tier):
            kv.append((f"Minimum named storm deductible ({tier})", f"{pctf(cfg['ns_min'][tier])} of location TIV"))
    kv += [("Large loss notification threshold", usd(250_000)), ("Large loss notification period", "7 days from notification to the Coverholder"),
           ("Claims settlement authority", usd(50_000))]
    p.kv(kv, cols=1, label_w=230)
    p.table(T_MINDED, [(usd(a), usd(b) if b else "and above", usd(m)) for a, b, m in cfg["min_aop"]], [150, 150, 210])
    p.section("4. Referral triggers — prior written approval required")
    r = cfg["referral"]
    kv = [("TIV any one location exceeding", usd(r["tiv_any"]))]
    if r.get("tiv_tier1"):
        kv.append(("TIV in a Tier 1 county exceeding", usd(r["tiv_tier1"])))
    kv += [("Year built earlier than", str(r["year_built"])), ("Premium below rated range", "Referral required")]
    p.kv(kv, cols=1, label_w=230)
    p.para("Classes marked Referral in section 1, and any limit above the maximum in section 3, also require prior approval.", size=8.5, color="#444444")
    p.section("5. Exclusions — prohibited risks")
    p.table(T_EXCL, [(f"E{i + 1}", OUT_OF_SCHEDULE[c], c) for i, c in enumerate(cfg["prohibited"])], [50, 330, 130])
    p.section("6. Aggregate and capacity limits")
    p.table(T_AGG, [(z, name, peril, usd(agg_limits[z]), "90%", "Open") for z, name, peril, _u in cfg["aggregates"]], [50, 150, 110, 110, 60, 50])
    p.para("When in-force TIV in a zone reaches the warning level the Carrier may, by endorsement, require referral of or stop incremental business in that zone.",
           size=8.5, color="#444444")
    p.signature("Priya Raman", f"Head of Property Underwriting, {CARRIER}", dmy(cfg["period"][0]))
    p.signature(cfg["contact"], f"{cfg['contact_title']}, {cfg['name']}", dmy(cfg["period"][0]))
    p.save()


def render_endorsement(path: Path, cfg: dict, number: int, effective: str, issued: str, reason: str, kv: list[tuple[str, str]],
                       tables: list[tuple[list[str], list[tuple], list[float]]], signer: str = "Priya Raman", signer_title: str = "Head of Property Underwriting"):
    p = Pdf(path, "carrier", f"Endorsement No. {number}", cfg["agreement"])
    p.title(f"Endorsement No. {number} to Binding Authority Agreement", f"{cfg['name']} · {cfg['program']}")
    p.kv([("Agreement number", cfg["agreement"]), ("Endorsement number", str(number)), ("Effective date", dmy(effective)), ("Date issued", dmy(issued))],
         cols=1, label_w=200)
    p.para(reason, size=9)
    p.section("Amended terms")
    if kv:
        p.kv(kv, cols=1, label_w=230)
    for headers, rows, widths in tables:
        p.table(headers, rows, widths)
    p.para("All other terms of the Agreement remain unchanged. Business bound on or after the effective date is subject to the amended terms.", size=8.5, color="#444444")
    p.signature(signer, f"{signer_title}, {CARRIER}", dmy(issued))
    p.save()


# ============================================================================ parse
def _conv(kind: str, s: str):
    s = s.strip()
    if kind == "money":
        return PX.money(s)
    if kind == "pct":
        return PX.pct(s)
    if kind == "days":
        m = re.search(r"(\d+)", s)
        return int(m.group(1)) if m else None
    if kind == "int":
        m = re.search(r"(\d+)", s)
        return int(m.group(1)) if m else None
    if kind == "date":
        return datetime.strptime(s, "%d %b %Y").date().isoformat()
    if kind == "period":
        a, b = [x.strip() for x in s.split(" to ")]
        return (datetime.strptime(a, "%d %b %Y").date().isoformat(), datetime.strptime(b, "%d %b %Y").date().isoformat())
    return s


def _row_anchor(doc_id, t, row, text=None):
    bb = [c[1] for c in row if c[1]]
    if not bb:
        return None
    box = (min(b[0] for b in bb) - 2, min(b[1] for b in bb) - 1, max(b[2] for b in bb) + 2, max(b[3] for b in bb) + 1)
    return pdf_anchor(doc_id, t.page, box, t.page_size, text or " · ".join(c[0] for c in row if c[0]))


def parse(path: Path, doc_id: str) -> dict:
    """Read a BAA or endorsement back into {terms, anchors, labels}. Tables are merged across page breaks."""
    ex = PX.extract(path, TABLES)
    terms: dict = {}
    anchors: dict = {}
    for kv in ex.kvs:
        if kv.label not in BAA_KV:
            continue
        key, kind = BAA_KV[kv.label]
        try:
            val = _conv(kind, kv.value)
        except (ValueError, IndexError):
            continue
        a = pdf_anchor(doc_id, kv.page, kv.bbox, kv.page_size, f"{kv.label}: {kv.value}")
        if key == "period":
            terms["period_start"], terms["period_end"] = val
            anchors["period_start"] = anchors["period_end"] = a
        elif key in ("ns_min_tier1", "ns_min_tier2"):
            terms.setdefault("ns_min", {})["Tier 1" if key.endswith("1") else "Tier 2"] = val
            anchors[f"ns_min.{'Tier 1' if key.endswith('1') else 'Tier 2'}"] = a
        else:
            terms[key] = val
            anchors[key] = a
    merged: list = []
    for t in ex.tables:
        prev = next((m for m in merged if m.headers == t.headers), None)
        if prev:
            prev.rows.extend(t.rows)
        else:
            merged.append(t)
    for t in merged:
        h = t.headers
        get = lambda row, name: row[h.index(name)][0].strip() if name in h and h.index(name) < len(row) else ""
        if h[:3] == T_CLASSES[:3]:
            for row in t.rows:
                code = get(row, "Code")
                if not code:
                    continue
                terms.setdefault("classes", {})[code] = {"label": get(row, "Class"), "rate": float(get(row, "Base rate per $100") or 0), "status": get(row, "Status")}
                anchors[f"classes.{code}"] = _row_anchor(doc_id, t, row)
        elif h[:3] == T_CONSTR[:3]:
            for row in t.rows:
                m = re.search(r"(\d)", get(row, "ISO class"))
                if m:
                    terms.setdefault("construction", {})[int(m.group(1))] = float(get(row, "Factor"))
                    anchors[f"construction.{m.group(1)}"] = _row_anchor(doc_id, t, row)
        elif h[:2] == T_DEDF[:2] and len(h) == 2:
            for i, row in enumerate(t.rows):
                d = PX.money(get(row, "AOP deductible"))
                if d is not None:
                    terms.setdefault("ded_factors", []).append((d, float(get(row, "Rating factor"))))
                    anchors[f"ded_factors.{int(d)}"] = _row_anchor(doc_id, t, row)
        elif h[:3] == T_TERR[:3]:
            for row in t.rows:
                s, c = get(row, "State"), get(row, "County")
                if not s:
                    continue
                f = get(row, "Factor")
                terms.setdefault("territories", {})[f"{s}|{c}"] = {"state": s, "county": c, "tier": get(row, "Tier"),
                                                                   "factor": float(f) if re.match(r"^[\d.]+$", f) else None, "status": get(row, "Status")}
                anchors[f"territories.{s}|{c}"] = _row_anchor(doc_id, t, row)
        elif h[:3] == T_MINDED[:3]:
            for row in t.rows:
                a = PX.money(get(row, "TIV from"))
                b = PX.money(get(row, "TIV to")) if "and above" not in get(row, "TIV to") else None
                m = PX.money(get(row, "Minimum AOP deductible"))
                if a is not None and m is not None:
                    terms.setdefault("min_aop", []).append((a, b, m))
                    anchors[f"min_aop.{int(a)}"] = _row_anchor(doc_id, t, row)
        elif h[:3] == T_EXCL[:3]:
            for row in t.rows:
                code = get(row, "Class code")
                if code:
                    terms.setdefault("prohibited", {})[code] = get(row, "Prohibited risk")
                    anchors[f"prohibited.{code}"] = _row_anchor(doc_id, t, row)
        elif h[:3] == T_AGG[:3]:
            for row in t.rows:
                z = get(row, "Zone")
                if not z:
                    continue
                terms.setdefault("aggregates", {})[z] = {"name": get(row, "Zone name"), "peril": get(row, "Peril"), "limit": PX.money(get(row, "Aggregate TIV limit")),
                                                         "warn": PX.pct(get(row, "Warning at")), "status": get(row, "Status")}
                anchors[f"aggregates.{z}"] = _row_anchor(doc_id, t, row)
    return {"terms": terms, "anchors": anchors, "pages": ex.pages, "kvs": len(ex.kvs), "tables": len(merged)}


# ============================================================================ versions
DICT_TERMS = ("classes", "territories", "prohibited", "aggregates", "construction", "ns_min")


def fold(versions: list[dict], as_of: str | None = None) -> tuple[dict, dict, int]:
    """Authority in force on `as_of` (all versions with effective date ≤ as_of, applied in order)."""
    terms: dict = {}
    anchors: dict = {}
    n = 0
    for v in versions:
        if as_of and v["effective"] > as_of:
            continue
        n = v["version"]
        for k, val in v["terms"].items():
            if k in DICT_TERMS and isinstance(val, dict):
                terms[k] = {**terms.get(k, {}), **val}
            elif k == "min_aop" and terms.get("min_aop"):
                cur = {a: (a, b, m) for a, b, m in terms["min_aop"]}
                for a, b, m in val:
                    cur[a] = (a, b if b is not None else cur.get(a, (a, None, m))[1], m)
                terms["min_aop"] = sorted(cur.values())
            else:
                terms[k] = val
        anchors.update(v["anchors"])
    return terms, anchors, n


def diff(before: dict, after: dict) -> list[dict]:
    """Human-readable list of what an endorsement changed."""
    out = []
    for k, v in after.items():
        if k in ("endorsement_no", "effective", "issued", "agreement_no"):
            continue
        if isinstance(v, dict):
            for kk, vv in v.items():
                old = (before.get(k) or {}).get(kk)
                if old != vv:
                    out.append({"term": f"{k}.{kk}", "label": f"{k.replace('_', ' ').capitalize()} · {kk}", "from": _show(old), "to": _show(vv)})
        elif k == "min_aop":
            cur = {a: m for a, b, m in (before.get("min_aop") or [])}
            for a, b, m in v:
                if cur.get(a) != m:
                    out.append({"term": f"min_aop.{int(a)}", "label": f"Minimum AOP deductible (TIV from {usd(a)})", "from": usd(cur.get(a)), "to": usd(m)})
        elif before.get(k) != v:
            out.append({"term": k, "label": TERM_LABEL.get(k, k), "from": _show(before.get(k), k), "to": _show(v, k)})
    return out


def _show(v, key: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, dict):
        if "status" in v and "limit" in v:
            return f"{usd(v['limit'])} · {v['status']}"
        if "status" in v:
            return v["status"]
        return ", ".join(f"{k} {pctf(x) if isinstance(x, float) and x < 1 else x}" for k, x in v.items())
    if isinstance(v, float) and v < 1:
        return pctf(v)
    if isinstance(v, (int, float)) and key not in ("large_loss_days", "bordereau_due_days", "ref_year_built"):
        return usd(v)
    return str(v)

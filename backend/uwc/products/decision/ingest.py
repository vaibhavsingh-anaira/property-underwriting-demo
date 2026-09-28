"""Parse new-business documents into the shared evidence ledger (rt.store), each value with its anchor.

SOV: the shared SOV parser (uwc.ingest.sov.parse_sov) and the shared row→observation mapping.
PDFs: the shared layout extractor (uwc.ingest.pdf_extract), key–value pairs and tables with bounding boxes.
Email: MIME body + statement patterns, highlighted in the email viewer.
Everything here works on a runtime-like object with `.store` and `.email_highlights`, so the sandbox runs the
same code on uploaded files."""
from __future__ import annotations

import email
import hashlib
import re
from datetime import date
from email import policy as email_policy
from pathlib import Path

from uwc.config import resolve_doc_path
from uwc.ingest import interpret as I
from uwc.ingest import pdf_extract as PX
from uwc.ingest.sov import METHOD as SOV_METHOD, map_construction, map_occupancy, map_sprinkler, parse_sov
from uwc.refdata import OCCUPANCY

from .model import CLASS_GUIDE, HAZARD_RANK

LR_TABLE = [["Claim #", "Date of loss", "Location"]]


def _anc(doc_id, kv) -> dict:
    return I.pdf_anchor(doc_id, kv.page, kv.bbox, kv.page_size, kv.value)


def classify(text: str | None) -> tuple[str | None, float, str | None]:
    """Northgate classification guide: most hazardous class evidenced by the phrases in `text`."""
    if not text:
        return None, 0.0, None
    t = text.lower()
    hits = [(cls, conf, ph) for ph, cls, conf in CLASS_GUIDE if ph in t]
    if not hits:
        cls, conf = map_occupancy(text)
        return cls, conf, None
    cls, conf, ph = max(hits, key=lambda x: (HAZARD_RANK.get(x[0], 0), x[1]))
    return cls, conf, ph


def _num(s: str) -> float | None:
    m = re.search(r"-?[\d,]+(?:\.\d+)?", s or "")
    return float(m.group(0).replace(",", "")) if m else None


# ============================================================================ SOV
def ingest_sov(rt, cid: str, doc: dict, d: str) -> int:
    p = parse_sov(resolve_doc_path(doc))
    rt.store.doc_issues[doc["doc_id"]] = p.issues
    rt.store.doc_method[doc["doc_id"]] = SOV_METHOD
    for row in p.rows:
        ent = I._entity_from_row(rt, cid, row, d, prior=False)
        ent.match_status, ent.match_method = "NEW", "new business"
        ent.aliases.append({"doc_id": doc["doc_id"], "loc_no": ent.loc_no_current, "address": ent.address, "row": row["_row"]})
        I._sov_rows_to_obs(rt, cid, ent.location_uid, row, doc, d, "current", doc["title"])
        raw = row.get("occupancy_raw", (None,))[0]
        cls, conf, ph = classify(raw)
        base, _ = map_occupancy(raw)
        if cls and cls != base and ph:
            I._obs(rt, cid, "location", ent.location_uid, "occupancy_class", cls, "N", "Broker / insured", f"{doc['title']} → Northgate classification guide",
                   d, {"doc_id": doc["doc_id"], "kind": "xlsx", "sheet": row["_sheet"], "cell": row["occupancy_raw"][1], "range": row["_range"]}, doc["doc_id"], conf, raw=raw)
    return len(p.rows)


# ============================================================================ ACORD 125/140-style application
APP_LOC = {"Occupancy": "occupancy_raw", "Construction": "construction_raw", "Year built": "year_built", "Stories": "stories", "Total area (sq ft)": "sqft",
           "Roof covering": "roof_type", "Roof year": "roof_year", "Sprinklered": "sprinkler_pct", "Fire alarm": "fire_alarm", "Protection class": "ppc",
           "Building limit": "building_value", "BPP limit": "contents_value", "Business income": "bi_value", "Max storage height (ft)": "storage_height_ft"}
APP_ACCT = {"Named insured": ("named_insured", str), "FEIN": ("fein", str), "Years in business": ("years_in_business", int), "NAICS": ("naics", str),
            "Proposed effective": ("effective_date", str), "Limit requested": ("limit_requested", _num), "Prior carrier": ("prior_carrier", str),
            "Prior premium": ("prior_premium", _num), "Losses in last 5 years": ("loss_count_declared", lambda s: int(_num(s) or 0)),
            "Total incurred": ("loss_incurred_declared", _num)}


def ingest_application(rt, cid: str, doc: dict, d: str) -> int:
    ex = PX.extract(resolve_doc_path(doc))
    did = doc["doc_id"]
    rt.store.doc_method[did] = PX.METHOD + " · ACORD 125/140 field map"
    fam, lab = "Broker / insured", "ACORD application"
    n = 0
    uid = None
    for kv in ex.kvs:
        if kv.label in APP_ACCT and not (kv.section or "").startswith("PREMISES"):
            f, conv = APP_ACCT[kv.label]
            try:
                v = conv(kv.value)
            except (TypeError, ValueError):
                continue
            if v is None:
                continue
            I._obs(rt, cid, "account", cid, f, v, "C", fam, lab, d, _anc(did, kv), did, 0.96)
            n += 1
            if f == "naics":
                cls = OCC_BY_NAICS.get(str(v))
                if cls:
                    I._obs(rt, cid, "account", cid, "operations_class", cls, "N", fam, f"{lab} → NAICS {v}", d, _anc(did, kv), did, 0.8, raw=v)
            continue
        if kv.label == "Premises address":
            uid = I._loc_by_address(rt, cid, kv.value)
            continue
        if not uid or kv.label not in APP_LOC:
            continue
        f = APP_LOC[kv.label]
        a = _anc(did, kv)
        if f == "sprinkler_pct":
            v = 1.0 if kv.value.startswith("Yes") else (PX.pct(kv.value) if kv.value.startswith("Partial") else 0.0)
            I._obs(rt, cid, "location", uid, f, v, "N", fam, lab, d, a, did, 0.92, raw=kv.value)
        elif f in ("occupancy_raw", "construction_raw"):
            I._obs(rt, cid, "location", uid, f, kv.value, "C", fam, lab, d, a, did, 0.95)
            if f == "occupancy_raw":
                cls, conf, ph = classify(kv.value)
                if cls:
                    I._obs(rt, cid, "location", uid, "occupancy_class", cls, "N", fam, f"{lab} → Northgate classification guide", d, a, did, conf, raw=kv.value)
            else:
                cc, conf = map_construction(kv.value)
                if cc:
                    I._obs(rt, cid, "location", uid, "construction_class", cc, "N", fam, f"{lab} → ISO construction map", d, a, did, conf, raw=kv.value)
        elif f in ("building_value", "contents_value", "bi_value"):
            I._obs(rt, cid, "location", uid, f, PX.money(kv.value), "C", fam, lab, d, a, did, 0.95)   # term None: the schedule governs values
        elif f in ("year_built", "stories", "roof_year", "ppc", "sqft", "storage_height_ft"):
            v = _num(kv.value)
            if v is None:
                continue
            I._obs(rt, cid, "location", uid, f, int(v) if f != "storage_height_ft" else float(v), "C", fam, lab, d, a, did, 0.95)
        else:
            I._obs(rt, cid, "location", uid, f, kv.value, "C", fam, lab, d, a, did, 0.95)
        n += 1
    lines = [(t, pg, bb) for t, pg, bb, sec in ex.paragraphs if sec == "DESCRIPTION OF OPERATIONS"]
    if lines:
        full = " ".join(t for t, *_ in lines)
        bb = (min(b[0] for *_, b in lines), min(b[1] for *_, b in lines), max(b[2] for *_, b in lines), max(b[3] for *_, b in lines))
        anc = I.pdf_anchor(did, lines[0][1], bb, (612.0, 792.0), full)
        I._obs(rt, cid, "account", cid, "operations_description", full, "C", fam, lab, d, anc, did, 0.95)
        cls, conf, ph = classify(full)
        if cls and ph:
            I._obs(rt, cid, "account", cid, "operations_class", cls, "N", fam, f"{lab} → classification guide ('{ph}')", d, anc, did, conf, raw=ph)
        n += 1
    return n


OCC_BY_NAICS = {v[2]: k for k, v in OCCUPANCY.items()}
OCC_BY_NAICS.update({"423930": "scrap", "493110": "warehouse", "493120": "cold_storage", "332710": "manufacturing"})


# ============================================================================ loss-control inspection (verified observations)
INSP = {"Construction": ("construction_class", lambda s: map_construction(s.split(" (")[0])[0]), "Year built": ("year_built", int), "Stories": ("stories", int),
        "Floor area (sq ft)": ("sqft", lambda s: int(s.replace(",", ""))), "Roof covering": ("roof_type", str), "Roof year (verified)": ("roof_year", int),
        "Occupancy observed": ("occupancy_class", I._occ_from_label), "Sprinkler protection": ("sprinkler_pct", PX.pct), "Fire alarm": ("fire_alarm", str),
        "Public protection class": ("ppc", int), "Max storage height (ft)": ("storage_height_ft", float), "Sprinkler design storage height (ft)": ("sprinkler_design_ft", float),
        "Commodity": ("commodity", str), "Roof condition": ("roof_condition_verified", str)}


def ingest_inspection(rt, cid: str, doc: dict, d: str) -> int:
    ex = PX.extract(resolve_doc_path(doc))
    did = doc["doc_id"]
    rt.store.doc_method[did] = PX.METHOD + " · loss-control report map"
    sd = next((kv.value for kv in ex.kvs if kv.label == "Survey date"), d)
    lab = f"{doc['doc_type']} {sd}"
    uid, n = None, 0
    for kv in ex.kvs:
        if kv.label == "Address":
            uid = I._loc_by_address(rt, cid, kv.value)
            continue
        if not uid or kv.label not in INSP:
            continue
        f, conv = INSP[kv.label]
        try:
            v = conv(kv.value)
        except (TypeError, ValueError):
            continue
        if v is None:
            continue
        I._obs(rt, cid, "location", uid, f, v, "V", "Engineering", lab, d, _anc(did, kv), did, 0.98, valid_from=sd)
        n += 1
    return n


# ============================================================================ loss runs
def ingest_loss_run(rt, cid: str, doc: dict, d: str) -> int:
    ex = PX.extract(resolve_doc_path(doc), LR_TABLE)
    did = doc["doc_id"]
    rt.store.doc_method[did] = PX.METHOD + " · loss-run table map"
    lab = doc["title"]
    n = 0
    for kv in ex.kvs:
        if kv.label == "Experience period":
            m = re.findall(r"\d{4}-\d{2}-\d{2}", kv.value)
            if len(m) == 2:
                I._obs(rt, cid, "account", cid, "loss_run_period", f"{m[0]}/{m[1]}", "S", "Carrier systems", lab, d, _anc(did, kv), did, 0.98)
                n += 1
        elif kv.label == "Valuation date":
            I._obs(rt, cid, "account", cid, "loss_run_valued", kv.value, "S", "Carrier systems", lab, d, _anc(did, kv), did, 0.98)
            n += 1
    for t in ex.tables:
        if t.headers[0] != "Claim #":
            continue
        for r in t.rows:
            clm = r[0][0]
            if not re.match(r"^[A-Z]{2,4}-\d{2}-\d{4}$", clm or ""):
                continue
            sid = f"{cid}:{clm}"
            inc = PX.money(r[7][0]) if len(r) > 7 else None
            anc = I.pdf_anchor(did, t.page, r[7][1] or r[0][1], t.page_size, r[7][0])
            I._obs(rt, cid, "claim", sid, "incurred", inc, "S", "Carrier systems", lab, d, anc, did, 0.97)
            I._obs(rt, cid, "claim", sid, "date_of_loss", r[1][0], "S", "Carrier systems", lab, d, I.pdf_anchor(did, t.page, r[1][1] or r[0][1], t.page_size, r[1][0]), did, 0.97)
            I._obs(rt, cid, "claim", sid, "cause", r[3][0], "S", "Carrier systems", lab, d, I.pdf_anchor(did, t.page, r[3][1] or r[0][1], t.page_size, r[3][0]), did, 0.97)
            loc = I._loc_by_address(rt, cid, r[2][0])
            if loc:
                I._obs(rt, cid, "claim", sid, "location_uid", loc, "S", "Carrier systems", lab, d, anc, did, 0.9)
            n += 1
    return n


# ============================================================================ manuscript wording
def ingest_manuscript(rt, cid: str, doc: dict, d: str) -> int:
    ex = PX.extract(resolve_doc_path(doc))
    did = doc["doc_id"]
    rt.store.doc_method[did] = PX.METHOD + " · clause pattern map (production: LLM clause → structured term, human-confirmed)"
    text = " ".join(t for t, *_ in ex.paragraphs)
    form = next((kv.value for kv in ex.kvs if kv.label == "Form number"), "manuscript")
    n = 0
    for m in re.finditer(r"paragraph ([A-Z]\.\d\.[a-z])\.?\s+([A-Za-z ]+?) of the Causes of Loss", text):
        para = next(((t, pg, bb) for t, pg, bb, _ in ex.paragraphs if m.group(1) in t), ex.paragraphs[0][:3])
        anc = I.pdf_anchor(did, para[1], para[2], (612.0, 792.0), para[0])
        op = "DELETE" if re.search(r"is deleted", text[m.end():m.end() + 160]) else "AMEND"
        I._obs(rt, cid, "account", cid, "manuscript_clause", f"{op} CP 10 30 {m.group(1)} ({m.group(2).strip()}) — {form}", "C", "Broker / insured", doc["title"], d, anc, did, 0.9)
        n += 1
    return n


# ============================================================================ broker email
EMAIL = [
    (r"requested effective date of (\d{4}-\d{2}-\d{2})", "effective_date", lambda m: m.group(1)),
    (r"target premium of \$([\d,]+)", "target_premium", lambda m: float(m.group(1).replace(",", ""))),
    (r"ready to bind at \$([\d,]+)", "bind_offer", lambda m: float(m.group(1).replace(",", ""))),
    (r"all three plants are fully sprinklered|both .* well protected|fully sprinklered office buildings", "sprinkler_statement", lambda m: m.group(0)),
    (r"storage is within the sprinkler design", "storage_statement", lambda m: m.group(0)),
    (r"(the prior carrier's runs will follow)", "missing_document", lambda m: "Prior carrier loss runs to follow"),
    (r"terms by (\d{4}-\d{2}-\d{2})", "quote_needed_by", lambda m: m.group(1)),
    (r"manuscript water damage amendment", "manuscript_requested", lambda m: m.group(0)),
    (r"(roof is in good shape)", "roof_statement", lambda m: m.group(0)),
]


def ingest_email(rt, cid: str, doc: dict, d: str) -> int:
    msg = email.message_from_bytes(resolve_doc_path(doc).read_bytes(), policy=email_policy.default)
    body = msg.get_body(preferencelist=("plain",)).get_content()
    did = doc["doc_id"]
    rt.store.doc_method[did] = "Email parser v1 (MIME · statement patterns · attachment routing)"
    hl = []
    for pat, f, conv in EMAIL:
        for m in re.finditer(pat, body, re.I):
            o = I._obs(rt, cid, "account", cid, f, conv(m), "C", "Broker / insured", f"Broker email {d}", d, {"doc_id": did, "kind": "eml", "text": m.group(0)}, did, 0.9)
            hl.append({"text": m.group(0), "field_code": f, "obs_id": o.obs_id})
    rt.store.doc_issues.setdefault(did, [])
    rt.email_highlights[did] = hl
    return len(hl)


# ============================================================================ roof schedule / contractor letter (broker replies)
def ingest_roof_schedule(rt, cid: str, doc: dict, d: str) -> int:
    ex = PX.extract(resolve_doc_path(doc), [["Location", "Address", "Roof year"]])
    did = doc["doc_id"]
    rt.store.doc_method[did] = PX.METHOD
    n = 0
    for t in ex.tables:
        for r in t.rows:
            uid = I._loc_by_address(rt, cid, r[1][0]) if len(r) > 1 else None
            if uid and len(r) > 3 and r[3][0] and not r[3][0].startswith("No work"):
                I._obs(rt, cid, "location", uid, "roof_replacement_planned", r[3][0], "C", "Broker / insured", doc["title"], d,
                       I.pdf_anchor(did, t.page, r[3][1] or r[0][1], t.page_size, r[3][0]), did, 0.93)
                n += 1
    return n


def ingest_contractor_letter(rt, cid: str, doc: dict, d: str) -> int:
    ex = PX.extract(resolve_doc_path(doc))
    did = doc["doc_id"]
    rt.store.doc_method[did] = PX.METHOD
    uid = None
    for kv in ex.kvs:
        if kv.label == "Premises":
            uid = I._loc_by_address(rt, cid, kv.value)
        elif kv.label == "Work" and uid:
            I._obs(rt, cid, "location", uid, "in_rack_claimed", kv.value, "C", "Broker / insured", doc["title"], d, _anc(did, kv), did, 0.93)
            return 1
    return 0


def doc_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:10]


def years_covered(periods: list[str], as_of: str) -> float:
    """Union of loss-run experience periods, in years, looking back from the valuation date."""
    iv = sorted((date.fromisoformat(a), date.fromisoformat(b)) for a, b in (p.split("/") for p in periods))
    tot, cur_s, cur_e = 0, None, None
    for s, e in iv:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                tot += (cur_e - cur_s).days
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        tot += (cur_e - cur_s).days
    return round(tot / 365.25, 1)

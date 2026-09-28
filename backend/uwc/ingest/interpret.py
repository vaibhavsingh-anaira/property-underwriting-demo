"""Interpret documents and system events into observations + entities.

This is the only place raw evidence enters the ledger. Each handler records
what it extracted (for the Extraction panel) and every observation carries an
anchor back to its source (cell, page+bbox, system record, vendor payload).
"""
from __future__ import annotations

import csv
import email
import json
import re
from email import policy as email_policy
from pathlib import Path
from typing import TYPE_CHECKING, Any

from uwc.config import WORLD_DIR, resolve_doc_path
from uwc.ingest import pdf_extract as PX
from uwc.ingest.sov import METHOD as SOV_METHOD, map_construction, map_occupancy, map_sprinkler, parse_sov
from uwc.ledger.matching import match_rows, std_address, sim
from uwc.ledger.store import LocationEntity

if TYPE_CHECKING:
    from uwc.runtime import Runtime

CONTRACT_KV = {
    "Limit of insurance": ("limit", "money"), "Limit basis": ("limit_basis", "basis"), "AOP deductible": ("aop_deductible", "money"),
    "Named storm deductible": ("named_storm_ded_pct", "pct"), "Named storm minimum": ("named_storm_ded_min", "money"),
    "Wind/hail deductible": ("wind_hail_ded_pct", "pct"), "Business income sublimit": ("bi_sublimit", "money"),
    "Flood sublimit": ("flood_sublimit", "money"), "Earthquake sublimit": ("eq_sublimit", "money"),
    "Total premium": ("premium", "money"), "Bound premium": ("premium", "money"), "Quoted premium": ("premium", "money"),
}
TABLES = [["Loc", "Address", "City"], ["Form", "Edition", "Title"], ["Loc", "Address", "Symbol"], ["Subjectivity", "Due", "Status at bind"],
          ["Subjectivity", "Due"], ["Claim #", "Date of loss", "Location"], ["Rec #", "Loc", "Category"], ["Property", "Area (sf)", "Replacement cost"]]


def _conv(kind: str, s: str):
    if kind == "money":
        return PX.money(s)
    if kind == "pct":
        return PX.pct(s)
    if kind == "basis":
        return {"Blanket": "blanket", "Scheduled": "scheduled", "Loss limit": "loss_limit"}.get(s.strip(), s)
    return s


def pdf_anchor(doc_id: str, page: int, bbox, page_size, text: str | None = None) -> dict:
    return {"doc_id": doc_id, "kind": "pdf", "page": page, "bbox": list(bbox), "page_size": list(page_size), "text": text}


# ============================================================================ documents
def ingest_document(rt: "Runtime", doc: dict, role: str, date: str, extra: dict | None = None):
    extra = extra or {}
    acct = doc.get("account_id")
    path = resolve_doc_path(doc)
    fn = {
        "sov_prior": _sov_prior, "sov_current": _sov_current, "quote": _contract_doc, "binder": _contract_doc, "policy": _contract_doc,
        "endorsement": _endorsement, "loss_run": _loss_run, "engineering": _engineering, "email": _email, "alarm_certs": _alarm_certs,
        "hood_certs": _hood_certs, "impairment": _impairment, "appraisal": _appraisal,
    }.get(role)
    rt.store.docs[doc["doc_id"]] = doc
    if fn:
        fn(rt, acct, doc, path, date, extra)


def _obs(rt, acct, st, sid, field, value, t, fam, label, date, anchor, doc_id=None, conf=0.95, term=None, raw=None, vendor=None,
         model=None, valid_from=None, vstatus=None):
    return rt.store.add(account_id=acct, subject_type=st, subject_id=sid, field_code=field, value=value, obs_type=t, source_family=fam,
                        source_label=label, recorded_at=date, valid_from=valid_from or date, anchor=anchor, doc_id=doc_id, confidence=conf,
                        term=term, raw=raw, vendor=vendor, model_version=model,
                        verification_status=vstatus or ("VERIFIED" if t == "V" else "UNVERIFIED"))


def _sov_rows_to_obs(rt, acct, uid, row, doc, date, term, label):
    did = doc["doc_id"]
    sheet = row["_sheet"]
    def a(cell):
        return {"doc_id": did, "kind": "xlsx", "sheet": sheet, "cell": cell, "range": row["_range"]}
    fam = "Broker / insured"
    for f in ("location_name", "address", "year_built", "stories", "sqft", "roof_year", "storage_height_ft"):
        if f in row and row[f][0] not in (None, ""):
            v = row[f][0]
            if f in ("year_built", "stories", "sqft", "roof_year") and isinstance(v, (int, float)):
                v = int(v)
            _obs(rt, acct, "location", uid, f, v, "C", fam, label, date, a(row[f][1]), did, 0.95, term=None if f not in ("sqft",) else term)
    if "occupancy_raw" in row and row["occupancy_raw"][0]:
        raw = row["occupancy_raw"][0]
        _obs(rt, acct, "location", uid, "occupancy_raw", raw, "C", fam, label, date, a(row["occupancy_raw"][1]), did, 0.95)
        cls, conf = map_occupancy(raw)
        if cls:
            _obs(rt, acct, "location", uid, "occupancy_class", cls, "N", fam, f"{label} → occupancy map", date, a(row["occupancy_raw"][1]), did, conf, raw=raw)
    if "construction_raw" in row and row["construction_raw"][0]:
        raw = row["construction_raw"][0]
        _obs(rt, acct, "location", uid, "construction_raw", raw, "C", fam, label, date, a(row["construction_raw"][1]), did, 0.95)
        cls, conf = map_construction(raw)
        if cls:
            _obs(rt, acct, "location", uid, "construction_class", cls, "N", fam, f"{label} → ISO construction map", date, a(row["construction_raw"][1]), did, conf, raw=raw)
    if "sprinkler" in row and row["sprinkler"][0] is not None:
        v = map_sprinkler(row["sprinkler"][0])
        if v is not None:
            _obs(rt, acct, "location", uid, "sprinkler_pct", v, "N", fam, label, date, a(row["sprinkler"][1]), did, 0.9, raw=row["sprinkler"][0])
    for f, fc in (("building_value", "building_value"), ("contents_value", "contents_value"), ("stock_value", "stock_value"),
                  ("bi_value", "bi_value"), ("tiv_reported", "tiv_reported")):
        if f in row and isinstance(row[f][0], (int, float)):
            _obs(rt, acct, "location", uid, fc, float(row[f][0]), "C", fam, label, date, a(row[f][1]), did, 0.97, term=term)


def _geocode(rt, acct, uid, ent: LocationEntity, date):
    key = f"{ent.address}|{ent.city}|{ent.state}".lower()
    v = rt.systems["vendors"].get(key)
    level, conf = "rooftop", 0.97
    if not v:
        # fall back: nearest known address on the same street in the same city (street-level interpolation)
        cands = [(sim(k.split("|")[0], ent.address), k) for k in rt.systems["vendors"] if k.split("|")[1] == ent.city.lower()]
        cands.sort(reverse=True)
        if cands and cands[0][0] > 0.6:
            v = rt.systems["vendors"][cands[0][1]]
            level, conf = "street", 0.62
    if not v:
        return
    g = v["geocode"]
    ent.lat, ent.lon, ent.geocode_level = g["lat"], g["lon"], level
    anc = {"doc_id": None, "kind": "vendor", "system": "Geocoder (mock)", "record_id": key, "path": "$.geocode"}
    _obs(rt, acct, "location", uid, "lat", g["lat"], "M", "External data", "Geocoder (mock)", date, anc, None, conf, vendor="Geocoder (mock)", model="geo-2026.2")
    _obs(rt, acct, "location", uid, "lon", g["lon"], "M", "External data", "Geocoder (mock)", date, anc, None, conf, vendor="Geocoder (mock)", model="geo-2026.2")
    _obs(rt, acct, "location", uid, "geocode_level", level, "M", "External data", "Geocoder (mock)", date, anc, None, conf, vendor="Geocoder (mock)")


def _entity_from_row(rt, acct, row, date, prior: bool) -> LocationEntity:
    uid = rt.store.new_location_uid(acct)
    g = lambda f: row.get(f, (None,))[0]
    ent = LocationEntity(location_uid=uid, account_id=acct, label=g("location_name") or g("address") or uid, address=str(g("address") or ""),
                         city=str(g("city") or ""), state=str(g("state") or ""), zip=str(g("zip") or ""), first_seen=date,
                         loc_no_prior=str(g("loc_no")) if prior and g("loc_no") is not None else None,
                         loc_no_current=str(g("loc_no")) if not prior and g("loc_no") is not None else None,
                         in_prior=prior, in_current=not prior, match_status="MATCHED" if prior else "NEW")
    rt.store.account_locations(acct)[uid] = ent
    return ent


def _sov_prior(rt, acct, doc, path, date, extra):
    p = parse_sov(path)
    rt.store.doc_issues[doc["doc_id"]] = p.issues
    rt.store.doc_method[doc["doc_id"]] = SOV_METHOD
    for row in p.rows:
        ent = _entity_from_row(rt, acct, row, date, prior=True)
        ent.aliases.append({"doc_id": doc["doc_id"], "loc_no": ent.loc_no_prior, "address": ent.address, "row": row["_row"]})
        _sov_rows_to_obs(rt, acct, ent.location_uid, row, doc, date, "prior", f"{doc['title']}")
        _geocode(rt, acct, ent.location_uid, ent, date)


def _sov_current(rt, acct, doc, path, date, extra):
    p = parse_sov(path)
    rt.store.doc_issues[doc["doc_id"]] = p.issues
    rt.store.doc_method[doc["doc_id"]] = SOV_METHOD
    locs = rt.store.account_locations(acct)
    prior_rows = []
    for uid, e in locs.items():
        if not e.in_prior:
            continue
        rv = lambda f: _latest(rt, uid, f)
        prior_rows.append({"uid": uid, "loc_no": e.loc_no_prior, "address": e.address, "city": e.city, "carrier_loc_id": e.carrier_loc_id,
                           "lat": e.lat, "lon": e.lon, "sqft": rv("sqft"), "tiv": rv("tiv_reported"), "construction": rv("construction_class"),
                           "stories": rv("stories")})
    cur_rows = []
    for i, row in enumerate(p.rows):
        g = lambda f: row.get(f, (None,))[0]
        tmp = LocationEntity(location_uid="tmp", account_id=acct, label="", address=str(g("address") or ""), city=str(g("city") or ""), state=str(g("state") or ""))
        key = f"{tmp.address}|{tmp.city}|{tmp.state}".lower()
        v = rt.systems["vendors"].get(key)
        cons, _ = map_construction(g("construction_raw"))
        cur_rows.append({"idx": i, "loc_no": g("loc_no"), "address": tmp.address, "city": tmp.city, "carrier_loc_id": None,
                         "lat": v["geocode"]["lat"] if v else None, "lon": v["geocode"]["lon"] if v else None, "sqft": g("sqft"),
                         "tiv": g("tiv_reported"), "construction": cons, "stories": g("stories")})
    decisions = match_rows(prior_rows, cur_rows)
    for d in decisions:
        if d["idx"] is None:
            e = locs[d["uid"]]
            e.match_status = d["status"]
            e.match_method = d["method"]
            e.match_score = d["score"]
            e.in_current = False
            if d.get("merged_into"):
                e.merged_into = d["merged_into"]
            continue
        row = p.rows[d["idx"]]
        g = lambda f: row.get(f, (None,))[0]
        if d["uid"]:
            e = locs[d["uid"]]
            e.in_current = True
            e.loc_no_current = str(g("loc_no")) if g("loc_no") is not None else None
            e.match_status, e.match_method, e.match_score = d["status"], d["method"], d["score"]
            e.proposed_target = d.get("proposed_uid")
            if d.get("merged_from"):
                e.merged_from = d["merged_from"]
                e.match_status = "MERGED"
            e.aliases.append({"doc_id": doc["doc_id"], "loc_no": e.loc_no_current, "address": str(g("address")), "row": row["_row"]})
            uid = e.location_uid
            if g("location_name") and g("location_name") != e.label:
                e.label = str(g("location_name"))
        else:
            e = _entity_from_row(rt, acct, row, date, prior=False)
            e.aliases.append({"doc_id": doc["doc_id"], "loc_no": e.loc_no_current, "address": e.address, "row": row["_row"]})
            uid = e.location_uid
            _geocode(rt, acct, uid, e, date)
        _sov_rows_to_obs(rt, acct, uid, row, doc, date, "current", doc["title"])
    rt.mark_renewal_sov(acct, doc["doc_id"], date)


def _latest(rt, uid, field):
    obs = rt.store.field_obs(uid, field)
    return obs[-1].value if obs else None


def _loc_by_address(rt, acct, address: str) -> str | None:
    locs = rt.store.account_locations(acct)
    a0 = address.split(",")[0]
    best, bs = None, 0.0
    for uid, e in locs.items():
        s = sim(e.address, a0)
        if s > bs:
            best, bs = uid, s
    return best if bs >= 0.85 else None


def _loc_by_no(rt, acct, loc_no: str, prior=True) -> str | None:
    for uid, e in rt.store.account_locations(acct).items():
        if (e.loc_no_prior if prior else e.loc_no_current) == str(loc_no):
            return uid
    return None


def _contract_doc(rt, acct, doc, path, date, extra):
    stage = extra.get("stage")  # quote_v3 | binder | policy
    ex = PX.extract(path, TABLES)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    sid = f"{acct}:{stage}"
    fam = "Carrier systems"
    label = doc["title"]
    for kv in ex.kvs:
        if kv.label in CONTRACT_KV:
            f, kind = CONTRACT_KV[kv.label]
            val = _conv(kind, kv.value)
            if kv.value in ("Included in limit", "Not covered", "—"):
                val = None
            _obs(rt, acct, "policy", sid, f, val, "C", fam, label, date, pdf_anchor(doc["doc_id"], kv.page, kv.bbox, kv.page_size, kv.value), doc["doc_id"], 0.97, term=extra.get("term"))
    merged: list = []
    for t in ex.tables:
        prev = next((m for m in merged if m.headers[:3] == t.headers[:3]), None)
        if prev and t.headers[0] in ("Form", "Loc", "Subjectivity") and t.headers[:3] != ["Loc", "Address", "City"]:
            prev.rows.extend(t.rows)
        else:
            merged.append(t)
    for t in merged:
        if t.headers[:2] == ["Form", "Edition"]:
            forms = [r[0][0] for r in t.rows if r[0][0]]
            bb = [r[0][1] for r in t.rows if r[0][1]]
            box = (min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb) + 300, max(b[3] for b in bb)) if bb else None
            _obs(rt, acct, "policy", sid, "forms", forms, "C", fam, label, date, pdf_anchor(doc["doc_id"], t.page, box, t.page_size), doc["doc_id"], 0.97, term=extra.get("term"))
        elif t.headers[:3] == ["Loc", "Address", "Symbol"]:
            sgs = []
            bb = []
            for r in t.rows:
                uid = _loc_by_address(rt, acct, r[1][0])
                sgs.append(f"{uid}|{r[2][0]}")
                if r[0][1]:
                    bb.append(r[0][1])
            box = (min(b[0] for b in bb), min(b[1] for b in bb), 560, max(b[3] for b in bb)) if bb else None
            _obs(rt, acct, "policy", sid, "safeguards", sgs, "C", fam, label, date, pdf_anchor(doc["doc_id"], t.page, box, t.page_size), doc["doc_id"], 0.95, term=extra.get("term"))
        elif t.headers[0] == "Subjectivity":
            subs = [r[0][0] for r in t.rows]
            bb = [r[0][1] for r in t.rows if r[0][1]]
            box = (bb[0][0], bb[0][1], 560, bb[-1][3]) if bb else None
            _obs(rt, acct, "policy", sid, "subjectivities", subs, "C", fam, label, date, pdf_anchor(doc["doc_id"], t.page, box, t.page_size), doc["doc_id"], 0.95, term=extra.get("term"))
        elif t.headers[:3] == ["Loc", "Address", "City"] and stage == "policy":
            for r in t.rows:
                uid = _loc_by_no(rt, acct, r[0][0]) or _loc_by_address(rt, acct, r[1][0])
                if not uid:
                    continue
                for col, f in ((5, "building_value"), (8, "tiv_reported")):
                    if len(r) > col and r[col][1]:
                        _obs(rt, acct, "location", uid, f, PX.money(r[col][0]), "S", fam, f"{label} — schedule", date,
                             pdf_anchor(doc["doc_id"], t.page, r[col][1], t.page_size, r[col][0]), doc["doc_id"], 0.99, term="prior")
    rt.register_contract_doc(acct, stage, doc["doc_id"], date)


def _endorsement(rt, acct, doc, path, date, extra):
    ex = PX.extract(path)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    rt.register_contract_doc(acct, extra.get("stage", "endorsement"), doc["doc_id"], date)


def _loss_run(rt, acct, doc, path, date, extra):
    ex = PX.extract(path, TABLES)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    for t in ex.tables:
        if t.headers[0] == "Claim #":
            for r in t.rows:
                cid = r[0][0]
                if not cid.startswith("CLM"):
                    continue
                inc = PX.money(r[7][0]) if len(r) > 7 else None
                _obs(rt, acct, "claim", f"{acct}:{cid}", "incurred", inc, "C", "Broker / insured", doc["title"], date,
                     pdf_anchor(doc["doc_id"], t.page, r[7][1] or r[0][1], t.page_size, r[7][0]), doc["doc_id"], 0.95)


def _engineering(rt, acct, doc, path, date, extra):
    ex = PX.extract(path, TABLES)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    survey_date = next((kv.value for kv in ex.kvs if kv.label == "Survey date"), date)
    fam, label = "Engineering", f"Engineering survey {survey_date}"
    cur_uid = None
    mapping = {"Construction": ("construction_class", lambda s: map_construction(s.split(" (")[0])[0]), "Year built": ("year_built", int),
               "Stories": ("stories", int), "Floor area (sq ft)": ("sqft", lambda s: int(s.replace(",", ""))), "Roof covering": ("roof_type", str),
               "Roof year (verified)": ("roof_year", int), "Occupancy observed": ("occupancy_class", _occ_from_label),
               "Sprinkler protection": ("sprinkler_pct", lambda s: PX.pct(s)), "Fire alarm": ("fire_alarm", str),
               "Max storage height (ft)": ("storage_height_ft", float), "Sprinkler design storage height (ft)": ("sprinkler_design_ft", float),
               "Commodity": ("commodity", str), "Cooking suppression": ("cooking_suppression_type", str)}
    for kv in ex.kvs:
        if kv.label == "Address":
            cur_uid = _loc_by_address(rt, acct, kv.value)
            continue
        if not cur_uid or kv.label not in mapping:
            continue
        f, conv = mapping[kv.label]
        try:
            val = conv(kv.value)
        except (ValueError, TypeError):
            continue
        if val is None:
            continue
        _obs(rt, acct, "location", cur_uid, f, val, "V", fam, label, date, pdf_anchor(doc["doc_id"], kv.page, kv.bbox, kv.page_size, kv.value),
             doc["doc_id"], 0.98, valid_from=survey_date)
    rt.engineering_doc(acct, doc["doc_id"], survey_date)


def _occ_from_label(s: str) -> str | None:
    from uwc.refdata import OCCUPANCY
    for k, v in OCCUPANCY.items():
        if v[0] == s:
            return k
    return map_occupancy(s)[0]


EMAIL_PATTERNS = [
    (r"target premium of \$([\d,]+)", "target_premium", lambda m: float(m.group(1).replace(",", "")), "account"),
    (r"expiring terms \((\d+(?:\.\d+)?)% named storm\)", "requested_ns_ded_pct", lambda m: float(m.group(1)) / 100, "account"),
    (r"cash on premises runs up to \$([\d,]+)", "cash_on_premises", lambda m: float(m.group(1).replace(",", "")), "account"),
    (r"all stores have burglar alarms", "burglar_alarm_all", lambda m: True, "account"),
    (r"(updated [\w\- ]+?) to follow", "missing_document", lambda m: m.group(1)[0].upper() + m.group(1)[1:], "account"),
    (r"values are unchanged from last year", "stated_change", lambda m: "Values unchanged from last year", "account"),
    (r"now storing ([\w\- ]+?) at the (\w+) facility", "occupancy_class", lambda m: "li_storage" if "batter" in m.group(1) else None, "location_city:2"),
]


def _email(rt, acct, doc, path, date, extra):
    msg = email.message_from_bytes(path.read_bytes(), policy=email_policy.default)
    body = msg.get_body(preferencelist=("plain",)).get_content()
    rt.store.doc_method[doc["doc_id"]] = "Email parser v1 (MIME · statement patterns · attachment routing)"
    highlights = []
    for pat, field, conv, target in EMAIL_PATTERNS:
        for m in re.finditer(pat, body, re.I):
            val = conv(m)
            if val is None:
                continue
            anc = {"doc_id": doc["doc_id"], "kind": "eml", "text": m.group(0)}
            if target == "account":
                o = _obs(rt, acct, "account", acct, field, val, "C", "Broker / insured", f"Broker email {date}", date, anc, doc["doc_id"], 0.9)
            else:
                city = m.group(int(target.split(":")[1]))
                uid = next((u for u, e in rt.store.account_locations(acct).items() if e.city.lower() == city.lower()), None)
                if not uid:
                    continue
                o = _obs(rt, acct, "location", uid, field, val, "N", "Broker / insured", f"Broker email {date} → occupancy map", date, anc, doc["doc_id"], 0.82, raw=m.group(0))
                _obs(rt, acct, "location", uid, "commodity", m.group(1), "C", "Broker / insured", f"Broker email {date}", date, anc, doc["doc_id"], 0.82)
            highlights.append({"text": m.group(0), "field_code": field, "obs_id": o.obs_id})
    rt.store.doc_issues.setdefault(doc["doc_id"], [])
    rt.email_highlights[doc["doc_id"]] = highlights
    # attachments are ingested as their own documents (role from the event)
    for att in extra.get("attachments", []):
        adoc = rt.world_docs[att["doc_id"]]
        role = att["role"]
        ingest_document(rt, adoc, role, date, {})


def _alarm_certs(rt, acct, doc, path, date, extra):
    ex = PX.extract(path)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    uid = None
    for kv in ex.kvs:
        if kv.label == "Protected premises":
            uid = _loc_by_address(rt, acct, kv.value)
        elif kv.label == "Central station monitoring" and uid:
            _obs(rt, acct, "location", uid, "burglar_monitored", kv.value.startswith("Yes"), "V", "External data", "Alarm certificate (SentryLine)", date,
                 pdf_anchor(doc["doc_id"], kv.page, kv.bbox, kv.page_size, kv.value), doc["doc_id"], 0.97)


def _hood_certs(rt, acct, doc, path, date, extra):
    ex = PX.extract(path)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    uid = None
    for kv in ex.kvs:
        if kv.label == "Premises":
            uid = _loc_by_address(rt, acct, kv.value)
        elif kv.label == "Suppression system inspected" and uid:
            anc = pdf_anchor(doc["doc_id"], kv.page, kv.bbox, kv.page_size, kv.value)
            _obs(rt, acct, "location", uid, "cooking_suppression_verified", kv.value.startswith("Yes"), "V", "External data", "Hood cleaning certificate", date, anc, doc["doc_id"], 0.96)
            _obs(rt, acct, "location", uid, "hood_cleaning_ok", True, "V", "External data", "Hood cleaning certificate", date, anc, doc["doc_id"], 0.96)


def _impairment(rt, acct, doc, path, date, extra):
    ex = PX.extract(path)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    uid = None
    for kv in ex.kvs:
        if kv.label == "Premises":
            uid = _loc_by_address(rt, acct, kv.value.split(", ", 1)[1] if ", " in kv.value else kv.value)
        elif kv.label == "Impairment" and uid:
            _obs(rt, acct, "location", uid, "sprinkler_impaired", True, "V", "Engineering", "Fire protection impairment notice", date,
                 pdf_anchor(doc["doc_id"], kv.page, kv.bbox, kv.page_size, kv.value), doc["doc_id"], 0.98)


def _appraisal(rt, acct, doc, path, date, extra):
    ex = PX.extract(path, TABLES)
    rt.store.doc_method[doc["doc_id"]] = PX.METHOD
    ed = next((kv for kv in ex.kvs if kv.label == "Effective date"), None)
    if ed:
        _obs(rt, acct, "account", acct, "appraisal_date", ed.value, "C", "Broker / insured", "Insurable value appraisal", date,
             pdf_anchor(doc["doc_id"], ed.page, ed.bbox, ed.page_size, ed.value), doc["doc_id"], 0.97)


# ============================================================================ system / vendor events
def ingest_cat_run(rt, acct, payload, date):
    """CAT team's as-bound run: exposure file (model input coding) + results."""
    exp = rt.world_docs[payload["exposure_doc"]]
    for d in ("exposure_doc", "elt_doc", "ep_doc"):
        rt.store.docs[payload[d]] = rt.world_docs[payload[d]]
    with (WORLD_DIR / exp["path"]).open() as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            uid = _loc_by_no(rt, acct, row["LocNumber"])
            if not uid:
                continue
            from uwc.refdata import CONSTRUCTION
            code = int(row["ConstructionCode"])
            iso = next((k for k, v in CONSTRUCTION.items() if v[2] == code), None)
            _obs(rt, acct, "location", uid, "cat_input_construction", iso, "S", "CAT model", "CAT exposure file (as bound)", date,
                 {"doc_id": exp["doc_id"], "kind": "csv", "cell": f"I{i}", "range": f"A{i}:S{i}", "text": row["ConstructionCode"]}, exp["doc_id"], 0.99)
    ep = json.loads((WORLD_DIR / rt.world_docs[payload["ep_doc"]]["path"]).read_text())
    rt.cat_runs.setdefault(acct, []).append({"snapshot": "AS_BOUND", "run_date": date, "result": ep, "exposure_doc_id": payload["exposure_doc"],
                                             "elt_doc_id": payload["elt_doc"], "ep_doc_id": payload["ep_doc"], "model_version": ep["model_version"]})


def enrich_location(rt, acct, uid, date):
    """Vendor enrichment (hazard, valuation, crime, property) — called at Pass 1 / on new locations."""
    e = rt.store.account_locations(acct)[uid]
    key = f"{e.address}|{e.city}|{e.state}".lower()
    v = rt.systems["vendors"].get(key)
    if not v:
        return None
    fam = "External data"
    for f, path, val, vendor in (
        ("ppc", "$.hazard.ppc", v["hazard"]["ppc"], "PPC service (mock)"),
        ("cat_zone", "$.hazard.cat_zone", v["hazard"]["cat_zone"], "Hazard API (mock)"),
        ("wind_tier", "$.hazard.wind_tier", v["hazard"]["wind_tier"], "Hazard API (mock)"),
        ("flood_zone", "$.hazard.flood_zone", v["hazard"]["flood_zone"], "Hazard API (mock)"),
        ("eq_zone", "$.hazard.eq_zone", v["hazard"]["eq_zone"], "Hazard API (mock)"),
        ("wildfire_score", "$.hazard.wildfire_score", v["hazard"]["wildfire_score"], "Hazard API (mock)"),
        ("model_rc", "$.valuation.model_rc", v["valuation"]["model_rc"], "Replacement-cost model (mock)"),
        ("rc_per_sqft_model", "$.valuation.rc_per_sqft", v["valuation"]["rc_per_sqft"], "Replacement-cost model (mock)"),
        ("burglary_score", "$.crime.burglary_score", v["crime"]["burglary_score"], "Crime scores (mock)"),
        ("roof_condition", "$.property.roof_condition", v["property"]["roof_condition"], "Property intelligence (mock)"),
    ):
        _obs(rt, acct, "location", uid, f, val, "M", fam, vendor, date,
             {"doc_id": rt.vendor_payload_doc(acct, date), "kind": "vendor", "system": vendor, "record_id": key, "path": path}, None, 0.88,
             vendor=vendor, model="2026.2")
    return v


def ingest_imagery(rt, acct, payload, date):
    doc = rt.world_docs[payload["doc_id"]]
    rt.store.docs[doc["doc_id"]] = doc
    uid = _loc_by_address(rt, acct, payload["location_address"])
    if not uid:
        return
    e = rt.store.account_locations(acct)[uid]
    e.imagery_docs.append(doc["doc_id"])
    key = f"{e.address}|{e.city}|{e.state}".lower()
    v = rt.systems["vendors"].get(key)
    if not v:
        return
    im = next((i for i in v["imagery"] if i["doc_id"] == doc["doc_id"]), None)
    anc = {"doc_id": doc["doc_id"], "kind": "image", "text": f"Capture {im['date'] if im else date}"}
    if im and im["style"] == "roof_hail":
        _obs(rt, acct, "location", uid, "roof_condition", "Poor", "M", "External data", "Aerial imagery analytics (mock)", date, anc, doc["doc_id"], 0.81, vendor="Aerial imagery (mock)", model="roof-ai 5.1")
    if im and im["style"] == "lot_empty":
        _obs(rt, acct, "location", uid, "vacancy_indicator", True, "M", "External data", "Aerial imagery analytics (mock)", date, anc, doc["doc_id"], 0.78, vendor="Aerial imagery (mock)", model="activity-ai 2.3")
    if im and im["style"] == "yard_racks":
        _obs(rt, acct, "location", uid, "yard_change", True, "M", "External data", "Aerial imagery analytics (mock)", date, anc, doc["doc_id"], 0.8, vendor="Aerial imagery (mock)", model="change-ai 3.0")


def ingest_model3d(rt, acct, payload, date):
    doc = rt.world_docs[payload["doc_id"]]
    rt.store.docs[doc["doc_id"]] = doc
    if payload.get("scope") == "site":
        rt.site_models[acct] = doc["doc_id"]
        return
    uid = _loc_by_address(rt, acct, payload["location_address"])
    if uid:
        rt.store.account_locations(acct)[uid].buildings_model_doc = doc["doc_id"]

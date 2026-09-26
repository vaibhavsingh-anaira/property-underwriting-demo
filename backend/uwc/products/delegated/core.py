"""Delegated authority runtime: state, world build (May–July history), bordereau ingestion, daily
coverholder behaviour (referral requests, restrictions) and dated events."""
from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

from uwc.ingest.sov import map_construction

from . import baa as B
from . import bordereau as BX
from . import engine as E
from . import world as W
from .refdata import COVERHOLDERS, MONTH_LABEL, ORDER, RISK_FIELDS, PREMIUM_FIELDS, CLAIM_FIELDS

CHANNEL = "Coverholder portal (mock)"
APPROVERS = ["Priya Raman", "Daniel Okafor"]


def new_state() -> dict:
    return {"built": False, "plan": {}, "authority": {}, "zone_map": {}, "bdx": {}, "rows": {}, "row_index": {}, "claims": {}, "exposure": {},
            "opening_gwp": {}, "annual_premium": {}, "exceptions": {}, "exc_index": {}, "referrals": [], "queries": [], "ledger": [], "audits": [],
            "reports": [], "restrictions": [], "amendments": [], "timeline": {}, "seq": {}, "prevented": [], "loss_advices": {}, "layout_override": {},
            "docs": {}, "build_ms": 0, "responses": []}


def docs_dir() -> Path:
    from uwc.runtime import RUNTIME_DOCS
    p = RUNTIME_DOCS / "da"
    p.mkdir(parents=True, exist_ok=True)
    return p


def log(st, rt, ch, stage, title, detail="", actor="Control engine", kind="engine", doc_id=None):
    st["seq"]["tl"] = st["seq"].get("tl", 0) + 1
    ev = {"event_id": f"da_tl_{st['seq']['tl']:05d}", "date": rt.clock, "kind": kind, "stage": stage, "title": title, "detail": detail, "actor": actor,
          "doc_id": doc_id, "finding_ids": []}
    st["timeline"].setdefault(ch, []).append(ev)
    return ev


def register(st, rt, ch, doc_id, doc_type, title, fmt, path: Path, channel=CHANNEL, received=None, **extra) -> dict:
    doc = rt.add_runtime_doc(ch, doc_id, doc_type, title, fmt, path, channel, term=None, product="delegated", **extra)
    doc["account_name"] = COVERHOLDERS[ch]["short"] if ch in COVERHOLDERS else None
    if received:
        doc["received_at"] = received
    st["docs"].setdefault(ch, []).append(doc_id)
    return doc


# ============================================================================ authority documents
def add_authority_doc(st, rt, ch, path: Path, doc_id: str, kind: str, title: str, received: str, effective: str | None = None, number: int = 0) -> dict:
    doc = register(st, rt, ch, doc_id, "Binding authority agreement" if kind == "BAA" else "BAA endorsement", title, "pdf", path, "Carrier DA registry (mock)", received)
    parsed = B.parse(path, doc_id)
    terms = parsed["terms"]
    before, _a, _n = E.authority(st, ch, None)
    versions = st["authority"].setdefault(ch, [])
    eff = effective or terms.get("effective") or terms.get("period_start")
    v = {"version": len(versions), "doc_id": doc_id, "kind": kind, "number": terms.get("endorsement_no", number), "effective": eff, "issued": terms.get("issued") or received,
         "terms": {k: x for k, x in terms.items() if k not in ("endorsement_no", "effective", "issued")}, "anchors": parsed["anchors"],
         "changes": B.diff(before, terms) if kind != "BAA" else [], "title": title, "pages": parsed["pages"], "parsed_terms": len(parsed["anchors"])}
    versions.append(v)
    st["_auth_cache"] = {}
    rt.store.doc_method[doc_id] = B.METHOD
    _authority_obs(rt, ch, doc_id, parsed, received)
    return v


def _authority_obs(rt, ch, doc_id, parsed, date_):
    """Parsed terms recorded in the evidence ledger so the shared document viewer lists them with their anchors."""
    t = parsed["terms"]
    subj = f"{ch}:BAA {t.get('agreement_no', '')}"
    for key, a in parsed["anchors"].items():
        if not a:
            continue
        head, _, sub = key.partition(".")
        val = t.get(head)
        if isinstance(val, dict) and sub:
            val = val.get(sub if head not in ("construction",) else int(sub))
            if isinstance(val, dict):
                val = " · ".join(f"{v}" for v in val.values() if v is not None)
        elif isinstance(val, list):
            val = a.get("text")
        elif isinstance(val, float):
            val = B.pctf(val) if val < 1 else B.usd(val)
        label = B.TERM_LABEL.get(head, head.replace("_", " "))
        rt.store.add(account_id=ch, subject_type="policy", subject_id=subj, field_code=f"{label} {sub}".strip().replace(" ", "_").lower(), value=str(val),
                     obs_type="C", source_family="Coverholder contract", source_label="Binding authority agreement", recorded_at=date_, valid_from=date_,
                     anchor=a, doc_id=doc_id, confidence=0.97)


# ============================================================================ bordereau ingestion
def _cfg(ch):
    return COVERHOLDERS[ch]


def due_date(st, ch, month) -> str:
    terms, _a, _v = E.authority(st, ch, W.month_end(month))
    return (date.fromisoformat(W.month_end(month)) + timedelta(days=terms.get("bordereau_due_days") or 15)).isoformat()


def ingest_bdx(st, rt, ch, path: Path, doc_id: str, kind: str, month: str, title: str, correction: bool = False, replaces: str | None = None) -> dict:
    """Parse one received bordereau (risk / premium / claims / exposure) with the real mapper and fold it into the ledger."""
    cfg = _cfg(ch)
    doc = register(st, rt, ch, doc_id, {"risk": "Risk bordereau", "premium": "Premium bordereau", "claims": "Claims bordereau", "exposure": "Exposure return"}[kind],
                   title, path.suffix.lstrip("."), path, CHANNEL, rt.clock)
    p = BX.parse_file(path, kind, {"umr": cfg["umr"], "agreement_no": cfg["agreement"], "period_end": W.month_end(month)} if kind != "exposure" else None)
    due = due_date(st, ch, month) if kind != "exposure" else "2026-05-15"
    late = max(0, (date.fromisoformat(rt.clock) - date.fromisoformat(due)).days) if not correction else 0
    fields = BX.FIELDSETS[kind]
    b = {"doc_id": doc_id, "ch": ch, "kind": kind, "month": month, "title": title, "received": rt.clock, "due": due, "days_late": late, "sheet": p["sheet"],
         "header_row": p["header_row"], "mapping": p["mapping"], "missing": p["missing"], "missing_labels": [fields[f][0] for f in p["missing"]],
         "issues": p["issues"], "stats": p["stats"], "dq_score": p["stats"].get("dq_score", 0), "rows": len(p["rows"]), "correction": correction,
         "replaces": replaces, "superseded_by": None, "skipped": p["skipped_rows"], "last_col": p.get("last_col"), "method": p["method"]}
    st["bdx"][doc_id] = b
    rt.store.doc_method[doc_id] = p["method"]
    rt.store.doc_issues[doc_id] = [{"code": i["code"], "label": i["label"], "anchor": {"sheet": p["sheet"], "cell": i["cell"]} if i.get("cell") else None,
                                    "severity": i["severity"]} for i in p["issues"]]
    for m in p["mapping"]:
        if m["field"]:
            rt.store.add(account_id=ch, subject_type="policy", subject_id=f"{ch}:{doc_id}", field_code=f"crs_{m['field']}", value=f"'{m['header']}' → {m['label']} ({m['method']}, {m['confidence']:.2f})",
                         obs_type="N", source_family="Coverholder bordereau", source_label=title, recorded_at=rt.clock, valid_from=rt.clock,
                         anchor={"doc_id": doc_id, "kind": "xlsx", "sheet": p["sheet"], "cell": f"{m['col']}{p['header_row']}"}, doc_id=doc_id, confidence=m["confidence"])
    if replaces and replaces in st["bdx"]:
        st["bdx"][replaces]["superseded_by"] = doc_id
    new_ids = []
    if kind == "exposure":
        for r in p["rows"]:
            if r.get("county"):
                st["exposure"].setdefault(ch, {})[f"{r.get('state')}|{r['county']}"] = {"state": r.get("state"), "county": r["county"], "policies": r.get("policies") or 0,
                                                                                         "tiv": r.get("tiv") or 0.0, "doc_id": doc_id, "cell": r["_cells"].get("tiv")}
        log(st, rt, ch, "02", title, f"{len(p['rows'])} counties · in-force TIV ${sum((r.get('tiv') or 0) for r in p['rows']):,.0f}", cfg["short"], "document", doc_id)
        return b
    if kind == "claims":
        for r in p["rows"]:
            if not r.get("claim_ref") or r.get("_duplicate_of"):
                continue
            snap = {k: r.get(k) for k in CLAIM_FIELDS if k not in ("umr", "agreement_no", "reporting_period")}
            snap.update(received=rt.clock, doc_id=doc_id, anchor={"doc_id": doc_id, "kind": "xlsx", "sheet": p["sheet"], "cell": r["_cells"].get("incurred"),
                                                                  "range": f"A{r['_r']}:{p.get('last_col', 'P')}{r['_r']}"},
                        incurred=r.get("incurred") if r.get("incurred") is not None else (r.get("paid") or 0) + (r.get("reserve") or 0))
            snap["paid"] = snap.get("paid") or 0.0
            st["claims"].setdefault(ch, {}).setdefault(r["claim_ref"], {})[month] = snap
        E.evaluate_claims(st, rt, ch)
        n_ex = sum(1 for e in st["exceptions"].values() if e["ch"] == ch and e["subject_type"] == "claim" and e["status"] in E.OPEN_STATES)
        log(st, rt, ch, "08", f"{title} checked", f"{len(p['rows'])} claims · {n_ex} open claims exceptions", "Control engine", "document", doc_id)
        E.evaluate_bordereau(st, rt, doc_id)
        return b
    if kind == "premium":
        _merge_premium(st, rt, ch, month, p, doc_id, b)
        ids = [rid for rid, r in st["rows"].items() if r["ch"] == ch and r["month"] == month and (r.get("prem") or {}).get("doc_id") == doc_id]
        res = E.evaluate_rows(st, rt, ids, f"Premium bordereau {title}")
        log(st, rt, ch, "06", f"{title} reconciled", f"{len(p['rows'])} lines · commission and premium reconciled to the risk bordereau", "Control engine", "document", doc_id)
        E.evaluate_bordereau(st, rt, doc_id)
        return b
    # risk
    counts: dict = {}
    for r in p["rows"]:
        cert = r.get("certificate_ref")
        if not cert:
            continue
        txn = r.get("transaction_type") or "NEW"
        if txn == "CORRECTION" or (replaces and _find_row(st, ch, month, cert, txn)):
            rid = _apply_correction(st, rt, ch, month, r, p, doc_id, title)
            if rid:
                new_ids.append(rid)
            continue
        rmonth = rt.clock[:7] if correction and txn == "CANCELLATION" else month
        k = (ch, rmonth, cert, txn)
        counts[k] = counts.get(k, 0) + 1
        rid = f"{ch}|{rmonth}|{cert}|{txn}|{counts[k]}"
        while rid in st["rows"]:
            counts[k] += 1
            rid = f"{ch}|{rmonth}|{cert}|{txn}|{counts[k]}"
        row = _canonical(ch, rmonth, r, p, doc_id)
        row["row_id"] = rid
        if r.get("_duplicate_of"):
            row["duplicate"] = r["_duplicate_of"]
        st["rows"][rid] = row
        st["row_index"].setdefault(f"{ch}|{cert}", []).append(rid)
        if txn in ("NEW", "RENEWAL") and row.get("gross_premium"):
            st["annual_premium"][f"{ch}|{cert}"] = row["gross_premium"]
        new_ids.append(rid)
    res = E.evaluate_rows(st, rt, new_ids, f"Bordereau {title}")
    E.evaluate_bordereau(st, rt, doc_id)
    E.evaluate_zones(st, rt, ch, W.month_end(month), month)
    ms = E.month_stats(st, ch, month)
    if not correction:
        log(st, rt, ch, "04", f"{title} checked against authority", f"{ms['policies']} lines · {ms['with_exceptions']} with exceptions ({ms['exception_rate'] * 100:.1f}%) · "
            f"mapping {p['stats'].get('mapping_confidence', 0) * 100:.0f}% · DQ {p['stats'].get('dq_score', 0):.0f}" + (f" · {late} days late" if late else ""), "Control engine", "document", doc_id)
    b["result"] = res
    return b


def _canonical(ch, month, r, p, doc_id) -> dict:
    row = {k: r.get(k) for k in RISK_FIELDS if k not in ("umr", "agreement_no", "reporting_period")}
    row.update(ch=ch, month=month, doc_id=doc_id, sheet=p["sheet"], r=r["_r"], cells=dict(r["_cells"]), last_col=p.get("last_col"), version=1, versions=[doc_id])
    row["transaction_type"] = row.get("transaction_type") or "NEW"
    if not row.get("class_code") and row.get("occupancy"):
        c, conf = E.map_class(row["occupancy"])
        row["class_code"], row["class_derived"] = c, conf
    if row.get("construction"):
        iso, conf = map_construction(row["construction"])
        row["iso"], row["iso_conf"] = iso, conf
    return row


def _find_row(st, ch, month, cert, txn=None):
    for rid in reversed(st["row_index"].get(f"{ch}|{cert}", [])):
        r = st["rows"][rid]
        if (month is None or r["month"] == month) and (txn is None or r["transaction_type"] == txn) and not r.get("duplicate"):
            return rid
    return None


def _apply_correction(st, rt, ch, month, r, p, doc_id, title):
    cert = r["certificate_ref"]
    txn = r.get("transaction_type")
    rid = _find_row(st, ch, None if txn == "CORRECTION" else month, cert, None if txn == "CORRECTION" else txn)
    if not rid:
        return None
    row = st["rows"][rid]
    new = _canonical(ch, row["month"], r, p, doc_id)
    changed = [f for f in RISK_FIELDS if f not in ("umr", "agreement_no", "reporting_period", "transaction_type") and new.get(f) is not None and new.get(f) != row.get(f)]
    for f in RISK_FIELDS:
        if f in ("umr", "agreement_no", "reporting_period", "transaction_type"):
            continue
        if new.get(f) is not None:
            row[f] = new[f]
    for k in ("class_code", "class_derived", "iso", "iso_conf"):
        if new.get(k) is not None:
            row[k] = new[k]
    row.update(doc_id=doc_id, sheet=p["sheet"], r=r["_r"], cells=new["cells"], last_col=p.get("last_col"), version=row["version"] + 1)
    row["versions"].append(doc_id)
    row.setdefault("changes", []).append({"date": rt.clock, "doc_id": doc_id, "fields": changed})
    return rid


def _merge_premium(st, rt, ch, month, p, doc_id, b):
    seen = set()
    for r in p["rows"]:
        cert = r.get("certificate_ref")
        if not cert or r.get("_duplicate_of"):
            continue
        txn = r.get("transaction_type") or "NEW"
        rid = _find_row(st, ch, month, cert, txn if txn != "CORRECTION" else None)
        if not rid:
            b["issues"].append({"code": "MISSING_IN_RISK", "severity": "MEDIUM", "label": f"{cert} on the premium bordereau but not on the risk bordereau", "cell": r["_cells"].get("certificate_ref"),
                                "field": "certificate_ref", "row": r["_r"]})
            continue
        row = st["rows"][rid]
        seen.add(rid)
        row["prem"] = {"doc_id": doc_id, "sheet": p["sheet"], "r": r["_r"], "cells": dict(r["_cells"]), "last_col": p.get("last_col"),
                       **{k: r.get(k) for k in ("gross_premium", "commission_pct", "commission_amount", "taxes", "net_premium")}}
        for k in ("commission_pct", "commission_amount", "net_premium", "taxes"):
            row[k] = r.get(k)
        if r.get("gross_premium") is not None and row.get("gross_premium") is not None and abs(r["gross_premium"] - row["gross_premium"]) > 1:
            b["issues"].append({"code": "PREMIUM_MISMATCH", "severity": "MEDIUM", "label": f"{cert}: premium bordereau {r['gross_premium']:,.0f} ≠ risk bordereau {row['gross_premium']:,.0f}",
                                "cell": r["_cells"].get("gross_premium"), "field": "gross_premium", "row": r["_r"]})
    for rid, row in st["rows"].items():
        if row["ch"] == ch and row["month"] == month and rid not in seen and not row.get("prem") and not row.get("duplicate"):
            b["issues"].append({"code": "MISSING_IN_PREMIUM", "severity": "MEDIUM", "label": f"{row['certificate_ref']} on the risk bordereau has no premium line", "cell": None, "field": None, "row": None})
    rt.store.doc_issues[doc_id] = [{"code": i["code"], "label": i["label"], "anchor": {"sheet": p["sheet"], "cell": i["cell"]} if i.get("cell") else None, "severity": i["severity"]}
                                   for i in b["issues"]]


# ============================================================================ coverholder behaviour (generator side)
def _plan_row_as_engine(ch, r) -> dict:
    return {**r, "ch": ch}


def _referral(st, rt, ch, r, reasons, decided_offset=1, status="APPROVED", approved=None, requested=None, decided=None, note=None) -> dict:
    cfg = _cfg(ch)
    st["seq"]["ref_" + ch] = st["seq"].get("ref_" + ch, 0) + 1
    ref = f"NGS-R-{cfg['cert_prefix']}-{st['seq']['ref_' + ch]:04d}"
    w = date.fromisoformat(r["written_date"])
    rec = {"ref": ref, "ch": ch, "certificate_ref": r["certificate_ref"], "insured": r["insured_name"], "requested": requested or (w - timedelta(days=decided_offset + 1)).isoformat(),
           "decided": decided or (w - timedelta(days=decided_offset)).isoformat(), "status": status, "approver": APPROVERS[len(st["referrals"]) % 2] if status != "PENDING" else None,
           "reasons": reasons, "approved": approved or {"limit": r.get("limit"), "tiv": r.get("tiv"), "aop_min": r.get("aop_deductible"), "ns_min": r.get("ns_deductible_pct"),
                                                       "premium_min": r.get("gross_premium"), "class_code": r.get("class_code")},
           "note": note, "zone": r.get("_zone")}
    st["referrals"].append(rec)
    return rec


def needs_referral(st, rt, ch, r) -> list[str]:
    res = E.check_row(st, rt, _plan_row_as_engine(ch, r))
    return [c["title"] for c in res if c["result"] == "REFER"]


def behave(st, rt, ch, r):
    """What the coverholder does when it binds one planned risk: refer when its own authority check says so (clean coverholders),
    or not (injected exceptions). Zone restrictions route new business to the carrier's referral desk (mock decides)."""
    inj = r.get("_inj")
    if r["transaction_type"] == "CANCELLATION" or r.get("_declined"):
        return
    truth = st["plan"][ch]["truth"].get(r["certificate_ref"], {})
    if inj in ("pricing", "missing_ref_year", "hidden_year") and truth.get("ref"):
        rec = _referral(st, rt, ch, r, needs_referral(st, rt, ch, {**r, "referral_ref": None}) or ["Referral"])
        truth["ref_id"] = rec["ref"]
        return
    if inj == "different_terms":
        rec = _referral(st, rt, ch, r, ["TIV above the referral threshold"], approved={"limit": r["limit"], "tiv": truth["approved_tiv"], "aop_min": r["aop_deductible"],
                                                                                         "premium_min": r.get("gross_premium"), "class_code": r["class_code"]})
        r["referral_ref"] = rec["ref"]
        return
    if inj:
        return
    terms, _a, _v = E.authority(st, ch, r["written_date"])
    z = E.zone_of(st, ch, r["state"], r["county"])
    zs = ((terms.get("aggregates") or {}).get(z or "") or {}).get("status")
    if zs in ("Refer", "Stop") and r["transaction_type"] == "NEW":
        n = st["seq"].setdefault(f"zone_{ch}", 0) + 1
        st["seq"][f"zone_{ch}"] = n
        if n == 5:  # written without referral despite the restriction
            r["_inj"] = "restricted_breach"
            st["plan"][ch]["truth"][r["certificate_ref"]] = {"kind": "restricted_breach", "response": "cancel", "month": r["written_date"][:7], "cert": r["certificate_ref"],
                                                             "insured": r["insured_name"]}
            return
        ok = zs == "Refer" and r["tiv"] <= 1_800_000 and (r.get("iso") or 0) >= 3
        d = r["written_date"]
        rec = _referral(st, rt, ch, r, [f"Incremental business in {((terms.get('aggregates') or {}).get(z) or {}).get('name', z)} ({zs.lower()} restriction)"],
                        status="APPROVED" if ok else "DECLINED", requested=(date.fromisoformat(d) - timedelta(days=2)).isoformat(),
                        decided=(date.fromisoformat(d) - timedelta(days=1)).isoformat(),
                        note="Within zone headroom; masonry or better" if ok else "Declined — zone aggregate above warning level")
        if ok:
            r["referral_ref"] = rec["ref"]
        else:
            r["_declined"] = True
            st["prevented"].append({"ch": ch, "date": d, "certificate_ref": r["certificate_ref"], "insured": r["insured_name"], "tiv": r["tiv"], "zone": z, "ref": rec["ref"]})
        return
    reasons = needs_referral(st, rt, ch, r)
    if reasons:
        rec = _referral(st, rt, ch, r, reasons)
        r["referral_ref"] = rec["ref"]


# ============================================================================ files for a month
def write_month(st, rt, ch, month, layout=None, suffix="") -> list[tuple[Path, str, str, str]]:
    cfg = _cfg(ch)
    lay = layout or st["layout_override"].get(ch) or cfg["layout"]
    rows = [r for r in st["plan"][ch]["rows"][month] if not r.get("_declined")]
    d = docs_dir()
    lab = MONTH_LABEL[month]
    out = []
    base = f"da_{ch[3:]}_{month.replace('-', '')}{suffix}"
    title_band = f"{cfg['name']} · {cfg['agreement']} · reporting period {lab}"
    p = d / f"{base}_risk.xlsx"
    W.write_risk(p, cfg, month, rows, lay, "risk", title_band if lay == "variant" else None)
    out.append((p, f"{base}_risk", "risk", f"{cfg['short']} risk bordereau — {lab}" + (" (resubmitted, CRS template)" if suffix else "")))
    p = d / f"{base}_premium.xlsx"
    W.write_risk(p, cfg, month, rows, lay, "premium", title_band if lay == "variant" else None)
    out.append((p, f"{base}_premium", "premium", f"{cfg['short']} premium bordereau — {lab}" + (" (resubmitted)" if suffix else "")))
    if not suffix:
        p = d / f"{base}_claims.xlsx"
        W.write_claims(p, cfg, month, st["plan"][ch]["claims"], lay)
        out.append((p, f"{base}_claims", "claims", f"{cfg['short']} claims bordereau — {lab}"))
    return out


def receive_month(st, rt, ch, month, layout=None, suffix="", replaces=None):
    files = write_month(st, rt, ch, month, layout, suffix)
    res = {}
    for path, did, kind, title in files:
        rep = None
        if replaces:
            rep = next((x for x, b in st["bdx"].items() if b["ch"] == ch and b["month"] == month and b["kind"] == kind and not b.get("superseded_by") and x != did), None)
        res[kind] = ingest_bdx(st, rt, ch, path, did, kind, month, title, replaces=rep)
    return res


# ============================================================================ world build
HISTORY_QUERIES = [("ch_meridian", "2026-05"), ("ch_meridian", "2026-06"), ("ch_northfield", "2026-06"), ("ch_palmcoast", "2026-06"), ("ch_ridgeway", "2026-05"),
                   ("ch_sierra", "2026-05")]


def build_world(rt):
    from . import actions as A
    t0 = time.time()
    st = rt.delegated
    saved_clock = rt.clock
    d = docs_dir()
    agenda: list[tuple[str, int, object]] = []
    for ch in ORDER:
        cfg = _cfg(ch)
        plan = W.make_plan(ch)
        st["plan"][ch] = plan
        st["zone_map"][ch] = {f"{t[0]}|{t[1]}": t[5] for t in cfg["territories"]}
        limits, exposure, gwp = _calibrate(cfg, plan)
        p = d / f"da_{ch[3:]}_baa.pdf"
        B.render_baa(p, cfg, limits)
        rt.clock = "2025-12-15"
        add_authority_doc(st, rt, ch, p, f"da_{ch[3:]}_baa", "BAA", f"Binding authority agreement {cfg['agreement']}", "2025-12-15")
        log(st, rt, ch, "01", "Binding authority agreement parsed", f"{cfg['agreement']} · {st['authority'][ch][0]['parsed_terms']} terms with page anchors", "Carrier DA registry (mock)", "document", f"da_{ch[3:]}_baa")
        e = cfg["endorsement"]
        p = d / f"da_{ch[3:]}_endt1.pdf"
        kv, tables = _endorsement_content(cfg, e)
        B.render_endorsement(p, cfg, 1, e["effective"], e["issued"], e["reason"], kv, tables)
        agenda.append((e["issued"], 0, lambda ch=ch, p=p, e=e: (add_authority_doc(st, rt, ch, p, f"da_{ch[3:]}_endt1", "Endorsement", "BAA endorsement No. 1", e["issued"], e["effective"], 1),
                                                                 log(st, rt, ch, "01", "Endorsement No. 1 parsed — authority v1", "; ".join(f"{c['label']}: {c['from']} → {c['to']}" for c in st["authority"][ch][-1]["changes"]),
                                                                     "Carrier DA registry (mock)", "document", f"da_{ch[3:]}_endt1"))))
        agenda.append(("2026-05-12", 1, lambda ch=ch, exposure=exposure, gwp=gwp: _exposure(st, rt, ch, exposure, gwp)))
        for m in ("2026-05", "2026-06", "2026-07"):
            agenda.append((W.month_end(m), 2, lambda ch=ch, m=m: _prepare_month(st, rt, ch, m)))
            recv = cfg["received_day"][m]
            if recv <= "2026-08-01":
                agenda.append((recv, 3, lambda ch=ch, m=m: receive_month(st, rt, ch, m)))
        for m in ("2026-08",):
            agenda.append((W.month_end("2026-07"), 4, lambda ch=ch, m=m: _price_month(st, rt, ch, m)))
    for ch, m in HISTORY_QUERIES:
        cfg = _cfg(ch)
        q_day = (date.fromisoformat(cfg["received_day"][m]) + timedelta(days=2)).isoformat()
        agenda.append((q_day, 5, lambda ch=ch, m=m: _history_query(rt, ch, m)))
    # Sierra's large loss advice for the wildfire (the fire at Casa Robles was never advised)
    agenda.append(("2026-07-20", 6, lambda: _loss_advice(st, rt, "ch_sierra")))
    agenda.sort(key=lambda x: (x[0], x[1]))
    for day, _p, fn in agenda:
        _run_until(st, rt, day)
        rt.clock = day
        fn()
    _run_until(st, rt, "2026-08-01")
    rt.clock = saved_clock
    # dated events the demo clock will replay
    for ch in ORDER:
        cfg = _cfg(ch)
        for m in ("2026-07", "2026-08"):
            if cfg["received_day"][m] > "2026-08-01":
                schedule(rt, cfg["received_day"][m], "delegated.bordereau", ch, f"{cfg['short']} — {MONTH_LABEL[m]} bordereaux received", {"ch": ch, "month": m})
    st["built"] = True
    st["build_ms"] = int((time.time() - t0) * 1000)


def _history_query(rt, ch, m):
    from . import actions as A
    try:
        A.raise_query(rt, ch, "u_claire", month=m, history=True)
    except ValueError as e:
        import sys
        print(f"[delegated] history query skipped: {e}", file=sys.stderr)


def _run_until(st, rt, day):
    """Replay scheduled history (coverholder responses) up to a date while building."""
    pend = sorted([e for e in rt.dynamic if e["type"].startswith("delegated.") and not e.get("done") and e["date"] <= day], key=lambda e: e["date"])
    for e in pend:
        e["done"] = True
        rt.clock = e["date"]
        handle_event(rt, e)


def schedule(rt, day, typ, ch, title, payload) -> dict:
    ev = {"date": day, "type": typ, "account_id": None, "account_name": _cfg(ch)["short"], "subject_id": ch, "title": title, "payload": payload, "product": "delegated"}
    rt.dynamic.append(ev)
    return ev


def handle_event(rt, e):
    from . import actions as A
    st = rt.delegated
    t, p = e["type"], e.get("payload", {})
    if t == "delegated.bordereau":
        ch, m = p["ch"], p["month"]
        _price_month(st, rt, ch, m)
        receive_month(st, rt, ch, m)
    elif t == "delegated.response":
        A.respond(rt, p["query_id"])
    elif t == "delegated.audit":
        A.audit_report(rt, p["audit_id"])
    elif t == "delegated.ack":
        A.acknowledge(rt, p["ch"], p["what"], p.get("ref"))
    elif t == "delegated.settle":
        A.settle(rt, p["entry_id"])


def on_day(rt, ds):
    st = getattr(rt, "delegated", None)
    if not st or not st.get("built"):
        return
    for ch in ORDER:
        m = ds[:7]
        rows = st["plan"][ch]["rows"].get(m)
        if not rows or m < "2026-08":
            continue
        _price_month(st, rt, ch, m)
        for r in rows:
            if r["written_date"] == ds and not r.get("_behaved"):
                r["_behaved"] = True
                behave(st, rt, ch, r)


def _prepare_month(st, rt, ch, m):
    _price_month(st, rt, ch, m)
    for r in st["plan"][ch]["rows"][m]:
        if not r.get("_behaved"):
            r["_behaved"] = True
            rt.clock = r["written_date"]
            behave(st, rt, ch, r)


def _price_month(st, rt, ch, m):
    plan = st["plan"][ch]
    if plan.get("_priced", {}).get(m):
        return
    cfg = _cfg(ch)
    book = plan.setdefault("_book", {})

    def rated_fn(r):
        terms, _a, _v = E.authority(st, ch, r["written_date"])
        x = E.rated(terms, r)
        if x is None and r.get("tiv"):
            x = r["tiv"] / 100 * 0.5
        return x
    W.price(plan["rows"][m], cfg, rated_fn, book)
    plan.setdefault("_priced", {})[m] = True


def _calibrate(cfg, plan):
    """Opening exposure (as at 30 Apr) by county and zone limits so each zone lands on its story utilisation at the end of July."""
    zones = {z: u for z, _n, _p, u in cfg["aggregates"]}
    terr = [t for t in cfg["territories"] if t[6] != "Excluded"]
    mov = {z: 0.0 for z in zones}
    monthly = {z: 0.0 for z in zones}
    for m in ("2026-05", "2026-06", "2026-07"):
        for r in plan["rows"][m]:
            z = r["_zone"]
            if z not in zones:
                continue
            t = r["transaction_type"]
            dlt = r["tiv"] if t == "NEW" else (r["tiv"] - (r.get("prior_tiv") or r["tiv"])) if t in ("RENEWAL", "ENDORSEMENT") else -r["tiv"]
            mov[z] += dlt
            if t in ("NEW", "RENEWAL"):
                monthly[z] += r["tiv"] / 3
    exposure = []
    zone_open = {z: 0.0 for z in zones}
    wsum = {z: sum(t[7] for t in terr if t[5] == z) for z in zones}
    for t in terr:
        z = t[5]
        base = monthly.get(z, 0) * 9.0
        share = t[7] / wsum[z] if z in wsum and wsum[z] else 0
        tiv = round(base * share, -4) if z in zones else round(t[7] * 2_000_000 * 9, -4)
        if cfg.get("endorsement", {}).get("territories_add") and t[0] in {x[0] for x in cfg["endorsement"]["territories_add"]}:
            tiv = 0.0
        pol = int(tiv / 1_900_000) if tiv else 0
        exposure.append({"state": t[0], "county": t[1], "policies": pol, "tiv": tiv})
        if z in zone_open:
            zone_open[z] += tiv
    limits = {}
    for z, u in zones.items():
        lim = (zone_open[z] + mov[z]) / u if u else 1e9
        limits[z] = max(25_000_000, round(lim / 5_000_000) * 5_000_000)
    gwp = sum(r.get("tiv", 0) for m in ("2026-05",) for r in plan["rows"][m] if r["transaction_type"] in ("NEW", "RENEWAL")) * 0.0055 * 3.6
    return limits, exposure, gwp


def _exposure(st, rt, ch, exposure, gwp):
    cfg = _cfg(ch)
    p = docs_dir() / f"da_{ch[3:]}_exposure_202604.xlsx"
    W.write_exposure(p, cfg, exposure, gwp)
    st["opening_gwp"][ch] = round(gwp)
    ingest_bdx(st, rt, ch, p, f"da_{ch[3:]}_exposure_202604", "exposure", "2026-04", f"{cfg['short']} exposure return — as at 30 Apr 2026")


def _loss_advice(st, rt, ch):
    cl = next((c for c in st["plan"][ch]["claims"] if c.get("cat")), None)
    if cl:
        st["loss_advices"][f"{ch}|{cl['claim_ref']}"] = rt.clock
        from . import actions as A
        A.write_email(st, rt, ch, f"Large loss advice — {cl['claim_ref']} {cl['insured_name']}", f"{_cfg(ch)['contact']} <claims@{_cfg(ch)['domain']}>",
                      "Delegated Authority <da@northgate.example>",
                      f"Large loss advice under {_cfg(ch)['agreement']}.\n\nClaim {cl['claim_ref']} — {cl['insured_name']} (certificate {cl['certificate_ref']}).\n"
                      f"Date of loss {cl['date_of_loss']}. Cause: {cl['cause']} ({cl['cat']}). Initial reserve estimate $1,200,000.\n\nFull details to follow on the claims bordereau.",
                      "Large loss advice", inbound=True)
        log(st, rt, ch, "08", "Large loss advice received", f"{cl['claim_ref']} · {cl['cause']} · {cl['cat']}", _cfg(ch)["short"], "document")


def _endorsement_content(cfg, e):
    kv, tables = [], []
    if e.get("min_aop"):
        rows = []
        for a, b, m in e["min_aop"]:
            rows.append((B.usd(a), B.usd(b) if b else "and above", B.usd(m)))
        tables.append((B.T_MINDED, rows, [150, 150, 210]))
    if e.get("ns_min"):
        for tier, v in e["ns_min"].items():
            kv.append((f"Minimum named storm deductible ({tier})", f"{B.pctf(v)} of location TIV"))
    if e.get("commission"):
        kv.append(("Commission", f"{B.pctf(e['commission'])} of gross premium"))
    if e.get("large_loss_days"):
        kv.append(("Large loss notification period", f"{e['large_loss_days']} days from notification to the Coverholder"))
    if e.get("territories_add"):
        tables.append((B.T_TERR, list(e["territories_add"]), [60, 160, 90, 80, 120]))
    return kv, tables

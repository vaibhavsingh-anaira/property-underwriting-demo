"""Decision Assurance workflow: intake → pack → judgement → intended action → assurance → routing → human final
decision → outcome. The product logic (REAL) calls the engine; the surrounding systems are stand-ins (MOCK):
mailbox, broker (documents 3 days after a request, quote replies after 4), inspection vendor (report 7 days after an
order), policy admin (quote and binder documents, read back by the extractor) and the claims feed (outcomes).

Every function takes the date it happens on (`on`), so the simulated background book is produced by exactly the same
code the presenter drives live."""
from __future__ import annotations

import json
import random
import re
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime
from pathlib import Path

from uwc.config import resolve_doc_path
from uwc.ingest import interpret as I
from uwc.ingest import pdf_extract as PX
from uwc.refdata import CITIES, OCCUPANCY, USER_BY_ID, ZONES

from . import docs as D
from . import engine as E
from . import ingest as N
from .model import AUTH_DOC, NB_AUTHORITY, NB_DOC, RC_PER_SQFT, CONS_RC, h8, money, nid, pct, st
from .world import HEROES, HERO_IDS, background, tiv_of


def _rd() -> Path:
    from uwc.runtime import RUNTIME_DOCS
    RUNTIME_DOCS.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DOCS


def plus(d: str, n: int) -> str:
    return (date.fromisoformat(d[:10]) + timedelta(days=n)).isoformat()


def log(rt, cid: str, kind: str, stage: str, title: str, detail: str = "", actor: str = "System", doc_id: str | None = None, on: str | None = None):
    s = st(rt)
    s.seq += 1
    ev = {"event_id": f"dtl_{s.seq:06d}", "date": on or rt.clock, "kind": kind, "stage": stage, "title": title, "detail": detail, "actor": actor,
          "doc_id": doc_id, "finding_ids": []}
    s.cases[cid]["timeline"].append(ev)
    return ev


def outbox(rt, cid: str, on: str, to: str, subject: str, body: str, channel: str = "email", related: str | None = None):
    m = {"message_id": f"msg_{len(rt.outbox) + 1}", "at": on, "channel": channel, "to": to, "subject": subject, "body": body, "account_id": cid,
         "related": related, "product": "decision", "href": f"/decision/cases/{cid}"}
    rt.outbox.append(m)
    return m


def register(rt, c: dict, did: str, doc_type: str, title: str, fmt: str, path: Path, channel: str, on: str, role: str | None = None, **extra) -> dict:
    doc = rt.add_runtime_doc(c["case_id"], did, doc_type, title, fmt, path, channel, term="New business", account_name=c["insured"], received_at=on, **extra)
    c["docs"].append({"doc_id": did, "role": role, "doc_type": doc_type, "title": title, "received_at": on})
    return doc


def uname(uid: str) -> str:
    return USER_BY_ID[uid]["name"]


# ============================================================================ case creation & submission files
def new_case(cid: str, t: dict) -> dict:
    return {"case_id": cid, "scenario": t.get("scenario"), "title": t["title"], "insured": t["insured"], "short": t["short"], "broker": t["broker"],
            "contact": t["contact"], "uw": t["uw"], "state": t["state"], "segment": t["segment"], "arrive": t["arrive"], "effective": t["effective"],
            "sched_mod": t.get("sched_mod", 1.0), "truth": t, "status": "EXPECTED", "received": None, "docs": [], "files": {}, "pack": None,
            "contradictions": [], "requests": [], "overrides": {}, "actions": [], "assurances": [], "referrals": [], "conditions": [], "decision": None,
            "quote": None, "bound": None, "outcome": None, "timeline": [], "feedback": [], "kind": t.get("kind", "hero" if t.get("scenario") else "background"),
            "judged": False, "exposure_events": []}


def make_files(rt, c: dict):
    t, cid, d0 = c["truth"], c["case_id"], c["arrive"]
    rd = _rd()
    f = {}
    p = rd / f"{cid}_app.pdf"
    D.render_application(t, p, plus(d0, -3))
    f["app"] = ("ACORD 125/140 application", f"ACORD_application_{t['short'].replace(' ', '_')}.pdf", p, "ACORD application")
    p = rd / f"{cid}_sov.xlsx"
    D.render_sov(t, p, plus(d0, -5))
    f["sov"] = ("Statement of values", f"SOV_{t['short'].replace(' ', '_')}.xlsx", p, "SOV")
    valued = plus(d0, -10)
    years = t["loss_years"]
    cutoff = date.fromisoformat(valued).replace(year=date.fromisoformat(valued).year - years).isoformat()
    shown = [x for x in t["losses"] if x["dol"] >= cutoff]
    p = rd / f"{cid}_lr1.pdf"
    carrier = t["prior_carrier"] if t["prior_carrier"] != "Various (fictional)" else "Lakeshore Casualty (fictional)"
    D.render_loss_run(t, p, valued, years, shown, carrier)
    f["loss_run"] = (f"Loss run — {carrier.split(' (')[0]} ({years} years)", f"Loss_run_{years}yr.pdf", p, "Loss run")
    if t.get("inspection"):
        p = rd / f"{cid}_insp.pdf"
        D.render_inspection(t, p, t["inspection"])
        f["inspection"] = (f"Loss control inspection — {t['inspection']['date']}", "Loss_control_inspection.pdf", p, "Inspection report")
    if t.get("manuscript"):
        p = rd / f"{cid}_ms.pdf"
        D.render_manuscript(t, p, t["manuscript"], plus(d0, -2))
        f["manuscript"] = (t["manuscript"]["title"], f"{t['manuscript']['form']}.pdf", p, "Manuscript wording")
    atts = [(v[1], v[2], "application/pdf" if v[2].suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") for v in f.values()]
    p = rd / f"{cid}_email.eml"
    D.render_email(t, p, d0, f"New business submission — {t['insured']} — eff. {t['effective']}", D.submission_body(t), atts)
    f["email"] = (f"Submission — {t['insured']}", p.name, p, "Broker email")
    c["files"] = {k: (v[0], v[1], str(v[2]), v[3]) for k, v in f.items()}


# ============================================================================ Stage 01–04: receive, parse, enrich, pack
PARSERS = [("sov", N.ingest_sov), ("app", N.ingest_application), ("inspection", N.ingest_inspection), ("loss_run", N.ingest_loss_run),
           ("manuscript", N.ingest_manuscript), ("email", N.ingest_email)]


def receive(rt, cid: str, on: str) -> str:
    c = st(rt).cases[cid]
    if c["received"]:
        return "Already received"
    fs = c["files"]
    att_ids = [f"{cid}_{k}" for k in fs if k != "email"]
    ed = register(rt, c, f"{cid}_email", "Broker email", fs["email"][0], "eml", Path(fs["email"][2]), "Broker email", on, "email", attachments=att_ids)
    log(rt, cid, "document", "01", "Submission received", f"{c['broker']} · {len(att_ids)} attachment(s)", "Mailbox (mock)", ed["doc_id"], on)
    counts = {}
    for k, fn in PARSERS:
        if k not in fs:
            continue
        title, fname, path, dtype = fs[k]
        doc = ed if k == "email" else register(rt, c, f"{cid}_{k}", dtype, title, Path(path).suffix[1:], Path(path), "Broker email", on, k if k != "app" else "application")
        if k != "email":
            doc["filename"] = fname
        counts[k] = fn(rt, cid, doc, on)
    enrich(rt, cid, on)
    c["received"] = on
    c["status"] = "PREPARED"
    n = sum(1 for _ in rt.store.account_obs(cid))
    log(rt, cid, "engine", "02", "Documents parsed into the evidence ledger",
        f"{n} observations with anchors · SOV {counts.get('sov', 0)} location(s) · application {counts.get('app', 0)} fields · loss runs {counts.get('loss_run', 0)} · inspection {counts.get('inspection', 0)}",
        "Extraction", None, on)
    pack = E.build_pack(rt, cid, on)
    log(rt, cid, "engine", "03", "Carrier context applied", f"Guidelines {E.G(on)['version']} · technical {money(pack['pricing']['technical'])} ({pack['pricing']['model']}) · "
        f"{len(pack['requirements'])} authority checks", "Control engine", None, on)
    log(rt, cid, "engine", "04", "Decision pack prepared", f"Draft: {DRAFT_LABEL[pack['draft']['action']]} · {len(pack['contradictions'])} contradiction(s) · "
        f"{len(pack['missing'])} missing item(s) · {len(pack['factors'])} risk factor(s)", "Control engine", None, on)
    return (f"Submission ingested: {len(att_ids)} attachments parsed into {n} observations; pack prepared — technical {money(pack['pricing']['technical'])}, "
            f"draft {DRAFT_LABEL[pack['draft']['action']].lower()}")


DRAFT_LABEL = {"DECLINE": "Decline", "REFER_CONDITIONAL_QUOTE": "Refer / conditionally quote", "REFER": "Refer", "REQUEST_INFO": "Request information",
               "QUOTE_SUBJECT_TO": "Quote subject to conditions", "QUOTE": "Quote"}


def _jit(key: str, span: float) -> float:
    return (int(h8(key), 16) / 0xFFFFFFFF - 0.5) * span


def enrich(rt, cid: str, on: str, persist: bool = True):
    """Vendor stubs (MOCK): geocode, hazard, property intelligence, replacement cost, company data."""
    c = st(rt).cases[cid]
    t = c["truth"]
    did = f"{cid}_vendor" if persist else None
    rows = []
    for uid, e in rt.store.account_locations(cid).items():
        city = CITIES.get(e.city)
        if not city:
            continue
        lat, lon, stt, zone, wt, fz, eq, wf = city
        lat, lon = round(lat + _jit(e.address + "a", 0.08), 5), round(lon + _jit(e.address + "o", 0.08), 5)
        occ = E.location_state(rt, cid, uid).get("occupancy_class") or "warehouse"
        cons = E.location_state(rt, cid, uid).get("construction_class") or 3
        sqft = E.location_state(rt, cid, uid).get("sqft") or 0
        rc = round(sqft * RC_PER_SQFT.get(occ, 150) * CONS_RC.get(cons, 1.0), -4)
        rows.append({"address": e.address, "city": e.city, "geocode": {"lat": lat, "lon": lon, "level": "rooftop"},
                     "hazard": {"cat_zone": zone, "wind_tier": wt, "flood_zone": fz, "eq_zone": eq, "wildfire_score": wf}, "valuation": {"model_rc": rc}, "uid": uid})
    comp = {"naics": t.get("company_naics", t.get("naics")), "years_in_business": t.get("years"), "financial_stress_score": 20 + int(h8(cid), 16) % 60,
            "revenue_band": "$50M–$250M" if c["segment"] == "Middle market" else "$5M–$50M"}
    if persist:
        p = _rd() / f"{did}.json"
        D.vendor_payload(t, p, [{k: v for k, v in r.items() if k != "uid"} for r in rows], comp)
        register(rt, c, did, "Vendor payload", "Hazard, property and company data (vendor stubs)", "json", p, "Vendor (mock)", on, "vendor")
    else:
        comp["naics"] = None
    for i, r in enumerate(rows):
        uid = r["uid"]
        base = f"$.locations[{i}]"
        for f, path, v, vend in (("lat", ".geocode.lat", r["geocode"]["lat"], "Geocoder (mock)"), ("lon", ".geocode.lon", r["geocode"]["lon"], "Geocoder (mock)"),
                                 ("geocode_level", ".geocode.level", "rooftop", "Geocoder (mock)"), ("cat_zone", ".hazard.cat_zone", r["hazard"]["cat_zone"], "Hazard API (mock)"),
                                 ("wind_tier", ".hazard.wind_tier", r["hazard"]["wind_tier"], "Hazard API (mock)"), ("flood_zone", ".hazard.flood_zone", r["hazard"]["flood_zone"], "Hazard API (mock)"),
                                 ("eq_zone", ".hazard.eq_zone", r["hazard"]["eq_zone"], "Hazard API (mock)"), ("wildfire_score", ".hazard.wildfire_score", r["hazard"]["wildfire_score"], "Hazard API (mock)"),
                                 ("model_rc", ".valuation.model_rc", r["valuation"]["model_rc"], "Replacement-cost model (mock)")):
            if v is None:
                continue
            I._obs(rt, cid, "location", uid, f, v, "M", "External data", vend, on, {"doc_id": did, "kind": "vendor", "system": vend, "record_id": r["address"], "path": base + path},
                   did, 0.88, vendor=vend, model="2026.2")
        e = rt.store.account_locations(cid)[uid]
        e.lat, e.lon, e.geocode_level = r["geocode"]["lat"], r["geocode"]["lon"], "rooftop"
    cls = N.OCC_BY_NAICS.get(comp["naics"])
    if cls:
        I._obs(rt, cid, "account", cid, "operations_class", cls, "M", "External data", f"Company data (mock) → NAICS {comp['naics']}", on,
               {"doc_id": did, "kind": "vendor", "system": "Company data (mock)", "record_id": t["insured"], "path": "$.company.naics"}, did, 0.85, vendor="Company data (mock)")
    if comp["naics"]:
        I._obs(rt, cid, "account", cid, "company_naics", comp["naics"], "M", "External data", "Company data (mock)", on,
               {"doc_id": did, "kind": "vendor", "system": "Company data (mock)", "record_id": t["insured"], "path": "$.company.naics"}, did, 0.85, vendor="Company data (mock)")


# ============================================================================ Stage 05 — underwriter judgement
def resolve_contradiction(rt, cid: str, ctr_id: str, choice: str, note: str, uid: str, on: str) -> dict:
    c = st(rt).cases[cid]
    x = next(k for k in c["contradictions"] if k["contradiction_id"] == ctr_id)
    chosen = x["resolved"] if choice != "other" else x["other"]
    if choice == "other":
        o = rt.store.obs[chosen["obs_id"]]
        I._obs(rt, cid, "location", x["location_uid"], x["field"], o.value, "V", "Underwriter decision", f"Underwriter determination ({uname(uid)})", on,
               chosen["anchor"], o.doc_id, 0.99, vstatus="VERIFIED")
    x["status"] = "RESOLVED"
    x["resolution"] = {"choice": chosen["source"], "value": chosen["value"], "by": uname(uid), "at": on, "note": note}
    c["judged"] = True
    log(rt, cid, "user", "05", f"Contradiction resolved: {x['field_label']} at {x['location']}", f"{chosen['source']} ({chosen['value']}) accepted" + (f" — {note}" if note else ""), uname(uid), chosen.get("doc_id"), on)
    E.build_pack(rt, cid, on)
    x2 = next(k for k in c["contradictions"] if k["contradiction_id"] == ctr_id)
    x2["status"], x2["resolution"] = "RESOLVED", x["resolution"]
    return x2


def resolve_all(rt, cid: str, uid: str, on: str) -> int:
    c = st(rt).cases[cid]
    n = 0
    for x in list(c["contradictions"]):
        if x["status"] == "OPEN":
            resolve_contradiction(rt, cid, x["contradiction_id"], "resolved", "Resolution policy: verified evidence governs", uid, on)
            n += 1
    return n


def override(rt, cid: str, rule_id: str, subject_id: str | None, reason: str, uid: str, on: str) -> dict:
    c = st(rt).cases[cid]
    key = f"{rule_id}|{subject_id or 'case'}"
    o = {"rule_id": rule_id, "subject_id": subject_id, "reason": reason, "by": uid, "by_name": uname(uid), "at": on}
    c["overrides"][key] = o
    c["judged"] = True
    log(rt, cid, "user", "05", f"Flag overridden: {rule_id}", reason, uname(uid), None, on)
    return o


REPLY_KINDS = [("loss_runs", re.compile(r"loss run", re.I)), ("roof", re.compile(r"roof", re.I)), ("in_rack", re.compile(r"in-rack|contractor", re.I)),
               ("appraisal", re.compile(r"apprais|valuation", re.I))]


def request_info(rt, cid: str, items: list[str], uid: str, on: str, schedule: bool = True, days: int = 3) -> dict:
    c = st(rt).cases[cid]
    rid = nid(rt, "req_")
    req = {"request_id": rid, "items": items, "sent": on, "due": plus(on, days), "status": "SENT", "by": uname(uid), "docs": []}
    c["requests"].append(req)
    c["judged"] = True
    body = f"Hi {c['contact'].split()[0]},\n\nTo complete our review of {c['insured']}, please provide:\n" + "\n".join(f"- {i}" for i in items) + f"\n\nThanks,\n{uname(uid)}\nNorthgate Specialty"
    outbox(rt, cid, on, f"{c['contact']} ({c['broker']})", f"{c['insured']} — information request", body, related=rid)
    log(rt, cid, "user", "05", "Information requested from broker", "; ".join(items), uname(uid), None, on)
    if schedule:
        rt.dynamic.append({"date": plus(on, days), "type": "decision.broker_docs", "account_id": None, "case_id": cid, "account_name": c["insured"],
                           "title": f"Broker returns requested documents — {c['short']}", "payload": {"request_id": rid}})
    return req


def broker_reply(rt, cid: str, rid: str, on: str) -> str:
    """Broker stub: returns a real document for each requested item; each is parsed like any other file."""
    c = st(rt).cases[cid]
    t = c["truth"]
    req = next(r for r in c["requests"] if r["request_id"] == rid)
    produced, notes = [], []
    for item in req["items"]:
        kind = next((k for k, rx in REPLY_KINDS if rx.search(item)), "generic")
        n = len(c["docs"]) + 1
        if kind == "loss_runs":
            p = _rd() / f"{cid}_r{n}_lr.pdf"
            valued = plus(on, -2)
            D.render_loss_run(t, p, valued, 5, t["losses"] + t.get("hidden_losses", []), t["prior_carrier"] if "Various" not in t["prior_carrier"] else "Lakeshore Casualty (fictional)")
            produced.append((f"{cid}_r{n}_lr", "Loss run (5 years, all carriers)", "Loss_runs_5yr.pdf", p, "Loss run", N.ingest_loss_run))
            notes.append("five years of loss runs")
        elif kind == "roof":
            p = _rd() / f"{cid}_r{n}_roof.pdf"
            D.render_roof_schedule(t, p, on)
            produced.append((f"{cid}_r{n}_roof", "Roof replacement schedule", "Roof_replacement_schedule.pdf", p, "Broker document", N.ingest_roof_schedule))
            notes.append("roof replacement schedule")
        elif kind == "in_rack":
            p = _rd() / f"{cid}_r{n}_rack.pdf"
            D.render_contractor_letter(t, p, plus(on, -1))
            produced.append((f"{cid}_r{n}_rack", "In-rack sprinkler completion letter", "In_rack_completion_letter.pdf", p, "Broker document", N.ingest_contractor_letter))
            notes.append("in-rack sprinkler completion letter")
        else:
            p = _rd() / f"{cid}_r{n}_doc.pdf"
            from uwc.world.pdfkit import Pdf
            pdf = Pdf(p, "broker", item[:50], c["insured"])
            pdf.title(item[:60], f"Provided {on}")
            pdf.para(f"Provided by {c['broker']} in response to the carrier's request: {item}.")
            pdf.save()
            produced.append((f"{cid}_r{n}_doc", item[:60], "Document.pdf", p, "Broker document", None))
            notes.append(item.lower())
    m = EmailMessage()
    m["From"] = f"{c['contact']} <{D._email_of(c['contact'], c['broker'])}>"
    m["To"] = f"{uname(c['uw'])} <newbusiness@northgate.example>"
    m["Subject"] = f"RE: {c['insured']} — information request"
    m["Date"] = format_datetime(datetime.fromisoformat(on + "T10:05:00-04:00"))
    m.set_content(f"Hi,\n\nPlease find attached: {', '.join(notes)}.\n\nRegards,\n{c['contact']}\n{c['broker']}")
    for did, title, fname, p, dt, _ in produced:
        m.add_attachment(p.read_bytes(), maintype="application", subtype="pdf", filename=fname)
    ep = _rd() / f"{cid}_reply_{rid}.eml"
    ep.write_bytes(bytes(m))
    register(rt, c, f"{cid}_reply_{rid}", "Broker email", m["Subject"], "eml", ep, "Broker email", on, "email", attachments=[x[0] for x in produced])
    rt.email_highlights[f"{cid}_reply_{rid}"] = []
    rt.store.doc_method[f"{cid}_reply_{rid}"] = "Email parser v1 (MIME · statement patterns · attachment routing)"
    for did, title, fname, p, dt, fn in produced:
        doc = register(rt, c, did, dt, title, "pdf", p, "Broker email", on, "reply_" + dt.lower().replace(" ", "_"))
        doc["filename"] = fname
        if fn:
            fn(rt, cid, doc, on)
        req["docs"].append(did)
    req["status"] = "RECEIVED"
    log(rt, cid, "mock", "05", "Broker returned the requested documents", "; ".join(notes), "Broker (mock)", f"{cid}_reply_{rid}", on)
    E.build_pack(rt, cid, on)
    cleared = refresh_conditions(rt, cid, on, None)
    return f"Broker returned {', '.join(notes)} on {on}; parsed into evidence" + (f" · condition cleared: {cleared[0]}" if cleared else "")


def order_inspection(rt, cid: str, uid: str, on: str, scope: str, schedule: bool = True, days: int = 7) -> str:
    c = st(rt).cases[cid]
    c["judged"] = True
    c.setdefault("surveys", []).append({"ordered": on, "scope": scope, "due": plus(on, days), "status": "ORDERED"})
    log(rt, cid, "user", "05", "Verification survey ordered", scope, uname(uid), None, on)
    if schedule:
        rt.dynamic.append({"date": plus(on, days), "type": "decision.inspection", "account_id": None, "case_id": cid, "account_name": c["insured"],
                           "title": f"Loss-control verification survey — {c['short']}", "payload": {"scope": scope}})
    return f"Verification survey ordered ({scope}); report due {plus(on, days)}"


def inspection_visit(rt, cid: str, on: str, scope: str) -> str:
    """Inspection vendor stub: surveys the risk as it really is on the visit date."""
    c = st(rt).cases[cid]
    t = c["truth"]
    has_letter = any(rt.store.field_obs(uid, "in_rack_claimed") for uid in rt.store.account_locations(cid))
    old = [i for i, l in enumerate(t["locations"]) if int(on[:4]) - l["roof"] > 20]
    insp = {"date": on, "firm": "Keystone Loss Control Services (fictional)", "engineer": "L. Park, PE", "notes": {}}
    verify = {"scope": scope, "locs": sorted(set(([0] if has_letter else []) + old)) or [0], "in_rack": has_letter, "roof_condition": "Fair — 5 to 7 years remaining life",
              "roof_locs": old, "notes": {0: "In-rack sprinklers installed at two levels across racks 1–48; hydraulic calculations reviewed; storage now within the design basis."} if has_letter else {}}
    p = _rd() / f"{cid}_survey_{on.replace('-', '')}.pdf"
    D.render_inspection(t, p, insp, verify)
    doc = register(rt, c, p.stem, "Verification survey", f"Verification survey — {on}", "pdf", p, "Engineering (mock)", on, "survey")
    n = N.ingest_inspection(rt, cid, doc, on)
    for s in c.get("surveys", []):
        s["status"] = "COMPLETED"
    log(rt, cid, "mock", "05", "Verification survey report received", f"{n} verified observations", "Inspection vendor (mock)", doc["doc_id"], on)
    E.build_pack(rt, cid, on)
    cleared = refresh_conditions(rt, cid, on, None)
    return f"Engineer visited {on}; report ingested as verified evidence ({n} observations)" + (f" · cleared: {'; '.join(cleared)}" if cleared else "")


# ============================================================================ referrals & approvals
def _memo(rt, c: dict, triggers: list[dict], note: str, uid: str, a: dict | None) -> str:
    lines = [f"**Referral — {c['insured']}** (requested by {uname(uid)}, L{USER_BY_ID[uid]['authority_level']})", ""]
    if a:
        lines.append(f"Intended action: {a['type'].title()} at **{money(a['premium'])}** · AOP {money(a.get('aop'))} · limit {money(a['limit'])} · line {a['line'] * 100:.0f}%")
    p = c.get("pack") or {}
    if p:
        lines.append(f"Technical {money(p['pricing']['technical'])} · suggested {money(p['pricing']['band_low'])}–{money(p['pricing']['band_high'])} · TIV {money(p['tiv'])}")
    lines += ["", "Requires approval for:", ""] + [f"- {t['title']} ({t['subject']}): {t['observed']} — L{t['level']}" for t in triggers]
    if note:
        lines += ["", f"Underwriter note: {note}"]
    return "\n".join(lines)


def create_referral(rt, cid: str, triggers: list[dict], note: str, uid: str, on: str, kind: str, a: dict | None = None, assurance_id: str | None = None) -> dict:
    c = st(rt).cases[cid]
    lvl = max([t["level"] for t in triggers] + [2])
    rid = nid(rt, "dref_")
    ref = {"referral_id": rid, "case_id": cid, "insured": c["insured"], "kind": kind, "requested_by": uname(uid), "requested_by_id": uid, "requested_at": on,
           "required_level": lvl, "triggers": triggers, "rule_ids": sorted({t["rule_id"] for t in triggers}), "memo": _memo(rt, c, triggers, note, uid, a),
           "action": dict(a) if a else None, "assurance_id": assurance_id, "status": "PENDING", "approver": None, "approver_id": None, "approver_level": None,
           "decided_at": None, "conditions": [], "envelope": {}, "note": note, "decision_note": None}
    st(rt).referrals[rid] = ref
    c["referrals"].append(rid)
    c["status"] = "REFERRED"
    ap = E.APPROVERS.get(min(4, lvl), "u_robert")
    outbox(rt, cid, on, f"{uname(ap)} (L{lvl} referral queue)", f"Referral: {c['insured']} — L{lvl}", ref["memo"], channel="in_app", related=rid)
    log(rt, cid, "user", "08" if kind == "action" else "05", f"Referred to L{lvl}" + (" (pre-referral)" if kind == "pre" else ""), "; ".join(t["title"] for t in triggers), uname(uid), None, on)
    return ref


def prerefer(rt, cid: str, note: str, uid: str, on: str) -> dict:
    c = st(rt).cases[cid]
    lvl = USER_BY_ID[uid]["authority_level"]
    p = c["pack"]
    trig = [{"rule_id": r["rule_id"], "title": r["requirement"].split(" — ")[0], "subject": r["requirement"].split(" — ")[-1], "observed": next((f["observed"] for f in p["factors"] if f["rule_id"] == r["rule_id"]), r["requirement"]),
             "level": r["level"]} for r in p["requirements"] if r["rule_id"] and not r["within"] and r["level"] > lvl]
    if not trig:
        raise ValueError("Nothing in the pack needs a referral above the underwriter's authority")
    c["judged"] = True
    return create_referral(rt, cid, trig, note, uid, on, "pre")


COND_CLEARS = [("in-rack", "in_rack"), ("roof", "roof"), ("loss run", "loss_runs"), ("apprais", "appraisal")]


def decide_referral(rt, rid: str, decision: str, conditions: list[str] | None, envelope: dict | None, note: str, uid: str, on: str) -> dict:
    ref = st(rt).referrals[rid]
    c = st(rt).cases[ref["case_id"]]
    u = USER_BY_ID[uid]
    if ref["status"] != "PENDING":
        raise ValueError(f"Referral is already {ref['status'].lower()}")
    if u["authority_level"] < ref["required_level"]:
        raise PermissionError(f"{u['name']} (L{u['authority_level']}) cannot decide an L{ref['required_level']} referral")
    ref.update({"status": "APPROVED" if decision == "APPROVE" else "DECLINED", "approver": u["name"], "approver_id": uid, "approver_level": u["authority_level"],
                "decided_at": on, "decision_note": note})
    if decision == "APPROVE":
        env = dict(envelope or {})
        a = ref.get("action")
        if a and not env:
            env = {"min_premium": a["premium"], "min_aop": a.get("aop"), "max_line": a["line"]}
        ref["envelope"] = env
        for text in conditions or []:
            kind = "term" if re.search(r"line limited|reinstated|manuscript limited", text, re.I) else "evidence"
            clears = next((k for kw, k in COND_CLEARS if kw in text.lower()), None)
            c["conditions"].append({"cond_id": nid(rt, "cond_"), "text": text, "source": f"Referral {rid} · {u['name']}", "kind": kind, "clears": clears,
                                    "status": "OPEN" if kind == "evidence" else "TERM", "due": "Before bind", "evidence": None})
        ref["conditions"] = conditions or []
        c["status"] = "APPROVED"
    else:
        c["status"] = "DECLINED" if ref["kind"] == "action" else "IN_REVIEW"
    outbox(rt, c["case_id"], on, ref["requested_by"], f"Referral {ref['status'].lower()}: {c['insured']}", (note or "") + ("\nConditions:\n" + "\n".join(f"- {x}" for x in conditions) if conditions else ""),
           channel="in_app", related=rid)
    log(rt, c["case_id"], "user", "08" if ref["kind"] == "action" else "05", f"Referral {ref['status'].lower()} by {u['name']} (L{u['authority_level']})",
        (note or "") + (" · conditions: " + "; ".join(conditions) if conditions else "") + (f" · envelope: {_env_text(ref['envelope'])}" if ref.get("envelope") else ""), u["name"], None, on)
    _feedback_on_referral(rt, c, ref)
    return ref


def _env_text(env: dict) -> str:
    parts = []
    if env.get("min_premium"):
        parts.append(f"premium ≥ {money(env['min_premium'])}")
    if env.get("min_aop"):
        parts.append(f"AOP ≥ {money(env['min_aop'])}")
    if env.get("max_line") and env["max_line"] < 1:
        parts.append(f"line ≤ {env['max_line'] * 100:.0f}%")
    if env.get("min_ns_pct"):
        parts.append(f"named storm ≥ {env['min_ns_pct'] * 100:.0f}%")
    if "manuscript" in env:
        parts.append(f"manuscript: {env['manuscript']}")
    return ", ".join(parts)


def covering_approval(rt, c: dict, rule_id: str, level: int, a: dict) -> dict | None:
    for rid in reversed(c.get("referrals", [])):
        ref = st(rt).referrals[rid]
        if ref["status"] == "APPROVED" and rule_id in ref["rule_ids"] and (ref["approver_level"] or 0) >= level:
            ok, _ = E.envelope_ok(ref["envelope"], a)
            if ok:
                return ref
    return None


def invalid_approval(rt, c: dict, rule_id: str, a: dict) -> dict | None:
    for rid in reversed(c.get("referrals", [])):
        ref = st(rt).referrals[rid]
        if ref["status"] == "APPROVED" and rule_id in ref["rule_ids"]:
            ok, why = E.envelope_ok(ref["envelope"], a)
            if not ok:
                return {"referral_id": rid, "why": why}
    return None


def refresh_conditions(rt, cid: str, on: str, a: dict | None) -> list[str]:
    """Clear pre-bind conditions when the matching evidence is in the ledger."""
    c = st(rt).cases[cid]
    cleared = []
    locs = list(rt.store.account_locations(cid))
    for k in c.get("conditions", []):
        if k["status"] != "OPEN":
            continue
        ev = None
        if k["clears"] == "in_rack":
            letter = [o for u in locs for o in rt.store.field_obs(u, "in_rack_claimed")]
            survey = [d for d in c["docs"] if d["doc_type"] == "Verification survey"]
            if letter and survey and "survey" in k["text"].lower():
                ev = survey[-1]["doc_id"]
            elif letter and "survey" not in k["text"].lower():
                ev = letter[-1].doc_id
        elif k["clears"] == "roof":
            obs = [o for u in locs for f in ("roof_replacement_planned", "roof_condition_verified") for o in rt.store.field_obs(u, f)]
            if obs:
                ev = obs[-1].doc_id
        elif k["clears"] == "loss_runs":
            if E.loss_run_years(rt, cid) >= 5:
                ev = next((d["doc_id"] for d in reversed(c["docs"]) if d["doc_type"] == "Loss run"), None)
        if ev:
            k["status"], k["evidence"], k["cleared_at"] = "CLEARED", ev, on
            cleared.append(k["text"])
            log(rt, cid, "engine", "09", "Pre-bind condition cleared", k["text"], "Control engine", ev, on)
    return cleared


# ============================================================================ Stage 06–08 — intended action, assurance, routing
def submit_action(rt, cid: str, raw: dict, uid: str, on: str) -> dict:
    c = st(rt).cases[cid]
    a = E.normalize(rt, c, raw)
    a.update({"action_id": nid(rt, "act_"), "by": uid, "by_name": uname(uid), "at": on, "version": len(c["actions"]) + 1})
    c["actions"].append(a)
    c["judged"] = True
    log(rt, cid, "user", "06", f"Intended action v{a['version']}: {a['type'].title()} at {money(a['premium'])}",
        f"AOP {money(a['aop'])} · limit {money(a['limit'])} · line {a['line'] * 100:.0f}%" + (f" · NS {pct(a.get('ns_pct'))}" if a.get("ns_pct") else "")
        + (f" · manuscript {a['manuscript']}" if a.get("manuscript") else "") + (f" · “{a['rationale']}”" if a.get("rationale") else ""), uname(uid), None, on)
    res = E.assure(rt, cid, a, on, uid)
    res.update({"assurance_id": nid(rt, "asr_"), "action_id": a["action_id"], "action_version": a["version"], "action_type": a["type"], "premium": a["premium"]})
    c["assurances"].append(res)
    st(rt).assurance_log.append({"assurance_id": res["assurance_id"], "case_id": cid, "at": on, "verdict": res["verdict"], "action_type": a["type"], "premium": a["premium"],
                                 "deviation": res["deviation"], "fails": res["counts"]["fail"], "flags": res["counts"]["flag"], "uw": uid})
    c["status"] = {"PASS": "READY", "PASS_WITH_FLAGS": "READY", "REFER_HOLD": "HOLD"}[res["verdict"]]
    log(rt, cid, "engine", "07", "Independent assurance run", f"{res['counts']['tier1']} tier-1 and {res['counts']['tier2']} tier-2 checks · {res['counts']['fail']} fail · {res['counts']['flag']} flag", "Assurance engine", None, on)
    log(rt, cid, "engine", "08", f"Verdict: {VL[res['verdict']]}", res["summary"] + f" · decision owner {res['owner']['name']}", "Assurance engine", None, on)
    for ch in res["checks"]:
        if ch["result"] in ("FAIL", "FLAG", "CONDITION"):
            s_ = st(rt).stats.setdefault(ch["rule_id"], {"fired": set(), "accepted": 0, "rejected": 0, "confirmed": 0, "not_confirmed": 0})
            s_["fired"].add(cid)
    return res


VL = {"PASS": "Pass", "PASS_WITH_FLAGS": "Pass with flags", "REFER_HOLD": "Refer / hold"}


def latest(c: dict) -> tuple[dict | None, dict | None]:
    return (c["actions"][-1] if c["actions"] else None), (c["assurances"][-1] if c["assurances"] else None)


def route(rt, cid: str, uid: str, on: str, note: str = "") -> str:
    c = st(rt).cases[cid]
    a, res = latest(c)
    if not res:
        raise ValueError("No intended action has been assured yet")
    if res["verdict"] != "REFER_HOLD":
        return f"{VL[res['verdict']]} — {res['owner']['name']} is the decision owner; no referral needed"
    fails = [ch for ch in res["checks"] if ch["result"] == "FAIL"]
    coverable = [ch for ch in fails if next(r for r in rt.rules.values() if r.rule_id == ch["rule_id"]).scope.get("coverable", True)]
    if not coverable:
        c["status"] = "HOLD"
        return "Hold — " + "; ".join(ch["title"] for ch in fails) + ". Resolve, then resubmit."
    if any(st(rt).referrals[r]["status"] == "PENDING" for r in c["referrals"]):
        return "Referral already pending"
    trig = [{"rule_id": ch["rule_id"], "title": ch["title"], "subject": ch["subject"], "observed": ch["observed"], "level": max(2, ch["level"])} for ch in coverable]
    ref = create_referral(rt, cid, trig, note or a.get("rationale", ""), a["by"], on, "action", a, res["assurance_id"])
    return f"Referred to L{ref['required_level']} ({uname(E.APPROVERS.get(min(4, ref['required_level']), 'u_robert'))}): " + "; ".join(t["title"] for t in trig)


# ============================================================================ Stage 09 — human final decision (PAS stub)
def final_decision(rt, cid: str, decision: str, uid: str, on: str, note: str = "") -> str:
    c = st(rt).cases[cid]
    a, res = latest(c)
    u = USER_BY_ID[uid]
    if decision == "DECLINE":
        c["decision"] = {"decision": "DECLINE", "by": u["name"], "by_id": uid, "level": u["authority_level"], "at": on, "note": note, "action_id": a["action_id"] if a else None,
                         "assurance_id": res["assurance_id"] if res else None}
        c["status"] = "DECLINED"
        outbox(rt, cid, on, f"{c['contact']} ({c['broker']})", f"{c['insured']} — declination", f"Thank you for the submission. Northgate is unable to offer terms. {note}".strip())
        log(rt, cid, "user", "09", "Final decision: decline", note, u["name"], None, on)
        _feedback_commit(rt, c, res, declined=True)
        return f"Declined by {u['name']} (L{u['authority_level']}); declination sent to {c['broker']}"
    if not a or not res:
        raise ValueError("No assured intended action to commit")
    if res["verdict"] == "REFER_HOLD":
        raise PermissionError(f"Assurance verdict is refer / hold — {res['owner']['why']}. Commitment blocked.")
    if uid != res["owner"]["user_id"] and u["authority_level"] < res["owner"]["level"]:
        raise PermissionError(f"The decision owner is {res['owner']['name']} (L{res['owner']['level']})")
    pas_ref = f"NB-{c['case_id'][3:].upper()}-{on[:4]}"
    if a["type"] == "QUOTE":
        p = _rd() / f"{cid}_quote_v{a['version']}.pdf"
        subj = [{"text": k["text"], "due": "Before bind", "rule_id": k.get("rule_id"), "subject_id": k.get("subject_id")} for k in res["conditions"] if k["status"] == "OPEN"]
        D.render_pas_doc("quote", p, c["truth"], pas_ref.replace("NB-", "QTE-"), on, a["premium"], a, subj, u["name"])
        doc = register(rt, c, p.stem, "Quote", f"Quotation v{a['version']} (policy admin)", "pdf", p, "PAS (mock)", on, "quote")
        rb = readback(rt, c, doc, a)
        c["quote"] = {"doc_id": doc["doc_id"], "action_id": a["action_id"], "premium": a["premium"], "at": on, "status": "SENT", "readback": rb, "subjectivities": subj}
        c["decision"] = {"decision": "QUOTE", "by": u["name"], "by_id": uid, "level": u["authority_level"], "at": on, "note": note, "action_id": a["action_id"], "assurance_id": res["assurance_id"],
                         "verdict": res["verdict"], "conditions": [k["text"] for k in subj]}
        c["status"] = "QUOTED"
        outbox(rt, cid, on, f"{c['contact']} ({c['broker']})", f"{c['insured']} — quotation", f"Please find our quotation at {money(a['premium'])}." + ("\nSubject to:\n" + "\n".join(f"- {s['text']}" for s in subj) if subj else ""), related=doc["doc_id"])
        log(rt, cid, "user", "09", f"Final decision: quote issued at {money(a['premium'])}", f"{VL[res['verdict']]} · quote document read back: {rb['summary']}", u["name"], doc["doc_id"], on)
        rt.dynamic.append({"date": plus(on, 4), "type": "decision.broker_quote", "account_id": None, "case_id": cid, "account_name": c["insured"], "title": f"Broker responds to quote — {c['short']}", "payload": {}})
        _feedback_commit(rt, c, res)
        return f"Quote issued at {money(a['premium'])} by {u['name']}; document read back {rb['summary']}" + (f" · {len(subj)} subjectivit{'y' if len(subj) == 1 else 'ies'} before bind" if subj else "")
    # BIND
    p = _rd() / f"{cid}_binder.pdf"
    D.render_pas_doc("binder", p, c["truth"], pas_ref.replace("NB-", "BND-"), on, a["premium"], a, [], u["name"])
    doc = register(rt, c, p.stem, "Binder", "Binder (policy admin)", "pdf", p, "PAS (mock)", on, "binder")
    rb = readback(rt, c, doc, a)
    states = E.loc_states(rt, cid)
    c["bound"] = {"doc_id": doc["doc_id"], "premium": a["premium"], "at": on, "action_id": a["action_id"], "limit": a["limit"], "line": a["line"],
                  "zone_contrib": E.zone_contrib(states, a["line"]), "readback": rb, "technical": res["technical"]}
    c["decision"] = {"decision": "BIND", "by": u["name"], "by_id": uid, "level": u["authority_level"], "at": on, "note": note, "action_id": a["action_id"], "assurance_id": res["assurance_id"],
                     "verdict": res["verdict"], "conditions": []}
    c["status"] = "BOUND"
    log(rt, cid, "user", "09", f"Final decision: bound at {money(a['premium'])}", f"{VL[res['verdict']]} · binder read back: {rb['summary']}", u["name"], doc["doc_id"], on)
    out = (c["truth"].get("script") or {}).get("outcome")
    if out:
        rt.dynamic.append({"date": plus(on, out.get("days", 180)), "type": "decision.outcome", "account_id": None, "case_id": cid, "account_name": c["insured"],
                           "title": f"Outcome review — {c['short']}", "payload": {}}) if c["kind"] == "hero" else None
    _feedback_commit(rt, c, res)
    return f"Bound at {money(a['premium'])} by {u['name']} — binder read back {rb['summary']}"


def readback(rt, c: dict, doc: dict, a: dict) -> dict:
    """Read the policy-admin document back with the extractor and compare it with the committed action."""
    ex = PX.extract(resolve_doc_path(doc), I.TABLES)
    got = {}
    for kv in ex.kvs:
        if kv.label in I.CONTRACT_KV:
            f, kind = I.CONTRACT_KV[kv.label]
            got[f] = I._conv(kind, kv.value)
            I._obs(rt, c["case_id"], "policy", f"{c['case_id']}:{doc['doc_id']}", f, got[f], "C", "Carrier systems", doc["title"], doc["received_at"],
                   I.pdf_anchor(doc["doc_id"], kv.page, kv.bbox, kv.page_size, kv.value), doc["doc_id"], 0.97)
    diffs = []
    for f, want in (("premium", a["premium"]), ("aop_deductible", a.get("aop")), ("limit", a["limit"]), ("named_storm_ded_pct", a.get("ns_pct"))):
        g = got.get(f)
        if want is not None and g is not None and abs(float(g) - float(want)) > max(1.0, 0.001 * float(want)):
            diffs.append(f"{f}: document {g} vs action {want}")
    return {"fields": len(got), "diffs": diffs, "summary": "matches the committed action" if not diffs else "MISMATCH — " + "; ".join(diffs)}


def broker_quote_reply(rt, cid: str, on: str) -> str:
    c = st(rt).cases[cid]
    if not c.get("quote") or c["quote"]["status"] != "SENT":
        return "No open quote"
    acc = (c["truth"].get("script") or {}).get("broker_accepts", True)
    c["quote"]["status"] = "ACCEPTED" if acc else "NOT_TAKEN"
    c["status"] = "ACCEPTED" if acc else "LOST"
    log(rt, cid, "mock", "09", "Broker accepted the quote" if acc else "Broker placed elsewhere", "Bind instruction to follow" if acc else "Lost to competitor", "Broker (mock)", None, on)
    return "Broker accepted the quote — bind instruction received" if acc else "Broker placed the risk elsewhere"


def bind(rt, cid: str, uid: str, on: str) -> str:
    c = st(rt).cases[cid]
    if c["status"] == "BOUND":
        return "Already bound"
    if not c.get("quote") or c["quote"]["status"] != "ACCEPTED":
        raise ValueError("Bind needs a quote accepted by the broker")
    qa = next(x for x in c["actions"] if x["action_id"] == c["quote"]["action_id"])
    raw = {k: qa.get(k) for k in ("aop", "ns_pct", "ns_min", "wh_pct", "line", "limit", "manuscript", "premium")}
    raw.update(type="BIND", rationale=qa.get("rationale") or "Bind as quoted")
    res = submit_action(rt, cid, raw, uid, on)
    if res["verdict"] == "REFER_HOLD":
        return f"Bind assurance: {VL[res['verdict']]} — " + "; ".join(ch["title"] for ch in res["checks"] if ch["result"] == "FAIL")
    return f"Bind assurance: {VL[res['verdict']]} · " + final_decision(rt, cid, "COMMIT", uid, on, "Bind as quoted")


# ============================================================================ Stage 10 — outcome feedback (claims stub)
CAUSE_RULES = {"hail": ["DA.ROOF.AGE", "DA.TERMS.HAIL_DED"], "wind": ["DA.ROOF.AGE", "DA.CAT.NS_DED_FLOOR", "DA.CAT.NS_MIN", "DA.ACCUM.ZONE"],
               "hurricane": ["DA.CAT.NS_DED_FLOOR", "DA.CAT.NS_MIN", "DA.ACCUM.ZONE", "DA.ROOF.AGE"], "fire": ["DA.PROT.PARTIAL_SPRINKLER", "DA.PROT.STORAGE_ABOVE_DESIGN", "DA.APPETITE.PROHIBITED"],
               "flood": ["DA.T2.MANUSCRIPT"], "water": ["DA.T2.MANUSCRIPT"], "equipment": ["DA.DOC.LOSS_RUNS", "DA.T2.RATIONALE_EVIDENCE", "DA.PRICE.DEVIATION"],
               "theft": []}


def _stat(rt, rule_id: str) -> dict:
    return st(rt).stats.setdefault(rule_id, {"fired": set(), "accepted": 0, "rejected": 0, "confirmed": 0, "not_confirmed": 0})


def _sync_rule_stats(rt):
    for rid, s_ in st(rt).stats.items():
        rt.rule_stats[rid] = {"accepted": s_["accepted"], "rejected": s_["rejected"]}


def _feedback_on_referral(rt, c: dict, ref: dict):
    """A senior decision on a referral is a human disposition of the flags that triggered it."""
    for rule_id in ref["rule_ids"]:
        ov = any(o["rule_id"] == rule_id for o in c.get("overrides", {}).values())
        if ov and ref["status"] == "DECLINED":
            _stat(rt, rule_id)["accepted"] += 1
    _sync_rule_stats(rt)


def _feedback_commit(rt, c: dict, res: dict | None, declined: bool = False):
    if not res or c.get("feedback"):
        return
    first = next((x for x in c["assurances"] if x["verdict"] != "PASS"), res)
    fb, seen = [], set()
    for ch in first["checks"]:
        if ch["result"] not in ("FAIL", "FLAG", "CONDITION") and not ch.get("covered_by"):
            continue
        if ch["rule_id"] in seen:
            continue
        seen.add(ch["rule_id"])
        ov = bool(ch.get("overridden"))
        fb.append({"rule_id": ch["rule_id"], "tier": ch["tier"], "subject_id": ch["subject_id"], "overridden": ov, "result": ch["result"], "outcome": None})
        if not ov:
            _stat(rt, ch["rule_id"])["accepted"] += 1
    c["feedback"] = fb
    _sync_rule_stats(rt)


def record_outcome(rt, cid: str, on: str, loss: dict | None) -> str:
    c = st(rt).cases[cid]
    if c.get("outcome"):
        return "Outcome already recorded"
    uids = list(rt.store.account_locations(cid))
    detail = None
    if loss:
        uid = uids[min(loss.get("loc", 0), len(uids) - 1)]
        clm = f"NS-CLM-{int(h8(cid, on), 16) % 90000 + 10000}"
        anc = {"doc_id": None, "kind": "system", "system": "Claims (mock)", "record_id": clm}
        for f, v in (("incurred", loss["incurred"]), ("date_of_loss", loss.get("dol", on)), ("cause", loss["cause"]), ("location_uid", uid)):
            I._obs(rt, cid, "claim", f"{cid}:{clm}", f, v, "S", "Carrier systems", "Claims system (mock)", on, anc, None, 0.99)
        excluded = bool(loss.get("excluded"))
        detail = {"claim_id": clm, "cause": loss["cause"], "incurred": loss["incurred"], "location_uid": uid, "location": rt.store.account_locations(cid)[uid].label,
                  "desc": loss.get("desc", ""), "excluded": excluded, "dol": loss.get("dol", on)}
    linked_rules = set(CAUSE_RULES.get((loss or {}).get("cause", ""), [])) if loss else set()
    results = []
    for f in c.get("feedback", []):
        hit = bool(loss) and f["rule_id"] in linked_rules and (f["subject_id"] in (None, detail["location_uid"]) if detail else False)
        f["outcome"] = "CONFIRMED" if hit else "NOT_CONFIRMED"
        s_ = _stat(rt, f["rule_id"])
        s_["confirmed" if hit else "not_confirmed"] += 1
        if f["overridden"]:
            s_["accepted" if hit else "rejected"] += 1
        results.append(f)
    _sync_rule_stats(rt)
    prevented = None
    if detail and detail["excluded"]:
        prevented = detail["incurred"]
    c["outcome"] = {"at": on, "loss": detail, "clean": not loss, "flags": len(results), "confirmed": sum(1 for f in results if f["outcome"] == "CONFIRMED"),
                    "overrides": sum(1 for f in results if f["overridden"]), "prevented_loss": prevented,
                    "loss_ratio": (detail["incurred"] / c["bound"]["premium"]) if detail and c.get("bound") and not detail["excluded"] else 0.0}
    if loss:
        log(rt, cid, "mock", "10", f"Loss reported: {loss['cause']}", f"{detail['desc']} · incurred {money(loss['incurred'])}" + (" · EXCLUDED under the reinstated water exclusion" if detail["excluded"] else ""), "Claims (mock)", None, on)
    log(rt, cid, "engine", "10", "Outcome fed back", f"{c['outcome']['confirmed']} of {len(results)} flag(s) confirmed by the outcome" + (f" · {money(prevented)} loss excluded — exposure the assurance removed" if prevented else ""), "Calibration", None, on)
    conf = [f["rule_id"] for f in results if f["outcome"] == "CONFIRMED"]
    return (f"Outcome {on}: " + (f"{loss['cause']} loss {money(loss['incurred'])} at {detail['location']}" + (" — excluded under the reinstated exclusion" if detail["excluded"] else "") if loss else "clean — no losses")
            + f" · {len(conf)} of {len(results)} flag(s) confirmed" + (f" ({', '.join(conf)})" if conf else ""))


def outcome_event(rt, cid: str, on: str) -> str:
    c = st(rt).cases[cid]
    o = (c["truth"].get("script") or {}).get("outcome") or {}
    if o.get("clean") or not o:
        return record_outcome(rt, cid, on, None)
    return record_outcome(rt, cid, on, {**o, "dol": plus(on, -9)})


# ============================================================================ events (dynamic, routed by runtime._apply)
def handle_event(rt, e: dict):
    cid = e.get("case_id")
    if not cid or cid not in st(rt).cases:
        return
    t, on = e["type"], e["date"]
    if t == "decision.submission":
        receive(rt, cid, on)
    elif t == "decision.broker_docs":
        broker_reply(rt, cid, e["payload"]["request_id"], on)
    elif t == "decision.inspection":
        inspection_visit(rt, cid, on, e["payload"].get("scope", "Verification survey"))
    elif t == "decision.broker_quote":
        broker_quote_reply(rt, cid, on)
    elif t == "decision.outcome":
        outcome_event(rt, cid, on)


def run_due(rt, cid: str, until: str) -> list[str]:
    """Advance the shared clock to `until`, letting the stand-ins act (broker, inspection, claims)."""
    before = len(st(rt).cases[cid]["timeline"])
    if until > rt.clock:
        rt.advance_to(until)
    return [ev["title"] for ev in st(rt).cases[cid]["timeline"][before:]]


def next_event(rt, cid: str, types: tuple[str, ...] | None = None) -> dict | None:
    pend = sorted([x for x in rt.dynamic if not x.get("done") and x.get("case_id") == cid and (not types or x["type"] in types)], key=lambda x: x["date"])
    return pend[0] if pend else None


# ============================================================================ world build (runs once per reset)
def build_world(rt):
    s = st(rt)
    rd = _rd()
    p = rd / f"{NB_DOC}.pdf"
    D.render_standards(p)
    rt.add_runtime_doc(None, NB_DOC, "Guidelines", "Northgate New Business Underwriting Standards 2026", "pdf", p, "Reference", term=None, received_at="2026-07-01")
    p = rd / f"{AUTH_DOC}.xlsx"
    D.render_authority(p)
    rt.add_runtime_doc(None, AUTH_DOC, "Authority matrix", "New business authority matrix 2026", "xlsx", p, "Reference", term=None, received_at="2026-07-01")
    for cid, t in HEROES.items():
        c = new_case(cid, t)
        s.cases[cid] = c
        make_files(rt, c)
        rt.dynamic.append({"date": t["arrive"], "type": "decision.submission", "account_id": None, "case_id": cid, "account_name": t["insured"],
                           "title": f"New business submission — {t['short']}", "payload": {}})
    s.heroes = list(HERO_IDS)
    for cid, t in background().items():
        c = new_case(cid, t)
        s.cases[cid] = c
        make_files(rt, c)
        simulate(rt, cid, "2026-08-01")
    s.order = list(s.cases)
    s.built = True


def simulate(rt, cid: str, horizon: str):
    """Simulated underwriters work a background case with the same product code, on the case's own dates."""
    c = st(rt).cases[cid]
    t = c["truth"]
    sc = t["script"]
    rng = random.Random(int(h8(cid, "sim"), 16))
    d = t["arrive"]
    uw = t["uw"]

    def ok(day):
        return day < horizon
    if not ok(d):
        return
    receive(rt, cid, d)
    d = plus(d, 1)
    if not ok(d):
        return
    resolve_all(rt, cid, uw, d)
    for ov in sc.get("override", []):
        uids = list(rt.store.account_locations(cid))
        subj = uids[ov["loc"]] if "loc" in ov and ov["rule"] != "DA.APPETITE.PROHIBITED" else None
        if ov["rule"] in (c["pack"] or {}).get("fired_rules", []):
            override(rt, cid, ov["rule"], subj, ov["reason"], uw, d)
    if sc.get("prerefer"):
        try:
            ref = prerefer(rt, cid, sc["prerefer"]["note"], uw, d)
            decide_referral(rt, ref["referral_id"], "APPROVE", sc["prerefer"].get("conditions"), sc["prerefer"].get("envelope") or None, "Approved", sc["prerefer"]["approver"]
                            if USER_BY_ID[sc["prerefer"]["approver"]]["authority_level"] >= ref["required_level"] else E.APPROVERS[min(4, ref["required_level"])], plus(d, 1))
        except ValueError:
            pass
    d = plus(d, 2)
    if not ok(d):
        return
    if (c["pack"] or {}).get("draft", {}).get("action") == "DECLINE" and not sc.get("override"):
        final_decision(rt, cid, "DECLINE", uw, d, "Declined class under current guidelines")
        return
    res = submit_action(rt, cid, sc["action"], uw, d)
    d = plus(d, 1)
    if not ok(d):
        route(rt, cid, uw, d) if res["verdict"] == "REFER_HOLD" and plus(d, -1) < horizon else None
        return
    if res["verdict"] == "REFER_HOLD":
        if sc.get("request_after_verdict"):
            req = request_info(rt, cid, sc.get("request") or ["Five years of currently valued loss runs"], uw, d, schedule=False)
            d = plus(d, 3)
            if not ok(d):
                return
            broker_reply(rt, cid, req["request_id"], d)
            res = submit_action(rt, cid, sc.get("revise") or sc["action"], uw, d)
        else:
            msg = route(rt, cid, uw, d)
            ref_ids = [r for r in c["referrals"] if st(rt).referrals[r]["status"] == "PENDING"]
            d = plus(d, rng.randint(1, 3))
            if not ok(d) or not ref_ids:
                return
            ref = st(rt).referrals[ref_ids[-1]]
            rd_ = sc.get("referral_decision") or {}
            approver = E.APPROVERS.get(min(4, ref["required_level"]), "u_robert")
            if rd_.get("decision") == "DECLINE":
                decide_referral(rt, ref["referral_id"], "DECLINE", [], None, rd_.get("note", "Declined"), approver, d)
                final_decision(rt, cid, "DECLINE", approver, d, rd_.get("note", ""))
                return
            if sc.get("revise") and not sc.get("approve_pct"):
                decide_referral(rt, ref["referral_id"], "DECLINE", [], None, "Re-price within authority", approver, d)
                res = submit_action(rt, cid, sc["revise"], uw, d)
                if res["verdict"] == "REFER_HOLD":
                    route(rt, cid, uw, d)
                    ref2 = st(rt).referrals[c["referrals"][-1]]
                    decide_referral(rt, ref2["referral_id"], "APPROVE", [], None, "Approved as revised", E.APPROVERS.get(min(4, ref2["required_level"]), "u_robert"), d)
                    res = submit_action(rt, cid, sc["revise"], uw, d)
            else:
                decide_referral(rt, ref["referral_id"], "APPROVE", rd_.get("conditions", []), rd_.get("envelope"), "Approved", approver, d)
                res = submit_action(rt, cid, sc["action"], uw, d)
    if res["verdict"] == "REFER_HOLD":
        return
    if res["action_type"] == "BIND":
        res = submit_action(rt, cid, {**sc["action"], "type": "QUOTE"}, uw, d)
    final_decision(rt, cid, "COMMIT", uw, d)
    d = plus(d, 4)
    if not ok(d):
        return
    broker_quote_reply(rt, cid, d)
    if c["status"] != "ACCEPTED":
        return
    d = max(d, t["effective"])
    if not ok(d):
        return
    for k in c["conditions"]:
        if k["status"] == "OPEN":
            k["status"], k["evidence"], k["cleared_at"] = "CLEARED", None, d
    if any(ch["result"] == "CONDITION" for ch in c["assurances"][-1]["checks"]):
        req = request_info(rt, cid, ["Roof replacement schedule"], uw, plus(d, -4), schedule=False)
        broker_reply(rt, cid, req["request_id"], plus(d, -1))
    bind(rt, cid, uw, d)
    if c["status"] != "BOUND":
        return
    # claims stub: losses by real risk features; outcome review at 180 days
    chk = plus(d, 180)
    feats = {f["rule_id"] for f in c.get("feedback", [])}
    p_loss = 0.1 + (0.3 if "DA.ROOF.AGE" in feats else 0) + (0.25 if "DA.PROT.PARTIAL_SPRINKLER" in feats else 0) + (0.15 if "DA.PRICE.DEVIATION" in feats else 0)
    loss = None
    if rng.random() < p_loss:
        cause = "hail" if "DA.ROOF.AGE" in feats and rng.random() < 0.7 else "fire" if "DA.PROT.PARTIAL_SPRINKLER" in feats and rng.random() < 0.6 else rng.choice(["water", "wind", "theft", "fire"])
        loss = {"cause": cause, "incurred": round(rng.uniform(25_000, 420_000), -3), "loc": 0 if cause in ("hail", "fire") and feats else rng.randrange(len(t["locations"])),
                "dol": plus(d, rng.randint(20, 170)), "desc": f"{cause.title()} loss"}
    if loss and loss["dol"] < horizon:
        if chk < horizon:
            record_outcome(rt, cid, chk, loss)
        else:
            c["interim_loss"] = loss
    elif chk < horizon:
        record_outcome(rt, cid, chk, None)

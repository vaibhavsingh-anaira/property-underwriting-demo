"""Generate the demo world: truth → documents + mock-system stores + event timeline.

    uv run python -m uwc.generate

Outputs (data/world/):
  docs/…                 every document (xlsx, pdf, eml, glb, png, csv, json)
  documents.json         document registry (metadata only)
  systems.json           backing stores for the mock carrier systems (PAS, claims, engineering, vendors, rater history)
  events.json            dated event script the runtime replays
  expected.json          expected findings per account (regression only — never read by the engine)
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from dataclasses import asdict
from pathlib import Path

from uwc.config import DOCS_DIR, SEED, WORLD_DIR
from uwc.mocks import cat as catmodel
from uwc.mocks import rater
from uwc.refdata import CONSTRUCTION, OCCUPANCY
from uwc.world import render_docs as R
from uwc.world.background import build_background
from uwc.world.builders import add_days
from uwc.world.render_3d import render_site
from uwc.world.render_img import render_aerial
from uwc.world.scenarios import HEROES
from uwc.world.truth import Account, Location, QuoteTruth

CT = {"pdf": "application/pdf", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "eml": "message/rfc822",
      "glb": "model/gltf-binary", "png": "image/png", "csv": "text/csv", "json": "application/json", "yaml": "text/yaml", "geojson": "application/geo+json"}


class World:
    def __init__(self):
        self.docs: list[dict] = []
        self.events: list[dict] = []
        self.systems: dict = {"pas": {}, "claims": {}, "engineering": {}, "vendors": {}, "rater": {}, "accounts": {}}
        self.expected: dict = {}

    def doc(self, doc_id: str, account: Account | None, doc_type: str, title: str, fmt: str, received: str, channel: str,
            term: str | None = None, **extra) -> Path:
        p = DOCS_DIR / f"{doc_id}.{fmt}"
        self.docs.append({"doc_id": doc_id, "account_id": account.account_id if account else None, "account_name": account.name if account else None,
                          "doc_type": doc_type, "title": title, "filename": extra.pop("filename", f"{doc_id}.{fmt}"), "format": fmt,
                          "received_at": received, "source_channel": channel, "term": term, "path": str(p.relative_to(WORLD_DIR)), **extra})
        return p

    def event(self, date: str, etype: str, account: Account | None, title: str, **payload):
        self.events.append({"date": date, "type": etype, "account_id": account.account_id if account else None,
                            "account_name": account.name if account else None, "title": title, "payload": payload})


def exposure_from_truth(l: Location, which: str) -> dict:
    v = l.values_prior if which == "prior" else l.values_current
    occ = (l.occupancy_prior or l.occupancy) if which == "prior" else l.occupancy
    return dict(location_uid=l.key, label=l.name, lat=l.lat, lon=l.lon, zone=l.zone, state=l.state, construction=l.construction, year_built=l.year_built,
                roof_year=l.roof_year if l.status != "new" else None, stories=l.stories, wind_tier=l.wind_tier, flood_zone=l.flood_zone,
                wildfire=l.wildfire, occupancy=occ, ppc=l.ppc, sprinkler_pct=l.sprinkler_pct,
                building=v.building, contents=v.contents, stock=v.stock, bi=v.bi)


def price_account(a: Account):
    """Set expiring premium / technical at bind / account modifier (mock rater, prior model version)."""
    E0 = [exposure_from_truth(l, "prior") for l in a.locations if l.values_prior]
    t = a.terms_issued.dict()
    kw = dict(share=a.carrier_share, attach=a.layer_attach, layer_limit=a.layer_limit,
              loss_limit=a.terms_issued.limit if a.terms_issued.limit_basis == "loss_limit" else None)
    if a.sim.get("tp_e0t0_target"):
        base = rater.technical(E0, t, **kw)["technical_premium"]
        a.account_mod = round(a.sim["tp_e0t0_target"] / base, 4)
    bind = rater.technical(E0, t, account_mod=a.account_mod, version=rater.PRIOR_MODEL_VERSION, **kw)
    a.tp_at_bind = round(bind["technical_premium"], -2)
    if not a.premium_expiring:
        a.premium_expiring = round(a.tp_at_bind * a.sim.get("adequacy", 1.0), -3)
    for q in a.quotes:
        pass
    if not a.quotes:
        a.quotes = [QuoteTruth(1, add_days(a.term_start, -20), a.premium_expiring, a.terms_quoted, "ACCEPTED", approved_by=None)]
    return E0, bind


def write_cat_run(w: World, a: Account, E0: list[dict], terms: dict, date: str, short: str):
    kw = dict(share=a.carrier_share, attach=a.layer_attach, layer_limit=a.layer_limit,
              loss_limit=a.terms_issued.limit if a.terms_issued.limit_basis == "loss_limit" else None)
    # the CAT team's exposure file as coded last year (may carry coding errors)
    coded = []
    for l, e in zip([l for l in a.locations if l.values_prior], E0):
        c = dict(e)
        from uwc.ingest.sov import map_construction
        mapped = map_construction(l.sov_construction_raw or l.construction_raw)[0]
        if mapped:
            c["construction"] = mapped
        if l.cat_construction_code:
            c["construction"] = l.cat_construction_code
        coded.append(c)
    res = catmodel.run(coded, terms, **kw)
    p = w.doc(f"d_{short}_cat_exposure_2025", a, "CAT exposure file", f"CAT exposure file (OED-style) — as bound {a.term_start[:4]}", "csv", date, "CAT (mock)", term="prior")
    with p.open("w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["AccNumber", "LocNumber", "LocName", "Latitude", "Longitude", "CountryCode", "AreaCode", "OccupancyCode", "ConstructionCode",
                     "YearBuilt", "NumberOfStoreys", "RoofYear", "BuildingTIV", "ContentsTIV", "OtherTIV", "BITIV", "LocPerilsCovered", "LocDedType", "LocDed1Building"])
        for l, c in zip([l for l in a.locations if l.values_prior], coded):
            wr.writerow([a.policy_no, l.loc_no_prior, l.name, l.lat, l.lon, "US", l.state, OCCUPANCY[c["occupancy"]][3], CONSTRUCTION[c["construction"]][2],
                         c["year_built"], c["stories"], c["roof_year"] or "", round(c["building"]), round(c["contents"]), round(c["stock"]), round(c["bi"]),
                         "WTC;WSS;QEQ;ORF;BFR", "NS%" if terms.get("named_storm_ded_pct") else "AOP",
                         terms.get("named_storm_ded_pct") or terms.get("aop_deductible")])
    pe = w.doc(f"d_{short}_cat_elt_2025", a, "CAT event loss table", f"Event loss table — as bound {a.term_start[:4]}", "csv", date, "CAT (mock)", term="prior")
    with pe.open("w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["EventID", "Peril", "Region", "Rate", "MeanLoss", "SDev", "ExposureValue"])
        for r in res["elt"][:1500]:
            wr.writerow([r["EventID"], r["Peril"], r["Region"], f"{r['Rate']:.6f}", round(r["MeanLoss"]), round(r["SDev"]), round(r["ExposureValue"])])
    pj = w.doc(f"d_{short}_cat_ep_2025", a, "CAT EP curve", f"EP curves & AAL — as bound {a.term_start[:4]}", "json", date, "CAT (mock)", term="prior")
    pj.write_text(json.dumps({"account": a.name, "run_date": date, "model_version": res["model_version"], "snapshot": "AS_BOUND",
                              "basis": "Carrier share, net of deductibles", "aal_total": round(res["aal_total"]),
                              "aal_by_peril": {k: round(v) for k, v in res["aal_by_peril"].items()},
                              "location_aal": {k: round(v) for k, v in res["loc_aal"].items()},
                              "oep": [{"rp": x["rp"], "loss": round(x["loss"])} for x in res["oep"]],
                              "aep": [{"rp": x["rp"], "loss": round(x["loss"])} for x in res["aep"]]}, indent=2))
    w.event(date, "cat.run_published", a, "CAT run (as bound) published", exposure_doc=f"d_{short}_cat_exposure_2025",
            elt_doc=f"d_{short}_cat_elt_2025", ep_doc=f"d_{short}_cat_ep_2025")
    return res


def build_account(w: World, a: Account, rng: random.Random, hero: bool):
    short = a.scenario.lower() if a.scenario else a.account_id.replace("acc_", "b")
    E0, bind = price_account(a)
    ts, te = a.term_start, a.term_end

    # ---------------- PAS: account + contract records (system of record)
    w.systems["accounts"][a.account_id] = {
        "account_id": a.account_id, "name": a.name, "scenario": a.scenario, "scenario_title": a.scenario_title, "segment": a.segment,
        "occupancy_family": a.occ_family, "hq_state": a.hq_state, "broker": a.broker, "broker_contact": a.broker_contact,
        "underwriter_id": a.underwriter_id, "tenure_years": a.tenure_years, "admitted": a.admitted, "fein": a.fein,
    }
    locs_sched = []
    for l in a.locations:
        if not l.values_prior:
            continue
        locs_sched.append({"carrier_loc_id": f"{a.policy_no}-L{l.loc_no_prior}", "loc_no": l.loc_no_prior, "name": l.name, "address": l.address,
                           "city": l.city, "state": l.state, "zip": l.zip, "occupancy_code": OCCUPANCY[l.occupancy_prior or l.occupancy][1],
                           "building": l.values_prior.building, "contents": l.values_prior.contents, "stock": l.values_prior.stock,
                           "bi": l.values_prior.bi})
    w.systems["pas"][a.account_id] = {
        "policy_no": a.policy_no, "term_start": ts, "term_end": te, "carrier_share": a.carrier_share, "layer_attach": a.layer_attach,
        "layer_limit": a.layer_limit, "premium": a.premium_expiring, "admitted": a.admitted,
        "quotes": [{"version": q.version, "date": q.date, "premium": q.premium, "terms": q.terms.dict(), "status": q.status,
                    "approved_by": q.approved_by, "approval_date": q.approval_date, "approval_terms_version": q.approval_terms_version,
                    "doc_id": f"d_{short}_quote_v{q.version}"} for q in a.quotes],
        "binder": {"terms": a.terms_binder.dict(), "date": add_days(ts, -3), "premium": a.premium_expiring, "doc_id": f"d_{short}_binder"},
        "issued": {"terms": a.terms_issued.dict(), "date": add_days(ts, 12), "premium": a.premium_expiring, "doc_id": f"d_{short}_dec",
                   "locations": locs_sched},
        "endorsements": [dict(asdict(e), doc_id=f"d_{short}_{e.endt_id.lower()}") for e in a.endorsements],
        "subjectivities": [dict(s, bind_date=add_days(ts, -3)) for s in a.subjectivities],
        "brokerage_prior": a.brokerage_prior, "brokerage_proposed": a.brokerage_proposed,
    }
    w.systems["rater"][a.account_id] = {"model_at_bind": rater.PRIOR_MODEL_VERSION, "tp_at_bind": a.tp_at_bind, "account_mod": a.account_mod,
                                        "bind_components": bind["components"], "selected_premium": a.premium_expiring}
    w.systems["claims"][a.account_id] = [dict(asdict(c), location_address=(a.loc(c.location_key).address if c.location_key else None),
                                              location_city=(a.loc(c.location_key).city if c.location_key else None)) for c in a.claims]
    w.systems["engineering"][a.account_id] = {
        "recommendations": [dict(asdict(r), location_address=a.loc(r.location_key).address) for r in a.recs],
        "surveys": [],
    }
    # ---------------- vendors: keyed by address (what a geocoder / hazard / valuation / crime API would answer)
    for l in a.locations:
        key = f"{l.address}|{l.city}|{l.state}".lower()
        w.systems["vendors"][key] = {
            "geocode": {"lat": l.lat, "lon": l.lon, "level": "rooftop", "confidence": 0.97, "std_address": f"{l.address.upper()}, {l.city.upper()}, {l.state} {l.zip}"},
            "hazard": {"ppc": l.ppc, "cat_zone": l.zone, "wind_tier": l.wind_tier, "flood_zone": l.flood_zone, "eq_zone": l.eq_zone, "wildfire_score": l.wildfire,
                       "distance_to_coast_km": 4.2 if l.wind_tier == "T1" else 38 if l.wind_tier == "T2" else 250},
            "valuation": {"model_rc": l.model_rc, "rc_per_sqft": round(l.model_rc / l.sqft, 1), "confidence": 0.86, "cost_index_trend_12m": 0.052},
            "crime": {"burglary_score": l.burglary_score, "larceny_score": max(10, l.burglary_score - 8), "arson_score": 30},
            "imagery": [{"date": im["date"], "style": im["style"], "doc_id": f"d_{short}_img_{l.key.lower()}_{im['date'][:4]}"} for im in l.imagery],
            "property": {"year_built": l.year_built, "stories": l.stories, "sqft": l.sqft,
                         "roof_condition": "Poor" if any(im["style"] == "roof_hail" for im in l.imagery) else "Fair" if 2026 - l.roof_year > 15 else "Good",
                         "vacancy_indicator": any(im["style"] == "lot_empty" for im in l.imagery),
                         "yard_change": any(im["style"] == "yard_racks" for im in l.imagery)},
        }

    # ---------------- prior-term documents
    sub_date = add_days(ts, -55)
    p = w.doc(f"d_{short}_sov_2025", a, "SOV", f"Statement of values — {ts[:4]} submission", "xlsx", sub_date, "Broker email", term="prior",
              filename=f"{a.name.replace(' ', '_').replace('&', 'and')}_SOV_{ts[:4]}.xlsx")
    notes_prior = R.render_sov(a, "prior", p, sub_date)
    w.event(sub_date, "doc.received", a, "Prior-term SOV received", doc_id=f"d_{short}_sov_2025", role="sov_prior", render=notes_prior)
    if hero and a.claims:
        pl = w.doc(f"d_{short}_lossrun", a, "Loss run", "Loss run (Northgate claims) — valued 2026-06-30", "pdf", "2026-07-01", "Claims (mock)", term="current")
        R.render_loss_run(a, "2026-06-30", pl)
        w.event("2026-07-01", "doc.received", a, "Loss run valued 2026-06-30", doc_id=f"d_{short}_lossrun", role="loss_run")
    for q in a.quotes:
        pq = w.doc(f"d_{short}_quote_v{q.version}", a, "Quote", f"Quote v{q.version} — {ts[:4]} term", "pdf", q.date, "PAS (mock)", term="prior")
        R.render_quote(a, q, pq)
        w.event(q.date, "doc.received", a, f"Quote v{q.version} issued", doc_id=f"d_{short}_quote_v{q.version}", role="quote", version=q.version)
        if q.approved_by:
            w.event(q.approval_date or q.date, "pas.approval", a, f"Referral approved (quote v{q.approval_terms_version})",
                    quote_version=q.approval_terms_version, approver=q.approved_by)
    pb = w.doc(f"d_{short}_binder", a, "Binder", f"Binder — {ts[:4]} term", "pdf", add_days(ts, -3), "PAS (mock)", term="prior")
    R.render_binder(a, pb, add_days(ts, -3))
    w.event(add_days(ts, -3), "pas.bound", a, "Bound — binder issued", doc_id=f"d_{short}_binder")
    pdc = w.doc(f"d_{short}_dec", a, "Declarations", f"Policy declarations — {ts[:4]}–{te[:4]}", "pdf", add_days(ts, 12), "PAS (mock)", term="prior")
    R.render_declarations(a, pdc, add_days(ts, 12))
    w.event(add_days(ts, 12), "pas.issued", a, "Policy issued", doc_id=f"d_{short}_dec")
    for e in a.endorsements:
        pe = w.doc(f"d_{short}_{e.endt_id.lower()}", a, "Endorsement", f"Endorsement {e.endt_id} — {e.type}", "pdf", e.effective, "PAS (mock)", term="prior")
        R.render_endorsement(a, e, pe)
        w.event(e.effective, "pas.endorsement", a, f"Endorsement {e.endt_id}: {e.type}", endt_id=e.endt_id, doc_id=f"d_{short}_{e.endt_id.lower()}")
    # CAT run at bind (CAT team)
    write_cat_run(w, a, E0, a.terms_issued.dict(), add_days(ts, -10), short)
    # claims & engineering system events
    for c in a.claims:
        w.event(c.report_date or c.dol, "claims.fnol", a, f"Claim {c.claim_id} reported ({c.cause.replace('_', ' ')})", claim_id=c.claim_id)
    surveys: dict[str, list[Location]] = {}
    for l in a.locations:
        if l.engineering_date:
            surveys.setdefault(l.engineering_date, []).append(l)
    for dte in a.engineering_survey_dates:
        surveys.setdefault(dte, [l for l in a.locations if l.values_prior])
    if hero:
        for dte, ls in sorted(surveys.items()):
            did = f"d_{short}_eng_{dte.replace('-', '')}"
            pe = w.doc(did, a, "Engineering report", f"Risk engineering report — {dte}", "pdf", add_days(dte, 14), "Engineering (mock)", term="prior")
            R.render_engineering(a, dte, ls, pe)
            w.systems["engineering"][a.account_id]["surveys"].append({"survey_id": did, "date": dte, "engineer": "Elena Brooks, CSP",
                                                                      "locations": [l.address for l in ls], "doc_id": did})
            w.event(add_days(dte, 14), "doc.received", a, f"Engineering report {dte}", doc_id=did, role="engineering")
    for r in a.recs:
        w.event(r.raised, "eng.rec_raised", a, f"Recommendation {r.rec_id} raised ({r.severity.lower()})", rec_id=r.rec_id)
        if r.closed_on:
            w.event(r.closed_on, "eng.rec_status", a, f"Recommendation {r.rec_id} marked {r.status.lower().replace('_', ' ')}", rec_id=r.rec_id, status=r.status)
    # imagery (vendor)
    for l in a.locations:
        for im in l.imagery:
            did = f"d_{short}_img_{l.key.lower()}_{im['date'][:4]}"
            pi = w.doc(did, a, "Aerial imagery", f"Aerial capture — {l.name} — {im['date']}", "png", add_days(im["date"], 3), "Vendor (mock)",
                       term="current" if im["date"] >= ts else "prior", location_key=l.key)
            render_aerial(pi, im["style"], im["date"], f"{l.name} · {l.address}, {l.city} {l.state}", seed=int(hashlib.md5(did.encode()).hexdigest()[:6], 16))
            w.event(add_days(im["date"], 3), "vendor.imagery", a, f"Aerial imagery captured — {l.name}", doc_id=did, location_address=l.address)
    # 3D site model (vendor / engineering-derived)
    if hero:
        glb_locs = [l for l in a.locations if l.status != "deleted"]
        if a.site_layout == "campus" and len(glb_locs) > 1:
            did = f"d_{short}_site3d"
            pg = w.doc(did, a, "3D site model", f"3D site model — {a.name}", "glb", "2026-07-15", "Vendor (mock)", term="current")
            render_site(glb_locs, pg)
            w.event("2026-07-15", "vendor.model3d", a, "3D site model delivered", doc_id=did, scope="site")
        for l in glb_locs:
            if len(glb_locs) > 12:
                break
            did = f"d_{short}_3d_{l.key.lower()}"
            pg = w.doc(did, a, "3D site model", f"3D model — {l.name}", "glb", "2026-07-15", "Vendor (mock)", term="current", location_key=l.key)
            flags = {}
            if any(im["style"] == "roof_hail" for im in l.imagery):
                flags = {b.key: {"roof_condition": "Poor"} for b in l.buildings}
            render_site([l], pg, flags)
            w.event("2026-07-15", "vendor.model3d", a, f"3D model delivered — {l.name}", doc_id=did, location_address=l.address)

    # ---------------- renewal documents
    for e in a.emails:
        atts = []
        for key in e.attachments:
            if key == "sov_2026":
                did = f"d_{short}_sov_2026"
                ps = w.doc(did, a, "SOV", f"Statement of values — {te[:4]} renewal", "xlsx", e.date, "Broker email", term="current",
                           filename=f"{a.name.replace(' ', '_').replace('&', 'and')}_SOV_{te[:4]}_renewal.xlsx")
                notes = R.render_sov(a, "current", ps, e.date)
                atts.append((Path(ps).name.replace(did, f"{a.name.replace(' ', '_').replace('&', 'and')}_SOV_{te[:4]}"), ps, CT["xlsx"], did, "sov_current", notes))
            elif key == "alarm_certs":
                did = f"d_{short}_alarm_certs"
                pc = w.doc(did, a, "Certificate", "Burglar alarm certificates", "pdf", e.date, "Broker email", term="current")
                R.render_alarm_certs(a, pc, e.date, rng)
                atts.append(("Alarm_certificates.pdf", pc, CT["pdf"], did, "alarm_certs", None))
            elif key == "hood_certs":
                did = f"d_{short}_hood_certs"
                pc = w.doc(did, a, "Certificate", "Kitchen hood cleaning certificates", "pdf", e.date, "Broker email", term="current")
                R.render_hood_certs(a, pc, e.date)
                atts.append(("Hood_cleaning_certificates.pdf", pc, CT["pdf"], did, "hood_certs", None))
        eid = f"d_{short}_email_{e.date.replace('-', '')}"
        pm = w.doc(eid, a, "Broker email", e.subject, "eml", e.date, "Broker email", term="current", attachments=[x[3] for x in atts])
        R.render_eml(e, [(f"{x[3]}.{x[1].suffix[1:]}" if x[4] != "sov_current" else x[1].name, x[1], x[2]) for x in atts], pm)
        w.event(e.date, "doc.received", a, f"Broker email: {e.subject}", doc_id=eid, role="email", kind=e.kind,
                attachments=[{"doc_id": x[3], "role": x[4], "render": x[5]} for x in atts])
    if a.scenario == "S5":
        pa = w.doc(f"d_{short}_appraisal_2021", a, "Appraisal", "Insurable value appraisal — 2021", "pdf", add_days(ts, -55), "Broker email", term="prior")
        R.render_appraisal(a, pa, a.locations[0].last_appraisal or "2021-03-10")
        w.event(add_days(ts, -55), "doc.received", a, "Appraisal (2021) received with submission", doc_id=f"d_{short}_appraisal_2021", role="appraisal")
    if a.scenario == "S7":
        pn = w.doc(f"d_{short}_impairment", a, "Certificate", "Fire protection impairment notice", "pdf", "2026-08-06", "Engineering (mock)", term="current")
        R.render_impairment_notice(a, pn, "2026-08-06")
        w.event("2026-08-06", "eng.impairment", a, "Sprinkler impairment notice — anchor building", doc_id=f"d_{short}_impairment", location_address=a.locations[0].address, system="sprinkler")
    # simulated underwriter behaviour for background accounts (runtime interprets these)
    if not hero:
        w.event(add_days(te, -62), "sim.uw_review", a, "Underwriter reviews findings")
        w.event(add_days(te, -45), "sim.uw_quote", a, "Underwriter issues renewal quote")
        w.event(add_days(te, -32), "sim.broker_response", a, "Broker responds to quote")
        w.event(add_days(te, -12), "sim.bind", a, "Renewal bound")
        w.event(add_days(te, 9), "sim.issue", a, "Renewal policy issued")
    w.expected[a.account_id] = {"scenario": a.scenario, "expected": a.expected, "issues": a.sim.get("issues", [])}


def main():
    if WORLD_DIR.exists():
        shutil.rmtree(WORLD_DIR)
    DOCS_DIR.mkdir(parents=True)
    rng = random.Random(SEED)
    w = World()
    heroes = [f(random.Random(SEED + i)) for i, f in enumerate(HEROES)]
    bg = build_background(random.Random(SEED + 99))
    # reference documents
    pg = {}
    for ver, dte in (("2025", "2025-01-02"), ("2026", "2026-07-01")):
        p = w.doc(f"d_ref_guidelines_{ver}", None, "Guidelines", f"Northgate Commercial Property Underwriting Guidelines {ver}", "pdf", dte, "Reference")
        pg[ver] = R.render_guidelines(ver, p)
        w.event(dte, "ref.guidelines_published", None, f"Underwriting guidelines v{ver} published", version=ver, doc_id=f"d_ref_guidelines_{ver}")
    pa = w.doc("d_ref_authority", None, "Authority matrix", "Underwriting authority matrix 2026", "xlsx", "2026-07-01", "Reference")
    R.render_authority_matrix(pa)
    w.systems["guideline_pages"] = pg
    for a in heroes:
        build_account(w, a, rng, hero=True)
    for a in bg:
        build_account(w, a, rng, hero=False)
    for d in w.docs:
        f = WORLD_DIR / d["path"]
        d["size_bytes"] = f.stat().st_size
        d["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
    w.events.sort(key=lambda e: (e["date"], e["type"]))
    for i, e in enumerate(w.events):
        e["event_id"] = f"ev_{i:05d}"
    (WORLD_DIR / "documents.json").write_text(json.dumps(w.docs, indent=1))
    (WORLD_DIR / "systems.json").write_text(json.dumps(w.systems, indent=1, default=str))
    (WORLD_DIR / "events.json").write_text(json.dumps(w.events, indent=1, default=str))
    (WORLD_DIR / "expected.json").write_text(json.dumps(w.expected, indent=1))
    print(f"accounts={len(heroes) + len(bg)} docs={len(w.docs)} events={len(w.events)}")


if __name__ == "__main__":
    main()

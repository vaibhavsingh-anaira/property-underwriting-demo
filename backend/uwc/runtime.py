"""Demo runtime: replays the dated event script through the mock systems and the
real engine, and exposes the user actions (dispositions, quotes, referrals,
bind, issue, data requests) the UI calls. The clock is frozen at DEMO_START and
only moves when the presenter advances it."""
from __future__ import annotations

import hashlib
import json
import pickle
import random
import shutil
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from uwc.config import DEMO_END, DEMO_START, RUNTIME_DIR, WORLD_DIR
from uwc.engine import pricing as P
from uwc.engine.evaluate import evaluate_account
from uwc.engine.rules import load_rules
from uwc.ingest import interpret as I
from uwc import fulfilment as F
from uwc.ledger.fields import display, label as flabel
from uwc.ledger.store import Store
from uwc.refdata import AUTHORITY, USER_BY_ID, ZONES, guideline_for
from uwc import runtime_docs as RD

RUNTIME_DOCS = RUNTIME_DIR / "docs"
SNAPSHOT = RUNTIME_DIR / "reset_state.pkl"


@dataclass
class Renewal:
    pass_no: int = 0
    pass_dates: dict = field(default_factory=dict)
    status: str = "NOT_STARTED"
    findings: dict = field(default_factory=dict)
    finding_ids: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)
    recommended_actions: list = field(default_factory=list)
    quotes: list = field(default_factory=list)
    referrals: list = field(default_factory=list)
    r_bound: dict | None = None
    r_issued: dict | None = None
    rarc: dict | None = None
    working: dict | None = None
    notice: dict | None = None
    narrative: dict | None = None
    integrity: float = 100.0
    loc_ctx: dict = field(default_factory=dict)
    acct_ctx: dict = field(default_factory=dict)
    diffs: list = field(default_factory=list)
    timeline: list = field(default_factory=list)
    last_eval: str | None = None
    fast_track_confirmed: bool = False


class Runtime:
    def __init__(self):
        self.world_docs: dict[str, dict] = {d["doc_id"]: d for d in json.loads((WORLD_DIR / "documents.json").read_text())}
        self.systems: dict = json.loads((WORLD_DIR / "systems.json").read_text())
        self.events: list[dict] = json.loads((WORLD_DIR / "events.json").read_text())
        self.rules = load_rules()
        self.injections = {"issuance_error": True, "broker_counter": True}
        self._fresh()

    # ------------------------------------------------------------------ state
    def _fresh(self):
        self.store = Store()
        self.clock = "2025-01-01"
        self.applied = 0
        self.pas: dict[str, dict] = {a: {"quotes": [], "approvals": [], "endorsements_applied": [], "subjectivities": []} for a in self.systems["accounts"]}
        self.claims: dict[str, list] = {}
        self.recs: dict[str, dict] = {}
        self.renewal_sov: dict[str, str] = {}
        self.cat_runs: dict[str, list] = {}
        self.contract_stages: dict[str, dict] = {}
        self.site_models: dict[str, str] = {}
        self.email_highlights: dict[str, list] = {}
        self.ren: dict[str, Renewal] = {a: Renewal() for a in self.systems["accounts"]}
        self.zone_contrib: dict[str, dict] = {}
        self.outbox: list[dict] = []
        self.dynamic: list[dict] = []
        self.global_log: list[dict] = []
        self.review_decisions: dict[str, str] = {}
        self.rule_stats: dict[str, dict] = {}
        self.new_findings_counter = 0
        self._vendor_docs: dict[tuple, str] = {}
        self._dirty: set[str] = set()
        self._seq = 0
        self.deferred: dict[str, list] = {}
        self.ful: dict = {"licences": {}, "received": {}, "r_subj": {}, "billing": {}, "counter": 0}
        from uwc import products as PR
        for m in PR.MODULES.values():
            m.init(self)

    @property
    def clock_date(self) -> date:
        return date.fromisoformat(self.clock)

    def boot(self):
        if SNAPSHOT.exists():
            try:
                self._load_snapshot()
                return
            except Exception:  # noqa: BLE001
                pass
        self.reset(rebuild=True)

    def reset(self, rebuild: bool = False):
        if not rebuild and SNAPSHOT.exists():
            self._load_snapshot()
            return
        if RUNTIME_DOCS.exists():
            shutil.rmtree(RUNTIME_DOCS)
        RUNTIME_DOCS.mkdir(parents=True, exist_ok=True)
        self._fresh()
        self.advance_to(DEMO_START.isoformat(), settle=True)
        from uwc import products as PR
        for m in PR.MODULES.values():
            m.build_world(self)
        self._save_snapshot()

    def _save_snapshot(self):
        keep = {k: v for k, v in self.__dict__.items() if k not in ("rules",)}
        SNAPSHOT.write_bytes(pickle.dumps(keep))
        snapdocs = RUNTIME_DIR / "reset_docs"
        if snapdocs.exists():
            shutil.rmtree(snapdocs)
        shutil.copytree(RUNTIME_DOCS, snapdocs)
        self.store.persist()

    def _load_snapshot(self):
        st = pickle.loads(SNAPSHOT.read_bytes())
        self.__dict__.update(st)
        self.rules = load_rules()
        if RUNTIME_DOCS.exists():
            shutil.rmtree(RUNTIME_DOCS)
        shutil.copytree(RUNTIME_DIR / "reset_docs", RUNTIME_DOCS)

    # ------------------------------------------------------------------ helpers
    def log(self, acct: str | None, kind: str, stage: str, title: str, detail: str = "", actor: str = "System", doc_id: str | None = None,
            finding_ids: list[str] | None = None):
        self._seq += 1
        ev = {"event_id": f"tl_{self._seq:06d}", "date": self.clock, "kind": kind, "stage": stage, "title": title, "detail": detail,
              "actor": actor, "doc_id": doc_id, "finding_ids": finding_ids or []}
        if acct:
            self.ren[acct].timeline.append(ev)
        else:
            self.global_log.append(ev)
        return ev

    def account_value(self, acct: str, field: str):
        obs = self.store.field_obs(acct, field)
        return obs[-1].value if obs else None

    def zone_total(self, z: str, which: str) -> float:
        bg = ZONES[z][6]
        return bg + sum(c.get(which, {}).get(z, 0) for c in self.zone_contrib.values())

    def mark_renewal_sov(self, acct: str, doc_id: str, date_: str):
        self.renewal_sov[acct] = doc_id
        self.log(acct, "document", "01", "Renewal SOV ingested", "Locations matched across years; values and COPE captured with cell anchors", "Ingestion", doc_id)
        self._pending_pass2 = getattr(self, "_pending_pass2", set()) | {acct}

    def register_contract_doc(self, acct: str, stage: str, doc_id: str, date_: str):
        self.contract_stages.setdefault(acct, {})[stage] = doc_id and stage

    def engineering_doc(self, acct: str, doc_id: str, survey_date: str):
        self.log(acct, "document", "05", f"Engineering survey {survey_date} ingested", "Verified (V) observations recorded", "Risk engineering", doc_id)

    def add_runtime_doc(self, acct: str | None, doc_id: str, doc_type: str, title: str, fmt: str, path: Path, channel: str, term: str | None = "current", **extra) -> dict:
        reg = self.systems["accounts"].get(acct, {}) if acct else {}
        doc = {"doc_id": doc_id, "account_id": acct, "account_name": reg.get("name"), "doc_type": doc_type, "title": title, "filename": path.name,
               "format": fmt, "received_at": self.clock, "source_channel": channel, "term": term, "runtime": True, "abs_path": str(path),
               "size_bytes": path.stat().st_size, **extra}
        self.world_docs[doc_id] = doc
        self.store.docs[doc_id] = doc
        return doc

    def vendor_payload_doc(self, acct: str, date_: str) -> str:
        key = (acct, date_)
        if key in self._vendor_docs:
            return self._vendor_docs[key]
        did = f"r_{acct}_vendor_{date_.replace('-', '')}"
        p = RUNTIME_DOCS / f"{did}.json"
        payload = {}
        for uid, e in self.store.account_locations(acct).items():
            k = f"{e.address}|{e.city}|{e.state}".lower()
            if k in self.systems["vendors"]:
                payload[k] = {kk: vv for kk, vv in self.systems["vendors"][k].items() if kk != "imagery"}
        p.write_text(json.dumps({"request": {"account": acct, "date": date_, "services": ["geocode", "hazard", "valuation", "crime", "property"]},
                                 "responses": payload}, indent=2))
        self.add_runtime_doc(acct, did, "Vendor payload", f"Vendor enrichment responses — {date_}", "json", p, "Vendor (mock)")
        self._vendor_docs[key] = did
        return did

    def record_cat_run(self, acct: str, snapshot: str, exposure: list[dict], terms: dict, res: dict):
        runs = self.cat_runs.setdefault(acct, [])
        h = hashlib.md5(json.dumps([exposure, P.terms_only(terms)], sort_keys=True, default=str).encode()).hexdigest()[:8]
        prev = next((r for r in runs if r["snapshot"] == snapshot), None)
        if prev and prev.get("hash") == h:
            return
        reg = self.systems["accounts"][acct]
        base = RUNTIME_DOCS / f"r_{acct}_cat_{snapshot.lower()}_{h}"
        ex, elt, ep = RD.write_cat_files(base, reg["name"], self.pas[acct].get("policy_no", ""), snapshot, self.clock, exposure, terms, res)
        docs = {}
        for kind, path, dt, fmt in (("exposure", ex, "CAT exposure file", "csv"), ("elt", elt, "CAT event loss table", "csv"), ("ep", ep, "CAT EP curve", "json")):
            did = f"{base.name}_{kind}"
            self.add_runtime_doc(acct, did, dt, f"{dt} — {snapshot.replace('_', ' ').lower()} run {self.clock}", fmt, path, "CAT (mock)")
            docs[kind] = did
        run = {"snapshot": snapshot, "run_date": self.clock, "hash": h, "result": json.loads(ep.read_text()), "exposure_doc_id": docs["exposure"],
               "elt_doc_id": docs["elt"], "ep_doc_id": docs["ep"], "model_version": res["model_version"], "exposure": exposure}
        runs[:] = [r for r in runs if r["snapshot"] != snapshot] + [run]
        if prev is None:
            self.log(acct, "mock", "06", f"CAT model run ({snapshot.replace('_', ' ').lower()})", f"AAL ${res['aal_total']:,.0f}", "CAT (mock)", docs["ep"])

    def obs_payload(self, o, winner=None) -> dict:
        subj = o.subject_id
        ent = None
        if o.subject_type == "location":
            ent = self.store.account_locations(o.account_id).get(subj)
        sl = ent.label if ent else (self.systems["accounts"].get(subj, {}).get("name") or subj.split(":")[-1])
        a = dict(o.anchor) if o.anchor else None
        if a is not None:
            a.setdefault("doc_id", None)
        return {"obs_id": o.obs_id, "subject_type": o.subject_type if o.subject_type in ("account", "location", "building", "policy", "coverage", "claim", "recommendation") else "account",
                "subject_id": subj, "subject_label": sl, "field_code": o.field_code, "field_label": flabel(o.field_code), "value": _jsonable(o.value),
                "value_display": display(o.field_code, o.value) if not isinstance(o.value, list) else ", ".join(map(str, o.value))[:200],
                "unit": None, "obs_type": o.obs_type, "source_family": o.source_family, "source_label": o.source_label, "anchor": a,
                "vendor": o.vendor, "model_version": o.model_version, "confidence": round(o.confidence, 2), "verification_status": o.verification_status,
                "valid_from": o.valid_from, "recorded_at": o.recorded_at, "is_resolved": bool(winner and winner.obs_id == o.obs_id)}

    # ------------------------------------------------------------------ timeline
    def pending_events(self) -> list[dict]:
        ev = self.events[self.applied:]
        return sorted(ev + [x for x in self.dynamic if not x.get("done")], key=lambda e: (e["date"], e.get("type", "")))

    def advance_to(self, target: str, settle: bool = False) -> list[dict]:
        applied = []
        self.new_findings_counter = 0
        day = self.clock_date
        end = date.fromisoformat(target)
        while day <= end:
            ds = day.isoformat()
            self.clock = ds
            while self.applied < len(self.events) and self.events[self.applied]["date"] <= ds:
                e = self.events[self.applied]
                self.applied += 1
                self._apply(e)
                applied.append(e)
            for e in [x for x in self.dynamic if not x.get("done") and x["date"] <= ds]:
                e["done"] = True
                self._apply(e)
                applied.append(e)
            self._daily_triggers()
            from uwc import products as PR
            for m in PR.MODULES.values():
                m.on_day(self, ds)
            for acct in sorted(self._dirty):
                if self.ren[acct].pass_no >= 1:
                    evaluate_account(self, acct)
            self._dirty.clear()
            day += timedelta(days=1)
        self.clock = target
        if settle:
            for acct, r in self.ren.items():
                if r.pass_no >= 1:
                    evaluate_account(self, acct)
        return applied

    def _daily_triggers(self):
        ds = self.clock
        for acct, pas in self.pas.items():
            ren = self.ren[acct]
            if not pas.get("term_end"):
                continue
            t150 = (date.fromisoformat(pas["term_end"]) - timedelta(days=150)).isoformat()
            if ren.pass_no == 0 and ds >= t150 and ds < pas["term_end"]:
                self._enrich(acct)
                self.log(acct, "engine", "15", "Pass 1 · internal drift scan (T-150)", "Claims, endorsements, engineering, guidelines and pricing re-run on expiring exposure", "Control engine")
                evaluate_account(self, acct, pass_no=1)
        for acct in list(getattr(self, "_pending_pass2", set())):
            self._pending_pass2.discard(acct)
            self._enrich(acct)
            self.log(acct, "engine", "15", "Pass 2 · submission delta", "Renewal SOV compared with the bound state", "Control engine")
            evaluate_account(self, acct, pass_no=2)

    def _enrich(self, acct: str):
        for uid, e in self.store.account_locations(acct).items():
            if not self.store.field_obs(uid, "cat_zone"):
                I.enrich_location(self, acct, uid, self.clock)

    # ------------------------------------------------------------------ event handlers
    LOCATION_BOUND = ("engineering", "loss_run")

    def _apply(self, e: dict):
        t, acct, p = e["type"], e.get("account_id"), e.get("payload", {})
        if acct:
            self._dirty.add(acct)
        # evidence about locations that predates the first schedule we hold is parked, then linked when entities exist
        if acct and not self.store.account_locations(acct) and (t in ("vendor.imagery", "vendor.model3d", "cat.run_published")
                                                                 or (t == "doc.received" and p.get("role") in self.LOCATION_BOUND)):
            self.deferred.setdefault(acct, []).append(e)
            return
        if t == "doc.received":
            doc = self.world_docs[p["doc_id"]]
            role = p.get("role")
            extra = {}
            if role == "quote":
                extra = {"stage": f"quote_v{p['version']}", "term": "prior"}
            if role == "email":
                extra = {"attachments": p.get("attachments", [])}
            I.ingest_document(self, doc, role, self.clock, extra)
            if role == "sov_prior" and self.deferred.get(acct):
                now = self.clock
                for de in self.deferred.pop(acct):
                    self.clock = de["date"]
                    self._apply(de)
                self.clock = now
            if role not in ("email",):
                self.log(acct, "document", _stage_of(role), e["title"], doc["title"], doc["source_channel"], doc["doc_id"])
            else:
                self.log(acct, "document", "01", e["title"], f"{len(p.get('attachments', []))} attachment(s)", "Broker", doc["doc_id"])
        elif t == "pas.approval":
            self.pas[acct]["approvals"].append({"quote_version": p["quote_version"], "approver": p["approver"], "date": self.clock})
            self.log(acct, "system", "07", e["title"], f"Approved by {USER_BY_ID[p['approver']]['name']}", "PAS (mock)")
        elif t == "pas.bound":
            src = self.systems["pas"][acct]
            pas = self.pas[acct]
            pas.update({k: src[k] for k in ("policy_no", "term_start", "term_end", "carrier_share", "layer_attach", "layer_limit", "premium", "admitted",
                                             "brokerage_prior", "brokerage_proposed")})
            pas["quotes"] = src["quotes"]
            pas["bind_date"] = self.clock
            pas["subjectivities"] = [dict(s) for s in src["subjectivities"]]
            acc = next((q for q in src["quotes"] if q["status"] == "ACCEPTED"), None)
            if acc:
                self.contract_stages.setdefault(acct, {})["quote_accepted"] = f"quote_v{acc['version']}"
            I.ingest_document(self, self.world_docs[p["doc_id"]], "binder", self.clock, {"stage": "binder", "term": "prior"})
            self.log(acct, "system", "10", "Bound", f"Premium ${src['premium']:,.0f}", "PAS (mock)", p["doc_id"])
        elif t == "pas.issued":
            src = self.systems["pas"][acct]
            I.ingest_document(self, self.world_docs[p["doc_id"]], "policy", self.clock, {"stage": "policy", "term": "prior"})
            for row in src["issued"]["locations"]:
                uid = I._loc_by_address(self, acct, row["address"])
                if uid:
                    self.store.account_locations(acct)[uid].carrier_loc_id = row["carrier_loc_id"]
                    I._obs(self, acct, "location", uid, "carrier_loc_id", row["carrier_loc_id"], "S", "Carrier systems", "PAS schedule (mock)", self.clock,
                           {"doc_id": None, "kind": "system", "system": "PAS (mock)", "record_id": row["carrier_loc_id"]})
            self.log(acct, "system", "11", "Policy issued", src["policy_no"], "PAS (mock)", p["doc_id"])
        elif t == "pas.endorsement":
            src = next(x for x in self.systems["pas"][acct]["endorsements"] if x["endt_id"] == p["endt_id"])
            I.ingest_document(self, self.world_docs[p["doc_id"]], "endorsement", self.clock, {"stage": f"endt_{p['endt_id']}"})
            locs = list(self.store.account_locations(acct).values())
            for k, v in src.get("changes", {}).items():
                if k == "vacancy_pct" and locs:
                    uid = locs[0].location_uid
                    anc = {"doc_id": p["doc_id"], "kind": "system", "system": "PAS (mock)", "record_id": src["endt_id"], "path": "$.changes.vacancy_pct"}
                    I._obs(self, acct, "location", uid, "vacancy_pct", v, "S", "Carrier systems", f"Endorsement {src['endt_id']}", self.clock, anc, p["doc_id"], 0.99, valid_from=src["effective"])
                    I._obs(self, acct, "location", uid, "vacancy_since", src["effective"], "S", "Carrier systems", f"Endorsement {src['endt_id']}", self.clock, anc, p["doc_id"], 0.99)
            self.pas[acct]["endorsements_applied"].append(src)
            self.log(acct, "system", "12", e["title"], src["description"], "PAS (mock)", p["doc_id"])
            if self.ren[acct].pass_no == 0:
                self._event_driven(acct, "Endorsement changed exposure")
        elif t == "claims.fnol":
            c = next(x for x in self.systems["claims"][acct] if x["claim_id"] == p["claim_id"])
            uid = I._loc_by_address(self, acct, c["location_address"]) if c.get("location_address") else None
            rec = dict(c, location_uid=uid)
            self.claims.setdefault(acct, []).append(rec)
            I._obs(self, acct, "claim", f"{acct}:{c['claim_id']}", "incurred", c["paid"] + c["reserve"], "S", "Carrier systems", "Claims system (mock)", self.clock,
                   {"doc_id": None, "kind": "system", "system": "Claims (mock)", "record_id": c["claim_id"]}, None, 0.99)
            self.log(acct, "system", "13", e["title"], f"{c['description']} · incurred ${c['paid'] + c['reserve']:,.0f}", "Claims (mock)")
            if c["paid"] + c["reserve"] >= 500_000 and self.ren[acct].pass_no == 0:
                self._event_driven(acct, "Large loss reported")
        elif t == "eng.rec_raised":
            r = next(x for x in self.systems["engineering"][acct]["recommendations"] if x["rec_id"] == p["rec_id"])
            uid = I._loc_by_address(self, acct, r["location_address"])
            status = "OPEN" if r.get("closed_on") else r["status"]
            self.recs.setdefault(acct, {})[r["rec_id"]] = {"rec_id": r["rec_id"], "location_uid": uid, "location_address": r["location_address"], "raised": r["raised"], "category": r["category"],
                                                           "description": r["description"], "severity": r["severity"], "due": r["due"], "status": status,
                                                           "bind_condition": r["bind_condition"], "completion_evidence": r["completion_evidence"] if status != "OPEN" else None,
                                                           "closed_on": None}
            self.log(acct, "system", "05", e["title"], r["description"], "Engineering (mock)")
        elif t == "eng.rec_status":
            r = next(x for x in self.systems["engineering"][acct]["recommendations"] if x["rec_id"] == p["rec_id"])
            rec = self.recs[acct][p["rec_id"]]
            rec["status"] = p["status"]
            rec["closed_on"] = self.clock
            rec["completion_evidence"] = r.get("completion_evidence")
            self.log(acct, "system", "12", e["title"], "No completion evidence attached" if not r.get("completion_evidence") else r["completion_evidence"], "Engineering (mock)")
        elif t == "eng.impairment":
            I.ingest_document(self, self.world_docs[p["doc_id"]], "impairment", self.clock)
            self.log(acct, "system", "12", e["title"], "Impairment notice ingested → event-driven re-evaluation", "Engineering (mock)", p["doc_id"])
            self._event_driven(acct, "Protection impairment")
        elif t == "vendor.imagery":
            I.ingest_imagery(self, acct, p, self.clock)
            self.log(acct, "mock", "04", e["title"], "Imagery analytics recorded as model-derived (M) observations", "Vendor (mock)", p["doc_id"])
        elif t == "vendor.model3d":
            I.ingest_model3d(self, acct, p, self.clock)
        elif t == "cat.run_published":
            I.ingest_cat_run(self, acct, p, self.clock)
            self.log(acct, "mock", "06", e["title"], "Model input coding captured for reconciliation", "CAT (mock)", p["ep_doc"])
        elif t == "ref.guidelines_published":
            self.store.docs[p["doc_id"]] = self.world_docs[p["doc_id"]]
            if p["version"] == "2026":
                self.store.docs["d_ref_authority"] = self.world_docs["d_ref_authority"]
            self.log(None, "system", "03", e["title"], "Rule library re-evaluated against the book", "Rule studio")
            for a, r in self.ren.items():
                if r.pass_no >= 1:
                    self._dirty.add(a)
        elif t.startswith("sim."):
            self._sim(t, acct)
        elif t == "broker.reply":
            self._broker_reply(e)
        elif "." in t and t.split(".", 1)[0] in ("decision", "delegated"):
            from uwc import products as PR
            PR.get(t.split(".", 1)[0]).handle_event(self, e)
        elif t == "broker.docs":
            F.handle_broker_docs(self, e)
            evaluate_account(self, acct)
        elif t == "eng.visit":
            F.handle_eng_visit(self, e)
            evaluate_account(self, acct)

    def _event_driven(self, acct: str, why: str):
        self._enrich(acct)
        self.log(acct, "engine", "12", f"Event-driven re-evaluation: {why}", "In-force monitoring outside the renewal window", "Control engine")
        evaluate_account(self, acct, pass_no=1)

    # ------------------------------------------------------------------ user actions
    def user(self, uid: str) -> dict:
        return USER_BY_ID.get(uid) or USER_BY_ID["u_maya"]

    def disposition(self, fid: str, decision: str, reason: str, note: str, uid: str) -> dict:
        f = self.find_finding(fid)
        acct = f["account_id"]
        f["status"] = {"ACCEPT": "ACCEPTED", "REJECT": "REJECTED", "DEFER": "DEFERRED"}[decision]
        f["disposition"] = {"decision": decision, "reason_code": reason, "note": note, "actor": self.user(uid)["name"], "at": self.clock}
        st = self.rule_stats.setdefault(f["rule_id"], {"accepted": 0, "rejected": 0})
        st["accepted" if decision == "ACCEPT" else "rejected" if decision == "REJECT" else "accepted"] += 0 if decision == "DEFER" else 1
        ren = self.ren[acct]
        if ren.status in ("ACTION_REQUIRED", "FAST_TRACK"):
            ren.status = "IN_REVIEW"
        self.log(acct, "user", "05", f"Finding {decision.lower()}ed: {f['title']}", f"Reason: {reason.replace('_', ' ')}" + (f" — {note}" if note else ""), self.user(uid)["name"], finding_ids=[fid])
        evaluate_account(self, acct)
        return f

    def find_finding(self, fid: str) -> dict:
        for r in self.ren.values():
            if fid in r.findings:
                return r.findings[fid]
        raise KeyError(fid)

    def whatif(self, acct: str, premium: float, terms: dict, brokerage: float | None = None) -> dict:
        from uwc.engine.views import snapshots
        from uwc.engine.evaluate import contract_views
        snaps = snapshots(self, acct)
        cv = contract_views(self, acct)
        exp = dict(cv.get("endorsed") or cv.get("policy") or {})
        T1 = {**exp, **{k: v for k, v in (self.ren[acct].working or {}).get("terms", {}).items()}, **terms}
        r = P.compute(self, acct, snaps["E0"], snaps["E1"], exp, T1, premium)
        r.pop("_runs")
        if brokerage is not None:
            b0 = self.pas[acct].get("brokerage_prior", 0.15)
            r["net"] = {"brokerage_expiring": b0, "brokerage_proposed": brokerage, "rarc_net": (premium * (1 - brokerage)) / (r["expected_premium"] * (1 - b0)) - 1}
        ren = self.ren[acct]
        levels = [(f["rule"].referral_level, f["title"]) for f in []]
        rule_levels = []
        for f in ren.findings.values():
            rule = self.rules.get(f["rule_id"])
            if f["status"] in ("OPEN", "ACCEPTED") and rule and rule.referral_level and f["family"] not in ("pricing", "cat_terms"):
                rule_levels.append((rule.referral_level, f"{f['title']} → L{rule.referral_level}"))
        g = guideline_for(self.clock_date)
        # term-driven referrals re-checked on the what-if terms
        has_t1 = any(s.get("wind_tier") == "T1" for s in snaps["current"])
        if has_t1 and (T1.get("named_storm_ded_pct") or 1) < g["wind_ded_floor_pct_t1"]:
            rule_levels.append((2, "Named storm deductible below guideline floor → L2"))
        tiv = r["tiv_renewal"] * self.pas[acct].get("carrier_share", 1.0)
        lvl, reasons = P.authority_required(r, tiv, 0, rule_levels)
        r.update({"required_authority_level": lvl, "authority_reasons": reasons, "adequacy_floor": g["adequacy_floor"],
                  "expiring_terms": P.terms_only(exp), "proposed_terms": P.terms_only(T1)})
        return r

    def create_quote(self, acct: str, premium: float, terms: dict, uid: str, sim: bool = False) -> dict:
        if not sim:
            F.require_cleared(self, acct)
        ren = self.ren[acct]
        r = self.whatif(acct, premium, terms)
        for q in ren.quotes:
            if q["status"] in ("DRAFT", "REFERRED", "APPROVED", "SENT"):
                q["status"] = "SUPERSEDED"
        v = len(ren.quotes) + 1
        full = dict(r["proposed_terms"])
        if terms.get("forms"):
            full["forms"] = list(terms["forms"])
        h = P.terms_hash(premium, full) + ("|" + ",".join(sorted(full["forms"])) if full.get("forms") else "")
        qid = f"q_{acct}_{v}"
        reg = self.systems["accounts"][acct]
        pas = self.pas[acct]
        term = (pas["term_end"], (date.fromisoformat(pas["term_end"]) + timedelta(days=365)).isoformat())
        path = RUNTIME_DOCS / f"{qid}.pdf"
        from uwc.engine.evaluate import contract_views
        exp = contract_views(self, acct).get("endorsed", {})
        RD.render_contract("quote", path, name=reg["name"], broker=reg["broker"], ref=pas["policy_no"].replace("NSP", "QTE") + f"-R{v}", date=self.clock,
                           term=term, premium=premium, terms={**exp, **full}, forms=full.get("forms") or exp.get("forms") or [], safeguards=[], subjectivities=[],
                           version=v, prepared_by=self.user(uid)["name"], share=pas.get("carrier_share", 1.0))
        doc = self.add_runtime_doc(acct, qid, "Quote", f"Renewal quote v{v}", "pdf", path, "PAS (mock)")
        I.ingest_document(self, doc, "quote", self.clock, {"stage": f"r_quote_v{v}", "term": "current"})
        need = r["required_authority_level"] > self.user(uid)["authority_level"]
        q = {"quote_id": qid, "version": v, "term": f"{term[0][:4]}–{term[1][:4]}", "created_at": self.clock, "created_by": self.user(uid)["name"],
             "premium": premium, "terms": full, "status": "DRAFT", "terms_hash": h, "doc_id": qid, "rarc": r["rarc"], "adequacy": r["adequacy"],
             "required_level": r["required_authority_level"], "needs_referral": need, "uw_reported_rarc": r["headline_change"] - 0.2 * (r["tiv_renewal"] / r["tiv_expiring"] - 1)}
        # invalidate approvals granted on different terms
        for ref in ren.referrals:
            if ref["status"] == "APPROVED" and ref["terms_hash"] != h:
                ref["status"] = "INVALIDATED"
                ref["invalidated_reason"] = f"Terms changed after approval (v{ref['quote_version']} → v{v})"
                self.log(acct, "engine", "07", "Approval invalidated", ref["invalidated_reason"], "Control engine")
        ren.quotes.append(q)
        ren.status = "IN_REVIEW" if ren.status in ("ACTION_REQUIRED", "FAST_TRACK", "IN_REVIEW") else ren.status
        self.log(acct, "user", "08", f"Quote v{v} drafted", f"${premium:,.0f} · RARC {r['rarc'] * 100:+.1f}% · adequacy {r['adequacy'] * 100:.1f}%"
                 + (f" · requires L{r['required_authority_level']} approval" if need else ""), self.user(uid)["name"], qid)
        evaluate_account(self, acct)
        return q

    def create_referral(self, acct: str, quote_id: str | None, note: str, uid: str) -> dict:
        ren = self.ren[acct]
        q = next((x for x in ren.quotes if x["quote_id"] == quote_id), ren.quotes[-1] if ren.quotes else None)
        r = ren.rarc or {}
        mats = [f for f in ren.findings.values() if f["material"] and f["status"] in ("OPEN", "ACCEPTED")]
        lines = [f"**Referral — {self.systems['accounts'][acct]['name']}** (requested by {self.user(uid)['name']}, L{self.user(uid)['authority_level']})", ""]
        if q:
            lines.append(f"Proposed: quote v{q['version']} at **${q['premium']:,.0f}** · RARC {q['rarc'] * 100:+.1f}% · adequacy {q['adequacy'] * 100:.1f}%")
        for why in r.get("authority_reasons", []):
            lines.append(f"- {why}")
        lines.append("")
        lines.append("Evidence:")
        for f in mats[:10]:
            lines.append(f"- {f['title']}: {f['observed']} [F:{f['finding_id']}]")
        if note:
            lines += ["", f"Underwriter note: {note}"]
        ref = {"referral_id": f"ref_{acct}_{len(ren.referrals) + 1}", "account_id": acct, "account_name": self.systems["accounts"][acct]["name"],
               "quote_id": q["quote_id"] if q else None, "quote_version": q["version"] if q else None, "terms_hash": q["terms_hash"] if q else None,
               "requested_by": self.user(uid)["name"], "requested_at": self.clock, "required_level": max(2, (q or {}).get("required_level") or r.get("required_authority_level", 2)),
               "reasons": r.get("authority_reasons", []), "memo": "\n".join(lines), "status": "PENDING", "approver": None, "decided_at": None,
               "conditions": None, "invalidated_reason": None}
        ren.referrals.append(ref)
        if q:
            q["status"] = "REFERRED"
        ren.status = "REFERRED"
        self.outbox.append({"message_id": f"msg_{len(self.outbox) + 1}", "at": self.clock, "channel": "in_app", "to": "Referral queue (L%d+)" % ref["required_level"],
                            "subject": f"Referral: {ref['account_name']}", "body": ref["memo"], "account_id": acct, "related": ref["referral_id"]})
        self.log(acct, "user", "07", "Referred", f"Requires L{ref['required_level']}", self.user(uid)["name"])
        return ref

    def decide_referral(self, rid: str, decision: str, conditions: str | None, uid: str) -> dict:
        for acct, ren in self.ren.items():
            for ref in ren.referrals:
                if ref["referral_id"] == rid:
                    u = self.user(uid)
                    if u["authority_level"] < ref["required_level"]:
                        raise PermissionError(f"{u['name']} (L{u['authority_level']}) cannot approve an L{ref['required_level']} referral")
                    ref["status"] = "APPROVED" if decision == "APPROVE" else "DECLINED"
                    ref["approver"] = u["name"]
                    ref["decided_at"] = self.clock
                    ref["conditions"] = conditions
                    q = next((x for x in ren.quotes if x["quote_id"] == ref["quote_id"]), None)
                    if q:
                        q["status"] = "APPROVED" if decision == "APPROVE" else "DRAFT"
                    ren.status = "IN_REVIEW"
                    if decision == "APPROVE":
                        F.add_subjectivities(self, acct, conditions)
                    self.log(acct, "user", "07", f"Referral {ref['status'].lower()}", (conditions or ""), u["name"])
                    return ref
        raise KeyError(rid)

    def send_quote(self, acct: str, qid: str, uid: str) -> dict:
        ren = self.ren[acct]
        q = next(x for x in ren.quotes if x["quote_id"] == qid)
        if q["needs_referral"] and q["status"] != "APPROVED":
            raise PermissionError(f"Quote v{q['version']} requires L{q['required_level']} approval before it can be sent")
        q["status"] = "SENT"
        ren.status = "QUOTED"
        reg = self.systems["accounts"][acct]
        self.outbox.append({"message_id": f"msg_{len(self.outbox) + 1}", "at": self.clock, "channel": "email", "to": f"{reg['broker_contact']} ({reg['broker']})",
                            "subject": f"{reg['name']} — renewal quote v{q['version']}", "body": f"Please find attached our renewal quotation at ${q['premium']:,.0f}.",
                            "account_id": acct, "related": qid})
        reply = (date.fromisoformat(self.clock) + timedelta(days=4)).isoformat()
        self.dynamic.append({"date": reply, "type": "broker.reply", "account_id": acct, "account_name": reg["name"], "title": "Broker responds to quote",
                             "payload": {"quote_id": qid}})
        self.log(acct, "user", "09", f"Quote v{q['version']} sent to broker", reg["broker"], self.user(uid)["name"], qid)
        return q

    def _broker_reply(self, e: dict):
        acct = e["account_id"]
        ren = self.ren[acct]
        q = next(x for x in ren.quotes if x["quote_id"] == e["payload"]["quote_id"])
        target = self.account_value(acct, "target_premium") or q["premium"]
        if q["status"] != "SENT":
            return
        tp = (ren.rarc or {}).get("tp_e1_t1") or q["premium"]
        if q["premium"] <= max(target * 1.06, tp * 1.02) or not self.injections.get("broker_counter"):
            q["status"] = "ACCEPTED"
            self.log(acct, "mock", "09", f"Broker accepted quote v{q['version']}", "Bind instruction to follow", "Broker (mock)")
        else:
            counter = round((q["premium"] + target) / 2, -3)
            self.log(acct, "mock", "09", f"Broker countered quote v{q['version']}", f"Counter at ${counter:,.0f}", "Broker (mock)")
            self.outbox.append({"message_id": f"msg_{len(self.outbox) + 1}", "at": self.clock, "channel": "email", "to": "Underwriter",
                                "subject": f"RE: {self.systems['accounts'][acct]['name']} — counter-offer", "body": f"Client can do ${counter:,.0f}.",
                                "account_id": acct, "related": q["quote_id"]})
            q["status"] = "ACCEPTED" if counter >= q["premium"] * 0.97 else "SENT"
            q["broker_counter"] = counter

    def data_request(self, acct: str, items: list[str], uid: str) -> dict:
        reg = self.systems["accounts"][acct]
        body = "Please provide the following ahead of renewal:\n" + "\n".join(f"- {i}" for i in items)
        m = {"message_id": f"msg_{len(self.outbox) + 1}", "at": self.clock, "channel": "email", "to": f"{reg['broker_contact']} ({reg['broker']})",
             "subject": f"{reg['name']} — renewal information request", "body": body, "account_id": acct, "related": None}
        self.outbox.append(m)
        self.log(acct, "user", "04", "Data request sent to broker", "; ".join(items), self.user(uid)["name"])
        m["reply_due"] = (self.clock_date + timedelta(days=3)).isoformat()
        F.schedule_broker_docs(self, acct, items)
        return m

    def bind(self, acct: str, qid: str, uid: str, sim_ok: bool = False) -> dict:
        ren = self.ren[acct]
        q = next(x for x in ren.quotes if x["quote_id"] == qid)
        if q["status"] not in ("ACCEPTED",):
            raise ValueError(f"Quote v{q['version']} is {q['status'].lower()} — bind needs the broker's acceptance")
        valid = not q["needs_referral"] or any(r["status"] == "APPROVED" and r["terms_hash"] == q["terms_hash"] for r in ren.referrals)
        if not valid and not sim_ok:
            raise PermissionError(f"Quote v{q['version']} needs L{q['required_level']} approval for these exact terms — bind blocked")
        if not sim_ok:
            F.require_cleared(self, acct)
        subj = [s for s in F.renewal_subjectivities(self, acct) if s["status"] == "OPEN"]
        reg = self.systems["accounts"][acct]
        pas = self.pas[acct]
        from uwc.engine.evaluate import contract_views
        exp = contract_views(self, acct).get("endorsed", {})
        term = (pas["term_end"], (date.fromisoformat(pas["term_end"]) + timedelta(days=365)).isoformat())
        path = RUNTIME_DOCS / f"{acct}_r_binder.pdf"
        terms = {**exp, **q["terms"]}
        RD.render_contract("binder", path, name=reg["name"], broker=reg["broker"], ref=pas["policy_no"].replace("NSP", "BND").replace("2025", "2026"),
                           date=self.clock, term=term, premium=q["premium"], terms=terms, forms=terms.get("forms") or exp.get("forms") or [], safeguards=[], subjectivities=subj,
                           share=pas.get("carrier_share", 1.0))
        doc = self.add_runtime_doc(acct, f"{acct}_r_binder", "Binder", "Renewal binder", "pdf", path, "PAS (mock)")
        self.contract_stages.setdefault(acct, {})["r_quote_accepted"] = f"r_quote_v{q['version']}"
        I.ingest_document(self, doc, "binder", self.clock, {"stage": "r_binder", "term": "current"})
        q["status"] = "BOUND"
        ren.r_bound = {"quote_id": qid, "date": self.clock, "premium": q["premium"], "terms": terms, "authority_valid": valid}
        ren.status = "BOUND"
        self.log(acct, "user", "10", "Renewal bound", f"${q['premium']:,.0f}" + ("" if valid else " — WITHOUT valid approval for these terms"), self.user(uid)["name"], doc["doc_id"])
        evaluate_account(self, acct, pass_no=3)
        return {"binder_doc_id": doc["doc_id"], "findings": [f for f in ren.findings.values() if f["pass"] == 3]}

    def issue(self, acct: str, uid: str) -> dict:
        ren = self.ren[acct]
        if not ren.r_bound:
            raise ValueError("Bind before issuing")
        reg = self.systems["accounts"][acct]
        pas = self.pas[acct]
        terms = dict(ren.r_bound["terms"])
        injected = None
        if self.injections.get("issuance_error") and reg.get("scenario"):
            if terms.get("named_storm_ded_min"):
                terms["named_storm_ded_min"] = None
                injected = "Named storm minimum dropped at issuance"
            elif terms.get("bi_sublimit"):
                terms["bi_sublimit"] = terms["bi_sublimit"] * 1.5
                injected = "BI sublimit keyed incorrectly at issuance"
            else:
                terms["aop_deductible"] = (terms.get("aop_deductible") or 25000) / 2
                injected = "AOP deductible keyed incorrectly at issuance"
        term = (pas["term_end"], (date.fromisoformat(pas["term_end"]) + timedelta(days=365)).isoformat())
        path = RUNTIME_DOCS / f"{acct}_r_policy.pdf"
        RD.render_contract("policy", path, name=reg["name"], broker=reg["broker"], ref=pas["policy_no"].replace("2025", "2026"), date=self.clock, term=term,
                           premium=ren.r_bound["premium"], terms=terms, forms=terms.get("forms") or [], safeguards=[], subjectivities=[],
                           share=pas.get("carrier_share", 1.0))
        doc = self.add_runtime_doc(acct, f"{acct}_r_policy", "Declarations", "Renewal policy declarations", "pdf", path, "PAS (mock)")
        I.ingest_document(self, doc, "policy", self.clock, {"stage": "r_policy", "term": "current"})
        ren.r_issued = {"date": self.clock, "doc_id": doc["doc_id"], "injected": injected}
        ren.status = "ISSUED"
        self.log(acct, "mock", "11", "Renewal policy issued (mock PAS)", injected or "Issued as bound", "PAS (mock)", doc["doc_id"])
        F.bill(self, acct, ren.r_bound["premium"])
        evaluate_account(self, acct, pass_no=3)
        return {"policy_doc_id": doc["doc_id"], "findings": [f for f in ren.findings.values() if f["pass"] == 3 and f["family"] == "contract_integrity"]}

    def non_renew(self, acct: str, uid: str):
        ren = self.ren[acct]
        reg = self.systems["accounts"][acct]
        n = ren.notice or {}
        ren.status = "NON_RENEWED"
        body = (f"Notice of non-renewal — {reg['name']}, policy {self.pas[acct].get('policy_no')}, expiring {self.pas[acct].get('term_end')}. "
                f"Issued {self.clock}; statutory notice {n.get('days_required') or '—'} days ({n.get('state')}), latest valid date {n.get('latest_notice_date')}.")
        self.outbox.append({"message_id": f"msg_{len(self.outbox) + 1}", "at": self.clock, "channel": "email", "to": f"{reg['name']} (insured) · cc {reg['broker']}",
                            "subject": f"Notice of non-renewal — {reg['name']}", "body": body, "account_id": acct, "related": None})
        self.log(acct, "user", "15", "Non-renewal notice issued", body, self.user(uid)["name"])
        for a in ren.actions:
            if a["type"] in ("NON_RENEW", "CONDITIONAL_RENEWAL_NOTICE"):
                a["status"] = "DONE"

    def match_decision(self, item_id: str, decision: str, uid: str):
        acct, loc_uid = item_id.split("|")
        e = self.store.account_locations(acct)[loc_uid]
        if decision == "CONFIRM":
            e.match_status, e.match_confirmed_by = "MATCHED", self.user(uid)["name"]
            e.match_method = (e.match_method or "") + " · confirmed"
        else:
            e.match_status = "NEW"
        self.review_decisions[item_id] = decision
        self.log(acct, "user", "04", f"Location match {decision.lower()}ed", e.label, self.user(uid)["name"])
        evaluate_account(self, acct)

    # ------------------------------------------------------------------ simulated underwriters (background book)
    def _sim(self, t: str, acct: str):
        ren = self.ren[acct]
        if ren.pass_no == 0 or self.systems["accounts"][acct].get("scenario"):
            return
        rng = random.Random(hash(acct + t) % 10_000 if False else int(hashlib.md5((acct + t).encode()).hexdigest()[:8], 16))
        reg = self.systems["accounts"][acct]
        uw = reg["underwriter_id"]
        if t == "sim.uw_review":
            for f in list(ren.findings.values()):
                if f["status"] == "OPEN" and f["material"]:
                    if rng.random() < 0.74:
                        self.disposition(f["finding_id"], "ACCEPT", "agree", "", uw)
                    else:
                        self.disposition(f["finding_id"], "REJECT", rng.choice(["already_known", "commercial_override", "immaterial", "data_wrong"]), "", uw)
            if not any(f["material"] for f in ren.findings.values()):
                ren.fast_track_confirmed = True
                self.log(acct, "user", "15", "Fast-track confirmed", "No material change", USER_BY_ID[uw]["name"])
        elif t == "sim.uw_quote":
            r = ren.rarc
            if not r:
                return
            accepted = [f for f in ren.findings.values() if f["status"] == "ACCEPTED"]
            if any(f["outcome"] == "DECLINE" for f in accepted):
                ren.status = "NON_RENEWED"
                self.log(acct, "user", "15", "Non-renewal notice issued", "Declined class", USER_BY_ID[uw]["name"])
                return
            tr = rng.uniform(-0.09, -0.02) if rng.random() < 0.4 else rng.uniform(-0.01, 0.05)
            prem = r["expected_premium"] * (1 + tr)
            if any(f["family"] in ("pricing", "valuation") for f in accepted):
                prem = max(prem, r["tp_e1_t1"] * rng.uniform(0.95, 1.02))
            terms = dict(ren.working["terms"]) if any(f["outcome"] == "TERM_BREACH" for f in accepted) else dict(r["expiring_terms"])
            q = self.create_quote(acct, round(prem, -3), terms, uw, sim=True)
            q["uw_reported_rarc"] = q["uw_reported_rarc"] + rng.gauss(0.0, 0.02)
            if q["needs_referral"]:
                ref = self.create_referral(acct, q["quote_id"], "", uw)
                approver = "u_priya" if ref["required_level"] <= 3 else "u_robert"
                self.decide_referral(ref["referral_id"], "APPROVE", None, approver)
            self.send_quote(acct, q["quote_id"], uw)
        elif t == "sim.broker_response":
            for q in ren.quotes:
                if q["status"] == "SENT":
                    q["status"] = "ACCEPTED"
            self.dynamic = [x for x in self.dynamic if not (x["account_id"] == acct and x["type"] == "broker.reply")]
        elif t == "sim.bind":
            q = next((x for x in ren.quotes if x["status"] == "ACCEPTED"), None)
            if q:
                self.bind(acct, q["quote_id"], uw, sim_ok=True)
        elif t == "sim.issue":
            if ren.r_bound and not ren.r_issued:
                saved = self.injections.get("issuance_error")
                self.injections["issuance_error"] = False
                self.issue(acct, uw)
                self.injections["issuance_error"] = saved


def _stage_of(role: str | None) -> str:
    return {"sov_prior": "01", "sov_current": "01", "loss_run": "13", "quote": "08", "engineering": "05", "appraisal": "04"}.get(role or "", "01")


def _jsonable(v: Any):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    return str(v)

"""Product 02 — Decision Intelligence & Assurance (new business).

Prepare the decision (stage 1 decision pack), support the judgement, control the commitment (stage 2 independent
assurance of the intended action), learn from outcomes. The human underwriter remains the final decision owner.
Implements the product interface documented in uwc/products/__init__.py."""
from __future__ import annotations

import copy
import time

from .model import GROUPS, ID, META, MOCK_CORE, PIPE, REAL_CORE, DState, st  # noqa: F401
from .api import router  # noqa: F401


def init(rt):
    rt.decision = DState()


def ensure(rt):
    """Snapshots built before this product existed carry no Decision state; build it on first use."""
    s = st(rt)
    if not s.built:
        from . import flow
        flow.build_world(rt)


def build_world(rt):
    from . import flow
    rt.decision = DState()
    flow.build_world(rt)


def on_day(rt, ds):
    pass


def handle_event(rt, e):
    from . import flow
    if st(rt).built:
        flow.handle_event(rt, e)


def pipeline_counts(rt) -> dict:
    ensure(rt)
    cs = list(st(rt).cases.values())
    rec = [c for c in cs if c["received"]]
    asr = [c for c in cs if c["assurances"]]
    last = [c["assurances"][-1]["verdict"] for c in asr]
    return {
        "01": [("submissions", len(rec)), ("expected", sum(1 for c in cs if not c["received"]))],
        "02": [("documents", sum(len(c["docs"]) for c in rec)), ("observations", sum(len(rt.store.by_account.get(c["case_id"], [])) for c in rec))],
        "03": [("priced", sum(1 for c in rec if c["pack"])), ("rules", sum(1 for r in rt.rules.values() if r.product == "decision"))],
        "04": [("packs", sum(1 for c in rec if c["pack"])), ("contradictions", sum(len(c["contradictions"]) for c in rec))],
        "05": [("judged", sum(1 for c in rec if c["judged"])), ("info requests", sum(len(c["requests"]) for c in rec))],
        "06": [("intended actions", sum(len(c["actions"]) for c in cs))],
        "07": [("assurance runs", sum(len(c["assurances"]) for c in cs))],
        "08": [("pass", last.count("PASS")), ("flags", last.count("PASS_WITH_FLAGS")), ("refer/hold", last.count("REFER_HOLD"))],
        "09": [("decided", sum(1 for c in cs if c["decision"])), ("bound", sum(1 for c in cs if c["bound"]))],
        "10": [("outcomes", sum(1 for c in cs if c["outcome"]))],
    }


def subjects(rt) -> list[dict]:
    ensure(rt)
    s = st(rt)
    return [{"id": cid, "label": f"{s.cases[cid]['scenario']} · {s.cases[cid]['short']} — {s.cases[cid]['title']}"} for cid in s.heroes]


def build_stage(rt, code, subject):
    ensure(rt)
    from . import stages
    return stages.build(rt, code, subject)


def run_stage(rt, code, subject):
    ensure(rt)
    from . import stages
    return stages.run(rt, code, subject)


def playbooks(rt):
    ensure(rt)
    from . import walkthroughs as PB
    return PB.all_playbooks(rt)


def run_step(rt, p, step):
    ensure(rt)
    from . import walkthroughs as PB
    return PB.run_step(rt, p, step)


def facts(rt, subject) -> list[dict]:
    ensure(rt)
    from . import stages
    return stages.facts(rt, subject)


def mocks(rt) -> list[dict]:
    ensure(rt)
    cs = st(rt).cases.values()
    ndocs = lambda types: sum(1 for c in cs for d in c["docs"] if d["doc_type"] in types)
    return [
        {"port": "MailboxPort", "name": "Submission mailbox (mock)", "stands_in_for": "Broker email / portal intake", "status": "UP", "records": sum(1 for c in cs if c["received"]), "last_sync": rt.clock},
        {"port": "BrokerPort", "name": "Broker (mock)", "stands_in_for": "Broker correspondence", "status": "UP", "records": sum(len(c["requests"]) for c in cs), "last_sync": rt.clock},
        {"port": "InspectionPort", "name": "Loss-control vendor (mock)", "stands_in_for": "Inspection / engineering vendor", "status": "UP", "records": ndocs({"Inspection report", "Verification survey"}), "last_sync": rt.clock},
        {"port": "RaterPort", "name": "NS-PROP-RATER v8.0 (mock)", "stands_in_for": "hx / carrier rating service", "status": "UP", "records": sum(len(c["assurances"]) + (1 if c["pack"] else 0) for c in cs), "last_sync": rt.clock},
        {"port": "CatModelPort", "name": "MockCat 3.1", "stands_in_for": "Moody's RMS / Verisk", "status": "UP", "records": sum(1 for c in cs if c["pack"]), "last_sync": rt.clock},
        {"port": "VendorPort", "name": "Hazard · property · company data (mock)", "stands_in_for": "Precisely · HazardHub · D&B", "status": "UP", "records": ndocs({"Vendor payload"}), "last_sync": rt.clock},
        {"port": "PolicyAdminPort", "name": "Policy admin (mock)", "stands_in_for": "Guidewire PolicyCenter / Duck Creek", "status": "UP", "records": ndocs({"Quote", "Binder"}), "last_sync": rt.clock},
        {"port": "ClaimsPort", "name": "Claims feed (mock)", "stands_in_for": "Guidewire ClaimCenter", "status": "UP", "records": sum(1 for c in cs if c["outcome"]), "last_sync": rt.clock},
    ]


def rule_fired(rt, rule_id: str) -> int:
    s = st(rt).stats.get(rule_id)
    return len(s["fired"]) if s else 0


def reevaluate_all(rt):
    """After a rule is published: rebuild every open case's pack and re-assure its latest intended action."""
    from . import engine as E
    from . import flow as FL
    for cid, c in st(rt).cases.items():
        if not c["received"] or c["status"] in ("BOUND", "DECLINED", "LOST"):
            continue
        E.build_pack(rt, cid, rt.clock)
        if c["actions"] and not c["decision"]:
            a = c["actions"][-1]
            res = E.assure(rt, cid, a, rt.clock, a["by"])
            res.update({"assurance_id": FL.nid(rt, "asr_"), "action_id": a["action_id"], "action_version": a["version"], "action_type": a["type"], "premium": a["premium"],
                        "rerun": "rule publish"})
            c["assurances"].append(res)
            FL.log(rt, cid, "engine", "07", "Re-assured after rule publish", res["summary"], "Assurance engine", None, rt.clock)


def backtest(rt, old, new) -> dict:
    from . import engine as E
    rid = new.rule_id
    t0 = time.time()
    s = st(rt)
    saved = (copy.deepcopy(s.cases), copy.deepcopy(s.stats), s.counter, s.seq, dict(rt.rule_stats))
    ctl = [cid for cid, c in s.cases.items() if c["actions"]]

    def fired_on() -> dict:
        out = {}
        for cid in ctl:
            c = s.cases[cid]
            res = E.assure(rt, cid, c["actions"][-1], c["actions"][-1]["at"], c["actions"][-1]["by"])
            for ch in res["checks"]:
                if ch["rule_id"] == rid and ch["result"] in ("FAIL", "FLAG", "CONDITION"):
                    out[cid] = {"account_id": cid, "account_name": c["insured"], "subject_label": ch["subject"], "observed": ch["observed"]}
        return out
    try:
        before = fired_on()
        rt.rules[rid] = new
        after = fired_on()
    finally:
        if old:
            rt.rules[rid] = old
        s.cases, s.stats, s.counter, s.seq = saved[0], saved[1], saved[2], saved[3]
        rt.rule_stats.clear()
        rt.rule_stats.update(saved[4])
    return {"control_set": f"Northgate new-business assurance runs as of {rt.clock} (latest intended action per case, frozen)", "accounts": len(ctl),
            "before": len(before), "after": len(after), "added": [v for k, v in after.items() if k not in before],
            "removed": [v for k, v in before.items() if k not in after], "duration_ms": int((time.time() - t0) * 1000)}

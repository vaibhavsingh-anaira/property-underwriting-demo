"""Workflow playbooks — scripted walks through the pipeline that exercise different
aspects of the renewal workflow (reprice/refer, fast-track, decline, mid-term event,
counter-offer, declined referral, human matching, engineering condition, contract
integrity), plus a generic 15-stage lifecycle for every scenario account.

Every step runs against the real engine and the mocks; nothing is canned output.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from uwc.refdata import USER_BY_ID

if TYPE_CHECKING:
    from uwc.runtime import Runtime


from uwc.playbook_defs import MOCK_CORE, PLAYBOOKS, REAL_CORE, S  # noqa: F401

HERO = ["acc_s1", "acc_s2", "acc_s3", "acc_s4", "acc_s5", "acc_s6", "acc_s7", "acc_s8", "acc_s9", "acc_s10", "acc_s11", "acc_s12"]


def all_playbooks(rt: "Runtime") -> list[dict]:
    from uwc.api import PIPE
    out = [dict(p) for p in PLAYBOOKS]
    for a in HERO:
        from uwc.narration import STAGE_LINES
        reg = rt.systems["accounts"][a]
        out.append({"id": f"lifecycle-{a}", "account_id": a, "title": "All 15 stages in order", "aspects": ["Full lifecycle"],
                    "intro": f"Here's {reg['name']}, taken through all fifteen stages of the underwriting lifecycle, one system at a time.",
                    "outro": "That's the full cycle, from submission to renewal, with every step evidenced.",
                    "brief": {"audience": "Anyone who wants to see every system in the chain for one account",
                              "problem": reg.get("scenario_title") or "Renewal lifecycle",
                              "story": ["Each of the 15 pipeline stages is opened in order for this account and its step is run: intake, clearance, appetite, extraction, engineering, pricing, authority, quote, negotiation, bind, issue, in-force, claims, portfolio, renewal engine."],
                              "watch": ["Which stages are the product (REAL) and which are stand-ins (MOCK) — the badge on each stage"],
                              "value": "Shows the platform sits across the whole chain, not at one point in it.", "questions": []},
                    "steps": [S(c, n, "stage", STAGE_LINES[c]) for c, n, *_ in PIPE]})
    for p in out:
        reg = rt.systems["accounts"][p["account_id"]]
        p["account_name"] = reg["name"]
        p["scenario"] = reg.get("scenario")
    return out


def get(rt: "Runtime", pid: str) -> dict:
    return next(p for p in all_playbooks(rt) if p["id"] == pid)


def _approver(level: int) -> str:
    for uid in ("u_daniel", "u_priya", "u_robert"):
        if USER_BY_ID[uid]["authority_level"] >= level:
            return uid
    return "u_robert"


def run_step(rt: "Runtime", p: dict, step: dict) -> str:
    from uwc import stages as ST
    from uwc.engine.evaluate import contract_views, evaluate_account
    from uwc.engine.pricing import recommended_terms
    acct = p["account_id"]
    ren = rt.ren[acct]
    uw = rt.systems["accounts"][acct]["underwriter_id"]
    a, prm = step["action"], step["params"]
    from uwc import fulfilment as F
    if a == "view":
        return f"Showing {step['label'].lower()}"
    if a == "clearance":
        c = F.clearance(rt, acct)
        return "Clearance passed — no duplicates, broker licensed in every location state, sanctions clear" if c["status"] == "CLEARED" else f"Clearance HOLD — {c['reason']}"
    if a == "try_quote":
        try:
            rt.create_quote(acct, round(ST._suggested_premium(rt, acct), -3), {}, uw)
        except ValueError as e:
            return f"Quote refused — {e}"
        return "Quote created (clearance was not on hold)"
    if a == "correct_issuance":
        return F.correct_issuance(rt, acct, uw)
    if a == "order_survey":
        F.order_survey(rt, acct, "u_elena", prm.get("scope") or "Verification survey")
        before = {k: v["status"] for k, v in rt.recs.get(acct, {}).items()}
        rt.advance_to((rt.clock_date + timedelta(days=7)).isoformat())
        after = rt.recs.get(acct, {})
        changed = [f"{k} {before.get(k, 'new')} → {v['status']}" for k, v in after.items() if before.get(k) != v["status"]]
        return f"Engineer visited {rt.clock}; report ingested as verified evidence" + (f" · {'; '.join(changed)}" if changed else "")
    if a == "refer_if_needed":
        q = ren.quotes[-1]
        if not q["needs_referral"]:
            return f"Quote v{q['version']} is within {USER_BY_ID[uw]['name']}'s authority — no referral needed"
        ref = rt.create_referral(acct, q["quote_id"], "", uw)
        who = _approver(ref["required_level"])
        rt.decide_referral(ref["referral_id"], "APPROVE", None, who)
        return f"Referred to L{ref['required_level']} and approved by {USER_BY_ID[who]['name']}"
    if a == "stage":
        return ST.run(rt, step["code"], acct)
    if a == "advance_submission":
        return ST.run(rt, "01", acct)
    if a == "advance_inforce":
        return ST.run(rt, "12", acct)
    if a == "reevaluate":
        return ST.run(rt, "15", acct)
    if a == "accept_findings":
        n = 0
        for f in list(ren.findings.values()):
            if f["status"] == "OPEN" and f["material"]:
                rt.disposition(f["finding_id"], "ACCEPT", "agree", "Accepted in walkthrough", uw)
                n += 1
        return f"{n} material findings accepted (reason: agree)"
    if a == "confirm_maintain":
        ren.fast_track_confirmed = True
        rt.log(acct, "user", "15", "Fast-track confirmed — maintain", "No material change; renewal on expiring terms", USER_BY_ID[uw]["name"])
        return "Fast-track confirmed"
    if a == "draft_quote":
        r = ren.rarc or {}
        exp = contract_views(rt, acct).get("endorsed", {})
        if prm.get("terms") == "recommended":
            has_t1 = any(s.get("wind_tier") == "T1" for s in ren.loc_ctx.values())
            t = recommended_terms(rt, acct, exp, has_t1)
            terms = {k: t.get(k) for k in ("named_storm_ded_pct", "named_storm_ded_min")}
        else:
            terms = {}
        mode = prm.get("mode", "suggested")
        tp = r.get("tp_e1_t1") or rt.pas[acct]["premium"]
        if mode == "expected":
            prem = r.get("expected_premium") or rt.pas[acct]["premium"]
        elif mode == "above_technical":
            prem = tp * 1.2
        elif mode == "low":
            prem = tp * 0.85
        elif mode == "technical":
            prem = tp
        elif mode == "counter":
            prem = next((q.get("broker_counter") for q in reversed(ren.quotes) if q.get("broker_counter")), tp)
        else:
            prem = ST._suggested_premium(rt, acct)
        if prm.get("add_forms"):
            terms["forms"] = sorted(set((exp.get("forms") or []) + prm["add_forms"]))
        q = rt.create_quote(acct, round(prem / 1000) * 1000, terms, uw)
        inv = [x for x in ren.referrals if x["status"] == "INVALIDATED" and x.get("invalidated_reason", "").endswith(f"v{q['version']})")]
        return (f"Quote v{q['version']} at ${q['premium']:,.0f} · RARC {q['rarc'] * 100:+.1f}% · adequacy {q['adequacy'] * 100:.1f}% · needs L{q['required_level']}"
                + (" · prior approval INVALIDATED (terms changed)" if inv else ""))
    if a == "refer":
        q = ren.quotes[-1] if ren.quotes else None
        ref = rt.create_referral(acct, q["quote_id"] if q else None, prm.get("note", ""), uw)
        return f"Referred to L{ref['required_level']}"
    if a in ("approve", "decline"):
        pend = [x for x in ren.referrals if x["status"] == "PENDING"]
        if not pend:
            return "No pending referral"
        who = _approver(pend[-1]["required_level"])
        rt.decide_referral(pend[-1]["referral_id"], "APPROVE" if a == "approve" else "DECLINE", prm.get("conditions"), who)
        return f"{'Approved' if a == 'approve' else 'Declined'} by {USER_BY_ID[who]['name']} (L{USER_BY_ID[who]['authority_level']})" + (f" — {prm['conditions']}" if prm.get("conditions") else "")
    if a == "send":
        q = ren.quotes[-1]
        rt.send_quote(acct, q["quote_id"], uw)
        return f"Quote v{q['version']} sent to the broker"
    if a == "broker_wait":
        rt.advance_to((date.fromisoformat(rt.clock) + timedelta(days=5)).isoformat())
        q = ren.quotes[-1]
        if q["status"] == "ACCEPTED":
            what = "accepted"
        elif q.get("broker_counter"):
            what = f"countered at ${q['broker_counter']:,.0f}"
        else:
            what = q["status"].lower()
        return f"Clock +5 days — broker {what} quote v{q['version']}"
    if a == "bind":
        q = next((x for x in reversed(ren.quotes) if x["status"] == "ACCEPTED"), None)
        if not q:
            raise ValueError("No accepted quote to bind")
        rt.bind(acct, q["quote_id"], uw)
        return f"Bound quote v{q['version']} — Pass 3 ran on the binder"
    if a == "issue":
        saved = rt.injections.get("issuance_error")
        rt.injections["issuance_error"] = bool(prm.get("injection"))
        try:
            rt.issue(acct, uw)
        finally:
            rt.injections["issuance_error"] = saved
        return f"Issued — {ren.r_issued['injected'] or 'as bound'}"
    if a == "data_request":
        items = prm.get("items") or [f["title"] for f in ren.findings.values() if f["outcome"] == "DATA_REQUEST" and f["status"] == "OPEN"]
        before = {f["finding_id"] for f in ren.findings.values() if f["status"] == "OPEN" and f["material"]}
        m = rt.data_request(acct, items, uw)
        if not prm.get("wait"):
            return f"Request sent to broker ({len(items)} items)"
        rt.advance_to(m["reply_due"])
        after = {f["finding_id"] for f in ren.findings.values() if f["status"] == "OPEN" and f["material"]}
        cleared = [s_ for s_ in F.renewal_subjectivities(rt, acct) if s_["status"] == "CLEARED" and s_.get("evidence", "") and s_["evidence"].startswith(f"r_{acct}")]
        return (f"Request sent; broker returned {len(items)} document(s) on {rt.clock}, parsed into evidence"
                + (f" · {len(before - after)} material finding(s) cleared" if before - after else "")
                + (f" · subjectivity cleared: {cleared[-1]['text']}" if cleared else ""))
    if a == "confirm_matches":
        n = 0
        for uid, e in list(rt.store.account_locations(acct).items()):
            if e.match_status == "AMBIGUOUS":
                rt.match_decision(f"{acct}|{uid}", "CONFIRM", uw)
                n += 1
        return f"{n} proposed matches confirmed by {USER_BY_ID[uw]['name']}"
    if a == "non_renew":
        rt.non_renew(acct, uw)
        n = ren.notice or {}
        return f"Non-renewal notice issued {rt.clock} (latest valid date {n.get('latest_notice_date')})"
    return "Unknown action"


_SPEAK = [(r"\bRARC\b", "real rate change"), (r"\bL(\d)\b", r"level \1"), (r"\bv(\d+)\b", r"version \1"), (r" · ", ". "), (r"→", "to"),
          (r"\bTP\b", "technical price"), (r"\bNS\b", "named storm"), (r"\+(\d)", r"plus \1"), (r"(?<![\w])-(\d)", r"minus \1")]


def speakable(msg: str | None) -> str:
    import re
    if not msg:
        return ""
    out = msg
    for pat, rep in _SPEAK:
        out = re.sub(pat, rep, out)
    return out if out.endswith(".") else out + "."

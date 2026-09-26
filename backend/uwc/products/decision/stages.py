"""Stage workspaces for the 10-stage Decision Assurance pipeline: `build` returns what that stage's system holds for
one case (same StageView shape as uwc.stages.build); `run` performs that stage's step for the case using its script,
so every hero can be walked through all ten stages from the clean 1 Aug state."""
from __future__ import annotations

from uwc.refdata import USER_BY_ID

from . import engine as E
from . import flow as FL
from .model import DIMENSIONS, NB_AUTHORITY, PIPE, STANDS_IN, VERDICT_LABEL, money, pct, st


def col(key: str, label: str, kind: str = "text") -> dict:
    return {"key": key, "label": label, "kind": kind}


def _docs(rt, c: dict, types: set[str] | None = None) -> list[dict]:
    from uwc.api import doc_meta
    out = [doc_meta(rt.store.docs[d["doc_id"]]) for d in c["docs"] if d["doc_id"] in rt.store.docs and (not types or d["doc_type"] in types)]
    return sorted(out, key=lambda d: d["received_at"], reverse=True)


def _events(c: dict, stages: set[str]) -> list[dict]:
    return [e for e in reversed(c["timeline"]) if e["stage"] in stages][:30]


def as_finding(c: dict, x: dict, created: str) -> dict:
    """A pack factor or an assurance check in the shared Finding shape, so the evidence drawer opens it."""
    sev = x.get("severity", "MEDIUM")
    return {"finding_id": f"{c['case_id']}|{x.get('rule_id') or 'contra'}|{x.get('subject_id') or 'case'}", "account_id": c["case_id"], "subject_type": "location" if x.get("subject_id") else "account",
            "subject_id": x.get("subject_id") or c["case_id"], "subject_label": x.get("subject", "Submission"), "rule_id": x.get("rule_id") or "EVIDENCE.CONTRADICTION",
            "rule_version": x.get("rule_version") or 1, "family": x.get("family", "data_integrity"), "title": x["title"], "description": x.get("note") or "", "severity": sev,
            "outcome": x.get("outcome", "FLAG"), "observed": x["observed"], "expected": x.get("expected", ""), "impact_usd": x.get("impact_usd", 0),
            "impact_method": "re-rated with the mock rater (premium-equivalent)", "confidence": 0.95, "materiality_score": x.get("impact_usd", 0), "material": sev in ("HIGH", "CRITICAL"),
            "evidence_obs_ids": x.get("evidence_obs_ids", []), "conflicting_obs_ids": [], "status": "OPEN", "disposition": None, "pass": 1, "created_at": created,
            "critique": {"verdict": "UPHELD", "note": f"Tier {x.get('tier', 1)} · {x.get('source') or ''}"} if x.get("tier") else None, "source": x.get("source") or ""}


def build(rt, code: str, cid: str) -> dict:
    s = st(rt)
    if cid not in s.cases:
        cid = s.heroes[0]
    c = s.cases[cid]
    meta = next(p for p in PIPE if p[0] == code)
    p = c.get("pack") or {}
    a, res = FL.latest(c)
    v = {"code": code, "name": meta[1], "group": meta[2], "component": meta[3], "mode": meta[4], "description": meta[5], "port": meta[6],
         "stands_in_for": STANDS_IN[code], "account": {"account_id": cid, "name": c["insured"], "scenario": c.get("scenario"), "href": f"/decision/cases/{cid}"},
         "clock": rt.clock, "status": "PENDING", "headline": "", "kpis": [], "tables": [], "documents": [], "events": [], "findings": [], "next_action": None}
    rec = bool(c["received"])
    if code == "01":
        emails = [d for d in c["docs"] if d["doc_type"] == "Broker email"]
        v["status"] = "DONE" if rec else "READY"
        v["headline"] = (f"Submission received {c['received']} from {c['broker']} with {len(c['files']) - 1} attachments" if rec
                         else f"Submission expected {c['arrive']} — the broker's email is in the mailbox stub's schedule")
        v["kpis"] = [{"label": "Broker", "value": c["broker"]}, {"label": "Contact", "value": c["contact"]}, {"label": "Effective", "value": c["effective"]},
                     {"label": "Underwriter", "value": USER_BY_ID[c["uw"]]["name"]}]
        v["tables"] = [{"title": "Mailbox — messages for this submission", "columns": [col("date", "Received", "date"), col("subject", "Subject"), col("doc", "Open", "doc")],
                        "rows": [{"date": d["received_at"], "subject": d["title"], "doc": d["doc_id"]} for d in emails]}]
        v["documents"] = _docs(rt, c, {"Broker email", "ACORD application", "SOV", "Loss run", "Inspection report", "Manuscript wording"})
        v["events"] = _events(c, {"01"})
        if not rec:
            v["next_action"] = {"label": f"Advance clock to {c['arrive']} — submission arrives", "description": "The mailbox stub delivers the broker's email; every attachment is parsed and the decision pack is prepared automatically."}
        return v
    if not rec:
        v["headline"] = f"Waiting for the submission ({c['arrive']})"
        v["next_action"] = {"label": "Run stage 01 first", "description": "The submission has not arrived yet."} if code != "01" else None
        return v
    from uwc.api import doc_meta
    if code == "02":
        drows = []
        for d in c["docs"]:
            doc = rt.store.docs.get(d["doc_id"])
            if not doc:
                continue
            m = doc_meta(doc)
            if m["extraction"] and m["extraction"]["fields"]:
                drows.append({"doc": d["doc_id"], "type": d["doc_type"], "title": d["title"], "fields": m["extraction"]["fields"], "confidence": m["extraction"]["avg_confidence"],
                              "method": rt.store.doc_method.get(d["doc_id"], "")[:60]})
        crow = [{"field": x["field_label"], "location": x["location"], "a": f"{x['resolved']['value']} · {x['resolved']['source']}", "b": f"{x['other']['value']} · {x['other']['source']}",
                 "impact": x["impact_usd"], "status": x["status"]} for x in p.get("contradictions", [])]
        n = p["evidence"]["facts"]
        v["status"] = "DONE"
        v["headline"] = f"{len(drows)} documents extracted into {n} anchored facts · {len(crow)} contradiction(s) between sources · {len(p['missing'])} missing item(s)"
        v["kpis"] = [{"label": "Anchored facts", "value": str(n)}, {"label": "Documents", "value": str(len(drows))},
                     {"label": "Contradictions", "value": str(len(crow)), "tone": "high" if crow else "ok"}, {"label": "Missing items", "value": str(len(p["missing"])), "tone": "high" if p["missing"] else "ok"}]
        v["tables"] = [{"title": "Extraction — every value keeps its cell / page / email anchor", "columns": [col("type", "Type"), col("title", "Document"), col("fields", "Fields"), col("confidence", "Avg conf.", "pct"), col("method", "Method", "mono"), col("doc", "Open", "doc")], "rows": drows},
                       {"title": "Contradictions between sources (priced by re-rating)", "columns": [col("field", "Field"), col("location", "Location"), col("a", "Resolved"), col("b", "Other source"), col("impact", "Rating impact", "money"), col("status", "Status", "badge")], "rows": crow},
                       {"title": "Missing information", "columns": [col("item", "Item"), col("why", "Why"), col("status", "Status", "badge")], "rows": [{"item": m["item"], "why": m["why"], "status": m["status"]} for m in p["missing"]]}]
        v["documents"] = _docs(rt, c)
        v["findings"] = [as_finding(c, f, c["received"]) for f in p["factors"] if f["rule_id"] is None]
        v["events"] = _events(c, {"01", "02"})
        return v
    if code == "03":
        px = p["pricing"]
        z = (p["portfolio"]["zones"] or [None])[0]
        v["status"] = "DONE"
        v["headline"] = (f"Technical {money(px['technical'])} ({px['model']}) · suggested {money(px['band_low'])}–{money(px['band_high'])} · "
                         f"{len([g for g in p['guidelines'] if g['result'] not in ('PASS', 'N/A')])} guideline rule(s) triggered" + (f" · {z['name']} {pct(z['util_before'])} → {pct(z['util_after'])}" if z else ""))
        v["kpis"] = [{"label": "Technical premium", "value": money(px["technical"])}, {"label": "Suggested range", "value": f"{money(px['band_low'], False)}–{money(px['band_high'], False)}"},
                     {"label": "CAT AAL", "value": money(px["aal"])}, {"label": "Required authority", "value": f"L{p['required_level']}", "tone": "high" if p["required_level"] > USER_BY_ID[c["uw"]]["authority_level"] else "ok"}]
        v["tables"] = [{"title": "Guidelines & appetite applied (rules in force today)", "columns": [col("rule", "Rule", "mono"), col("title", "Rule"), col("subject", "Subject"), col("result", "Result", "badge"), col("cite", "Citation")],
                        "rows": [{"rule": g["rule_id"], "title": g["title"], "subject": g["subject"], "result": g["result"], "cite": g["citation"]["label"]} for g in p["guidelines"]]},
                       {"title": "Pricing — mock rater components", "columns": [col("component", "Component"), col("value", "Value", "money")], "rows": px["components"] + [{"component": "Technical premium", "value": px["technical"]}]},
                       {"title": "Authority & referral requirements (new-business matrix)", "columns": [col("req", "Requirement"), col("level", "Level"), col("within", "Within authority", "badge")],
                        "rows": [{"req": r["requirement"], "level": f"L{r['level']}", "within": "YES" if r["within"] else "REFER"} for r in p["requirements"]]},
                       {"title": "Portfolio — accumulation (in-force + bound new business)", "columns": [col("zone", "Zone"), col("before", "Before", "pct"), col("after", "After", "pct"), col("inc", "PML added", "money")],
                        "rows": [{"zone": x["name"], "before": x["util_before"], "after": x["util_after"], "inc": x["increase"]} for x in p["portfolio"]["zones"]]}]
        v["documents"] = _docs(rt, c, {"Vendor payload"})
        v["events"] = _events(c, {"03"})
        return v
    if code == "04":
        d = p["draft"]
        v["status"] = "DONE"
        v["headline"] = f"Draft: {FL.DRAFT_LABEL[d['action']]} — {d['why']}"
        v["kpis"] = [{"label": "Draft action", "value": FL.DRAFT_LABEL[d["action"]], "tone": "crit" if d["action"] == "DECLINE" else "high" if d["action"].startswith("REFER") else "ok"},
                     {"label": "Risk factors", "value": str(len(p["factors"]))}, {"label": "Source-linked facts", "value": str(p["evidence"]["facts"])},
                     {"label": "Prep hours saved", "value": f"{p['prep']['saved']:.1f} h"}]
        v["tables"] = [{"title": "Material risk factors", "columns": [col("title", "Factor"), col("subject", "Subject"), col("observed", "Observed"), col("impact", "Impact", "money")],
                        "rows": [{"title": f["title"], "subject": f["subject"], "observed": f["observed"], "impact": f["impact_usd"]} for f in p["factors"]]},
                       {"title": "Before the final decision", "columns": [col("item", "Item")], "rows": [{"item": x} for x in d["before_final"]] or [{"item": "Nothing outstanding"}]}]
        v["findings"] = [as_finding(c, f, c["received"]) for f in p["factors"]]
        v["events"] = _events(c, {"04"})
        return v
    if code == "05":
        rows = [{"what": "Contradiction", "detail": f"{x['field_label']} at {x['location']}", "status": x["status"], "by": (x.get("resolution") or {}).get("by", "")} for x in p.get("contradictions", [])]
        rows += [{"what": "Information request", "detail": "; ".join(r["items"]), "status": r["status"], "by": r["by"]} for r in c["requests"]]
        rows += [{"what": "Override", "detail": f"{o['rule_id']}: {o['reason']}", "status": "RECORDED", "by": o["by_name"]} for o in c["overrides"].values()]
        rows += [{"what": "Pre-referral", "detail": "; ".join(t["title"] for t in s.referrals[r]["triggers"]), "status": s.referrals[r]["status"], "by": s.referrals[r]["approver"] or ""}
                 for r in c["referrals"] if s.referrals[r]["kind"] == "pre"]
        openc = sum(1 for x in p.get("contradictions", []) if x["status"] == "OPEN")
        v["status"] = "DONE" if c["judged"] else "READY"
        v["headline"] = f"{len(rows)} judgement item(s) · {openc} contradiction(s) open · {len(c['requests'])} information request(s)"
        v["kpis"] = [{"label": "Open contradictions", "value": str(openc), "tone": "high" if openc else "ok"}, {"label": "Requests", "value": str(len(c["requests"]))},
                     {"label": "Overrides", "value": str(len(c["overrides"]))}, {"label": "Decision owner", "value": USER_BY_ID[c["uw"]]["name"]}]
        v["tables"] = [{"title": "Underwriter judgement log", "columns": [col("what", "Item"), col("detail", "Detail"), col("status", "Status", "badge"), col("by", "By")], "rows": rows}]
        v["documents"] = _docs(rt, c, {"Broker document", "Loss run", "Verification survey"})
        v["events"] = _events(c, {"05"})
        if not c["judged"]:
            v["next_action"] = {"label": "Run the underwriter's judgement", "description": "Resolves contradictions per policy, requests missing information from the broker, records overrides and pre-referrals from the case script."}
        return v
    if code == "06":
        rows = [{"v": f"v{x['version']}", "type": x["type"], "premium": x["premium"], "aop": x["aop"], "limit": x["limit"], "line": x["line"], "ms": x.get("manuscript") or "—",
                 "by": x["by_name"], "at": x["at"], "why": x.get("rationale", "")} for x in c["actions"]]
        v["status"] = "DONE" if c["actions"] else "READY"
        v["headline"] = (f"Intended action v{a['version']}: {a['type'].title()} at {money(a['premium'])} · AOP {money(a['aop'])} · limit {money(a['limit'], False)} · line {a['line'] * 100:.0f}%"
                         if a else "No intended action yet")
        if a:
            v["kpis"] = [{"label": "Action", "value": a["type"].title()}, {"label": "Premium", "value": money(a["premium"])},
                         {"label": "vs technical", "value": pct(res["deviation"], True) if res else "—"}, {"label": "By", "value": a["by_name"]}]
        v["tables"] = [{"title": "Intended actions", "columns": [col("v", "Ver"), col("type", "Action", "badge"), col("premium", "Premium", "money"), col("aop", "AOP", "money"), col("limit", "Limit", "money"),
                                                                col("line", "Line", "pct"), col("ms", "Manuscript"), col("by", "By"), col("at", "Date", "date"), col("why", "Rationale")], "rows": rows}]
        v["events"] = _events(c, {"06"})
        if not c["actions"]:
            v["next_action"] = {"label": "Submit the underwriter's intended action", "description": "From the case script: action, premium, deductible, limit, line, wording and rationale."}
        return v
    if code == "07":
        if not res:
            v["headline"] = "No intended action to assure"
            return v
        ch = [x for x in res["checks"] if x["result"] != "N/A"]
        v["status"] = "DONE"
        v["headline"] = f"{res['counts']['tier1']} tier-1 and {res['counts']['tier2']} tier-2 checks on action v{res['action_version']} · {res['counts']['fail']} fail · {res['counts']['flag']} flag · {res['counts']['pass']} pass"
        v["kpis"] = [{"label": "Tier 1 checks", "value": str(res["counts"]["tier1"])}, {"label": "Tier 2 checks", "value": str(res["counts"]["tier2"])},
                     {"label": "Fail", "value": str(res["counts"]["fail"]), "tone": "crit" if res["counts"]["fail"] else "ok"}, {"label": "Flags", "value": str(res["counts"]["flag"]), "tone": "high" if res["counts"]["flag"] else "ok"}]
        v["tables"] = [{"title": "Checks on the intended action", "columns": [col("tier", "Tier"), col("dim", "Dimension"), col("rule", "Rule", "mono"), col("subject", "Subject"), col("result", "Result", "badge"), col("observed", "Observed"), col("note", "Note")],
                        "rows": [{"tier": f"T{x['tier']}", "dim": x["dimension"].title(), "rule": x["rule_id"], "subject": x["subject"], "result": x["result"], "observed": x["observed"], "note": x["note"] or ""} for x in ch]}]
        v["findings"] = [as_finding(c, x, res["run_at"]) for x in ch if x["result"] in ("FAIL", "FLAG", "CONDITION")]
        v["events"] = _events(c, {"07"})
        return v
    if code == "08":
        if not res:
            v["headline"] = "No verdict yet"
            return v
        v["status"] = "DONE"
        v["headline"] = f"{VERDICT_LABEL[res['verdict']]} — {res['summary']}"
        v["kpis"] = [{"label": "Verdict", "value": VERDICT_LABEL[res["verdict"]], "tone": {"PASS": "ok", "PASS_WITH_FLAGS": "high", "REFER_HOLD": "crit"}[res["verdict"]]},
                     {"label": "Decision owner", "value": f"{res['owner']['name']} (L{res['owner']['level']})"}, {"label": "Exposure flagged", "value": money(res["exposure_usd"])},
                     {"label": "Conditions", "value": str(sum(1 for k in res["conditions"] if k["status"] == "OPEN"))}]
        v["tables"] = [{"title": "By dimension", "columns": [col("dim", "Dimension"), col("result", "Result", "badge"), col("summary", "Summary")],
                        "rows": [{"dim": d["label"], "result": d["result"], "summary": d["summary"]} for d in res["dimensions"]]},
                       {"title": "Remaining conditions", "columns": [col("text", "Condition"), col("due", "Due"), col("status", "Status", "badge")], "rows": res["conditions"]},
                       {"title": "Tier 3 — human judgement required", "columns": [col("why", "Reason")], "rows": [{"why": x} for x in res["tier3"]]},
                       {"title": "Referrals", "columns": [col("id", "Referral", "mono"), col("level", "Level"), col("status", "Status", "badge"), col("approver", "Approver"), col("env", "Envelope")],
                        "rows": [{"id": r, "level": f"L{s.referrals[r]['required_level']}", "status": s.referrals[r]["status"], "approver": s.referrals[r]["approver"] or "",
                                  "env": FL._env_text(s.referrals[r]["envelope"])} for r in c["referrals"]]}]
        v["events"] = _events(c, {"08"})
        if res["verdict"] == "REFER_HOLD" and not any(s.referrals[r]["status"] == "PENDING" for r in c["referrals"]):
            v["next_action"] = {"label": "Route the verdict", "description": "Refers to the level that covers the failing checks (or holds for blocking items); the approver's decision follows the case script."}
        return v
    if code == "09":
        dcs = c.get("decision")
        v["status"] = "DONE" if c["status"] in ("BOUND", "DECLINED", "LOST") else "READY" if res and res["verdict"] != "REFER_HOLD" else "PENDING"
        v["headline"] = (f"{dcs['decision'].title()} by {dcs['by']} (L{dcs['level']}) on {dcs['at']} · status {c['status'].lower()}" if dcs else "Awaiting the human final decision")
        v["kpis"] = [{"label": "Status", "value": c["status"].title()}, {"label": "Decision", "value": dcs["decision"].title() if dcs else "—"},
                     {"label": "Quote", "value": money(c["quote"]["premium"]) + f" · {c['quote']['status'].lower()}" if c.get("quote") else "—"},
                     {"label": "Bound", "value": money(c["bound"]["premium"]) if c.get("bound") else "—"}]
        rb = [x for x in (c.get("quote"), c.get("bound")) if x]
        v["tables"] = [{"title": "Policy admin documents read back by the extractor", "columns": [col("doc", "Document", "doc"), col("premium", "Premium", "money"), col("summary", "Read-back")],
                        "rows": [{"doc": x["doc_id"], "premium": x["premium"], "summary": x["readback"]["summary"]} for x in rb]},
                       {"title": "Pre-bind conditions", "columns": [col("text", "Condition"), col("source", "Source"), col("status", "Status", "badge")], "rows": [{"text": k["text"], "source": k["source"], "status": k["status"]} for k in c["conditions"]]}]
        v["documents"] = _docs(rt, c, {"Quote", "Binder"})
        v["events"] = _events(c, {"09"})
        if c["status"] not in ("BOUND", "DECLINED", "LOST"):
            v["next_action"] = {"label": "Take the final decision", "description": "Quote → broker reply (+4 days) → pre-bind conditions → bind, through the policy-admin stub; or decline."}
        return v
    if code == "10":
        o = c.get("outcome")
        v["status"] = "DONE" if o else "READY" if c.get("bound") else "NOT_APPLICABLE" if c["status"] in ("DECLINED", "LOST") else "PENDING"
        v["headline"] = ((f"Outcome {o['at']}: " + (f"{o['loss']['cause']} loss {money(o['loss']['incurred'])} at {o['loss']['location']}" + (" (excluded)" if o['loss']['excluded'] else "") if o["loss"] else "clean")
                          + f" · {o['confirmed']} of {o['flags']} flag(s) confirmed") if o else "Outcome review 6 months after bind" if c.get("bound") else "No bound policy to learn from")
        stats = []
        for rid in sorted({f["rule_id"] for f in c.get("feedback", [])}):
            s_ = s.stats.get(rid, {})
            tot = s_.get("accepted", 0) + s_.get("rejected", 0)
            stats.append({"rule": rid, "fired": len(s_.get("fired", ())), "confirmed": s_.get("confirmed", 0), "not": s_.get("not_confirmed", 0), "precision": (s_["accepted"] / tot) if tot else None})
        v["kpis"] = [{"label": "Flags on commitment", "value": str(len(c.get("feedback", [])))}, {"label": "Confirmed", "value": str(o["confirmed"]) if o else "—"},
                     {"label": "Overrides", "value": str(sum(1 for f in c.get("feedback", []) if f["overridden"]))}, {"label": "Loss excluded", "value": money(o["prevented_loss"]) if o and o.get("prevented_loss") else "—"}]
        v["tables"] = [{"title": "Flags on this case and their outcome", "columns": [col("rule", "Rule", "mono"), col("tier", "Tier"), col("ov", "Overridden", "badge"), col("out", "Outcome", "badge")],
                        "rows": [{"rule": f["rule_id"], "tier": f"T{f['tier']}", "ov": "YES" if f["overridden"] else "NO", "out": f["outcome"] or "PENDING"} for f in c.get("feedback", [])]},
                       {"title": "Rule precision across the book (dispositions + outcomes)", "columns": [col("rule", "Rule", "mono"), col("fired", "Fired"), col("confirmed", "Outcome-confirmed"), col("not", "Not confirmed"), col("precision", "Precision", "pct")], "rows": stats}]
        v["events"] = _events(c, {"10"})
        if c.get("bound") and not o:
            v["next_action"] = {"label": "Advance to the outcome review", "description": "The claims stub reports losses (or none) up to six months after bind; flags are scored against what happened."}
        return v
    return v


# ============================================================================ run a stage for a case (lifecycle & stage workspace)
def run(rt, code: str, cid: str) -> str:
    s = st(rt)
    c = s.cases[cid]
    sc = c["truth"]["script"]
    uw = c["uw"]
    if code == "01":
        if c["received"]:
            return f"Submission already received {c['received']}"
        FL.run_due(rt, cid, c["arrive"])
        p = c["pack"]
        return (f"Clock advanced to {c['arrive']}: submission parsed into {p['evidence']['facts']} anchored facts from {p['evidence']['documents']} documents; "
                f"decision pack prepared in the same run")
    if not c["received"]:
        raise ValueError(f"The submission arrives {c['arrive']} — run stage 01 first")
    p = E.build_pack(rt, cid, rt.clock)
    if code == "02":
        return (f"{p['evidence']['facts']} source-linked facts · {len(p['contradictions'])} contradiction(s)"
                + (f" ({'; '.join(x['field_label'] + ' at ' + x['location'] + ': ' + x['resolved']['value'] + ' vs ' + x['other']['value'] for x in p['contradictions'][:2])})" if p["contradictions"] else "")
                + f" · {len(p['missing'])} missing item(s)")
    if code == "03":
        px = p["pricing"]
        return (f"Technical {money(px['technical'])}, suggested {money(px['band_low'])}–{money(px['band_high'])}; required authority L{p['required_level']}"
                + (f"; {p['portfolio']['zone_name']} {pct(p['portfolio']['zone_util_before'])} → {pct(p['portfolio']['zone_util_after'])}" if p["portfolio"]["zone_name"] else ""))
    if code == "04":
        return f"Draft recommendation: {FL.DRAFT_LABEL[p['draft']['action']]} · {len(p['factors'])} risk factor(s) · before final decision: {len(p['draft']['before_final'])} item(s)"
    if code == "05":
        return judge(rt, cid)
    if code == "06":
        a, res = FL.latest(c)
        if a and not (res and res["verdict"] == "REFER_HOLD" and sc.get("revise") and _approved_or_fixed(rt, c)):
            return f"Intended action v{a['version']} already submitted: {a['type'].title()} at {money(a['premium'])}"
        raw = sc["revise"] if a else sc["action"]
        r = FL.submit_action(rt, cid, raw, uw, rt.clock)
        return f"Intended action submitted: {r['action_type'].title()} at {money(r['premium'])} ({pct(r['deviation'], True)} vs technical) → {VERDICT_LABEL[r['verdict']]}"
    if code == "07":
        a, res = FL.latest(c)
        if not a:
            run(rt, "06", cid)
            a, res = FL.latest(c)
        return res["summary"]
    if code == "08":
        return route_stage(rt, cid)
    if code == "09":
        return decide_stage(rt, cid)
    if code == "10":
        if c.get("outcome"):
            return "Outcome already recorded"
        if not c.get("bound"):
            return "No bound policy — nothing to learn from yet" if c["status"] not in ("DECLINED",) else "Declined — exposure prevented; no outcome to track"
        ev = FL.next_event(rt, cid, ("decision.outcome",))
        if ev:
            FL.run_due(rt, cid, ev["date"])
        o = c["outcome"]
        return ((f"Outcome review {o['at']}: " + (f"{o['loss']['cause']} loss {money(o['loss']['incurred'])} at {o['loss']['location']}" + (" — excluded under the reinstated exclusion" if o["loss"]["excluded"] else "") if o["loss"] else "clean, no losses"))
                + f" · {o['confirmed']} of {o['flags']} flag(s) confirmed") if o else "Outcome not yet due"


def _approved_or_fixed(rt, c: dict) -> bool:
    s = st(rt)
    return any(s.referrals[r]["status"] in ("APPROVED", "DECLINED") and s.referrals[r]["kind"] == "action" for r in c["referrals"]) or any(r["status"] == "RECEIVED" for r in c["requests"])


def judge(rt, cid: str) -> str:
    """The underwriter's judgement from the case script: resolve, override, request, pre-refer."""
    s = st(rt)
    c = s.cases[cid]
    sc = c["truth"]["script"]
    uw = c["uw"]
    msgs = []
    n = FL.resolve_all(rt, cid, uw, rt.clock)
    if n:
        msgs.append(f"{n} contradiction(s) resolved on the verified source")
    for ov in sc.get("override", []):
        uids = list(rt.store.account_locations(cid))
        subj = uids[ov["loc"]] if "loc" in ov else None
        key = f"{ov['rule']}|{subj or 'case'}"
        if key not in c["overrides"]:
            FL.override(rt, cid, ov["rule"], subj, ov["reason"], uw, rt.clock)
            msgs.append(f"override recorded on {ov['rule']}")
    if sc.get("request") and not sc.get("request_after_verdict") and not sc.get("survey") and not c["requests"]:
        FL.request_info(rt, cid, sc["request"], uw, rt.clock)
        msgs.append(f"requested from broker: {'; '.join(sc['request'])}")
    if sc.get("prerefer") and not any(s.referrals[r]["kind"] == "pre" for r in c["referrals"]):
        ref = FL.prerefer(rt, cid, sc["prerefer"]["note"], uw, rt.clock)
        pr = sc["prerefer"]
        FL.decide_referral(rt, ref["referral_id"], "APPROVE", pr.get("conditions"), pr.get("envelope"), "Approved on the evidence", pr["approver"], rt.clock)
        msgs.append(f"pre-referred to L{ref['required_level']} and approved by {USER_BY_ID[pr['approver']]['name']} ({FL._env_text(ref['envelope'])})")
    c["judged"] = True
    return "; ".join(msgs).capitalize() if msgs else "Pack reviewed — nothing to resolve"


def route_stage(rt, cid: str) -> str:
    s = st(rt)
    c = s.cases[cid]
    sc = c["truth"]["script"]
    uw = c["uw"]
    a, res = FL.latest(c)
    if not res:
        run(rt, "06", cid)
        a, res = FL.latest(c)
    if res["verdict"] != "REFER_HOLD":
        return f"{VERDICT_LABEL[res['verdict']]} — {res['owner']['name']} decides; no referral"
    if sc.get("request_after_verdict"):
        req = FL.request_info(rt, cid, sc["request"], uw, rt.clock)
        FL.run_due(rt, cid, req["due"])
        r = FL.submit_action(rt, cid, sc["revise"], uw, rt.clock)
        return (f"Hold: requested {'; '.join(sc['request'])}; broker returned it {req['due']}; technical now {money(r['technical'])}; "
                f"revised to {r['action_type'].title()} at {money(r['premium'])} ({pct(r['deviation'], True)}) → {VERDICT_LABEL[r['verdict']]}")
    msg = FL.route(rt, cid, uw, rt.clock)
    pend = [r for r in c["referrals"] if s.referrals[r]["status"] == "PENDING"]
    if not pend:
        return msg
    ref = s.referrals[pend[-1]]
    rd = sc.get("referral_decision") or {"approver": E.APPROVERS.get(min(4, ref["required_level"])), "decision": "APPROVE", "conditions": [], "envelope": None}
    ap = rd["approver"] if USER_BY_ID[rd["approver"]]["authority_level"] >= ref["required_level"] else E.APPROVERS[min(4, ref["required_level"])]
    FL.decide_referral(rt, ref["referral_id"], rd["decision"], rd.get("conditions"), rd.get("envelope"), rd.get("note", ""), ap, rt.clock)
    out = f"{msg} · {rd['decision'].lower()}d by {USER_BY_ID[ap]['name']}"
    if rd["decision"] == "APPROVE" and sc.get("revise"):
        r = FL.submit_action(rt, cid, sc["revise"], uw, rt.clock)
        out += f" · revised action {r['action_type'].title()} at {money(r['premium'])} → {VERDICT_LABEL[r['verdict']]}"
    elif rd["decision"] == "APPROVE":
        r = FL.submit_action(rt, cid, sc["action"], uw, rt.clock)
        out += f" · re-assured → {VERDICT_LABEL[r['verdict']]}"
    return out


def decide_stage(rt, cid: str) -> str:
    s = st(rt)
    c = s.cases[cid]
    sc = c["truth"]["script"]
    uw = c["uw"]
    a, res = FL.latest(c)
    if c["status"] in ("BOUND", "DECLINED", "LOST"):
        return f"Already {c['status'].lower()}"
    if any(s.referrals[r]["status"] == "DECLINED" and s.referrals[r]["kind"] == "action" for r in c["referrals"]) or (c["pack"]["draft"]["action"] == "DECLINE" and not sc.get("override")):
        ref = next((s.referrals[r] for r in c["referrals"] if s.referrals[r]["status"] == "DECLINED"), None)
        return FL.final_decision(rt, cid, "DECLINE", ref["approver_id"] if ref else uw, rt.clock, (ref or {}).get("decision_note") or "Outside appetite")
    if not res or res["verdict"] == "REFER_HOLD":
        raise ValueError("Verdict is refer / hold — route it first (stage 08)")
    msgs = []
    if not c.get("quote"):
        if res["action_type"] == "BIND":
            FL.submit_action(rt, cid, {**{k: a.get(k) for k in ("aop", "ns_pct", "ns_min", "wh_pct", "line", "limit", "manuscript", "premium")}, "type": "QUOTE", "rationale": a.get("rationale")}, uw, rt.clock)
        msgs.append(FL.final_decision(rt, cid, "COMMIT", uw, rt.clock))
    for item in sc.get("request", []) if sc.get("survey") else []:
        if not any(item in r["items"] for r in c["requests"]):
            FL.request_info(rt, cid, [item], uw, rt.clock)
    if sc.get("survey") and not c.get("surveys"):
        msgs.append(FL.order_inspection(rt, cid, uw, rt.clock, "Verify in-rack sprinklers and roof condition"))
    due = [x["date"] for x in rt.dynamic if not x.get("done") and x.get("case_id") == cid and x["type"] in ("decision.broker_quote", "decision.broker_docs", "decision.inspection")]
    if due:
        FL.run_due(rt, cid, max(due))
        msgs.append(f"clock → {rt.clock}: broker {c['quote']['status'].lower().replace('_', ' ')}")
    if c["status"] == "LOST":
        return " · ".join(msgs)
    msgs.append(FL.bind(rt, cid, uw, rt.clock))
    return " · ".join(msgs)


def facts(rt, cid: str) -> list[dict]:
    s = st(rt)
    c = s.cases.get(cid)
    if not c:
        return []
    out = [{"label": "Case", "value": f"{c['insured']} · {c.get('scenario') or ''}"}, {"label": "Status", "value": c["status"].replace("_", " ").title()}]
    p = c.get("pack")
    if p:
        out += [{"label": "Technical premium", "value": f"{money(p['pricing']['technical'])} (suggested {money(p['pricing']['band_low'])}–{money(p['pricing']['band_high'])})"},
                {"label": "Decision pack", "value": f"{p['evidence']['facts']} source-linked facts · {len(p['contradictions'])} contradiction(s) · draft {FL.DRAFT_LABEL[p['draft']['action']].lower()}"}]
    a, res = FL.latest(c)
    if res:
        out += [{"label": f"Intended action v{a['version']}", "value": f"{a['type'].title()} {money(a['premium'])} ({pct(res['deviation'], True)} vs technical)"},
                {"label": "Assurance verdict", "value": f"{VERDICT_LABEL[res['verdict']]} · owner {res['owner']['name']}"}]
    for r in c["referrals"][-1:]:
        ref = s.referrals[r]
        out.append({"label": "Latest referral", "value": f"L{ref['required_level']} · {ref['status'].lower()}" + (f" by {ref['approver']}" if ref["approver"] else "")})
    if c.get("quote"):
        out.append({"label": "Quote", "value": f"{money(c['quote']['premium'])} · {c['quote']['status'].lower().replace('_', ' ')}"})
    if c.get("bound"):
        out.append({"label": "Bound", "value": f"{c['bound']['at']} at {money(c['bound']['premium'])}"})
    ex = case_exposure(rt, c)
    if ex["total"]:
        out.append({"label": "Exposure corrected / prevented", "value": money(ex["total"])})
    if c.get("outcome"):
        o = c["outcome"]
        out.append({"label": "Outcome", "value": (f"{o['loss']['cause']} {money(o['loss']['incurred'])}" + (" (excluded)" if o["loss"]["excluded"] else "") if o["loss"] else "clean") + f" · {o['confirmed']}/{o['flags']} flags confirmed"})
    return out


def case_exposure(rt, c: dict) -> dict:
    """Material underwriting exposure corrected or prevented before commitment, premium-equivalent $ (see guide)."""
    prep = sum(x["impact_usd"] for x in c.get("contradictions", []) if x["status"] == "RESOLVED" and x.get("adverse_resolved") and x["material"])
    asr = 0
    kind = None
    advs = [x for x in c["assurances"] if x["verdict"] == "REFER_HOLD"]
    if advs:
        first = advs[0]
        a0 = next(x for x in c["actions"] if x["action_id"] == first["action_id"])
        if c["status"] == "DECLINED":
            asr, kind = first["technical"], "declined"
        else:
            fin = c["actions"][-1]
            if fin["action_id"] != a0["action_id"]:
                last = c["assurances"][-1]
                asr = max(0, fin["premium"] - a0["premium"]) + max(0, first["technical"] - last["technical"] if fin["line"] < a0["line"] or fin.get("manuscript") != a0.get("manuscript") else 0)
                kind = "corrected"
    elif c["status"] == "DECLINED" and c.get("pack"):
        asr, kind = c["pack"]["pricing"]["technical"], "declined at preparation"
    return {"preparation": round(prep), "assurance": round(asr), "total": round(prep + asr), "kind": kind,
            "loss_avoided": (c.get("outcome") or {}).get("prevented_loss") or 0}

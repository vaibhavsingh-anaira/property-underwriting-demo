"""Stage workspaces for the 11-stage delegated authority pipeline (same StageView shape as uwc.stages.build)."""
from __future__ import annotations

from . import actions as A
from . import baa as B
from . import engine as E
from . import views as V
from .refdata import COVERHOLDERS, MONTH_LABEL, TXN_LABEL

STANDS_IN = {"01": "Anaira contract extraction · Lloyd's DA registry / binder store", "02": "Coverholder portal · bordereau inbox (Lloyd's DDM / Xchanging)",
             "03": "Anaira bordereau mapper (CRS v5.2)", "04": "Anaira authority rules", "05": "Carrier referral system (e.g. Duck Creek / Send referral queue)",
             "06": "Carrier finance ledger (e.g. Charles Taylor / SAP FS-CD)", "07": "Anaira aggregates · CAT accumulation feed (e.g. Verisk / Moody's RMS)",
             "08": "Anaira claims controls · TPA / coverholder claims system", "09": "Anaira breach register", "10": "Coverholder (MGA) — email and portal",
             "11": "Anaira reporting · DA registry endorsement store"}


def col(key, label, kind="text"):
    return {"key": key, "label": label, "kind": kind}


def _events(st, ch, stages):
    return [e for e in reversed(st["timeline"].get(ch, [])) if e["stage"] in stages][:40]


def _docs(st, rt, ch, types):
    out = [V.doc_meta(rt, d) for d in st["docs"].get(ch, []) if (rt.store.docs.get(d) or {}).get("doc_type") in types]
    return sorted([d for d in out if d], key=lambda d: d["received_at"], reverse=True)


def _next_arrival(rt, ch):
    ev = sorted([e for e in rt.dynamic if e["type"] == "delegated.bordereau" and e.get("subject_id") == ch and not e.get("done")], key=lambda e: e["date"])
    return ev[0] if ev else None


def _next_response(rt, ch):
    ev = sorted([e for e in rt.dynamic if e["type"] in ("delegated.response", "delegated.audit") and e.get("subject_id") == ch and not e.get("done")], key=lambda e: e["date"])
    return ev[0] if ev else None


def _latest_bdx(st, ch, kind="risk"):
    bs = [b for b in st["bdx"].values() if b["ch"] == ch and b["kind"] == kind and not b.get("correction") or (b["ch"] == ch and b["kind"] == kind and b.get("replaces"))]
    bs = [b for b in bs if not b.get("superseded_by")]
    return max(bs, key=lambda b: (b["month"], b["received"])) if bs else None


def build(rt, code, ch, pipe) -> dict:
    st = rt.delegated
    meta = next(p for p in pipe if p[0] == code)
    cfg = COVERHOLDERS[ch]
    v = {"code": code, "name": meta[1], "group": meta[2], "component": meta[3], "mode": meta[4], "description": meta[5], "port": meta[6], "stands_in_for": STANDS_IN[code],
         "account": {"account_id": ch, "name": cfg["name"], "scenario": cfg["scenario"], "href": f"/delegated/coverholders/{ch}"}, "clock": rt.clock, "status": "PENDING",
         "headline": "", "kpis": [], "tables": [], "documents": [], "events": [], "findings": [], "next_action": None}
    terms, anchors, ver = E.authority(st, ch, rt.clock)
    lm = V.latest_month(st, ch)
    if code == "01":
        versions = st["authority"][ch]
        av = V.authority_view(st, rt, ch)
        v["status"] = "DONE"
        v["headline"] = (f"{cfg['agreement']} parsed from PDF into {versions[0]['parsed_terms']} anchored terms · authority v{ver} in force "
                         f"({len(versions) - 1} endorsement{'s' if len(versions) != 2 else ''})")
        v["kpis"] = [{"label": "Authority period", "value": f"{terms['period_start'][:7]} → {terms['period_end'][:7]}"}, {"label": "Max limit any one risk", "value": B.usd(terms.get("max_limit"))},
                     {"label": "Commission", "value": B.pctf(terms.get("commission_pct") or 0)}, {"label": "Classes · territories", "value": f"{len(terms.get('classes', {}))} · {len(terms.get('territories', {}))}"}]
        v["tables"] = [{"title": "Authority terms in force (read back from the agreement and endorsements)", "columns": [col("label", "Term"), col("value", "Value"), col("doc", "Source", "doc")],
                        "rows": [{"label": k["label"], "value": k["value"], "doc": k["doc_id"]} for k in av["kv"]]},
                       {"title": "Authority versions", "columns": [col("version", "v"), col("title", "Document"), col("effective", "Effective", "date"), col("changes", "Changes"), col("doc", "Open", "doc")],
                        "rows": [{"version": x["version"], "title": x["title"], "effective": x["effective"], "changes": "; ".join(f"{c['label']}: {c['from']} → {c['to']}" for c in x["changes"]) or "Original agreement",
                                  "doc": x["doc_id"]} for x in av["versions"]]}]
        v["documents"] = _docs(st, rt, ch, {"Binding authority agreement", "BAA endorsement"})
        v["events"] = _events(st, ch, {"01"})
        v["next_action"] = {"label": "Re-read the agreement and endorsements", "description": "Runs the layout extractor on every authority PDF again and rebuilds the versioned authority."}
    elif code == "02":
        bs = [b for b in V.bordereaux(st, rt, ch) if not b["correction"]]
        nxt = _next_arrival(rt, ch)
        risk = [b for b in bs if b["kind"] == "risk"]
        v["status"] = "DONE" if bs else "READY"
        v["headline"] = (f"{len(bs)} files received · latest {MONTH_LABEL.get(lm, lm)} on {risk[0]['received']}" + (f" ({risk[0]['days_late']} days late)" if risk and risk[0]["days_late"] else " (on time)")
                         if risk else "Waiting for the first bordereau")
        v["kpis"] = [{"label": "Files received", "value": str(len(bs))}, {"label": "On time", "value": f"{sum(1 for b in risk if not b['days_late'])}/{len(risk)}", "tone": "ok" if all(not b['days_late'] for b in risk) else "high"},
                     {"label": "Next due", "value": nxt["date"] if nxt else "—"}, {"label": "Channel", "value": "Portal (mock)"}]
        v["tables"] = [{"title": "Bordereau inbox", "columns": [col("month", "Period"), col("kind", "Type", "badge"), col("received", "Received", "date"), col("due", "Due", "date"), col("late", "Days late"),
                                                                  col("rows", "Rows"), col("doc", "Open", "doc")],
                        "rows": [{"month": MONTH_LABEL.get(b["month"], b["month"]), "kind": b["kind"].upper(), "received": b["received"], "due": b["due"], "late": b["days_late"] or "—", "rows": b["rows"], "doc": b["doc_id"]} for b in bs]}]
        v["documents"] = _docs(st, rt, ch, {"Risk bordereau", "Premium bordereau", "Claims bordereau", "Exposure return"})
        v["events"] = _events(st, ch, {"02"})
        if nxt:
            v["next_action"] = {"label": f"Advance clock to {nxt['date']} — {nxt['title']}", "description": "Replays the coverholder portal to the next submission; the files are parsed and checked on arrival."}
    elif code == "03":
        b = _latest_bdx(st, ch)
        if b:
            v["status"] = "DONE"
            v["headline"] = (f"{b['title']}: {len([m for m in b['mapping'] if m['field']])}/{len(b['mapping'])} columns mapped to CRS v5.2 · confidence {b['stats']['mapping_confidence'] * 100:.0f}% · "
                             f"DQ {b['dq_score']:.0f}/100" + (f" · {len(b['missing'])} mandatory field(s) missing" if b["missing"] else ""))
            v["kpis"] = [{"label": "Mapping confidence", "value": f"{b['stats']['mapping_confidence'] * 100:.0f}%", "tone": "ok" if b["stats"]["mapping_confidence"] > 0.9 else "high"},
                         {"label": "DQ score", "value": f"{b['dq_score']:.0f}", "tone": "ok" if b["dq_score"] >= 90 else "high" if b["dq_score"] >= 75 else "crit"},
                         {"label": "Missing mandatory", "value": str(len(b["missing"])), "tone": "crit" if b["missing"] else "ok"}, {"label": "Validation issues", "value": str(len(b["issues"]))}]
            v["tables"] = [{"title": f"Column mapping — {b['title']}", "columns": [col("col", "Col", "mono"), col("header", "Header in file"), col("field", "CRS v5.2 field"), col("conf", "Confidence", "pct"), col("method", "Method", "badge")],
                            "rows": [{"col": m["col"], "header": m["header"], "field": m["label"] or "— unmapped", "conf": m["confidence"], "method": m["method"].upper()} for m in b["mapping"]]
                            + [{"col": "—", "header": "(absent)", "field": x, "conf": 0, "method": "MISSING"} for x in b["missing_labels"]]},
                           {"title": "Validation issues (click Open to see the file)", "columns": [col("sev", "Severity", "badge"), col("code", "Check", "mono"), col("cell", "Cell", "mono"), col("label", "Issue"), col("doc", "Open", "doc")],
                            "rows": [{"sev": i["severity"], "code": i["code"], "cell": i["cell"] or "—", "label": i["label"], "doc": b["doc_id"]} for i in b["issues"][:120]]}]
            v["documents"] = _docs(st, rt, ch, {"Risk bordereau", "Premium bordereau"})
            v["next_action"] = {"label": "Re-run the mapper on the latest risk bordereau", "description": "Header detection, CRS synonym mapping and validation on the file as received."}
        else:
            v["headline"] = "No bordereau received yet"
        v["events"] = _events(st, ch, {"03", "04"})
    elif code == "04":
        ms = E.month_stats(st, ch, lm) if lm else None
        reg = [r for r in V.register(st, rt, {"ch": ch, "status": "all", "subject": "policy"})]
        v["status"] = "DONE" if ms else "PENDING"
        if ms:
            v["headline"] = (f"{MONTH_LABEL[lm]}: {ms['policies']} lines checked against authority v{ver} · {ms['with_exceptions']} with exceptions ({ms['exception_rate'] * 100:.1f}%) · "
                             f"trend " + " → ".join(f"{t['rate'] * 100:.1f}%" for t in E.scorecard(st, rt, ch)["trend"]))
            v["kpis"] = [{"label": "Lines checked", "value": f"{ms['policies']:,}"}, {"label": "With exceptions", "value": str(ms["with_exceptions"]), "tone": "crit" if ms["with_exceptions"] else "ok"},
                         {"label": "Exception rate", "value": f"{ms['exception_rate'] * 100:.1f}%"}, {"label": "Within authority (now)", "value": f"{ms['within_authority'] * 100:.1f}%"}]
        v["tables"] = [{"title": "Policies with authority exceptions (all months)", "columns": [col("month", "Month"), col("cert", "Certificate", "mono"), col("insured", "Insured"), col("check", "Checks"),
                                                                                                  col("status", "Status", "badge"), col("tied", "Premium tied", "money")],
                        "rows": [{"month": MONTH_LABEL.get(r["month"], r["month"]), "cert": r["certificate_ref"], "insured": r["insured"], "check": "; ".join(f"{c['check']} {c['written']} vs {c['authority']}" for c in r["checks"] if c["status"] != "AUTHORISED")[:160],
                                  "status": r["status"], "tied": r["premium_tied"]} for r in reg]}]
        v["documents"] = _docs(st, rt, ch, {"Risk bordereau"})
        v["events"] = _events(st, ch, {"04"})
        v["next_action"] = {"label": "Re-run every authority check", "description": "Re-evaluates every bordereau line against the authority in force on the date it was written."}
    elif code == "05":
        refs = [e for e in st["exceptions"].values() if e["ch"] == ch and e.get("referral")]
        ok = [e for e in refs if e["referral"]["result"] == E.REFER_OK]
        miss = [e for e in refs if e["referral"]["result"] != E.REFER_OK and E.raised(e)]
        recs = [r for r in st["referrals"] if r["ch"] == ch and r["requested"] <= rt.clock]
        v["status"] = "DONE" if refs else "NOT_APPLICABLE"
        v["headline"] = f"{len(refs)} referral triggers · {len(ok)} matched to an approval · {len(miss)} without a valid approval (missing, declined or different terms)"
        v["kpis"] = [{"label": "Triggers", "value": str(len(refs))}, {"label": "Approval matched", "value": str(len(ok)), "tone": "ok"},
                     {"label": "No valid approval", "value": str(len(miss)), "tone": "crit" if miss else "ok"}, {"label": "Referral system records", "value": str(len(recs))}]
        v["tables"] = [{"title": "Referral reconciliation — triggers without a valid approval", "columns": [col("cert", "Certificate", "mono"), col("insured", "Insured"), col("check", "Trigger"),
                                                                                                             col("ref", "Ref on bordereau", "mono"), col("result", "Result", "badge"), col("detail", "Detail"), col("status", "Status", "badge")],
                        "rows": [{"cert": e["certificate_ref"], "insured": e["insured"], "check": e["check"], "ref": e["referral"].get("ref") or "—", "result": e["referral"]["result"],
                                  "detail": e["referral"]["detail"], "status": e["status"]} for e in miss]},
                       {"title": "Carrier referral system (mock) — requests from this coverholder", "columns": [col("ref", "Ref", "mono"), col("cert", "Certificate", "mono"), col("insured", "Insured"),
                                                                                                                col("requested", "Requested", "date"), col("status", "Decision", "badge"), col("approver", "By"), col("reasons", "Reasons")],
                        "rows": [{"ref": r["ref"], "cert": r["certificate_ref"], "insured": r["insured"], "requested": r["requested"], "status": r["status"], "approver": r["approver"] or "—",
                                  "reasons": "; ".join(r["reasons"])[:120]} for r in recs[::-1][:80]]}]
        v["events"] = _events(st, ch, {"05"})
        v["next_action"] = {"label": "Reconcile to the referral system", "description": "Looks up every referral trigger's reference in the carrier referral system and checks that the approval pre-dates binding and covers the written terms."}
    elif code == "06":
        comm = [e for e in st["exceptions"].values() if e["ch"] == ch and e["family"] in ("commission", "premium") and E.raised(e)]
        open_c = [e for e in comm if e["status"] in E.OPEN_STATES and e["family"] == "commission"]
        led = [x for x in st["ledger"] if x["ch"] == ch]
        cap = E.capacity(st, ch, rt.clock)
        pb = _latest_bdx(st, ch, "premium")
        v["status"] = "DONE" if pb else "PENDING"
        v["headline"] = (f"Commission contract {B.pctf(terms.get('commission_pct') or 0)} · {len(open_c)} open over-deduction(s) worth ${sum(e['impact_usd'] for e in open_c):,.0f} · "
                         f"{len(led)} debit note(s) posted · GPI {(cap['util'] or 0) * 100:.0f}% of limit (projected)")
        v["kpis"] = [{"label": "Open commission $", "value": f"${sum(e['impact_usd'] for e in open_c):,.0f}", "tone": "crit" if open_c else "ok"},
                     {"label": "Debit notes", "value": str(len(led))}, {"label": "GWP YTD", "value": B.usd(cap["ytd"])}, {"label": "Premium bdx issues", "value": str(len(pb["issues"])) if pb else "—"}]
        v["tables"] = [{"title": "Premium & commission exceptions", "columns": [col("cert", "Certificate", "mono"), col("insured", "Insured"), col("check", "Check"), col("written", "Reported"),
                                                                                 col("authority", "Contract"), col("amount", "Discrepancy", "money"), col("status", "Status", "badge")],
                        "rows": [{"cert": e["certificate_ref"], "insured": e["insured"], "check": e["check"], "written": e["written"], "authority": e["authority"], "amount": e["impact_usd"], "status": e["status"]} for e in comm]},
                       {"title": "Finance ledger (mock)", "columns": [col("id", "Entry", "mono"), col("date", "Date", "date"), col("type", "Type"), col("amount", "Amount", "money"), col("status", "Status", "badge"), col("doc", "Open", "doc")],
                        "rows": [{"id": x["entry_id"], "date": x["date"], "type": x["type"], "amount": x["amount"], "status": x["status"], "doc": x["doc_id"]} for x in led]}]
        v["documents"] = _docs(st, rt, ch, {"Premium bordereau", "Debit note"})
        v["events"] = _events(st, ch, {"06"})
        if open_c:
            v["next_action"] = {"label": "Post the commission reconciliation", "description": "Raises a debit note in the finance ledger (mock) for commission deducted above the contract rate."}
    elif code == "07":
        zs = E.aggregates(st, ch, rt.clock)
        hot = [z for z in zs if z["util"] and z["util"] >= (z["warn"] or 0.9)]
        rest = [r for r in st["restrictions"] if r["ch"] == ch]
        prev = [p for p in st["prevented"] if p["ch"] == ch]
        v["status"] = "DONE"
        v["headline"] = (f"{len(zs)} zones monitored · top {zs[0]['name']} {zs[0]['util'] * 100:.1f}% of limit" + (f" · {len(hot)} above warning" if hot else "") +
                         (f" · {rest[-1]['name']} restricted ({rest[-1]['mode'].lower()}) since {rest[-1]['effective']}" if rest else "") +
                         (f" · {len(prev)} risks declined, ${sum(p['tiv'] for p in prev):,.0f} TIV kept off the zone" if prev else ""))
        v["kpis"] = [{"label": "Top zone", "value": f"{zs[0]['zone']} {zs[0]['util'] * 100:.1f}%", "tone": "crit" if hot else "ok"}, {"label": "Above warning", "value": str(len(hot)), "tone": "crit" if hot else "ok"},
                     {"label": "Restrictions", "value": str(len(rest))}, {"label": "Exposure prevented", "value": B.usd(sum(p["tiv"] for p in prev))}]
        v["tables"] = [{"title": "Aggregates vs thresholds (exposure return + bordereau movements · CAT feed zones)", "columns": [col("zone", "Zone", "mono"), col("name", "Name"), col("peril", "Peril"), col("tiv", "In-force TIV", "money"),
                                                                                                                          col("limit", "Limit", "money"), col("util", "Utilisation", "pct"), col("status", "Status", "badge"), col("pml", "1-in-100 PML", "money")],
                        "rows": [{"zone": z["zone"], "name": z["name"], "peril": z["peril"], "tiv": z["tiv"], "limit": z["limit"], "util": z["util"], "status": ("ABOVE WARNING " if z["util"] >= z["warn"] else "") + z["status"].upper(), "pml": z["pml_100"]} for z in zs]},
                       {"title": "Incremental business declined at the carrier's referral desk (mock decision)", "columns": [col("date", "Date", "date"), col("cert", "Certificate", "mono"), col("insured", "Insured"), col("tiv", "TIV", "money"), col("ref", "Referral", "mono")],
                        "rows": [{"date": p["date"], "cert": p["certificate_ref"], "insured": p["insured"], "tiv": p["tiv"], "ref": p["ref"]} for p in prev]}]
        v["documents"] = _docs(st, rt, ch, {"Exposure return", "BAA endorsement"})
        v["events"] = _events(st, ch, {"07"}) + _events(st, ch, {"11"})[:3]
        if hot and not any(r["zone"] == hot[0]["zone"] for r in rest):
            v["next_action"] = {"label": f"Refer incremental business in {hot[0]['name']}", "description": "Issues an endorsement to the BAA (PDF, parsed back) setting the zone to referral-only from tomorrow."}
    elif code == "08":
        cl = V.claims(st, ch)
        ex = [e for e in st["exceptions"].values() if e["ch"] == ch and e["subject_type"] == "claim" and e["status"] in E.OPEN_STATES]
        sc = E.scorecard(st, rt, ch)
        v["status"] = "DONE" if cl else "PENDING"
        v["headline"] = f"{len(cl)} claims on the latest claims bordereau · incurred ${sum(c['incurred'] or 0 for c in cl):,.0f} · {len(ex)} open claims exceptions · incurred ÷ written {(sc['loss_ratio'] or 0) * 100:.1f}%"
        v["kpis"] = [{"label": "Claims", "value": str(len(cl))}, {"label": "Incurred", "value": B.usd(sum(c['incurred'] or 0 for c in cl))}, {"label": "Open exceptions", "value": str(len(ex)), "tone": "crit" if ex else "ok"},
                     {"label": "Incurred ÷ written", "value": f"{(sc['loss_ratio'] or 0) * 100:.1f}%"}]
        v["tables"] = [{"title": "Claims exceptions", "columns": [col("claim", "Claim", "mono"), col("insured", "Insured"), col("check", "Check"), col("written", "Observed"), col("status", "Status", "badge"), col("amount", "$", "money")],
                        "rows": [{"claim": e.get("claim_ref"), "insured": e["insured"], "check": e["title"], "written": e["written"], "status": e["status"], "amount": e["impact_usd"]} for e in ex]},
                       {"title": "Claims bordereau (latest snapshot)", "columns": [col("claim", "Claim", "mono"), col("cert", "Certificate", "mono"), col("insured", "Insured"), col("dol", "Loss", "date"), col("cause", "Cause"),
                                                                                    col("paid", "Paid", "money"), col("reserve", "Reserve", "money"), col("incurred", "Incurred", "money"), col("change", "Movement", "money"), col("doc", "Open", "doc")],
                        "rows": [{"claim": c["claim_ref"], "cert": c["certificate_ref"], "insured": c["insured_name"], "dol": c["date_of_loss"], "cause": c["cause"], "paid": c["paid"], "reserve": c["reserve"],
                                  "incurred": c["incurred"], "change": c["incurred_change"], "doc": c["doc_id"]} for c in cl]}]
        v["documents"] = _docs(st, rt, ch, {"Claims bordereau"})
        v["events"] = _events(st, ch, {"08"})
        if ex and not any(e["status"] == "QUERIED" for e in ex):
            v["next_action"] = {"label": "Query the coverholder on the claims exceptions", "description": "Requests the claim files and explanations; the coverholder replies after a few days."}
    elif code == "09":
        reg = V.register(st, rt, {"ch": ch, "status": "open"})
        openx = [e for e in st["exceptions"].values() if e["ch"] == ch and e["status"] == "OPEN"]
        v["status"] = "DONE" if reg else "NOT_APPLICABLE"
        v["headline"] = f"{len(reg)} open items in the breach register · ${sum(r['impact_usd'] for r in reg):,.0f} at stake · {len(openx)} exception(s) not yet queried"
        v["kpis"] = [{"label": "Open items", "value": str(len(reg)), "tone": "crit" if reg else "ok"}, {"label": "Not yet queried", "value": str(len(openx))},
                     {"label": "Premium tied", "value": B.usd(sum(r["premium_tied"] for r in reg))}, {"label": "Escalated", "value": str(sum(1 for r in reg if r["status"] == "ESCALATED"))}]
        v["tables"] = [{"title": "Breach register — open items", "columns": [col("month", "Month"), col("cert", "Certificate / subject", "mono"), col("insured", "Insured / subject"), col("checks", "Exceptions"),
                                                                            col("status", "Status", "badge"), col("stake", "$ at stake", "money")],
                        "rows": [{"month": MONTH_LABEL.get(r["month"], r["month"]), "cert": r["certificate_ref"], "insured": r["insured"], "checks": "; ".join(c["check"] for c in r["checks"] if c["status"] in E.OPEN_STATES)[:120],
                                  "status": r["status"], "stake": r["impact_usd"]} for r in reg]}]
        v["events"] = _events(st, ch, {"09"})
        if openx:
            v["next_action"] = {"label": f"Query the coverholder on {len(openx)} open exception(s)", "description": "Sends one query with the side-by-side authority result per policy; the mocked coverholder replies after a few days."}
    elif code == "10":
        qs = [q for q in st["queries"] if q["ch"] == ch]
        nxt = _next_response(rt, ch)
        v["status"] = "DONE" if qs else "NOT_APPLICABLE"
        v["headline"] = (f"{len(qs)} queries · {sum(1 for q in qs if q['status'] == 'SENT')} awaiting a reply" + (f" · next reply due {nxt['date']}" if nxt else "")) if qs else "No queries raised"
        v["kpis"] = [{"label": "Queries", "value": str(len(qs))}, {"label": "Awaiting reply", "value": str(sum(1 for q in qs if q["status"] == "SENT"))},
                     {"label": "Reply time (mock)", "value": f"{cfg['response_days']} days"}, {"label": "Turnaround", "value": f"{E.scorecard(st, rt, ch)['turnaround_days'] or '—'} days"}]
        v["tables"] = [{"title": "Queries and coverholder responses", "columns": [col("id", "Query", "mono"), col("created", "Sent", "date"), col("kind", "Type", "badge"), col("items", "Items"), col("status", "Status", "badge"),
                                                                                  col("responded", "Replied", "date"), col("summary", "Outcome"), col("doc", "Reply", "doc")],
                        "rows": [{"id": q["query_id"], "created": q["created"], "kind": q["kind"].upper(), "items": len(q["items"]), "status": q["status"], "responded": q["responded"],
                                  "summary": ", ".join(f"{k.replace('_', ' ')} {v_}" for k, v_ in (q["summary"] or {}).items() if v_ and k not in ("dq_before",)), "doc": q["response"] or q["doc_id"]} for q in qs[::-1]]}]
        v["documents"] = _docs(st, rt, ch, {"Carrier query", "Coverholder response", "Risk bordereau"})
        v["events"] = _events(st, ch, {"10"})
        if nxt:
            v["next_action"] = {"label": f"Advance clock to {nxt['date']} — {nxt['title']}", "description": "The mocked coverholder replies by rule; corrected bordereaux are parsed and re-checked."}
    elif code == "11":
        sc = E.scorecard(st, rt, ch)
        reps = [r for r in st["reports"] if r["ch"] == ch]
        am = [a for a in st["amendments"] if a["ch"] == ch]
        rq = E.rarc(st, ch)["quarters"]
        v["status"] = "DONE" if reps else "READY"
        v["headline"] = (f"Scorecard {sc['grade']} ({sc['score']:.0f}) · within authority {sc['within_authority'] * 100:.1f}% · exception trend {sc['direction']} · "
                         + (f"{rq[-1]['quarter']} RARC {rq[-1]['rarc'] * 100:+.1f}% vs headline {rq[-1]['headline'] * 100:+.1f}%" if rq and rq[-1]["rarc"] is not None else "no renewals yet"))
        v["kpis"] = [{"label": "Grade", "value": f"{sc['grade']} · {sc['score']:.0f}", "tone": "ok" if sc["grade"] in "AB" else "high" if sc["grade"] == "C" else "crit"},
                     {"label": "Within authority", "value": f"{sc['within_authority'] * 100:.1f}%"}, {"label": "DQ score", "value": f"{sc['dq_score'] or 0:.0f}"},
                     {"label": "Avg days late", "value": f"{sc['avg_days_late']:.0f}"}]
        v["tables"] = [{"title": "Scorecard components (0–100)", "columns": [col("k", "Component"), col("v", "Score"), col("basis", "Basis")],
                        "rows": [{"k": "Authority", "v": sc["components"]["authority"], "basis": f"latest exception rate {sc['trend'][-1]['rate'] * 100:.1f}%" if sc["trend"] else ""},
                                 {"k": "Data quality", "v": sc["components"]["data_quality"], "basis": "CRS completeness, validity, mapping, consistency"},
                                 {"k": "Timeliness", "v": sc["components"]["timeliness"], "basis": f"avg {sc['avg_days_late']} days late"},
                                 {"k": "Loss", "v": sc["components"]["loss"], "basis": f"incurred ÷ written {(sc['loss_ratio'] or 0) * 100:.1f}%"},
                                 {"k": "Trend", "v": sc["components"]["trend"], "basis": sc["direction"]}]},
                       {"title": "Quarterly RARC from bordereaux", "columns": [col("q", "Quarter"), col("n", "Renewals used"), col("headline", "Headline", "pct"), col("exp", "TIV change", "pct"), col("rarc", "RARC", "pct")],
                        "rows": [{"q": q["label"], "n": f"{q['used']} of {q['renewals']}", "headline": q["headline"], "exp": q["exposure_change"], "rarc": q["rarc"]} for q in rq]},
                       {"title": "Reports issued and authority amendments", "columns": [col("id", "Ref", "mono"), col("date", "Date", "date"), col("what", "What"), col("doc", "Open", "doc")],
                        "rows": [{"id": r["report_id"], "date": r["issued"], "what": f"Authority report {MONTH_LABEL[r['month']]}", "doc": r["doc_id"]} for r in reps]
                        + [{"id": f"Endt {a['number']}", "date": a["issued"], "what": a["note"] or a["kind"], "doc": a["doc_id"]} for a in am]}]
        v["documents"] = _docs(st, rt, ch, {"Authority report", "BAA endorsement", "Audit report"})
        v["events"] = _events(st, ch, {"11"})
        if lm and not any(r["month"] == lm for r in reps):
            v["next_action"] = {"label": f"Issue the {MONTH_LABEL[lm]} authority report", "description": "Renders the monthly authority report (PDF) and sends it to the coverholder."}
    return v


def run(rt, code, ch) -> str:
    st = rt.delegated
    cfg = COVERHOLDERS[ch]
    uid = "u_claire"
    if code == "01":
        n = 0
        for v in st["authority"][ch]:
            from uwc.api import doc_path
            from . import core as C
            doc = rt.store.docs[v["doc_id"]]
            p = B.parse(doc_path(doc), v["doc_id"])
            v["terms"] = {k: x for k, x in p["terms"].items() if k not in ("endorsement_no", "effective", "issued")}
            v["anchors"] = p["anchors"]
            n += len(p["anchors"])
        st["_auth_cache"] = {}
        return f"Re-read {len(st['authority'][ch])} authority documents: {n} terms with page anchors · authority v{len(st['authority'][ch]) - 1} in force"
    if code == "02":
        nxt = _next_arrival(rt, ch)
        if not nxt:
            return "No further bordereaux scheduled"
        return advance_to_bdx(rt, ch)
    if code == "03":
        b = _latest_bdx(st, ch)
        if not b:
            raise ValueError("No bordereau received yet")
        from uwc.api import doc_path
        from . import bordereau as BX
        p = BX.parse_file(doc_path(rt.store.docs[b["doc_id"]]), "risk", {"umr": cfg["umr"], "agreement_no": cfg["agreement"]})
        return (f"Mapper re-run on {b['title']}: {sum(1 for m in p['mapping'] if m['field'])}/{len(p['mapping'])} columns mapped · confidence {p['stats']['mapping_confidence'] * 100:.0f}% · "
                f"{len(p['missing'])} mandatory fields missing · {len(p['issues'])} validation issues · DQ {p['stats']['dq_score']:.0f}")
    if code == "04":
        ids = [rid for rid, r in st["rows"].items() if r["ch"] == ch]
        res = E.evaluate_rows(st, rt, ids, "Re-check")
        lm = V.latest_month(st, ch)
        ms = E.month_stats(st, ch, lm)
        return f"{len(ids):,} lines re-checked · {MONTH_LABEL[lm]} exception rate {ms['exception_rate'] * 100:.1f}% · {res['added']} new, {res['resolved']} resolved"
    if code == "05":
        return reconcile(rt, ch)
    if code == "06":
        try:
            e = A.post_commission(rt, ch, uid)
        except ValueError as x:
            return str(x)
        return f"Debit note {e['entry_id']} posted: ${e['amount']:,.2f} commission over-deducted on {len(e['items'])} policies"
    if code == "07":
        zs = [z for z in E.aggregates(st, ch, rt.clock) if z["util"] and z["util"] >= (z["warn"] or 0.9)]
        if not zs:
            top = E.aggregates(st, ch, rt.clock)[0]
            return f"All zones below warning — top {top['name']} at {top['util'] * 100:.1f}%"
        v = A.restrict_zone(rt, ch, zs[0]["zone"], "Refer", uid)
        return f"Endorsement No. {v['number']} issued and parsed: incremental business in {zs[0]['name']} ({zs[0]['util'] * 100:.1f}%) now referral-only from {v['effective']}"
    if code == "08":
        ex = [e for e in st["exceptions"].values() if e["ch"] == ch and e["subject_type"] == "claim" and e["status"] == "OPEN"]
        if not ex:
            E.evaluate_claims(st, rt, ch)
            n = sum(1 for e in st["exceptions"].values() if e["ch"] == ch and e["subject_type"] == "claim" and e["status"] in E.OPEN_STATES)
            return f"Claims re-checked · {n} open claims exceptions"
        q = A.raise_query(rt, ch, uid, kind="claims")
        return f"Claims query {q['query_id']} sent: {len(q['items'])} claims · reply due {q['due']}"
    if code == "09":
        try:
            q = A.raise_query(rt, ch, uid)
        except ValueError as x:
            return str(x)
        return f"Query {q['query_id']} sent to {cfg['short']}: {len(q['items'])} policies · {sum(len(i['exc_ids']) for i in q['items'])} exceptions · reply due {q['due']}"
    if code == "10":
        try:
            return await_response(rt, ch)
        except ValueError as x:
            return str(x)
    if code == "11":
        lm = V.latest_month(st, ch)
        r = A.issue_report(rt, ch, lm, uid)
        s = r["summary"]
        return f"{MONTH_LABEL[lm]} authority report {r['report_id']} issued: {s['policies']} policies · within authority {s['within_authority'] * 100:.1f}% · grade {s['grade']}"
    return "Unknown stage"


def reconcile(rt, ch) -> str:
    st = rt.delegated
    ids = sorted({e["row_id"] for e in st["exceptions"].values() if e["ch"] == ch and e.get("referral")})
    res = E.evaluate_rows(st, rt, ids, "Referral reconciliation")
    refs = [e for e in st["exceptions"].values() if e["ch"] == ch and e.get("referral")]
    ok = sum(1 for e in refs if e["referral"]["result"] == E.REFER_OK)
    miss = [e for e in refs if e["referral"]["result"] != E.REFER_OK and e["status"] in E.OPEN_STATES]
    kinds = {}
    for e in miss:
        kinds[e["referral"]["result"]] = kinds.get(e["referral"]["result"], 0) + 1
    return (f"{len(refs)} referral triggers reconciled · {ok} matched to an approval · {len(miss)} open without a valid approval"
            + (" (" + ", ".join(f"{n} {k.replace('_', ' ').lower()}" for k, n in kinds.items()) + ")" if kinds else "") + f" · {res['resolved']} resolved")


def advance_to_bdx(rt, ch, month=None) -> str:
    st = rt.delegated
    ev = sorted([e for e in rt.dynamic if e["type"] == "delegated.bordereau" and e.get("subject_id") == ch and not e.get("done") and (month is None or e["payload"]["month"] == month)],
                key=lambda e: e["date"])
    if not ev:
        raise ValueError("No bordereau scheduled")
    e = ev[0]
    m = e["payload"]["month"]
    if e["date"] > rt.clock:
        rt.advance_to(e["date"])
    b = next((b for b in st["bdx"].values() if b["ch"] == ch and b["month"] == m and b["kind"] == "risk" and not b.get("correction")), None)
    ms = E.month_stats(st, ch, m)
    sc = E.scorecard(st, rt, ch)
    return (f"{MONTH_LABEL[m]} bordereaux received {b['received']}" + (f", {b['days_late']} days late" if b["days_late"] else " on time") +
            f" · {ms['policies']} lines · mapping {b['stats']['mapping_confidence'] * 100:.0f}% · DQ {b['dq_score']:.0f} · {ms['with_exceptions']} policies with exceptions ({ms['exception_rate'] * 100:.1f}%)"
            + (" · trend " + " → ".join(f"{t['rate'] * 100:.1f}%" for t in sc["trend"]) if len(sc["trend"]) > 1 else ""))


def await_response(rt, ch) -> str:
    st = rt.delegated
    ev = sorted([e for e in rt.dynamic if e["type"] in ("delegated.response", "delegated.audit") and e.get("subject_id") == ch and not e.get("done")], key=lambda e: e["date"])
    if not ev:
        raise ValueError("Nothing awaited from the coverholder")
    e = ev[0]
    rt.advance_to(e["date"])
    if e["type"] == "delegated.audit":
        a = next(x for x in st["audits"] if x["audit_id"] == e["payload"]["audit_id"])
        f = a["findings"]
        return f"Audit {a['audit_id']} reported {a['reported']}: {f['sampled']} files sampled · {f['confirmed']} with authority exceptions · {f['disputes']} disputes reviewed · rating {f['rating']}"
    q = next(x for x in st["queries"] if x["query_id"] == e["payload"]["query_id"])
    s = q["summary"] or {}
    if q["kind"] == "data_quality":
        return (f"{COVERHOLDERS[ch]['short']} resubmitted {rt.clock} in the CRS v5.2 template: {s.get('resubmitted')} files · DQ {s.get('dq_after') or 0:.0f}/100 · "
                f"{s.get('revealed')} authority exception(s) now visible that the missing fields had hidden")
    return f"{COVERHOLDERS[ch]['short']} replied to {q['query_id']} on {q['responded']}: " + A._summary_text({k: s.get(k, 0) for k in ("corrected", "referral_located", "disputed", "agreed", "cancelled", "explained")}, s.get("resolved", 0))

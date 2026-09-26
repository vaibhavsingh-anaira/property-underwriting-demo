"""Carrier actions and the mocked coverholder side of the loop.

Carrier (REAL): raise a query with the side-by-side evidence, accept / escalate a breach, post a commission
reconciliation, restrict a zone or amend the authority by endorsement (a PDF, parsed back like the BAA),
request an audit, issue the monthly authority report.
Coverholder (MOCK, rule-based): replies after N days — provides a missing referral reference, corrects the
bordereau, endorses the policy to the minimum, cancels, disputes, or agrees a commission adjustment. Every
correction arrives as a real correction bordereau that is parsed and re-checked like any other file."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

from uwc.refdata import USER_BY_ID
from uwc.world.pdfkit import Pdf

from . import baa as B
from . import core as C
from . import engine as E
from . import world as W
from .refdata import COVERHOLDERS, MONTH_LABEL, TXN_LABEL

CARRIER_FROM = "Delegated Authority <da@northgate.example>"


def _u(uid) -> dict:
    return USER_BY_ID.get(uid) or {"name": "Claire Donovan", "title": "Head of Delegated Authority"}


def _plus(rt, days) -> str:
    return (rt.clock_date + timedelta(days=days)).isoformat()


def outbox(rt, ch, subject, body, related=None, href=None, to=None, channel="email"):
    cfg = COVERHOLDERS[ch]
    m = {"message_id": f"msg_{len(rt.outbox) + 1}", "at": rt.clock, "channel": channel, "to": to or f"{cfg['contact']} ({cfg['name']})", "subject": subject,
         "body": body, "account_id": ch, "related": related, "product": "delegated", "href": href or f"/delegated/coverholders/{ch}"}
    rt.outbox.append(m)
    return m


def write_email(st, rt, ch, subject, frm, to, body, doc_type, attachments=(), inbound=False) -> dict:
    cfg = COVERHOLDERS[ch]
    st["seq"]["eml"] = st["seq"].get("eml", 0) + 1
    did = f"da_eml_{st['seq']['eml']:04d}"
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = frm, to, subject
    m["Date"] = format_datetime(datetime.fromisoformat(rt.clock + "T10:15:00-04:00"))
    m.set_content(body)
    ids = []
    for path, fname, adid in attachments:
        sub = "pdf" if str(path).endswith(".pdf") else "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        m.add_attachment(Path(path).read_bytes(), maintype="application", subtype=sub, filename=fname)
        ids.append(adid)
    p = C.docs_dir() / f"{did}.eml"
    p.write_bytes(bytes(m))
    return C.register(st, rt, ch, did, doc_type, subject, "eml", p, "Coverholder email (mock)" if inbound else "Carrier outbox", rt.clock, attachments=ids)


# ============================================================================ queries
def _open_for_query(st, ch, month=None, exc_ids=None, kind="breach"):
    out = []
    for e in st["exceptions"].values():
        if e["ch"] != ch or e["status"] not in ("OPEN",):
            continue
        if exc_ids and e["exc_id"] not in exc_ids:
            continue
        if kind == "breach" and e["subject_type"] != "policy":
            continue
        if kind == "claims" and e["subject_type"] != "claim":
            continue
        if kind == "data_quality" and e["subject_type"] != "bordereau":
            continue
        if month and e["month"] != month and not exc_ids:
            continue
        out.append(e)
    return out


def _line(e) -> str:
    ref = e.get("referral") or {}
    tail = f" — referral: {'none located' if ref.get('result') == 'NOT_FOUND' else ref.get('detail', '')}" if ref else ""
    return f"{e['check']}: written {e['written']} vs authority {e['authority']}" + (f" ({e['delta']})" if e.get("delta") else "") + tail


def raise_query(rt, ch, uid, month=None, exc_ids=None, kind="breach", history=False) -> dict:
    """Query the coverholder on open exceptions, one item per policy, with the side-by-side authority result."""
    st = rt.delegated
    cfg = COVERHOLDERS[ch]
    exs = _open_for_query(st, ch, month, exc_ids, kind)
    if kind == "data_quality":
        bd = [b for b in st["bdx"].values() if b["ch"] == ch and b["kind"] in ("risk", "premium") and not b.get("superseded_by") and not b.get("correction")
              and (not month or b["month"] == month) and (b["missing"] or b["dq_score"] < 90)]
        if not bd:
            raise ValueError("No bordereau to query")
    elif not exs:
        raise ValueError(f"No open {kind.replace('_', ' ')} exceptions for {cfg['short']}" + (f" in {MONTH_LABEL.get(month, month)}" if month else ""))
    qid = E._nid(st, "Q")
    items: dict[str, dict] = {}
    for e in exs:
        it = items.setdefault(e["policy_key"], {"policy_key": e["policy_key"], "certificate_ref": e["certificate_ref"], "insured": e["insured"], "exc_ids": [], "lines": [],
                                                "subject_type": e["subject_type"], "claim_ref": e.get("claim_ref")})
        it["exc_ids"].append(e["exc_id"])
        it["lines"].append(_line(e))
        e["status"] = "QUERIED"
        e["query_ids"].append(qid)
        E._hist(e, rt, "Queried", _u(uid)["name"], qid)
    who = _u(uid)
    if kind == "data_quality":
        lines = []
        for b in bd:
            top = [i for i in b["issues"] if i["severity"] in ("HIGH", "MEDIUM")][:12]
            lines.append(f"{b['title']} (received {b['received']}, due {b['due']}, {b['days_late']} days late) — DQ score {b['dq_score']:.0f}/100")
            if b["missing_labels"]:
                lines.append("  Mandatory CRS v5.2 fields missing: " + ", ".join(b["missing_labels"]))
            lines += [f"  {i['cell'] or ''} {i['label']}" for i in top]
        body = (f"Dear {cfg['contact']},\n\nWe have validated your bordereaux against Lloyd's CRS v5.2 and the reporting terms of {cfg['agreement']}. "
                f"Please resubmit in the CRS v5.2 template with every mandatory field completed:\n\n" + "\n".join(lines) +
                f"\n\nThe validation report is available on the portal. Please resubmit by {_plus(rt, 7)}.\n\nRegards,\n{who['name']}\n{who.get('title', '')}, Northgate Specialty")
        subject = f"{cfg['agreement']} — bordereau resubmission required ({', '.join(MONTH_LABEL[b['month']] for b in sorted(bd, key=lambda b: b['month']) if b['kind'] == 'risk')})"
        items = {f"bdx:{b['doc_id']}": {"policy_key": f"bdx:{b['doc_id']}", "certificate_ref": b["title"], "insured": b["title"], "exc_ids": [], "lines": [], "subject_type": "bordereau",
                                         "doc_id": b["doc_id"], "month": b["month"], "kind": b["kind"]} for b in bd}
    else:
        body = (f"Dear {cfg['contact']},\n\nOur authority checks on your bordereaux under {cfg['agreement']} (UMR {cfg['umr']}) found the following. "
                f"For each item please provide the carrier's referral approval, a corrected bordereau line, or your explanation:\n\n")
        for i, it in enumerate(items.values(), 1):
            body += f"{i}. {it['insured']} — {it['certificate_ref']}\n" + "".join(f"   · {ln}\n" for ln in it["lines"])
        body += f"\nPlease respond by {_plus(rt, 10)}.\n\nRegards,\n{who['name']}\n{who.get('title', '')}, Northgate Specialty"
        subject = f"{cfg['agreement']} — authority exceptions for review ({len(items)} {'policy' if len(items) == 1 else 'policies'})" if kind == "breach" else \
            f"{cfg['agreement']} — claims bordereau review ({len(items)} claims)"
    doc = write_email(st, rt, ch, subject, CARRIER_FROM, f"{cfg['contact']} <{cfg['contact'].split()[0].lower()}@{cfg['domain']}>", body, "Carrier query")
    q = {"query_id": qid, "ch": ch, "kind": kind, "created": rt.clock, "by": who["name"], "month": month, "items": list(items.values()), "status": "SENT", "due": _plus(rt, 10),
         "doc_id": doc["doc_id"], "response": None, "responded": None, "summary": None}
    st["queries"].append(q)
    outbox(rt, ch, subject, body, qid, f"/delegated/breaches?ch={ch}&query={qid}")
    C.log(st, rt, ch, "10", f"Query {qid} sent", f"{len(items)} item(s) · reply due {q['due']}", who["name"], "user", doc["doc_id"])
    days = COVERHOLDERS[ch]["response_days"]
    C.schedule(rt, _plus(rt, days), "delegated.response", ch, f"{cfg['short']} responds to query {qid}", {"query_id": qid})
    return q


CLAIM_TRUTH = {"Wildfire": ("admit", "The risk was bound by a newly hired underwriter who was not aware of the Butte County exclusion. We accept it was outside our authority. "
                                     "We have instructed our claims team to keep the carrier informed of every reserve movement and await the carrier's coverage position."),
               "Fire": ("explain", "The fire was notified to us the day after the loss. Our claims team treated it as attritional until the adjuster's first report and did not send a "
                                   "large loss advice. We accept the notification was late."),
               "Water damage": ("explain", "The reserve was increased on the adjuster's second report: the sprinkler line failure saturated racked stock across two bays. "
                                           "Report attached to the claim file."),
               "Theft": ("explain", "The claim was settled by our in-house handler at $72,500 in error; our settlement authority is $50,000. We will seek retrospective approval.")}


def respond(rt, qid):
    """MOCK coverholder: answers each query item by rule from the generator's truth for that risk."""
    st = rt.delegated
    q = next(x for x in st["queries"] if x["query_id"] == qid)
    if q["status"] != "SENT":
        return q
    ch = q["ch"]
    cfg = COVERHOLDERS[ch]
    plan = st["plan"][ch]
    if q["kind"] == "data_quality":
        return _respond_dq(rt, q)
    corrections, paras, summary = [], [], {"corrected": 0, "referral_located": 0, "disputed": 0, "agreed": 0, "cancelled": 0, "explained": 0}
    cancels = []
    for it in q["items"]:
        exs = [st["exceptions"][x] for x in it["exc_ids"]]
        if it["subject_type"] == "claim":
            cause = next((c["cause"] for c in plan["claims"] if c["claim_ref"] == it.get("claim_ref")), "")
            beh, text = CLAIM_TRUTH.get(cause, ("explain", "We have reviewed the claim file; details attached."))
            for e in exs:
                e["response"] = {"date": rt.clock, "kind": beh, "text": text}
            paras.append(f"{it['insured']} ({it.get('claim_ref')}): {text}")
            summary["explained"] += 1
            continue
        cert = it["certificate_ref"]
        row = _plan_row(plan, cert, exs)
        truth = plan["truth"].get(cert) or plan["truth"].get(f"{cert}|CANCELLATION") or {}
        beh = truth.get("response") or "dispute"
        if beh == "correct" and row is not None:
            fix = dict(row)
            fix.update(truth.get("true", {}))
            if truth.get("kind") == "canx_return":
                fix["gross_premium"] = -round((row.get("_base_premium") or 0) * max(0, (date.fromisoformat(row["expiry"]) - date.fromisoformat(row["written_date"])).days) / 365)
            if truth.get("kind") == "limit":
                fix["limit"] = float(cfg["max_limit"])
            row.update({k: v for k, v in fix.items() if not k.startswith("_") or k == "_base_premium"})
            corrections.append(fix)
            paras.append(f"{it['insured']} ({cert}): keying error on our side — corrected line on the attached correction bordereau.")
            summary["corrected"] += 1
        elif beh == "endorse" and row is not None:
            fix = dict(row)
            fix.update(truth.get("true", {}))
            row.update(truth.get("true", {}))
            corrections.append(fix)
            paras.append(f"{it['insured']} ({cert}): we have endorsed the policy to the minimum deductible effective {rt.clock}; corrected line attached.")
            summary["corrected"] += 1
        elif beh == "provide_ref" and row is not None and truth.get("ref_id"):
            fix = dict(row)
            fix["referral_ref"] = truth["ref_id"]
            row["referral_ref"] = truth["ref_id"]
            corrections.append(fix)
            paras.append(f"{it['insured']} ({cert}): referred and approved before binding under {truth['ref_id']} — the reference was omitted from the bordereau; corrected line attached.")
            summary["referral_located"] += 1
        elif beh == "cancel" and row is not None:
            cancels.append(row)
            paras.append(f"{it['insured']} ({cert}): agreed this is outside our authority — the policy has been cancelled pro-rata effective {rt.clock}.")
            summary["cancelled"] += 1
        elif beh == "accept":
            paras.append(f"{it['insured']} ({cert}): we agree commission should have been deducted at the contract rate and accept the adjustment on the next settlement.")
            summary["agreed"] += 1
            for e in exs:
                e["response"] = {"date": rt.clock, "kind": "accept", "text": "Commission adjustment agreed"}
        elif beh == "admit":
            text = ("The risk was bound by an underwriter unaware of the county exclusion. We accept it was outside our authority and will cancel at the carrier's instruction.")
            paras.append(f"{it['insured']} ({cert}): {text}")
            for e in exs:
                e["response"] = {"date": rt.clock, "kind": "admit", "text": text}
            summary["explained"] += 1
        else:
            text = {"showcase": "The risk was discussed by phone with a Northgate underwriter before binding and we understood it was agreed. We request retrospective approval; "
                                "we disagree that premium was inadequate for a cold-storage risk with this loss history.",
                    "missing_ref_tier1": "We believed the location was outside Tier 1 based on our own wind map. We request retrospective approval.",
                    "limit": "The insured's lender required a $6M+ limit and we considered it within our authority on a first-loss basis. We request retrospective approval.",
                    "limit_stretch": "We read the amended authority as allowing limits up to $8M for warehouses. We request confirmation or retrospective approval.",
                    "hidden_year": "The building was fully renovated in 2009 (roof, electrics, plumbing); we treated it as a 2009 building. We request the carrier's view."}.get(truth.get("kind"),
                                                                                                                                                                   "We believe this risk was written in line with the agreement and request the carrier's review.")
            paras.append(f"{it['insured']} ({cert}): {text}")
            for e in exs:
                e["response"] = {"date": rt.clock, "kind": "dispute", "text": text}
            summary["disputed"] += 1
    atts = []
    corr_doc = None
    if corrections or cancels:
        corr_doc, path = _correction_file(st, rt, ch, qid, corrections, cancels)
        atts.append((path, path.name, corr_doc))
    body = f"Dear {q['by']},\n\nThank you for your query {qid}. Our responses:\n\n" + "\n\n".join(f"{i}. {p}" for i, p in enumerate(paras, 1)) + \
           f"\n\nKind regards,\n{cfg['contact']}\n{cfg['contact_title']}, {cfg['name']}"
    doc = write_email(st, rt, ch, f"RE: {qid} — response from {cfg['short']}", f"{cfg['contact']} <{cfg['contact'].split()[0].lower()}@{cfg['domain']}>", CARRIER_FROM, body,
                      "Coverholder response", [(p, n, d) for p, n, d in atts], inbound=True)
    before = {x: st["exceptions"][x]["status"] for it in q["items"] for x in it["exc_ids"]}
    if corr_doc:
        month = q.get("month") or max((st["exceptions"][x]["month"] for it in q["items"] for x in it["exc_ids"]), default=rt.clock[:7])
        C.ingest_bdx(st, rt, ch, atts[0][0], corr_doc, "risk", month, f"{cfg['short']} correction bordereau — {qid}", correction=True)
    for row in cancels:
        for x in st["exceptions"].values():
            if x["ch"] == ch and x["certificate_ref"] == row["certificate_ref"] and x["status"] in E.OPEN_STATES:
                x["status"], x["resolved_at"], x["resolution"], x["resolution_kind"] = "RESOLVED", rt.clock, f"Policy cancelled pro-rata effective {rt.clock} (coverholder response to {qid})", "cancelled"
                E._hist(x, rt, "Resolved", cfg["short"], x["resolution"])
    posted = {i for e in st["ledger"] for i in e.get("exc_ids", [])}
    for it in q["items"]:
        for x in it["exc_ids"]:
            e = st["exceptions"][x]
            if e["status"] == "QUERIED":
                if e["family"] == "commission" and x in posted:
                    e["status"], e["resolved_at"], e["resolution"] = "RESOLVED", rt.clock, "Commission adjustment agreed by the coverholder; debit note already posted"
                else:
                    e["status"] = "RESPONDED"
                E._hist(e, rt, "Coverholder responded", cfg["short"], (e.get("response") or {}).get("text", "Corrected bordereau supplied"))
    resolved = sum(1 for it in q["items"] for x in it["exc_ids"] if st["exceptions"][x]["status"] == "RESOLVED" and before.get(x) != "RESOLVED")
    q.update(status="RESPONDED", responded=rt.clock, response=doc["doc_id"], correction_doc=corr_doc, summary={**summary, "resolved": resolved})
    C.log(st, rt, ch, "10", f"{cfg['short']} responded to {qid}", _summary_text(summary, resolved), cfg["short"], "mock", doc["doc_id"])
    E.evaluate_claims(st, rt, ch)
    return q


def _summary_text(s, resolved) -> str:
    parts = [f"{s['corrected']} corrected" if s["corrected"] else "", f"{s['referral_located']} referral located" if s["referral_located"] else "",
             f"{s['cancelled']} cancelled" if s["cancelled"] else "", f"{s['agreed']} commission adjustment agreed" if s["agreed"] else "",
             f"{s['disputed']} disputed" if s["disputed"] else "", f"{s['explained']} explained" if s["explained"] else ""]
    return " · ".join(p for p in parts if p) + f" · {resolved} exception(s) resolved on re-check"


def _plan_row(plan, cert, exs):
    txn = next((st_e.get("txn") for st_e in exs if st_e.get("txn")), None)
    for m in sorted(plan["rows"], reverse=True):
        for r in plan["rows"][m]:
            if r["certificate_ref"] == cert and (txn is None or r["transaction_type"] == txn):
                return r
    return None


def _correction_file(st, rt, ch, qid, corrections, cancels):
    cfg = COVERHOLDERS[ch]
    rows = []
    for r in corrections:
        x = dict(r)
        x["transaction_type"] = "CORRECTION"
        rows.append(x)
    for r in cancels:
        x = dict(r)
        x["transaction_type"] = "CANCELLATION"
        x["written_date"] = rt.clock
        frac = max(0, (date.fromisoformat(r["expiry"]) - rt.clock_date).days) / 365
        x["gross_premium"] = -round((r.get("gross_premium") or 0) * frac)
        x["prior_tiv"] = None
        rows.append(x)
    did = f"da_{ch[3:]}_corr_{qid.lower()}"
    path = C.docs_dir() / f"{did}.xlsx"
    W.write_risk(path, cfg, rt.clock[:7], rows, "crs" if cfg["layout"] == "messy" else cfg["layout"], "risk", f"{cfg['name']} · correction bordereau · response to {qid}")
    return did, path


def _respond_dq(rt, q):
    st = rt.delegated
    ch = q["ch"]
    cfg = COVERHOLDERS[ch]
    st["layout_override"][ch] = "crs"
    months = sorted({it["month"] for it in q["items"]})
    atts, res, written = [], {}, []
    for m in months:
        for path, did, kind, title in C.write_month(st, rt, ch, m, "crs", "_v2"):
            atts.append((path, path.name, did))
            written.append((m, path, did, kind, title))
    body = (f"Dear {q['by']},\n\nApologies for the format and timing issues. Attached are the {', '.join(MONTH_LABEL[m] for m in months)} risk and premium bordereaux resubmitted in the "
            f"Lloyd's CRS v5.2 template with construction, year built and county completed from our policy system. From the August bordereau we will report in this template "
            f"within the 15-day deadline.\n\nKind regards,\n{cfg['contact']}\n{cfg['contact_title']}, {cfg['name']}")
    doc = write_email(st, rt, ch, f"RE: {q['query_id']} — resubmitted bordereaux (CRS v5.2)", f"{cfg['contact']} <{cfg['contact'].split()[0].lower()}@{cfg['domain']}>", CARRIER_FROM, body,
                      "Coverholder response", atts, inbound=True)
    before = {e["exc_id"] for e in st["exceptions"].values() if e["ch"] == ch and e["status"] in E.OPEN_STATES}
    for m, path, did, kind, title in written:
        if True:
            old = next((x for x, b in st["bdx"].items() if b["ch"] == ch and b["month"] == m and b["kind"] == kind and not b.get("superseded_by") and x != did), None)
            res[kind] = C.ingest_bdx(st, rt, ch, path, did, kind, m, title, correction=True, replaces=old)
    for b in st["bdx"].values():
        if b["ch"] == ch and b.get("superseded_by"):
            E.clear_subject(st, rt, ch, "bordereau", f"{b['kind']}:{b['month']}", "DA.DATA.MANDATORY_FIELDS", f"Resubmitted in the CRS v5.2 template ({b['superseded_by']})")
    after = {e["exc_id"] for e in st["exceptions"].values() if e["ch"] == ch and e["status"] in E.OPEN_STATES and e["subject_type"] == "policy"}
    revealed = [st["exceptions"][x] for x in after - before]
    # August arrives on time in the CRS template
    for e in rt.dynamic:
        if e["type"] == "delegated.bordereau" and e.get("subject_id") == ch and e["payload"]["month"] == "2026-08" and not e.get("done"):
            e["date"] = "2026-09-12"
            e["title"] = f"{cfg['short']} — Aug 2026 bordereaux received (CRS template)"
    q.update(status="RESPONDED", responded=rt.clock, response=doc["doc_id"], summary={"resubmitted": len(atts), "revealed": len(revealed),
                                                                                         "dq_before": q["items"][0].get("dq_before"), "resolved": 0})
    nb = next((b for b in st["bdx"].values() if b["ch"] == ch and b["kind"] == "risk" and b.get("replaces")), None)
    q["summary"]["dq_after"] = nb["dq_score"] if nb else None
    C.log(st, rt, ch, "10", f"{cfg['short']} resubmitted in the CRS v5.2 template", f"{len(atts)} files · {len(revealed)} authority exception(s) now visible", cfg["short"], "mock", doc["doc_id"])
    return q


# ============================================================================ carrier decisions
def decide(rt, exc_ids, decision, uid, note=""):
    st = rt.delegated
    who = _u(uid)["name"]
    out = []
    for x in exc_ids:
        e = st["exceptions"][x]
        if e["status"] not in E.OPEN_STATES:
            continue
        if decision == "ACCEPT":
            e["status"], e["resolved_at"], e["resolution"] = "ACCEPTED", rt.clock, f"Ratified by {who} — held covered" + (f": {note}" if note else "")
        elif decision == "ESCALATE":
            e["status"] = "ESCALATED"
            e["resolution"] = f"Escalated by {who}" + (f": {note}" if note else "")
        elif decision == "RESOLVE":
            e["status"], e["resolved_at"], e["resolution"] = "RESOLVED", rt.clock, f"Closed by {who}" + (f": {note}" if note else "")
        E._hist(e, rt, {"ACCEPT": "Accepted (ratified)", "ESCALATE": "Escalated", "RESOLVE": "Resolved"}[decision], who, note)
        out.append(e)
        C.log(st, rt, e["ch"], "09", f"{e['title']} — {decision.lower()}d", f"{e['insured']} · {e['certificate_ref']}" + (f" · {note}" if note else ""), who, "user")
    E.evaluate_claims(st, rt, out[0]["ch"]) if out else None
    return out


def post_commission(rt, ch, uid) -> dict:
    """Commission reconciliation: debit note for commission deducted above the contract rate (mock finance ledger)."""
    st = rt.delegated
    cfg = COVERHOLDERS[ch]
    exs = [e for e in st["exceptions"].values() if e["ch"] == ch and e["family"] == "commission" and e["status"] in E.OPEN_STATES]
    if not exs:
        raise ValueError(f"No open commission discrepancies for {cfg['short']}")
    amt = round(sum(e["impact_usd"] for e in exs), 2)
    eid = E._nid(st, "DN")
    items = [{"certificate_ref": e["certificate_ref"], "insured": e["insured"], "reported": e["written"], "contract": e["authority"], "amount": e["impact_usd"],
              "gross": e["premium_tied"]} for e in exs]
    p = C.docs_dir() / f"da_{eid.lower()}.pdf"
    pdf = Pdf(p, "carrier", "Debit note", eid)
    pdf.title(f"Debit note {eid}", f"Commission reconciliation · {cfg['name']} · {cfg['agreement']}")
    pdf.kv([("Coverholder", cfg["name"]), ("Agreement number", cfg["agreement"]), ("Date issued", B.dmy(rt.clock)), ("Amount due", B.usd(amt))], cols=1, label_w=200)
    pdf.table(["Certificate", "Insured", "Reported", "Contract", "Gross premium", "Over-deducted"],
              [(i["certificate_ref"], i["insured"][:30], i["reported"], i["contract"], B.usd(i["gross"]), f"${i['amount']:,.2f}") for i in items], [80, 150, 60, 60, 90, 80])
    pdf.para("Commission deducted above the rate in section 3 of the Agreement is due to the Carrier and will be offset against the next premium settlement.", size=8.5)
    pdf.save()
    doc = C.register(st, rt, ch, f"da_{eid.lower()}", "Debit note", f"Debit note {eid} — commission reconciliation", "pdf", p, "Finance ledger (mock)", rt.clock)
    entry = {"entry_id": eid, "ch": ch, "date": rt.clock, "type": "Debit note — commission over-deduction", "amount": amt, "status": "POSTED", "items": items,
             "exc_ids": [e["exc_id"] for e in exs], "doc_id": doc["doc_id"], "by": _u(uid)["name"], "settled": None}
    st["ledger"].append(entry)
    for e in exs:
        e["status"], e["resolved_at"], e["resolution"] = "RESOLVED", rt.clock, f"Commission adjusted — debit note {eid} posted to the coverholder account"
        E._hist(e, rt, "Resolved", _u(uid)["name"], e["resolution"])
    outbox(rt, ch, f"{cfg['agreement']} — debit note {eid} (commission reconciliation)", f"Debit note {eid} for ${amt:,.2f}: commission deducted above the contract rate on "
           f"{len(items)} policies. It will be offset against the next premium settlement.", eid)
    C.log(st, rt, ch, "06", f"Debit note {eid} posted", f"${amt:,.2f} over-deducted commission on {len(items)} policies", _u(uid)["name"], "user", doc["doc_id"])
    C.schedule(rt, _plus(rt, 5), "delegated.settle", ch, f"{cfg['short']} settles debit note {eid}", {"entry_id": eid})
    return entry


def settle(rt, entry_id):
    st = rt.delegated
    e = next(x for x in st["ledger"] if x["entry_id"] == entry_id)
    e["status"], e["settled"] = "SETTLED", rt.clock
    C.log(st, rt, e["ch"], "06", f"Debit note {entry_id} settled", f"${e['amount']:,.2f} offset against the premium remittance", "Finance ledger (mock)", "mock")


# ============================================================================ authority amendments (endorsements, parsed back)
def _next_endt(st, ch) -> int:
    return max([v.get("number") or 0 for v in st["authority"][ch]] + [0]) + 1


def issue_endorsement(rt, ch, uid, effective, reason, kv=(), tables=(), kind="amendment", note="") -> dict:
    st = rt.delegated
    cfg = COVERHOLDERS[ch]
    n = _next_endt(st, ch)
    did = f"da_{ch[3:]}_endt{n}"
    p = C.docs_dir() / f"{did}.pdf"
    who = _u(uid)
    B.render_endorsement(p, cfg, n, effective, rt.clock, reason, list(kv), list(tables), who["name"], who.get("title", "Head of Delegated Authority"))
    v = C.add_authority_doc(st, rt, ch, p, did, "Endorsement", f"BAA endorsement No. {n}", rt.clock, effective, n)
    st["amendments"].append({"ch": ch, "number": n, "doc_id": did, "effective": effective, "issued": rt.clock, "kind": kind, "by": who["name"], "changes": v["changes"], "note": note})
    ids = [rid for rid, r in st["rows"].items() if r["ch"] == ch and (r.get("written_date") or "") >= effective]
    res = E.evaluate_rows(st, rt, ids, f"Endorsement No. {n}")
    E.evaluate_zones(st, rt, ch, rt.clock, rt.clock[:7])
    chg = "; ".join(f"{c['label']}: {c['from']} → {c['to']}" for c in v["changes"])
    outbox(rt, ch, f"{cfg['agreement']} — Endorsement No. {n} effective {effective}", f"{reason}\n\nAmended terms: {chg}", did, f"/delegated/coverholders/{ch}?tab=authority")
    C.log(st, rt, ch, "11", f"Endorsement No. {n} issued and parsed — authority v{v['version']}", chg, who["name"], "user", did)
    C.schedule(rt, _plus(rt, 1), "delegated.ack", ch, f"{cfg['short']} acknowledges Endorsement No. {n}", {"ch": ch, "what": f"Endorsement No. {n}", "ref": did})
    return {**v, "reevaluated": len(ids), "result": res}


def restrict_zone(rt, ch, zone, mode, uid, effective=None) -> dict:
    st = rt.delegated
    terms, _a, _v = E.authority(st, ch, rt.clock)
    a = (terms.get("aggregates") or {}).get(zone)
    if not a:
        raise ValueError(f"Zone {zone} is not in the authority")
    eff = effective or _plus(rt, 1)
    zs = {z["zone"]: z for z in E.aggregates(st, ch, rt.clock)}
    util = zs.get(zone, {}).get("util") or 0
    reason = (f"In-force TIV in {a['name']} has reached {util * 100:.1f}% of the aggregate limit against a {a['warn'] * 100:.0f}% warning level. With effect from "
              f"{B.dmy(eff)} all incremental business in the zone (new business and renewals with more than 5% additional TIV) "
              + ("requires the Carrier's prior written approval." if mode == "Refer" else "is suspended."))
    v = issue_endorsement(rt, ch, uid, eff, reason, tables=[(B.T_AGG, [(zone, a["name"], a["peril"], B.usd(a["limit"]), B.pctf(a["warn"]), mode)], [50, 150, 110, 110, 60, 50])],
                          kind="restriction")
    st["restrictions"].append({"ch": ch, "zone": zone, "name": a["name"], "mode": mode, "effective": eff, "issued": rt.clock, "util_at_issue": util, "doc_id": v["doc_id"]})
    return v


AMENDMENTS = {
    "ch_northfield": {"label": "Capacity increase — maximum limit $7.5M", "effective": "2026-08-15",
                      "reason": "Following the coverholder's request and a clean scorecard, the maximum limit any one risk is increased and the TIV referral threshold aligned.",
                      "kv": [("Maximum limit any one risk", "$7,500,000"), ("TIV any one location exceeding", "$7,500,000")]},
    "ch_meridian": {"label": "Authority tightened after audit", "effective": "2026-10-01",
                    "reason": "Following the carrier audit, the maximum limit is reduced and all risks with TIV above $2,500,000 require prior approval until the remediation plan is complete.",
                    "kv": [("Maximum limit any one risk", "$3,500,000"), ("TIV any one location exceeding", "$2,500,000"), ("Premium tolerance below rated premium", "5%")]},
}


def amend(rt, ch, uid, preset=None) -> dict:
    a = AMENDMENTS.get(preset or ch)
    if not a:
        raise ValueError("No amendment preset for this coverholder")
    eff = max(a["effective"], rt.clock)
    return issue_endorsement(rt, ch, uid, eff, a["reason"], kv=a["kv"], kind="amendment", note=a["label"])


def acknowledge(rt, ch, what, ref=None):
    st = rt.delegated
    cfg = COVERHOLDERS[ch]
    write_email(st, rt, ch, f"RE: {what} — acknowledged", f"{cfg['contact']} <{cfg['contact'].split()[0].lower()}@{cfg['domain']}>", CARRIER_FROM,
                f"We acknowledge {what}. Our binding system has been updated so that affected business is referred to the carrier before binding.\n\n{cfg['contact']}\n{cfg['name']}",
                "Coverholder response", inbound=True)
    C.log(st, rt, ch, "11", f"{what} acknowledged by {cfg['short']}", "Binding system updated (coverholder confirmation)", cfg["short"], "mock")


# ============================================================================ audit
def request_audit(rt, ch, uid) -> dict:
    st = rt.delegated
    cfg = COVERHOLDERS[ch]
    aid = E._nid(st, "AUD")
    a = {"audit_id": aid, "ch": ch, "requested": rt.clock, "by": _u(uid)["name"], "visit": _plus(rt, 10), "report_due": _plus(rt, 14), "status": "SCHEDULED", "doc_id": None, "findings": None}
    st["audits"].append(a)
    outbox(rt, ch, f"{cfg['agreement']} — carrier audit visit {a['visit']}", f"Under the audit clause of {cfg['agreement']} we will visit on {a['visit']} to review a sample of "
           "policy files, the referral log, commission calculations and claims files. Please make the underwriting files for the attached list available.", aid)
    C.log(st, rt, ch, "11", f"Audit {aid} requested", f"Visit {a['visit']} · report due {a['report_due']}", a["by"], "user")
    C.schedule(rt, a["report_due"], "delegated.audit", ch, f"Audit report — {cfg['short']}", {"audit_id": aid})
    return a


def audit_report(rt, aid):
    """MOCK audit team: samples files and writes a report; the sample results are the engine's own checks on those files."""
    st = rt.delegated
    a = next(x for x in st["audits"] if x["audit_id"] == aid)
    ch = a["ch"]
    cfg = COVERHOLDERS[ch]
    rows = sorted(E.policy_rows(st, ch), key=lambda r: r["row_id"])
    exc_rows = {e["row_id"] for e in st["exceptions"].values() if e["ch"] == ch and e.get("row_id") and E.raised(e)}
    sample = [r for r in rows if r["row_id"] in exc_rows] + [r for i, r in enumerate(rows) if i % max(1, len(rows) // 20) == 0 and r["row_id"] not in exc_rows][:20]
    confirmed = [r for r in sample if r["row_id"] in exc_rows]
    esc = [e for e in st["exceptions"].values() if e["ch"] == ch and e["status"] in ("ESCALATED", "RESPONDED")]
    sc = E.scorecard(st, rt, ch)
    rating = "Unsatisfactory" if (sc["trend"] and sc["trend"][-1]["rate"] > 0.015) or len(esc) > 2 else "Requires improvement" if confirmed else "Satisfactory"
    p = C.docs_dir() / f"da_{aid.lower()}.pdf"
    pdf = Pdf(p, "engineering", "Coverholder audit report", aid)
    pdf.title("Coverholder audit report", f"{cfg['name']} · {cfg['agreement']} · visit {a['visit']}")
    pdf.kv([("Coverholder", cfg["name"]), ("Audit reference", aid), ("Files sampled", str(len(sample))), ("Files with authority exceptions", str(len(confirmed))),
            ("Open disputes reviewed", str(len(esc))), ("Overall rating", rating)], cols=1, label_w=200)
    pdf.section("Findings")
    pdf.table(["Certificate", "Insured", "Finding"], [(r["certificate_ref"], (r.get("insured_name") or "")[:28],
                                                        "; ".join(sorted({e["check"] for e in st["exceptions"].values() if e.get("row_id") == r["row_id"] and E.raised(e)}))[:70])
                                                       for r in confirmed], [90, 160, 260])
    pdf.para("Referral log: " + ("approvals are not recorded against certificates; several risks requiring referral were bound without evidence of approval." if any(
        e["family"] == "referral" or (e.get("referral") and e["referral"]["result"] == "NOT_FOUND") for e in st["exceptions"].values() if e["ch"] == ch and E.raised(e))
                                  else "maintained and reconciled to the carrier system."))
    pdf.para("Disputed items: no written evidence of carrier approval was produced for any disputed risk." if esc else "No disputed items.")
    pdf.para("Recommendations: tighten authority until the remediation plan is complete; weekly referral log reconciliation; retraining on deductible bands and commission rates."
             if rating != "Satisfactory" else "No action required.")
    pdf.signature("Harper & Lowe DA Audit (mock)", "Delegated authority audit team", B.dmy(rt.clock))
    pdf.save()
    doc = C.register(st, rt, ch, f"da_{aid.lower()}", "Audit report", f"Coverholder audit report {aid}", "pdf", p, "Audit team (mock)", rt.clock)
    a.update(status="REPORTED", doc_id=doc["doc_id"], findings={"sampled": len(sample), "confirmed": len(confirmed), "disputes": len(esc), "rating": rating}, reported=rt.clock)
    for e in esc:
        E._hist(e, rt, "Audit", "Audit team (mock)", f"{aid}: no written evidence of carrier approval — confirmed outside authority")
        e["audit_note"] = f"{aid}: confirmed outside authority"
    C.log(st, rt, ch, "11", f"Audit {aid} reported — {rating}", f"{len(sample)} files sampled · {len(confirmed)} with exceptions · {len(esc)} disputes reviewed", "Audit team (mock)", "mock", doc["doc_id"])


# ============================================================================ monthly authority report
def issue_report(rt, ch, month, uid) -> dict:
    st = rt.delegated
    cfg = COVERHOLDERS[ch]
    r = E.report(st, rt, ch, month)
    rid = E._nid(st, "RPT")
    p = C.docs_dir() / f"da_{rid.lower()}.pdf"
    pdf = Pdf(p, "carrier", "Monthly authority report", rid)
    pdf.title("Monthly authority report", f"{cfg['name']} · {cfg['agreement']} · {MONTH_LABEL[month]}")
    pdf.kv([("Policies checked", f"{r['policies']:,}"), ("Within authority", f"{r['within_authority'] * 100:.1f}%"), ("Policies with exceptions", f"{r['with_exceptions']} ({r['exception_rate'] * 100:.1f}%)"),
            ("Premium tied to exceptions", B.usd(r["premium_tied"])), ("Commission discrepancy", B.usd(r["commission_discrepancy"])),
            ("Missing referrals", str(r["missing_referrals"])), ("Scorecard grade", r["grade"])], cols=1, label_w=200)
    pdf.section("Authority exceptions by type")
    pdf.table(["Type", "Exceptions", "Open", "Premium tied"], [(t["label"], str(t["count"]), str(t["open"]), B.usd(t["premium_tied"])) for t in r["types"]], [220, 90, 90, 110])
    pdf.section("Aggregates")
    pdf.table(["Zone", "In-force TIV", "Limit", "Utilisation"], [(z["name"], B.usd(z["tiv"]), B.usd(z["limit"]), f"{(z['util'] or 0) * 100:.1f}%") for z in r["zones"]], [180, 110, 110, 110])
    pdf.section("Exception trend")
    pdf.table(["Month", "Policies", "With exceptions", "Rate"], [(MONTH_LABEL[t["month"]], str(t["policies"]), str(t["with_exceptions"]), f"{t['rate'] * 100:.1f}%") for t in r["trend"]], [150, 120, 120, 120])
    pdf.section("Recommended actions")
    for x in r["recommendations"] or ["None"]:
        pdf.para(f"• {x}", size=9)
    pdf.save()
    doc = C.register(st, rt, ch, f"da_{rid.lower()}", "Authority report", f"Monthly authority report — {cfg['short']} {MONTH_LABEL[month]}", "pdf", p, "Anaira reporting", rt.clock)
    rep = {"report_id": rid, "ch": ch, "month": month, "issued": rt.clock, "by": _u(uid)["name"], "doc_id": doc["doc_id"], "summary": {k: r[k] for k in ("policies", "within_authority", "exception_rate",
                                                                                                                                                     "premium_tied", "commission_discrepancy", "missing_referrals", "grade")}}
    st["reports"].append(rep)
    outbox(rt, ch, f"{cfg['agreement']} — monthly authority report {MONTH_LABEL[month]}", f"Policies checked {r['policies']:,}; within authority {r['within_authority'] * 100:.1f}%; "
           f"exception rate {r['exception_rate'] * 100:.1f}%; premium tied to exceptions ${r['premium_tied']:,.0f}.", rid)
    C.log(st, rt, ch, "11", f"Authority report {MONTH_LABEL[month]} issued", f"Grade {r['grade']} · {r['with_exceptions']} policies with exceptions", _u(uid)["name"], "user", doc["doc_id"])
    return rep

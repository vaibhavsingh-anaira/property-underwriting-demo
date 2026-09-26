"""Delegated authority workflows: complete real-life flows a carrier's DA team runs, from the bordereau arriving
to the authority being corrected. Narration carries no figures — the engine's live result is read out after each step."""
from __future__ import annotations

from datetime import date, timedelta

from uwc.playbook_defs import S

from . import actions as A
from . import engine as E
from . import stages as SG
from . import views as V
from .refdata import COVERHOLDERS, MONTH_LABEL, ORDER

REAL_CORE = ["Binding authority agreement and endorsements read back from PDF into a versioned authority with page anchors",
             "Bordereau mapping to Lloyd's CRS v5.2 with confidence, validation with cell references",
             "Authority rules (YAML, tested) per policy against the authority in force when it was written",
             "Referral reconciliation, commission and premium reconciliation, zone aggregates, claims controls",
             "Breach register, monthly authority report, coverholder scorecard, quarterly RARC from bordereaux"]
MOCK_CORE = ["Coverholder portal and the coverholder itself (sends the files; replies to queries by rule after a few days — corrects, provides a referral reference, cancels, disputes, agrees)",
             "Carrier referral system (records approvals; decides zone referrals by headroom rule)", "Finance ledger (debit notes, settlement)",
             "CAT aggregate feed (county → zone, PML ratio)", "DA registry / binder store, audit team"]

PLAYBOOKS: list[dict] = [
    {"id": "dac-monthly-close", "account_id": "ch_meridian", "title": "Monthly bordereau close — breaches, queries, corrections, authority report",
     "aspects": ["Bordereau mapping", "Authority checks", "Breach register", "Coverholder query", "Correction bordereau", "Authority report"],
     "intro": "Meridian Gulf writes small commercial property along the Gulf Coast on Northgate's paper. Its July bordereau arrived this morning. "
              "This is the monthly close a delegated authority team runs, done in minutes instead of weeks, and every breach tied to the exact cell and the exact clause.",
     "outro": "The month is closed. Every policy was checked against the authority in force the day it was bound, the coverholder answered with evidence, corrections were re-checked, "
              "and what is still disputed is escalated with the file attached.",
     "brief": {"audience": "Head of delegated authority, DA operations, Lloyd's managing agent oversight",
               "problem": "Bordereaux arrive monthly, are keyed into spreadsheets and sampled. Most carriers check a fraction of policies, weeks late, and rarely against the contract as endorsed.",
               "story": ["The July risk and premium bordereaux arrive in the coverholder's own template and are mapped to CRS v5.2.",
                         "Every line is checked against the binding authority agreement as endorsed on the date it was written.",
                         "The breach register shows each policy side by side: written versus authority, with the bordereau cell and the BAA clause.",
                         "One query goes to the coverholder with the evidence; the mocked coverholder replies with corrections, a cancellation, a dispute and an agreed commission adjustment.",
                         "The correction bordereau is parsed and re-checked; commission is reconciled by debit note; the dispute is escalated; the monthly report is issued."],
               "watch": ["Stage 09: the side-by-side authority result per policy", "Stage 10: the coverholder's reply and the correction bordereau", "Stage 06: the debit note",
                         "Stage 11: the monthly authority report"],
               "value": "Every policy checked every month, breaches evidenced to the cell and the clause, corrections verified rather than trusted.",
               "questions": ["What share of bordereau lines do you check today, and how long after the month closes?", "How do you know a correction was actually made?"]},
     "steps": [S("02", "July bordereaux received", "view", "The coverholder's July risk, premium and claims bordereaux arrived through the portal this morning."),
               S("03", "Mapped to Lloyd's CRS v5.2", "view", "The files are in Meridian's own template. Every column is mapped to the CRS standard with a confidence, and every value keeps its cell."),
               S("04", "Every line checked against the authority", "stage", "Each line is checked against the binding authority as endorsed on the day it was bound: class, territory, limit, deductibles, pricing, referrals and commission."),
               S("09", "The breach register, policy by policy", "view", "This cold storage risk is the pattern the deck describes: limit above authority, deductible below the minimum, premium below the rated range, no referral located, and commission deducted above the contract rate."),
               S("09", "Query the coverholder with the evidence", "query", "One query goes to the coverholder, one item per policy, with the side-by-side result.", month="2026-07"),
               S("10", "The coverholder replies", "await_response", "We move the clock to the coverholder's reply. It sends a correction bordereau, which is parsed and re-checked like any other file."),
               S("06", "Commission reconciliation", "commission", "Commission deducted above the contract rate becomes a debit note in the finance ledger, offset against the next premium settlement."),
               S("09", "Escalate what is still disputed", "decide", "Where the coverholder disputes without evidence of approval, the item is escalated with the file attached.", decision="ESCALATE",
                 which="disputed", note="No written approval evidenced — referred to the DA committee"),
               S("11", "Monthly authority report", "report", "And the monthly authority report goes to the coverholder, with exceptions by type, dollars tied to them, and the trend.")]},
    {"id": "dac-referrals-commission", "account_id": "ch_meridian", "title": "Missing referrals and commission reconciliation",
     "aspects": ["Referral system", "Approval on different terms", "Commission over-deduction", "Debit note"],
     "intro": "Two of the most common delegated authority leaks are referrals that were never made, and commission taken at a higher rate than the contract. Here's how both are closed for Meridian Gulf.",
     "outro": "Referrals are only authority if the approval exists, pre-dates binding and covers what was written. Commission is contract, not custom. Both are now reconciled every month, automatically.",
     "brief": {"audience": "DA managers, finance and credit control, audit",
               "problem": "Coverholders report referral references loosely or not at all, and approvals are rarely compared with the terms actually bound. Commission differences hide in net settlements.",
               "story": ["Every referral trigger on the bordereau is reconciled to the carrier's referral system.",
                         "Some approvals are missing, one approval covers less than was written.",
                         "The coverholder is queried on exactly those items and replies with references and corrections.",
                         "Commission deducted above the contract rate is reconciled line by line and posted as a debit note; the coverholder settles it."],
               "watch": ["Stage 05: approval found / not found / different terms", "Stage 06: commission contract vs reported, and the ledger"],
               "value": "Missing referrals and commission leakage found on every line, with the recovery posted.",
               "questions": ["How do you evidence that a referral approval covered the risk as bound?", "How much commission would a line-by-line check recover on your book?"]},
     "steps": [S("05", "Referral triggers against the referral system", "view", "Every line that needed the carrier's prior approval is matched to the carrier's referral system."),
               S("05", "Reconcile", "reconcile", "The approval must exist, pre-date binding, and cover the terms that were actually written."),
               S("05", "Query the missing approvals", "query", "The coverholder is asked for the approvals the platform could not find, and for the one that does not cover the written terms.", which="referral"),
               S("10", "The coverholder replies", "await_response", "Some references were simply left off the bordereau. Others were never obtained."),
               S("05", "Re-reconcile", "reconcile", "The corrected lines are re-checked against the referral system."),
               S("06", "Commission contract versus reported", "view", "Now commission. The contract rate is read from the agreement; the reported rate from the premium bordereau."),
               S("06", "Post the debit note", "commission", "The over-deduction is posted as a debit note in the finance ledger."),
               S("06", "Settlement", "advance", "The coverholder settles the debit note against its next premium remittance.", days=6),
               S("11", "Scorecard", "summarise", "And the coverholder's scorecard reflects both.", kind="scorecard")]},
    {"id": "dac-florida-aggregate", "account_id": "ch_palmcoast", "title": "Florida CAT aggregate hits its threshold — refer incremental business",
     "aspects": ["Zone aggregates", "Authority restriction by endorsement", "Referral desk", "Restriction monitoring"],
     "intro": "Palm Coast writes coastal commercial property in Florida. Its South Florida aggregate has just gone through the warning level in its binding authority. Watch the carrier act on it, and then check the restriction actually worked.",
     "outro": "The aggregate was controlled while the coverholder kept writing. The restriction was issued as a contract change, read back by the same extractor, and enforced on the very next bordereau.",
     "brief": {"audience": "CUO, CAT management, delegated authority, reinsurance",
               "problem": "Delegated CAT exposure is usually seen a quarter late. By the time a zone is over its limit, the business is already bound.",
               "story": ["In-force TIV by zone is rebuilt from the coverholder's exposure return and every bordereau movement.",
                         "South Florida is above its warning level; the carrier issues an endorsement making incremental business referral-only.",
                         "During August the coverholder's new zone business goes to the carrier's referral desk; some is approved, some declined.",
                         "The August bordereau shows the restriction working — and flags the risks written without referral."],
               "watch": ["Stage 07: zone utilisation versus warning and limit", "Stage 01: the new authority version", "Stage 05: referral desk decisions", "Stage 09: restriction breaches"],
               "value": "Unauthorised CAT exposure prevented before it is bound, and the residual breaches caught on arrival.",
               "questions": ["How quickly do you see delegated CAT accumulation today?", "How do you enforce a zone restriction on a coverholder's system?"]},
     "steps": [S("07", "South Florida against its aggregate", "view", "In-force TIV in each zone is the coverholder's exposure return plus every bordereau movement since."),
               S("07", "Aggregate position", "summarise", "South Florida is through its warning level.", kind="aggregates"),
               S("07", "Refer incremental business in the zone", "restrict", "The carrier issues an endorsement: new business and material increases in South Florida now need prior approval.", zone="MIA", mode="Refer"),
               S("01", "The authority, as amended", "view", "The endorsement is a PDF, read back by the same extractor as the agreement. The authority now has a new version, effective tomorrow."),
               S("05", "August at the referral desk", "advance", "Through August, the coverholder routes new South Florida business to the carrier's referral desk.", to="2026-08-31"),
               S("02", "August bordereaux arrive", "advance_bdx", "In September the August bordereaux arrive and are checked against the amended authority."),
               S("07", "Did the restriction work?", "summarise", "Here is the zone now, against where it would have been.", kind="aggregates"),
               S("09", "Query the risks written without referral", "query", "The risks bound in the zone without referral are queried.", month="2026-08"),
               S("10", "The coverholder replies", "await_response", "The coverholder agrees and cancels them."),
               S("11", "Authority report", "report", "And the August authority report records the position.")]},
    {"id": "dac-bordereau-resubmission", "account_id": "ch_ridgeway", "title": "Messy, late bordereau — mapping, resubmission, hidden breaches revealed",
     "aspects": ["CRS v5.2 mapping", "Validation with cell references", "Late submission", "Resubmission", "Hidden breaches"],
     "intro": "Ridgeway sends its bordereaux late, in its own format, with mandatory fields missing. Most carriers accept that as noise. Here, data quality is an authority control, because missing fields hide breaches.",
     "outro": "The resubmission did more than tidy the data. It exposed authority breaches the missing fields had been hiding, and it moved the coverholder onto the standard for good.",
     "brief": {"audience": "DA operations, bordereau management teams, Lloyd's MA oversight",
               "problem": "Non-standard bordereaux are fixed by hand, so problems are fixed silently and the coverholder never improves. Missing fields mean checks can't run.",
               "story": ["The July bordereau arrives late, in a production-report layout, with construction, year built and county missing.",
                         "The mapper shows what it recognised and with what confidence; every validation issue points to a cell.",
                         "The carrier asks for a resubmission in the CRS template; the mocked coverholder sends one.",
                         "With complete data, the authority checks find breaches that were invisible before; the August bordereau arrives on time in the standard."],
               "watch": ["Stage 03: the mapping table and validation issues", "Stage 04: new exceptions after resubmission", "Stage 11: timeliness and data quality on the scorecard"],
               "value": "Data quality measured, fed back and fixed at the source — and no breach hidden by a missing field.",
               "questions": ["How many coverholders report in their own format?", "Which checks can't run on your bordereaux today because fields are missing?"]},
     "steps": [S("02", "History: late every month", "view", "May and June arrived after the due date in the agreement."),
               S("02", "The July bordereau arrives", "advance_bdx", "Here comes July. Late again."),
               S("03", "What the mapper recognised", "view", "Abbreviated headers are mapped with confidence; unmapped columns and missing mandatory fields are listed, and every issue points to a cell."),
               S("10", "Ask for a resubmission in the CRS template", "query", "The carrier asks for a resubmission in the CRS template, with the validation report attached.", kind="data_quality"),
               S("10", "The coverholder resubmits", "await_response", "The coverholder resubmits in the standard template with the missing fields completed."),
               S("04", "Breaches the missing data was hiding", "view", "With complete data the checks can run. Two older buildings were bound without the referral the agreement requires."),
               S("09", "Query them", "query", "Those are queried.", month="2026-07"),
               S("10", "The coverholder replies", "await_response", "One reference is supplied; one is disputed on the grounds that the building was fully renovated."),
               S("09", "Accept the renovation", "decide", "The underwriter accepts the renovation evidence and ratifies the risk.", decision="ACCEPT", which="disputed", note="Full 2009 renovation evidenced; held covered"),
               S("02", "August arrives — on time, in the standard", "advance_bdx", "And August arrives on time, in the CRS template."),
               S("11", "Scorecard", "summarise", "The scorecard shows the change.", kind="scorecard")]},
    {"id": "dac-claims-large-loss", "account_id": "ch_sierra", "title": "Claims bordereau — large loss on an out-of-authority risk, notified late",
     "aspects": ["Claims bordereau", "Claim on an out-of-authority risk", "Late large-loss notification", "Reserve movement", "Coverage review", "Audit"],
     "intro": "Sierra Crest writes commercial property in the western states. Its claims bordereau has just surfaced a large wildfire loss on a risk that should never have been bound. This is where authority control meets claims.",
     "outro": "The breach found in May became the coverage question in July. Because both sit on the same register, the carrier knew its position the day the claim arrived.",
     "brief": {"audience": "Claims, DA managers, CUO, reinsurance and legal",
               "problem": "Claims and authority are checked by different teams on different files, so losses on risks bound outside authority are paid before anyone connects them.",
               "story": ["The July claims bordereau shows a wildfire total loss on a risk in an excluded county, bound in May.",
                         "A kitchen fire above the large-loss threshold was only advised through the bordereau, weeks late; a reserve on a water claim tripled; a claim was paid above the coverholder's settlement authority.",
                         "The policy breach is escalated for a coverage decision; the claims team queries the coverholder.",
                         "The August claims bordereau shows the wildfire reserve moving; an audit visit is requested and reported."],
               "watch": ["Stage 08: claims exceptions and the claims bordereau", "Stage 09: the policy breach behind the claim", "Stage 11: the audit report"],
               "value": "Coverage position known on day one; notification and settlement authority breaches recorded on the scorecard.",
               "questions": ["Would your claims team know that a large loss sits on a risk bound outside authority?", "How do you monitor large-loss notification by coverholders?"]},
     "steps": [S("08", "July claims bordereau", "view", "The July claims bordereau is checked against the policy register and the claims terms of the agreement."),
               S("08", "What the claims controls found", "summarise", "Four claims exceptions.", kind="claims"),
               S("09", "The policy behind the wildfire loss", "view", "The wildfire loss sits on a policy bound in May in a county the agreement excludes. The breach was queried in June, and the coverholder admitted it."),
               S("09", "Escalate for a coverage decision", "decide", "The policy breach is escalated for a coverage decision and a possible recovery from the coverholder.", decision="ESCALATE", which="admitted",
                 note="Coverage review — reserve rights; recovery from coverholder E&O to be considered"),
               S("08", "Query the claims", "query", "The claims team asks the coverholder for the files and explanations.", kind="claims"),
               S("10", "The coverholder replies", "await_response", "The coverholder explains each one."),
               S("02", "August bordereaux arrive", "advance_bdx", "In September the August claims bordereau shows how the losses developed."),
               S("08", "Claims position", "summarise", "Here is where the claims now stand.", kind="claims"),
               S("11", "Request an audit", "audit", "The carrier requests an audit visit."),
               S("11", "Audit report", "await_response", "The audit team samples files and reports.")]},
    {"id": "dac-authority-amendment", "account_id": "ch_northfield", "title": "Authority amendment mid-period — capacity increase for a clean coverholder",
     "aspects": ["Scorecard", "Endorsement to the BAA", "Versioned authority", "Re-evaluation"],
     "intro": "Northfield is the benchmark coverholder: on time, in the standard, referring when it should. It has asked for more capacity. Here's how an amendment is made, and how the platform applies it to the right business from the right date.",
     "outro": "Authority is a contract with versions. Every line is checked against the version in force the day it was bound, so an amendment helps exactly the business it was meant to, and nothing else.",
     "brief": {"audience": "Head of DA, underwriting management, program business",
               "problem": "Authority changes are emailed and applied by memory. Nobody can say which terms governed which risk.",
               "story": ["Northfield's scorecard supports a capacity increase.", "The carrier issues an endorsement effective mid-August raising the maximum limit.",
                         "The August bordereau is checked: larger risks bound after the effective date are within the amended authority; one goes beyond even that.",
                         "The coverholder's explanation is reviewed and the risk ratified."],
               "watch": ["Stage 11: scorecard", "Stage 01: authority versions and what changed", "Stage 04: August checked against v1 and v2 by bind date"],
               "value": "Amendments applied precisely by effective date, with an audit trail of which terms governed which risk.",
               "questions": ["How do you evidence which version of an authority applied to a claim?"]},
     "steps": [S("11", "Northfield's scorecard", "view", "Northfield's scorecard: exceptions near zero, data quality high, always on time."),
               S("11", "The case for more capacity", "summarise", "The numbers behind the request.", kind="scorecard"),
               S("01", "Issue the endorsement", "amend", "The carrier issues an endorsement raising the maximum limit, effective mid-August. It is read back by the extractor into a new authority version."),
               S("01", "Authority versions", "view", "The authority now has versions, and each one says exactly what changed."),
               S("02", "August bordereaux arrive", "advance_bdx", "The August bordereau arrives and every line is checked against the version in force on its bind date."),
               S("04", "Applied by bind date", "summarise", "Larger risks bound after the effective date are within the amended authority.", kind="amendment"),
               S("09", "One risk beyond even the new limit", "query", "One risk was written above even the new limit. It is queried.", month="2026-08"),
               S("10", "The coverholder replies", "await_response", "The coverholder explains how it read the amendment."),
               S("09", "Ratify", "decide", "The underwriter reviews it and ratifies the risk.", decision="ACCEPT", which="disputed", note="Reviewed with the coverholder; ratified as a one-off"),
               S("11", "Authority report", "report", "And the monthly report is issued.")]},
    {"id": "dac-quarterly-review", "account_id": "ch_meridian", "title": "Quarterly review — deteriorating trend, RARC from bordereaux, audit, tightened authority",
     "aspects": ["Exception trend", "Quarterly RARC from bordereaux", "Scorecard", "Audit", "Authority tightened"],
     "intro": "The quarterly review with Meridian Gulf. The August bordereau is due. The question for the carrier is whether this coverholder's authority should stay as it is.",
     "outro": "The decision to tighten authority rests on four months of evidence, computed from the coverholder's own bordereaux, and it is applied as a contract change from a clear date.",
     "brief": {"audience": "CUO, Lloyd's managing agent, DA committee",
               "problem": "Coverholder reviews rely on anecdotes and a sample. Rate change on delegated business is rarely measured like-for-like, although MS3 requires it.",
               "story": ["The August bordereau confirms the exception rate has risen every month.",
                         "Quarterly RARC is computed from renewal lines: premium change adjusted for TIV and deductible changes using the agreement's own rating factors.",
                         "The scorecard combines authority, data quality, timeliness, loss and trend.",
                         "An audit visit confirms the disputed items; the authority is tightened by endorsement."],
               "watch": ["Stage 04: the trend", "Stage 11: RARC by quarter and the scorecard", "Stage 11: the audit report and the new endorsement"],
               "value": "Rate adequacy and authority discipline measured on the coverholder's own data, and acted on in the contract.",
               "questions": ["Do you compute RARC on delegated renewals today?", "What evidence does your DA committee see before changing an authority?"]},
     "steps": [S("02", "August bordereaux arrive", "advance_bdx", "The August bordereaux arrive and are checked on receipt."),
               S("04", "The exception trend", "summarise", "The exception rate, month by month.", kind="trend"),
               S("11", "Quarterly RARC from bordereaux", "summarise", "Rate change on renewals, like for like: premium change adjusted for exposure and deductible changes with the agreement's own rating factors.", kind="rarc"),
               S("11", "The scorecard", "summarise", "The scorecard combines authority, data quality, timeliness, loss and trend.", kind="scorecard"),
               S("11", "Request an audit visit", "audit", "The DA committee asks for an audit visit before deciding."),
               S("11", "Audit report", "await_response", "The audit samples files, including every disputed item."),
               S("01", "Tighten the authority", "amend", "The authority is tightened by endorsement from the start of next quarter: lower maximum limit and more referrals, until the remediation plan is complete."),
               S("11", "August authority report", "report", "And the August report goes to the coverholder with the decision.")]},
]


def all_playbooks(rt, pipe) -> list[dict]:
    out = []
    for p in PLAYBOOKS:
        cfg = COVERHOLDERS[p["account_id"]]
        out.append({**p, "account_name": cfg["name"], "scenario": cfg["scenario"], "subject_href": f"/delegated/coverholders/{p['account_id']}"})
    lines = {"01": "The binding authority agreement and its endorsements are read back into a versioned authority.", "02": "The coverholder's bordereaux arrive through the portal.",
             "03": "Each file is mapped to the Lloyd's reporting standard and validated.", "04": "Every line is checked against the authority in force the day it was bound.",
             "05": "Referral triggers are reconciled to the carrier's referral system.", "06": "Premium and commission are reconciled; over-deductions become a debit note.",
             "07": "Zone aggregates are rebuilt and compared with the agreement's limits.", "08": "The claims bordereau is checked against the policy register and the claims terms.",
             "09": "Open breaches go to the coverholder with the evidence.", "10": "The coverholder replies, and corrections are re-checked.",
             "11": "The authority report and scorecard are issued, and the authority amended if needed."}
    for ch in ORDER:
        cfg = COVERHOLDERS[ch]
        out.append({"id": f"lifecycle-{ch}", "account_id": ch, "account_name": cfg["name"], "scenario": cfg["scenario"], "subject_href": f"/delegated/coverholders/{ch}",
                    "title": "All 11 stages in order", "aspects": ["Full lifecycle"],
                    "intro": f"Here's {cfg['name']}, taken through all eleven stages of delegated authority control, one system at a time.",
                    "outro": "That's the full control cycle, from the contract to the corrected authority, with every step evidenced.",
                    "brief": {"audience": "Anyone who wants to see every system in the chain for one coverholder", "problem": cfg["title"],
                              "story": ["Each of the 11 stages is opened in order and its step is run: authority, bordereau intake, mapping, checks, referrals, premium and commission, aggregates, claims, breach register, query and response, report."],
                              "watch": ["Which stages are the product (REAL) and which are stand-ins (MOCK) — the badge on each stage"],
                              "value": "Shows the platform covers the whole delegated authority control loop.", "questions": []},
                    "steps": [S(c, n, "stage", lines[c]) for c, n, *_ in pipe]})
    return out


def _filter(st, ch, which):
    exs = [e for e in st["exceptions"].values() if e["ch"] == ch and e["status"] in E.OPEN_STATES]
    if which == "disputed":
        return [e for e in exs if e["status"] == "RESPONDED" and (e.get("response") or {}).get("kind") == "dispute"]
    if which == "admitted":
        return [e for e in exs if (e.get("response") or {}).get("kind") == "admit" and e["subject_type"] == "policy"]
    if which == "referral":
        return [e for e in exs if e["status"] == "OPEN" and e.get("referral") and e["referral"]["result"] != E.REFER_OK]
    return exs


def run_step(rt, p, step) -> str:
    st = rt.delegated
    ch = p["account_id"]
    cfg = COVERHOLDERS[ch]
    a, prm = step["action"], step["params"]
    uid = "u_claire"
    if a == "view":
        return f"Showing {step['label'].lower()}"
    if a == "stage":
        return SG.run(rt, step["code"], ch)
    if a == "advance_bdx":
        return SG.advance_to_bdx(rt, ch, prm.get("month"))
    if a == "query":
        kind = prm.get("kind", "breach")
        ids = [e["exc_id"] for e in _filter(st, ch, prm["which"])] if prm.get("which") else None
        q = A.raise_query(rt, ch, uid, month=prm.get("month") if kind != "data_quality" else None, exc_ids=ids, kind=kind)
        if kind == "data_quality":
            b = [st["bdx"][it["doc_id"]] for it in q["items"]]
            return (f"Resubmission request {q['query_id']} sent: {len(b)} files · DQ {min(x['dq_score'] for x in b):.0f}/100 · "
                    f"{len(b[0]['missing'])} mandatory CRS fields missing · {sum(len(x['issues']) for x in b)} validation issues · due {q['due']}")
        return f"Query {q['query_id']} sent to {cfg['short']}: {len(q['items'])} {'policies' if kind == 'breach' else 'claims'} · {sum(len(i['exc_ids']) for i in q['items'])} exceptions · reply due {q['due']}"
    if a == "await_response":
        return SG.await_response(rt, ch)
    if a == "reconcile":
        return SG.reconcile(rt, ch)
    if a == "commission":
        e = A.post_commission(rt, ch, uid)
        return f"Debit note {e['entry_id']} posted: ${e['amount']:,.2f} commission over-deducted on {len(e['items'])} policies ({', '.join(i['reported'] + ' vs ' + i['contract'] for i in e['items'][:1])})"
    if a == "decide":
        exs = _filter(st, ch, prm.get("which", "disputed"))
        if not exs:
            return "Nothing awaiting a decision"
        out = A.decide(rt, [e["exc_id"] for e in exs], prm["decision"], uid, prm.get("note", ""))
        pols = {e["policy_key"] for e in out}
        return f"{len(out)} exception(s) on {len(pols)} {'policy' if len(pols) == 1 else 'policies'} {'escalated' if prm['decision'] == 'ESCALATE' else 'ratified' if prm['decision'] == 'ACCEPT' else 'closed'}: " + \
            "; ".join(sorted({f"{e['insured']} ({e['check']})" for e in out}))[:220]
    if a == "report":
        m = prm.get("month") or V.latest_month(st, ch)
        r = A.issue_report(rt, ch, m, uid)
        s = r["summary"]
        return (f"{MONTH_LABEL[m]} authority report {r['report_id']} sent: {s['policies']} policies checked · within authority {s['within_authority'] * 100:.1f}% · exception rate "
                f"{s['exception_rate'] * 100:.1f}% · premium tied ${s['premium_tied']:,.0f} · grade {s['grade']}")
    if a == "restrict":
        zs = {z["zone"]: z for z in E.aggregates(st, ch, rt.clock)}
        v = A.restrict_zone(rt, ch, prm["zone"], prm["mode"], uid)
        z = zs[prm["zone"]]
        return f"Endorsement No. {v['number']} issued and read back as authority v{v['version']}: {z['name']} ({z['util'] * 100:.1f}% of limit) {prm['mode'].lower()} from {v['effective']}"
    if a == "amend":
        v = A.amend(rt, ch, uid)
        return (f"Endorsement No. {v['number']} issued and read back as authority v{v['version']}, effective {v['effective']}: " +
                "; ".join(f"{c['label']} {c['from']} → {c['to']}" for c in v["changes"]))
    if a == "audit":
        x = A.request_audit(rt, ch, uid)
        return f"Audit {x['audit_id']} requested: visit {x['visit']}, report due {x['report_due']}"
    if a == "advance":
        start = rt.clock
        target = prm.get("to") or (rt.clock_date + timedelta(days=int(prm.get("days", 1)))).isoformat()
        n_ref = len(st["referrals"])
        n_prev = len(st["prevented"])
        rt.advance_to(target)
        new = [r for r in st["referrals"][n_ref:] if r["ch"] == ch]
        prev = st["prevented"][n_prev:]
        led = [x for x in st["ledger"] if x["ch"] == ch and x.get("settled") and x["settled"] > start]
        parts = [f"Clock {start} → {rt.clock}"]
        if new:
            parts.append(f"{len(new)} referral requests at the carrier desk: {sum(1 for r in new if r['status'] == 'APPROVED')} approved, {sum(1 for r in new if r['status'] == 'DECLINED')} declined")
        if prev:
            parts.append(f"${sum(p_['tiv'] for p_ in prev):,.0f} TIV declined and never bound")
        for x in led:
            parts.append(f"debit note {x['entry_id']} settled (${x['amount']:,.2f})")
        return " · ".join(parts)
    if a == "summarise":
        return summarise(rt, ch, prm["kind"])
    return "Unknown action"


def summarise(rt, ch, kind) -> str:
    st = rt.delegated
    sc = E.scorecard(st, rt, ch)
    if kind == "scorecard":
        return (f"Grade {sc['grade']} ({sc['score']:.0f}/100) · within authority {sc['within_authority'] * 100:.1f}% · exception trend " + " → ".join(f"{t['rate'] * 100:.1f}%" for t in sc["trend"]) +
                f" · DQ {sc['dq_score'] or 0:.0f} · avg {sc['avg_days_late']:.0f} days late · incurred ÷ written {(sc['loss_ratio'] or 0) * 100:.1f}%" +
                (f" · correction turnaround {sc['turnaround_days']} days" if sc["turnaround_days"] else ""))
    if kind == "trend":
        return f"Exception rate {' → '.join(f'{MONTH_LABEL[t['month']][:3]} {t['rate'] * 100:.1f}%' for t in sc['trend'])} — {sc['direction']}"
    if kind == "aggregates":
        zs = E.aggregates(st, ch, rt.clock)
        z = zs[0]
        prev = sum(p["tiv"] for p in st["prevented"] if p["ch"] == ch and p["zone"] == z["zone"])
        s = f"{z['name']} in-force TIV ${z['tiv']:,.0f} = {z['util'] * 100:.1f}% of the ${z['limit']:,.0f} limit (warning {z['warn'] * 100:.0f}%) · status {z['status']}"
        if prev:
            s += f" · without the restriction {((z['tiv'] + prev) / z['limit']) * 100:.1f}% — ${prev:,.0f} of TIV declined at the referral desk"
        return s + f" · next zone {zs[1]['name']} {zs[1]['util'] * 100:.1f}%"
    if kind == "rarc":
        qs = E.rarc(st, ch)["quarters"]
        return " · ".join(f"{q['label']}: {q['used']} renewals, headline {q['headline'] * 100:+.1f}%, TIV {q['exposure_change'] * 100:+.1f}%, RARC {q['rarc'] * 100:+.1f}%" for q in qs if q["rarc"] is not None)
    if kind == "claims":
        cl = V.claims(st, ch)
        ex = [e for e in st["exceptions"].values() if e["ch"] == ch and e["subject_type"] == "claim" and e["status"] in E.OPEN_STATES]
        top = cl[0] if cl else None
        return (f"{len(cl)} claims · incurred ${sum(c['incurred'] or 0 for c in cl):,.0f} · {len(ex)} open claims exceptions ({'; '.join(sorted({e['title'] for e in ex}))[:200]})"
                + (f" · largest {top['claim_ref']} {top['cause'].lower()} ${top['incurred']:,.0f}" if top else "") + f" · incurred ÷ written {(sc['loss_ratio'] or 0) * 100:.1f}%")
    if kind == "amendment":
        am = [x for x in st["amendments"] if x["ch"] == ch]
        if not am:
            return "No amendment issued"
        eff = am[-1]["effective"]
        rows = [r for r in E.policy_rows(st, ch) if r.get("written_date", "") >= eff and r.get("transaction_type") == "NEW" and (r.get("limit") or 0) > 5_000_000]
        ok = [r for r in rows if not any(e.get("row_id") == r["row_id"] and E.raised(e) and e["status"] in E.OPEN_STATES for e in st["exceptions"].values())]
        before = [r for r in E.policy_rows(st, ch) if r.get("written_date", "") < eff and (r.get("limit") or 0) > 5_000_000]
        return (f"{len(rows)} risks above the old $5M limit bound after {eff}: {len(ok)} within the amended authority, {len(rows) - len(ok)} outside it · "
                f"{len(before)} bound before {eff} were checked against the original authority")
    return "—"


def facts(rt, ch) -> list[dict]:
    st = rt.delegated
    if not st.get("built"):
        return []
    s = V.summary(st, rt, ch)
    out = [{"label": "Coverholder", "value": f"{s['name']} · {s['scenario']}"}, {"label": "Agreement", "value": f"{s['agreement']} · authority v{s['authority_version']}"},
           {"label": "Scorecard", "value": f"{s['grade']} ({s['score']:.0f}) · within authority {s['within_authority'] * 100:.1f}%"},
           {"label": "Exception trend", "value": " → ".join(f"{t['rate'] * 100:.1f}%" for t in s["trend"]) + f" ({s['direction']})"},
           {"label": "Open exceptions", "value": f"{s['open_exceptions']} ({s['open_policies']} policies) · ${s['at_stake']:,.0f} at stake on policies and claims"}]
    if s["commission_open"]:
        out.append({"label": "Commission discrepancy open", "value": f"${s['commission_open']:,.2f}"})
    led = [x for x in st["ledger"] if x["ch"] == ch]
    if led:
        out.append({"label": "Debit notes", "value": "; ".join(f"{x['entry_id']} ${x['amount']:,.2f} {x['status'].lower()}" for x in led)})
    if s["top_zone"]:
        z = s["top_zone"]
        out.append({"label": "Top zone", "value": f"{z['name']} {z['util'] * 100:.1f}% of limit · {z['status']}"})
    prev = [p for p in st["prevented"] if p["ch"] == ch]
    if prev:
        out.append({"label": "Exposure prevented", "value": f"${sum(p['tiv'] for p in prev):,.0f} TIV declined ({len(prev)} risks)"})
    qs = [q for q in st["queries"] if q["ch"] == ch]
    if qs:
        out.append({"label": "Queries", "value": f"{len(qs)} · {sum(1 for q in qs if q['status'] == 'SENT')} awaiting reply"})
    if s["rarc"] and s["rarc"]["rarc"] is not None:
        out.append({"label": f"RARC {s['rarc']['quarter']}", "value": f"{s['rarc']['rarc'] * 100:+.1f}% (headline {s['rarc']['headline'] * 100:+.1f}%)"})
    out.append({"label": "Data quality · timeliness", "value": f"DQ {s['dq_score'] or 0:.0f} · avg {s['avg_days_late']:.0f} days late"})
    if s["loss_ratio"] is not None:
        out.append({"label": "Incurred ÷ written", "value": f"{s['loss_ratio'] * 100:.1f}%"})
    am = [x for x in st["amendments"] if x["ch"] == ch]
    if am:
        out.append({"label": "Latest amendment", "value": f"Endorsement No. {am[-1]['number']} effective {am[-1]['effective']}"})
    au = [x for x in st["audits"] if x["ch"] == ch and x.get("findings")]
    if au:
        out.append({"label": "Audit", "value": f"{au[-1]['audit_id']} — {au[-1]['findings']['rating']}"})
    return out

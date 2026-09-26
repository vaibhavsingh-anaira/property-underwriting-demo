"""Decision Assurance workflow playbooks. Each step runs real engine logic from the clean 1 Aug state; narration is
written for a carrier audience without figures — the live result each step returns is read out after it runs."""
from __future__ import annotations

from uwc.refdata import USER_BY_ID

from . import engine as E
from . import flow as FL
from . import stages as SG
from .model import PIPE, VERDICT_LABEL, money, pct, st


def S(code: str, label: str, action: str = "view", say: str = "", **params) -> dict:
    return {"code": code, "label": label, "action": action, "say": say or label, "params": params}


PLAYBOOKS = [
    {"id": "da-deck-d1", "account_id": "nb_d1", "title": "Deck example — sprinkler contradiction and roof age: pass with flags",
     "aspects": ["Decision pack", "Contradiction", "Pre-referral envelope", "Pass with flags", "Outcome feedback"],
     "intro": "Halvorsen Precision is a three-plant manufacturer coming to Northgate as new business. We'll prepare the decision before anyone opens the file, "
              "let the underwriter make her judgement, and then check her intended quote independently before it goes out.",
     "outro": "The underwriter made every decision. The platform prepared the file, found what the application got wrong, and checked the commitment against the carrier's own rules before it was made.",
     "brief": {"audience": "CUO, head of underwriting, underwriting operations",
               "problem": "Expert time goes on assembling the case; contradictions between the application and the inspection get missed; and the underwriter deciding is usually the one validating the decision.",
               "story": ["The submission is parsed into source-linked facts; the application's 'fully sprinklered' contradicts the inspection, and the difference is priced by re-rating.",
                         "The pack sets out risk factors, guidelines, technical price and range, the underwriter's authority and a draft action: refer, or quote conditionally.",
                         "The underwriter confirms the inspection, asks for the roof schedule and pre-refers the sprinkler exposure; the senior approves inside an envelope.",
                         "Her intended quote is assured on five dimensions: pass with flags, one condition before bind.",
                         "Quote issued and read back; the roof schedule arrives; bind is assured again and goes through.",
                         "Months later a hail loss hits the old roof — the flag is confirmed and its precision improves."],
               "watch": ["Case page · contradiction card: both sources side by side, click either to open the document at the anchor",
                         "Assurance result: per-dimension pass, deviation against permitted authority, the remaining condition",
                         "Referral envelope: the approval covers this action because it sits inside the approved minimums"],
               "value": "Case preparation in minutes, a contradiction caught before pricing, and a commitment checked independently — without taking the decision away from the underwriter.",
               "questions": ["How often does your application disagree with the inspection, and who notices?", "Who checks the intended quote against authority before it goes out today?"]},
     "steps": [
         S("01", "Submission arrives and is parsed", "arrive", "The broker sends the submission: application, schedule, five years of loss runs and a recent loss-control inspection. It's parsed the moment it lands."),
         S("02", "Facts, contradictions, missing information", "view", "Every value is extracted with its source. The application and the schedule say the Dallas plant is fully sprinklered; the inspection says the coating wing isn't. The platform has priced the difference."),
         S("03", "Carrier context: guidelines, price, authority", "view", "Carrier context: guidelines, the authority matrix and the rater. A technical price, a suggested range, and the underwriter's own deviation authority."),
         S("04", "Draft recommendation", "view", "The draft: refer, or quote conditionally. Before the decision, the contradiction must be resolved, the old Fort Worth roof needs a replacement schedule, and the sprinkler exposure needs a senior sign-off."),
         S("05", "Underwriter confirms the inspection", "resolve", "The underwriter confirms the inspection over the application. The pack re-rates on verified protection."),
         S("05", "Roof schedule requested from the broker", "request", "She asks the broker for the roof replacement schedule."),
         S("05", "Sprinkler exposure pre-referred and approved", "prerefer", "And she refers the sprinkler exposure to a senior underwriter, who approves it inside an envelope: a minimum premium and a minimum deductible."),
         S("06", "Intended action: quote", "action", "Now her judgement: a quote inside the suggested range, with the higher deductible."),
         S("07", "Independent assurance", "view", "Independent assurance runs on exactly that action: evidence, pricing, guidelines, appetite and authority."),
         S("08", "Pass with flags", "view", "Pass with flags. Evidence, guidelines and authority pass; the price sits inside her deviation authority; one condition remains before bind — the roof schedule."),
         S("09", "Quote issued and read back", "commit", "She's the decision owner. The quote is issued through the policy system, then read back and compared with the intended action."),
         S("09", "Broker replies", "broker_wait", "The broker sends the roof schedule, and accepts."),
         S("09", "Bind — assured again", "bind", "At bind, assurance runs again. The condition has cleared on evidence, so the bind goes through."),
         S("10", "Outcome feedback", "outcome", "Months later, hail hits the old Fort Worth roof. The flag that asked for the roof schedule is confirmed, and the rule's precision is updated."),
     ]},
    {"id": "da-clean-d2", "account_id": "nb_d2", "title": "Clean submission — pass, decided in a day",
     "aspects": ["Auto-prepared pack", "Pass", "Fast decision"],
     "intro": "Most submissions aren't problems. Larkspur Plaza is a clean office risk. Watch how little human time it takes when the evidence agrees.",
     "outro": "Every control ran. None found anything worth an underwriter's time, so the underwriter spent almost none.",
     "brief": {"audience": "Underwriting operations, heads of underwriting",
               "problem": "Clean submissions take the same assembly effort as hard ones, so the hard ones wait.",
               "story": ["Submission parsed; no contradictions, nothing missing, nothing outside appetite.", "The underwriter quotes near technical; assurance passes on every dimension.",
                         "Quote, acceptance and bind in one sitting; a clean outcome six months later."],
               "watch": ["Dashboard: auto-prepared share and preparation hours saved", "Assurance result: every dimension passes"],
               "value": "Minutes per clean submission, with the full evidence trail kept.", "questions": ["What share of your submissions is clean?", "How long does a clean one take today?"]},
     "steps": [
         S("01", "Submission arrives and is parsed", "arrive", "The submission arrives and is parsed."),
         S("04", "Pack: nothing material", "view", "The pack is clean: sources agree, nothing is missing, and the class is in appetite. The draft is simply to quote."),
         S("06", "Intended action: quote near technical", "action", "The underwriter quotes just above technical."),
         S("08", "Pass", "view", "Assurance passes on all five dimensions. The underwriter is the decision owner."),
         S("09", "Quote issued", "commit", "The quote is issued and read back."),
         S("09", "Broker accepts", "broker_wait", "The broker accepts."),
         S("09", "Bound", "bind", "Bound, after one more assurance pass on the bind itself."),
         S("10", "Outcome: clean", "outcome", "Six months on, no losses. A clean pass is feedback too."),
     ]},
    {"id": "da-hold-d3", "account_id": "nb_d3", "title": "Bind below technical on incomplete loss runs — hold, corrected, bound",
     "aspects": ["Required documents", "Deviation authority", "Rationale critique", "Error intercepted"],
     "intro": "Cardinal Ridge is a cold-storage operator. The broker wants to bind this week at a price well below technical, with only three of the five years of loss runs on file.",
     "outro": "The commitment was stopped before it was made, corrected on the full evidence, and bound within authority.",
     "brief": {"audience": "CUO, head of underwriting, pricing",
               "problem": "Under deadline pressure, underwriters bind below technical on an incomplete file, beyond their deviation authority.",
               "story": ["Only three years of loss runs arrive; the pack asks for five before any bind.", "The underwriter intends to bind at the broker's price.",
                         "Assurance holds: a required document is missing, the deviation is beyond her authority, and the rationale leans on a loss history the file doesn't have.",
                         "The broker sends the missing years: an ammonia refrigeration loss the three-year run didn't show. Technical is re-rated.",
                         "The underwriter re-quotes inside her authority; assurance passes; quote, acceptance, bind."],
               "watch": ["Assurance result: evidence fail + authority fail, with the permitted deviation", "Pricing context: the experience modifier moving once five years are on file",
                         "Dashboard: exposure corrected before commitment"],
               "value": "An under-priced bind prevented, and the premium corrected on evidence rather than argument.",
               "questions": ["How many new-business binds go out with fewer than five years of loss runs?", "Who sees a deviation beyond authority before bind?"]},
     "steps": [
         S("01", "Submission arrives and is parsed", "arrive", "The submission arrives. The broker's email says the older loss runs will follow."),
         S("02", "Three of five years of loss runs", "view", "The pack sees three years of loss runs where the standard requires five, and records the broker's promise from the email."),
         S("06", "Intended action: bind at the broker's price", "action", "The underwriter intends to bind at the broker's price, citing a clean three-year record."),
         S("08", "Refer / hold", "view", "Hold. Bind is blocked while a required document is outstanding; the deviation is beyond her authority; and the tier-two critique notes the rationale rests on an incomplete loss history."),
         S("05", "Missing loss runs requested; broker returns them", "request_wait", "She asks for the missing years. The broker returns them three days later, and they're parsed like any other document."),
         S("03", "Re-rated on five years", "view", "The older years include a large refrigeration loss. The experience modifier moves, and so does technical."),
         S("06", "Revised action: quote within authority", "revise", "She re-quotes, inside her deviation authority."),
         S("08", "Pass", "view", "Assurance passes."),
         S("09", "Quote issued", "commit", "The quote is issued and read back."),
         S("09", "Broker accepts", "broker_wait", "The broker accepts."),
         S("09", "Bound", "bind", "Bound, with a complete file and a price the carrier can defend."),
         S("10", "Outcome", "outcome", "The outcome review closes the loop on the flags that fired."),
     ]},
    {"id": "da-decline-d4", "account_id": "nb_d4", "title": "Declined class hidden in the operations description — override refused, declined",
     "aspects": ["Classification guide", "Prohibited class", "Override needs L4", "Declination"],
     "intro": "Rivergate Industrial arrives described as warehousing. The schedule and the class code agree. The operations description and third-party company data tell a different story.",
     "outro": "The class was found in the words, not the code. The override was stopped at the only level allowed to grant it, and the decline went out the same day.",
     "brief": {"audience": "CUO, compliance, portfolio management",
               "problem": "Declined classes enter the book under benign codes; the description that gives them away is read by nobody.",
               "story": ["The classification guide reads the operations description: shredding and baling of metals is scrap, a declined class; company data agrees.",
                         "The underwriter overrides the class and quotes as a warehouse.",
                         "Assurance holds: prohibited class, an override contrary to the evidence, and a price far below technical for the evidenced class.",
                         "Referred to the CUO, who declines; the declination goes to the broker."],
               "watch": ["Case page · classification evidence, each source clickable", "Tier 2: override contrary to evidence", "Outbox: the declination"],
               "value": "Appetite enforced on what the risk is, not what it is called.", "questions": ["How would a misclassified declined class be found in your book today?"]},
     "steps": [
         S("01", "Submission arrives and is parsed", "arrive", "The submission arrives as a warehousing risk."),
         S("02", "Classification from every source", "view", "The classification guide reads every source. The operations description — shredding and baling of ferrous and non-ferrous metals — is scrap. Company data agrees. The schedule says warehouse."),
         S("04", "Draft: decline", "view", "Scrap is declined under the carrier's guidelines, so the draft is to decline. Only the chief underwriting officer can grant an exception."),
         S("05", "Underwriter overrides the class", "override", "The underwriter disagrees: to him it's a warehouse with some incidental processing. He records an override."),
         S("06", "Intended action: quote as a warehouse", "action", "And intends to quote it at a warehouse rate."),
         S("08", "Refer / hold", "view", "Hold. The class is prohibited, the override contradicts the evidence, and the price is far below technical for the class the evidence supports."),
         S("08", "Referred to the CUO", "route", "It goes to the one level that can decide it."),
         S("08", "CUO declines", "decide_referral", "The chief underwriting officer declines. No exception."),
         S("09", "Declination sent", "decline", "The declination goes to the broker, and the decision is recorded with its evidence."),
     ]},
    {"id": "da-portfolio-d5", "account_id": "nb_d5", "title": "Coastal hotels push Tampa Bay over threshold — portfolio referral, reduced line",
     "aspects": ["Accumulation", "Portfolio referral", "Approval envelope", "Line size"],
     "intro": "Pelican Bay owns two beachfront hotels in Tampa Bay. The risk is well built and well priced. The problem is where it sits in the portfolio.",
     "outro": "A good risk, written at the right size for the portfolio, with the approval tied to exactly that size.",
     "brief": {"audience": "CUO, portfolio management, reinsurance",
               "problem": "Individual underwriting decisions consume catastrophe capacity nobody is watching at the point of quote.",
               "story": ["The pack computes the zone's utilisation before and after this risk, on the in-force book plus bound new business.",
                         "The underwriter quotes a full line at technical; assurance refers it to portfolio authority.",
                         "The head of property approves a half line only; the revised action passes inside the envelope, with the accumulation flag kept on the file."],
               "watch": ["Portfolio card: before/after utilisation and the maximum line that would stay under threshold", "Referral envelope: maximum line"],
               "value": "Capacity allocated at the point of decision, not discovered at the next portfolio review.",
               "questions": ["Where does accumulation enter a new-business decision today?"]},
     "steps": [
         S("01", "Submission arrives and is parsed", "arrive", "The submission arrives and is parsed."),
         S("03", "Portfolio context", "view", "The pack puts the risk in its portfolio: Tampa Bay utilisation before and after, against the carrier's threshold."),
         S("06", "Intended action: full line at technical", "action", "The underwriter quotes a full line at technical, on guideline named-storm terms."),
         S("08", "Refer — portfolio authority", "view", "Pricing and terms pass. Appetite doesn't: the zone goes over threshold. That needs portfolio authority."),
         S("08", "Referred to the head of property", "route", "It's referred to the head of property."),
         S("08", "Approved at a half line", "decide_referral", "She approves a half line only. The approval is an envelope: anything bigger isn't covered."),
         S("06", "Revised action: half line", "revise", "The underwriter revises to a half line."),
         S("08", "Pass with flags", "view", "It passes inside the envelope. The zone stays flagged on the file, so the exception stays visible."),
         S("09", "Quote issued", "commit", "The quote is issued."),
         S("09", "Broker accepts", "broker_wait", "The broker accepts."),
         S("09", "Bound", "bind", "Bound, at the approved size."),
         S("10", "Outcome", "outcome", "The outcome review closes the loop."),
     ]},
    {"id": "da-override-d6", "account_id": "nb_d6", "title": "Flag overridden, manuscript deletes the water exclusion — senior approves with conditions; loss months later",
     "aspects": ["Override critique", "Manuscript wording", "Tier 3 senior review", "Pre-bind conditions", "Outcome feedback"],
     "intro": "Palmetto Gateway is a port-side logistics operation. The inspection found racks above the sprinkler design, and the broker wants their own water-damage wording.",
     "outro": "The senior decided with the full picture, the conditions were met on evidence before bind, and the outcome proved what the wording would have given away.",
     "brief": {"audience": "CUO, head of property, claims, wordings",
               "problem": "Overrides are rarely checked against evidence, and manuscript wording slips through because nobody reads it against the risk.",
               "story": ["The inspection shows storage above the sprinkler design; the underwriter overrides, citing in-rack sprinklers — with no evidence on file, and a verified inspection saying otherwise.",
                         "The broker's manuscript deletes the water exclusion in a flood zone.",
                         "Tier-two critique flags the override and the wording; the case goes to the head of property.",
                         "She approves with conditions: the exclusion reinstated except sprinkler leakage, in-rack protection evidenced and verified, and a roof survey before bind.",
                         "The contractor letter arrives, the engineer verifies, the conditions clear, and the risk binds.",
                         "Months later a storm surge floods the port building. The loss is excluded under the reinstated wording."],
               "watch": ["Tier 2 checks: override rationale vs evidence; manuscript wording", "Referral: conditions and envelope", "Outcome: the excluded loss, and the manuscript flag confirmed"],
               "value": "The exposure the wording would have given back is measured by what actually happened.",
               "questions": ["Who reads manuscript wording against the risk before bind?", "How do you know an override's reason is true?"]},
     "steps": [
         S("01", "Submission arrives and is parsed", "arrive", "The submission arrives with the broker's manuscript wording attached."),
         S("02", "Inspection: racks above the sprinkler design", "view", "The inspection is verified evidence: racks at thirty feet over a system designed for twenty, and no in-rack sprinklers."),
         S("04", "Draft: refer, conditionally quote", "view", "The draft: refer, or quote conditionally, with the storage deficiency and the old port roof as conditions."),
         S("05", "Underwriter overrides the storage flag", "override", "The underwriter overrides the storage flag. Her reason: in-rack sprinklers were installed last year, according to the insured."),
         S("06", "Intended action: quote with the broker's wording", "action", "She intends to quote below technical, with the broker's manuscript."),
         S("07", "Tier 2 critique", "view", "Tier two reads what a rule can't: the override relies on evidence that isn't on file and contradicts the inspection; and the manuscript deletes the water exclusion in a flood zone."),
         S("08", "Refer — senior review", "view", "Refer. This needs a senior decision."),
         S("08", "Referred to the head of property", "route", "It goes to the head of property with a memo that cites every source."),
         S("08", "Approved with conditions", "decide_referral", "She approves with conditions: the water exclusion reinstated except sprinkler leakage, the in-rack protection evidenced and verified before bind, and a roof survey."),
         S("06", "Revised action: limited manuscript", "revise", "The underwriter revises the wording to the approved version."),
         S("08", "Pass with flags", "view", "It passes, with the conditions open before bind."),
         S("09", "Quote issued with subjectivities", "commit", "The quote goes out with the conditions as subjectivities."),
         S("05", "Contractor letter requested", "request_wait", "The broker sends the in-rack contractor's completion letter."),
         S("09", "Broker accepts", "broker_wait", "The broker accepts, subject to the conditions."),
         S("05", "Engineer verifies on site", "survey", "An engineer visits and verifies the installation, and the port roof."),
         S("09", "Bound — conditions cleared on evidence", "bind", "At bind, assurance confirms every condition cleared on evidence."),
         S("10", "Outcome: storm surge", "outcome", "Months later, a storm surge floods the port building. Under the broker's wording it would have been covered. Under the approved wording, it's excluded."),
     ]},
]


def all_playbooks(rt) -> list[dict]:
    s = st(rt)
    out = [dict(p) for p in PLAYBOOKS]
    lines = {c: f"{n}." for c, n, *_ in PIPE}
    say = {"01": "The submission arrives and is parsed.", "02": "Every value is extracted with its source; contradictions and gaps are found.",
           "03": "Guidelines, authority, price and portfolio are applied.", "04": "The draft decision pack is ready before a human opens the file.",
           "05": "The underwriter exercises judgement on the pack.", "06": "The intended action is recorded, with its rationale.",
           "07": "Assurance checks the action independently.", "08": "Pass, pass with flags, or refer — with the decision owner.",
           "09": "The human decision owner commits, through the policy system.", "10": "The outcome comes back and calibrates the flags."}
    for cid in s.heroes:
        c = s.cases[cid]
        out.append({"id": f"lifecycle-{cid}", "account_id": cid, "title": "All 10 stages in order", "aspects": ["Full lifecycle"],
                    "intro": f"Here's {c['short']}, taken through all ten stages of the decision, one system at a time.",
                    "outro": "Prepared, judged, assured, decided and learned from — every step evidenced.",
                    "brief": {"audience": "Anyone who wants to see every stage for one submission", "problem": c["title"],
                              "story": ["Each of the ten stages is opened in order and its step is run from the case script: submission, document intelligence, carrier context, draft, judgement, intended action, assurance, verdict, final decision, outcome."],
                              "watch": ["Which stages are the product (REAL) and which are stand-ins (MOCK)"], "value": "Shows where the product sits on both sides of the human decision.", "questions": []},
                    "steps": [S(code, lines[code][:-1], "stage", say[code]) for code, *_ in PIPE]})
    for p in out:
        c = s.cases[p["account_id"]]
        p.update(account_name=c["short"], scenario=c.get("scenario"), subject_href=f"/decision/cases/{p['account_id']}")
    return out


def _v(res) -> str:
    return VERDICT_LABEL[res["verdict"]]


def run_step(rt, p: dict, step: dict) -> str:
    s = st(rt)
    cid = p["account_id"]
    c = s.cases[cid]
    sc = c["truth"]["script"]
    uw = c["uw"]
    a = step["action"]
    if a == "view":
        return f"Showing {step['label'].lower()}"
    if a == "stage":
        return SG.run(rt, step["code"], cid)
    if a == "arrive":
        return SG.run(rt, "01", cid)
    if a == "resolve":
        before = [x for x in c["contradictions"] if x["status"] == "OPEN"]
        n = FL.resolve_all(rt, cid, uw, rt.clock)
        x = before[0] if before else None
        return (f"{n} contradiction(s) resolved: {x['field_label']} at {x['location']} = {x['resolved']['value']} ({x['resolved']['source']}); "
                f"rating impact of the claimed value {money(x['impact_usd'])}; technical {money(c['pack']['pricing']['technical'])}") if x else "No open contradictions"
    if a == "request":
        r = FL.request_info(rt, cid, sc["request"], uw, rt.clock)
        return f"Requested from {c['broker']}: {'; '.join(r['items'])} (reply due {r['due']})"
    if a == "request_wait":
        items = sc["request"]
        pend = [r for r in c["requests"] if r["status"] == "SENT"]
        r = pend[-1] if pend else FL.request_info(rt, cid, items, uw, rt.clock)
        FL.run_due(rt, cid, r["due"])
        p_ = c["pack"]
        return f"Broker returned {'; '.join(r['items']).lower()} on {r['due']}; parsed into evidence · loss runs on file {p_['loss_run_years']:g} years · technical {money(p_['pricing']['technical'])} (experience modifier {p_['pricing']['exp_mod']})"
    if a == "prerefer":
        pr = sc["prerefer"]
        ref = FL.prerefer(rt, cid, pr["note"], uw, rt.clock)
        FL.decide_referral(rt, ref["referral_id"], "APPROVE", pr.get("conditions"), pr.get("envelope"), "Approved on the evidence", pr["approver"], rt.clock)
        return f"Pre-referred to L{ref['required_level']} ({'; '.join(t['title'] for t in ref['triggers'])}); approved by {USER_BY_ID[pr['approver']]['name']} — envelope {FL._env_text(ref['envelope'])}"
    if a == "override":
        msgs = []
        for ov in sc["override"]:
            uids = list(rt.store.account_locations(cid))
            subj = uids[ov["loc"]] if "loc" in ov else None
            FL.override(rt, cid, ov["rule"], subj, ov["reason"], uw, rt.clock)
            msgs.append(f"{ov['rule']} overridden by {USER_BY_ID[uw]['name']}: “{ov['reason']}”")
        return "; ".join(msgs)
    if a in ("action", "revise"):
        raw = sc["action"] if a == "action" else sc["revise"]
        res = FL.submit_action(rt, cid, raw, uw, rt.clock)
        act = c["actions"][-1]
        return (f"{act['type'].title()} at {money(act['premium'])} · AOP {money(act['aop'])} · line {act['line'] * 100:.0f}%"
                + (f" · manuscript {act['manuscript']}" if act.get("manuscript") else "")
                + f" — {pct(res['deviation'], True)} vs technical {money(res['technical'])}, permitted ±{res['permitted_dev'] * 100:.0f}% → {_v(res)}"
                + (f" ({res['counts']['fail']} fail: {', '.join(ch['rule_id'] for ch in res['checks'] if ch['result'] == 'FAIL')})" if res["counts"]["fail"] else "")
                + (f" · {sum(1 for k in res['conditions'] if k['status'] == 'OPEN')} condition(s) before bind" if any(k["status"] == "OPEN" for k in res["conditions"]) else ""))
    if a == "route":
        return FL.route(rt, cid, uw, rt.clock)
    if a == "decide_referral":
        pend = [r for r in c["referrals"] if s.referrals[r]["status"] == "PENDING"]
        if not pend:
            return "No pending referral"
        ref = s.referrals[pend[-1]]
        rd = sc["referral_decision"]
        FL.decide_referral(rt, ref["referral_id"], rd["decision"], rd.get("conditions"), rd.get("envelope"), rd.get("note", ""), rd["approver"], rt.clock)
        return (f"{rd['decision'].title()}d by {USER_BY_ID[rd['approver']]['name']} (L{USER_BY_ID[rd['approver']]['authority_level']})"
                + (f" · envelope {FL._env_text(ref['envelope'])}" if ref.get("envelope") else "") + (f" · {len(rd.get('conditions') or [])} condition(s)" if rd.get("conditions") else ""))
    if a == "commit":
        return FL.final_decision(rt, cid, "COMMIT", uw, rt.clock)
    if a == "decline":
        ref = next((s.referrals[r] for r in c["referrals"] if s.referrals[r]["status"] == "DECLINED"), None)
        return FL.final_decision(rt, cid, "DECLINE", ref["approver_id"] if ref else uw, rt.clock, (ref or {}).get("decision_note") or "Outside appetite")
    if a == "broker_wait":
        ev = FL.next_event(rt, cid, ("decision.broker_quote",))
        if not ev:
            return f"Broker reply already in: quote {(c.get('quote') or {}).get('status', 'none').lower().replace('_', ' ')}"
        titles = FL.run_due(rt, cid, ev["date"])
        return f"Clock → {rt.clock}: " + "; ".join(titles[-3:]).lower()
    if a == "survey":
        FL.order_inspection(rt, cid, "u_elena", rt.clock, "Verify in-rack sprinklers and roof condition")
        ev = FL.next_event(rt, cid, ("decision.inspection",))
        FL.run_due(rt, cid, ev["date"])
        evc = [k for k in c["conditions"] if k.get("kind") == "evidence"]
        cl = [k for k in evc if k["status"] == "CLEARED"]
        return f"Engineer visited {ev['date']}; verified observations recorded" + (f" · evidence conditions cleared: {len(cl)} of {len(evc)}" if evc else "")
    if a == "bind":
        return FL.bind(rt, cid, uw, rt.clock)
    if a == "outcome":
        return SG.run(rt, "10", cid)
    return "Unknown action"

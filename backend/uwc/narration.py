"""Presenter narration for the workflow playbooks — written for a carrier audience
(CUO, head of property, underwriting operations). One entry per playbook step, plus
an intro and an outro. Figures quoted are the ones the engine produces on a clean run."""

NARRATION: dict[str, dict] = {
    "reprice-refer": {
        "intro": "This is ABC Manufacturing, a five-location manufacturer renewing on the first of November. I'll take it from the broker's submission to an issued policy, and show you exactly where a conventional renewal would have leaked margin.",
        "steps": [
            "The broker's renewal submission lands in the mailbox. The email and the attached statement of values are ingested automatically. Nobody rekeys a thing.",
            "Every value is extracted with its exact cell reference. Matching this year's schedule against last year's finds a new Tampa building that was never on the expiring schedule, and notices that the Reno warehouse now describes battery storage.",
            "Now the rater and the cat model are re-run three times on controlled snapshots. Insured values are up about twenty-six percent, but modelled risk is up sixty-six, because the Tampa hurricane exposure nearly doubled. The broker's target looks like a ten percent increase. Like-for-like, it's a rate cut of about twenty-seven percent.",
            "Appetite is fine. Light manufacturing is in appetite under the 2026 guidelines. The problem here isn't the class. It's price and terms.",
            "The underwriter reviews the material findings and accepts them. Every decision carries a reason code, so the carrier learns which rules are precise and which are noise.",
            "We draft a quote at ninety-five percent of technical, and move the named-storm deductible to the three percent floor the new guidelines require.",
            "Authority is checked on the intended terms, not on the file. The Tampa accumulation and the linked water losses take this above the underwriter's authority, so it's referred, with a memo that cites every piece of evidence.",
            "The approver signs off, with a condition: the roof replacement schedule before bind. That approval is locked to a hash of these exact terms. If anyone changes them, it's void.",
            "The quote goes to the broker.",
            "Five days later, the broker accepts.",
            "At bind, the platform re-checks authority and compares the binder with the accepted quote, field by field.",
            "Here's where most carriers lose control. The policy system keys the named-storm minimum incorrectly at issuance. Normally, nobody would see this until a claim.",
            "The platform catches it the same day, and raises an endorsement correction, with the binder and the issued policy side by side as evidence.",
        ],
        "outro": "That's one renewal. Margin protected, terms corrected, authority enforced, and an audit trail your reinsurers or regulator can follow line by line.",
    },
    "fast-track": {
        "intro": "Not every renewal needs work. Crestline is an eight-building office portfolio. Watch how quickly the platform clears an account where nothing material has changed.",
        "steps": [
            "The renewal schedule arrived in July. Values are trended in line with construction-cost inflation.",
            "All eight buildings match last year's schedule, one for one. No new locations, no occupancy changes, no conflicting evidence.",
            "Technical price and adequacy are comfortably above the floor. There's nothing to fix.",
            "So the underwriter confirms the fast-track with one click. On a typical book, forty to fifty percent of renewals go down this lane. That's where the handling-time saving comes from.",
            "The quote is set at the exposure-adjusted expiring premium. A flat rate change, on a like-for-like basis.",
            "Sent to the broker.",
            "Accepted.",
            "Bound.",
            "And issued, exactly as bound.",
            "The contract check confirms that quote, binder and policy agree. Minutes of work, fully evidenced.",
        ],
        "outro": "Fast-tracking isn't skipping the checks. Every control still ran. It just didn't find anything worth a human's time.",
    },
    "decline-notice": {
        "intro": "Delta Scrap Metals is a long-standing account in a class the carrier has just decided to exit. This one is about acting on a guideline change in time.",
        "steps": [
            "The 2026 guidelines, effective the first of July, decline scrap and recycling yards. The platform re-evaluated the entire book the day they were published.",
            "This is an admitted policy in Louisiana, so a non-renewal needs statutory notice. The platform works out the latest valid notice date, and counts down to it.",
            "The underwriter asks for an exception, on the strength of a long relationship. That goes to the chief underwriting officer.",
            "The C U O declines. The class is outside appetite.",
            "The non-renewal notice goes out inside the statutory window, to the insured and the broker, and it's logged against the account.",
            "And the exposure leaves the portfolio view.",
        ],
        "outro": "A guideline change only creates value if it reaches every affected account before the notice windows close.",
    },
    "midterm-event": {
        "intro": "Renewal isn't the only moment that matters. Pinecrest Plaza is mid-term, and the risk has changed underneath the policy.",
        "steps": [
            "In April, an endorsement recorded that the anchor tenant had left. Sixty-two percent of the centre is now vacant.",
            "In August, a fire-protection impairment notice arrives. The sprinkler riser in the vacant anchor unit has been shut off.",
            "That notice is recorded as verified evidence. Vacant and unsprinklered is one of the worst fire combinations there is.",
            "The platform doesn't wait for renewal. It raises a critical referral the same day.",
            "A senior underwriter approves continuation, subject to the sprinklers being restored and a fire watch within seven days.",
            "The condition letter goes to the insured through the broker, listing exactly what's required.",
            "And the account is re-evaluated with the conditions in place.",
        ],
        "outro": "That's in-force monitoring. The carrier finds out when the risk changes, not when the loss happens.",
    },
    "counter-offer": {
        "intro": "Negotiation is where discipline usually slips. Let's see what happens when the broker pushes back.",
        "steps": [
            "The renewal submission arrives.",
            "Pricing is re-run on the new exposure.",
            "The underwriter opens at twenty percent above technical.",
            "It's referred, because of the Tampa accumulation.",
            "And approved, on those exact terms.",
            "Sent to the broker.",
            "The broker counters, at five hundred and eighty thousand.",
            "The underwriter re-quotes at the counter. Watch the approval. Because the terms changed, the earlier approval is invalidated automatically.",
            "So the new terms have to be referred again.",
            "Re-approved, against the new terms hash.",
            "Sent.",
            "Accepted.",
            "Bound.",
            "And issued clean.",
        ],
        "outro": "Approvals attach to terms, not to accounts. That closes one of the most common authority gaps in commercial underwriting.",
    },
    "referral-declined": {
        "intro": "Lumen Jewelers has fourteen stores carrying high-value stock. This walkthrough shows the platform stopping an underpriced quote.",
        "steps": [
            "Security first. Three stores in high-crime areas have alarms that aren't centrally monitored, even though the policy requires it as a protective safeguard.",
            "Pricing compares the expiring premium with technical.",
            "The underwriter tries eighty-five percent of technical.",
            "That's below the adequacy floor, so it needs a referral.",
            "The approver declines. It's below adequacy, and the security conditions are missing.",
            "The underwriter re-quotes at ninety-five percent of technical.",
            "Referred again.",
            "Approved, with a condition: monitored alarm certificates for the three stores before bind.",
            "Sent.",
            "Accepted.",
            "Bound.",
            "Issued.",
        ],
        "outro": "The platform doesn't replace the underwriter's judgement. It makes sure that judgement is exercised on the right facts, at the right authority.",
    },
    "matching-dq": {
        "intro": "Summit University's facilities team renumbered every building this year. For most systems, that breaks the year-over-year comparison entirely.",
        "steps": [
            "The schedule arrived in thousands of dollars, with a totals row and a hidden notes sheet. The parser scales the values, drops the totals, and records every correction it made.",
            "Thirty-six buildings match automatically. Three addresses are close but not certain, so they're proposed to a human, and the underwriter confirms them.",
            "Pricing is re-run on the matched exposure, including the new Innovation Center and the two halls that were merged in the renovation.",
            "Clean data, confirmed matches, and every decision recorded.",
        ],
        "outro": "If you can't match locations across years, every downstream comparison is noise. This is the foundation everything else sits on.",
    },
    "engineering-condition": {
        "intro": "Keystone Plastics shows what happens when an engineering commitment isn't kept.",
        "steps": [
            "Last year, installing spark detection on a dust collector was a condition of binding. The register shows it closed, but with no completion evidence.",
            "In March, a one point four million dollar fire started in that same dust collector. The platform links the claim to the open recommendation.",
            "The underwriter accepts the engineering findings.",
            "A request goes to the broker for verified completion evidence.",
            "The renewal is quoted at ninety-five percent of technical.",
            "Referred, because of the linked loss.",
            "Approved, subject to risk engineering verifying the work before bind.",
            "Sent.",
            "Accepted.",
            "Bound, with the condition attached.",
        ],
        "outro": "Engineering recommendations only reduce losses if someone checks they were done. Here, that check is automatic.",
    },
    "contract-authority": {
        "intro": "St. Aurelia is a hospital campus. Its problems started last year, in the contract itself.",
        "steps": [
            "On the expiring policy, the named-storm minimum from the binder never made it onto the issued policy.",
            "And the referral approved version two of the quote. Version three, with a lower minimum, is what was actually bound.",
            "In October, the renewal submission arrives.",
            "Pricing is re-run.",
            "The renewal is quoted on guideline terms.",
            "Referred.",
            "Approved, subject to the generator load test that was still outstanding from last year.",
            "Sent.",
            "Accepted.",
            "Bound.",
            "And the policy system drops the named-storm minimum again at issuance.",
            "This time, it's caught the same day.",
        ],
        "outro": "Contract integrity is the cheapest control to run, and one of the most expensive to skip.",
    },
}

STAGE_LINES = {
    "01": "The broker's submission arrives in the mailbox and is ingested automatically.",
    "02": "Clearance checks for duplicates, broker licensing and sanctions.",
    "03": "Appetite and triage apply the guidelines in force today.",
    "04": "Documents are extracted with exact anchors, and every location is matched and enriched.",
    "05": "The engineering register shows each recommendation, and whether it was verified.",
    "06": "The rater and cat model are re-run on controlled snapshots, to separate exposure, terms and pure rate.",
    "07": "Authority is checked on the intended terms, and referrals go to the right level.",
    "08": "A quote version is drafted, and locked to a hash of its terms.",
    "09": "The quote goes to the broker, and the broker responds.",
    "10": "At bind, authority is re-checked, and the binder is compared with the quote.",
    "11": "The policy is issued, and compared with the binder.",
    "12": "Mid-term events, like endorsements, claims and impairments, trigger an immediate re-evaluation.",
    "13": "Claims are linked back to locations and to engineering recommendations.",
    "14": "The account's contribution to portfolio accumulation is tracked.",
    "15": "The renewal engine records the passes, findings and actions, and the cycle begins again.",
}


def for_playbook(p: dict) -> dict:
    if p.get("intro"):
        return {"intro": p["intro"], "outro": p["outro"], "steps": [s.get("say") or s["label"] for s in p["steps"]]}
    n = NARRATION.get(p["id"])
    if n:
        return n
    return {"intro": f"Here's {p['account_name']}, taken through all fifteen stages of the underwriting lifecycle.",
            "steps": [STAGE_LINES[s["code"]] for s in p["steps"]],
            "outro": "That's the full cycle, from submission to renewal, with every step evidenced."}

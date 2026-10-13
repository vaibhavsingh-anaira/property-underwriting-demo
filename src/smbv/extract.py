"""LLM extraction of underwriting facts from a business's own website, with verbatim evidence.

A fact counts only if its quote is found in the page text; otherwise it is downgraded to not_stated."""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import json
import re
from datetime import datetime, timezone
import pandas as pd
from smbv.config import load
from smbv.db import connect
from smbv.llm import client, model

PROMPT_VERSION = "v2"
FACTS = {
    "serves_alcohol": "This location serves beer, wine, spirits or cocktails (a drinks menu, bar, wine list, happy hour with drinks). "
                      "A 'Margarita pizza', 'cocktail sauce' or 'BYOB' is not alcohol service.",
    "deep_frying": "The menu includes deep-fried items (fries, fried chicken, tempura, wings, calamari, fritters, donuts).",
    "delivery": "The business offers delivery itself or through a delivery app (DoorDash, Uber Eats, Grubhub, Seamless).",
    "open_after_midnight": "Posted hours show this location open past 12:00 midnight on at least one day.",
    "outdoor_seating": "The business offers outdoor seating (patio, sidewalk, terrace, garden, rooftop, outdoor dining).",
}
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_this_business": {"type": "BOOLEAN"},
        "name_on_page": {"type": "STRING"},
        "facts": {"type": "OBJECT", "required": list(FACTS), "properties": {
            f: {"type": "OBJECT", "required": ["value", "quote"], "properties": {
                "value": {"type": "STRING", "enum": ["yes", "no", "not_stated"]},
                "quote": {"type": "STRING"}}} for f in FACTS}},
    },
    "required": ["is_this_business", "name_on_page", "facts"],
}


def prompt(name: str, address: str, text: str) -> str:
    rules = "\n".join(f"- {k}: {v}" for k, v in FACTS.items())
    return f"""You verify facts for a restaurant insurance application using ONLY the website text below.
Business on the application: {name}, {address}, New York.

First decide is_this_business: true if the text is this business's own site (a multi-location brand counts if this location
or the brand menu is shown); false if it is a different business, a directory, a parked domain or an error page.

For each fact answer "yes" only if the text clearly states it for this business.
Answer "no" ONLY when the text explicitly rules it out (e.g. "we do not serve alcohol", "alcohol-free", "BYOB", "dine-in only, no delivery",
posted hours that all end before midnight). A menu or page that simply does not mention something is "not_stated", never "no".
Customer reviews quoted on the page count as weaker evidence: use them only if nothing else on the page answers the fact.
Copy a short verbatim quote (5-25 words, exactly as written) that supports a yes/no answer; use "" for not_stated.
Facts:
{rules}

WEBSITE TEXT:
{text}"""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w$%.,:&'-]+", " ", s.lower())).strip()


def verified(quote: str, text: str) -> bool:
    q = _norm(quote)
    return len(q) >= 3 and q in _norm(text)


def _call(row) -> dict:
    from google.genai import types
    text = row.text[: load()["extract"]["max_chars"]]
    p = prompt(row.name, f"{row.house} {row.street}", text)
    key = hashlib.sha256(f"{model()}|{PROMPT_VERSION}|{p}".encode()).hexdigest()
    try:
        r = client().models.generate_content(model=model(), contents=p, config=types.GenerateContentConfig(
            temperature=0, response_mime_type="application/json", response_schema=SCHEMA))
        out = json.loads(r.text)
        usage = r.usage_metadata
        tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0) if usage else None
        err = None
    except Exception as e:
        out, tokens, err = None, None, f"{type(e).__name__}: {str(e)[:200]}"
    return {"business_id": row.business_id, "input_hash": key, "model": model(), "prompt_version": PROMPT_VERSION,
            "response": json.dumps(out) if out else None, "tokens": tokens, "error": err, "text": text,
            "url": row.final_url or row.url, "created_at": datetime.now(timezone.utc).isoformat()}


def run() -> None:
    cfg, con = load()["extract"], connect()
    con.execute("CREATE TABLE IF NOT EXISTS llm_calls (business_id VARCHAR, input_hash VARCHAR, model VARCHAR, prompt_version VARCHAR,"
                " response VARCHAR, tokens INTEGER, error VARCHAR, url VARCHAR, created_at VARCHAR)")
    con.execute("CREATE TABLE IF NOT EXISTS web_facts (business_id VARCHAR, fact VARCHAR, value VARCHAR, quote VARCHAR,"
                " quote_verified BOOLEAN, is_this_business BOOLEAN, url VARCHAR, model VARCHAR, prompt_version VARCHAR)")
    todo = con.execute(f"""SELECT w.business_id, w.url, w.final_url, w.text, b.name, b.house, b.street
        FROM web_pages w JOIN businesses b USING (business_id)
        WHERE w.words >= 80 AND w.business_id NOT IN (SELECT business_id FROM llm_calls WHERE error IS NULL AND prompt_version='{PROMPT_VERSION}')
        ORDER BY hash(w.business_id)""").df()
    if cfg["max_businesses"]:
        done = con.execute(f"SELECT count(DISTINCT business_id) FROM llm_calls WHERE error IS NULL AND prompt_version='{PROMPT_VERSION}'").fetchone()[0]
        todo = todo.head(max(cfg["max_businesses"] - done, 0))
    print(f"[extract] {len(todo):,} businesses -> {model()}")
    with cf.ThreadPoolExecutor(cfg["workers"]) as ex:
        res = list(ex.map(_call, todo.itertuples()))
    calls = pd.DataFrame(res)
    if len(calls):
        con.execute("INSERT INTO llm_calls SELECT business_id, input_hash, model, prompt_version, response, tokens, error, url, created_at FROM calls")
        facts = []
        for r in res:
            if not r["response"]:
                continue
            out = json.loads(r["response"])
            for f in FACTS:
                v = out["facts"].get(f, {})
                ok = verified(v.get("quote", ""), r["text"]) if v.get("value") in ("yes", "no") else None
                facts.append({"business_id": r["business_id"], "fact": f,
                              "value": v.get("value") if ok is not False else "not_stated",
                              "quote": v.get("quote", ""), "quote_verified": ok, "is_this_business": out["is_this_business"],
                              "url": r["url"], "model": r["model"], "prompt_version": PROMPT_VERSION})
        fdf = pd.DataFrame(facts)
        con.execute("DELETE FROM web_facts WHERE business_id IN (SELECT business_id FROM fdf)")
        con.execute("INSERT INTO web_facts SELECT * FROM fdf")
    s = con.execute("SELECT count(*), sum((error IS NOT NULL)::INT), sum(tokens) FROM llm_calls").fetchone()
    q = con.execute("SELECT avg(quote_verified::INT) FROM web_facts WHERE quote_verified IS NOT NULL").fetchone()[0]
    print(f"[extract] calls: {s[0]:,} | errors: {s[1]:,} | tokens: {s[2] or 0:,} | quotes found verbatim in page: {(q or 0):.0%}")
    con.close()

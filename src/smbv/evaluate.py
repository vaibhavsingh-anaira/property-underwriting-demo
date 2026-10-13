"""Measure the pipeline on real data and write reports/evaluation.md."""
from __future__ import annotations
import os
from datetime import datetime, timezone
import pandas as pd
from smbv.config import ROOT, load
from smbv.db import connect, raw
from smbv.extract import PROMPT_VERSION
from smbv.ingest import DATASET_URL, SOURCES


def _pr(df: pd.DataFrame, pred: str, truth: str) -> str:
    tp = ((df[pred]) & (df[truth])).sum(); fp = ((df[pred]) & (~df[truth])).sum(); fn = ((~df[pred]) & (df[truth])).sum()
    p = tp / (tp + fp) if tp + fp else float("nan"); r = tp / (tp + fn) if tp + fn else float("nan")
    return f"precision {p:.0%}, recall {r:.0%} (n={len(df):,}; tp {tp}, fp {fp}, fn {fn})"


def run() -> None:
    con, cfg = connect(read_only=True), load()
    L = []
    w = L.append
    w(f"# Pipeline evaluation\n\nGenerated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · scope: {', '.join(cfg['scope']['boroughs'])} · "
      f"LLM: {cfg['gemini']['model']}\n\nAll numbers are computed from real downloaded records; nothing is synthetic.\n")
    w("## 1. Sources ingested\n\n| Source | Rows | Downloaded (UTC) | Dataset |\n|---|---|---|---|")
    for name in [*SOURCES, "osm"]:
        p = raw(name)
        if os.path.exists(p):
            n = len(pd.read_parquet(p, columns=[pd.read_parquet(p).columns[0]]))
            ts = datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).strftime("%Y-%m-%d %H:%M")
            w(f"| {name} | {n:,} | {ts} | {DATASET_URL.get(name, 'OpenStreetMap Overpass API')} |")

    nb = con.execute("SELECT count(*) FROM businesses").fetchone()[0]
    w(f"\n## 2. Entity resolution\n\nBusinesses in scope (inspected food establishments): **{nb:,}**\n\n| Source | Businesses linked | Share | Methods |\n|---|---|---|---|")
    for r in con.execute("SELECT source, count(DISTINCT business_id), string_agg(DISTINCT method, ', ') FROM links GROUP BY 1 ORDER BY 2 DESC").fetchall():
        w(f"| {r[0]} | {r[1]:,} | {r[1] / nb:.0%} | {r[2]} |")
    shared = con.execute("SELECT avg((tenants_in_lot > 1)::INT) FROM businesses").fetchone()[0]
    w(f"\nBusinesses sharing a tax lot with another food business: {shared:.0%}. Building-level records (violations, 311) "
      "for these lots cannot be attributed to one tenant and are labelled as building-level.")
    corp = con.execute("SELECT count(DISTINCT q.legal_name), (SELECT count(DISTINCT legal_name) FROM corp_queries) "
                       "FROM corp_queries q JOIN corps c ON c.current_entity_name = q.variant").fetchone()
    w(f"\nLegal names found in the NY company register: {corp[0]:,} of {corp[1]:,} ({corp[0] / max(corp[1], 1):.0%}).")

    pages = con.execute(f"SELECT count(*), avg((words >= {cfg['crawl']['min_words']})::INT), avg((method='headless')::INT), "
                        "avg((note='disallowed by robots.txt')::INT) FROM web_pages").fetchone()
    w(f"\n## 3. Websites\n\nSites fetched: {pages[0]:,} · usable ({cfg['crawl']['min_words']}+ words): {pages[1]:.0%} · "
      f"needed headless rendering: {pages[2]:.0%} · blocked by robots.txt: {pages[3]:.0%}")

    calls = con.execute("SELECT count(*), sum((error IS NULL)::INT), sum(tokens) FROM llm_calls WHERE prompt_version = ?", [PROMPT_VERSION]).fetchone()
    wf = con.execute("SELECT * FROM web_facts").df()
    own = wf.drop_duplicates("business_id").is_this_business.mean() if len(wf) else float("nan")
    qv = wf.quote_verified.dropna().mean() if len(wf) else float("nan")
    w(f"\n## 4. LLM extraction\n\nPrompt {PROMPT_VERSION} · calls: {calls[0]:,} ({calls[1]:,} succeeded) · tokens: {calls[2] or 0:,} · page judged to be the business's own site: {own:.0%} · "
      f"yes/no answers whose quote was found verbatim in the page: {qv:.0%} (answers failing this check are discarded)\n")
    w("| Fact | yes | no | not stated |\n|---|---|---|---|")
    for f, g in wf[wf.is_this_business].groupby("fact"):
        v = g.value.value_counts(normalize=True)
        w(f"| {f} | {v.get('yes', 0):.0%} | {v.get('no', 0):.0%} | {v.get('not_stated', 0):.0%} |")

    lic = set(con.execute("SELECT business_id FROM links WHERE source='liquor_licences'").df().business_id)
    w("\n## 5. Accuracy against official records\n\nTruth for `serves_alcohol`: an active on-premises NYS liquor licence linked to the business. "
      "Licence matching itself misses some businesses, so a share of 'false positives' are real bars whose licence was not matched; "
      "they appear in the app as conflicts to review.\n")
    a = wf[(wf.fact == "serves_alcohol") & wf.is_this_business].copy()
    if len(a):
        a["pred"], a["truth"] = a.value.eq("yes"), a.business_id.isin(lic)
        w(f"- Website + Gemini, all sites with a verdict: {_pr(a, 'pred', 'truth')}")
        s = a[a.value != "not_stated"]
        w(f"- Website + Gemini, only where the site states yes or no: {_pr(s, 'pred', 'truth')}")
    osm = con.execute("SELECT l.business_id FROM links l WHERE source='osm'").df()
    o = pd.read_parquet(raw("osm"))
    bars = set(con.execute("SELECT business_id, source_key FROM links WHERE source='osm'").df()
               .merge(o[["osm_id", "amenity"]], left_on="source_key", right_on="osm_id").query("amenity in ['bar','pub','biergarten','nightclub']").business_id)
    osm["pred"], osm["truth"] = osm.business_id.isin(bars), osm.business_id.isin(lic)
    w(f"- OpenStreetMap amenity=bar/pub, all linked venues: {_pr(osm, 'pred', 'truth')}")

    f = con.execute("SELECT * FROM facts").df()
    w(f"\n## 6. Coverage and conflicts\n\n| Fact | Businesses with a value | Share of {nb:,} | Conflicts |\n|---|---|---|---|")
    for fact, g in f.groupby("fact"):
        w(f"| {fact} | {len(g):,} | {len(g) / nb:.0%} | {g.conflict.sum():,} |")
    ex = con.execute("""SELECT b.name, b.house || ' ' || b.street AS address, f.fact, f.value, f.source, f.disagreeing
        FROM facts f JOIN businesses b USING (business_id) WHERE f.conflict ORDER BY hash(f.business_id) LIMIT 12""").df()
    if len(ex):
        w("\nSample conflicts (each one is a question an underwriter would ask):\n\n| Business | Address | Fact | Resolved | From | Disagreeing |\n|---|---|---|---|---|---|")
        for r in ex.itertuples():
            w(f"| {r.name} | {r.address} | {r.fact} | {r.value} | {r.source} | {r.disagreeing} |")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "evaluation.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    con.close()

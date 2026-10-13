"""Look up legal entities (from licences) in the NY Department of State register: formation date, entity type.

Queried on demand rather than bulk-downloaded (4.3M rows statewide). Every queried name is cached."""
from __future__ import annotations
import re
import pandas as pd
from smbv.db import connect
from smbv.ingest import _get

DATASET = "https://data.ny.gov/resource/n9v6-gdp6.json"


def variants(legal: str) -> set[str]:
    u = " ".join(legal.upper().split())
    base = {u, u.rstrip("."), u.replace(",", ""), u.replace(",", "").rstrip(".")}
    base |= {re.sub(r"\bINC$", "INC.", v) for v in base} | {re.sub(r"\bCORP$", "CORP.", v) for v in base}
    return {v for v in base if v}


def run() -> None:
    con = connect()
    con.execute("CREATE TABLE IF NOT EXISTS corp_queries (legal_name VARCHAR, variant VARCHAR)")
    con.execute("CREATE TABLE IF NOT EXISTS corps (dos_id VARCHAR, current_entity_name VARCHAR, initial_dos_filing_date VARCHAR,"
                " entity_type VARCHAR, county VARCHAR, jurisdiction VARCHAR)")
    names = [r[0] for r in con.execute("SELECT DISTINCT legal_name FROM legal_names WHERE legal_name IS NOT NULL "
                                       "AND legal_name NOT IN (SELECT legal_name FROM corp_queries)").fetchall()]
    pairs = [(n, v) for n in names for v in variants(n)]
    print(f"[corps] {len(names):,} new legal names, {len(pairs):,} spellings to query")
    found = []
    for i in range(0, len(pairs), 40):
        chunk = pairs[i:i + 40]
        inlist = ",".join("'" + v.replace("'", "''") + "'" for _, v in chunk)
        rows = _get(DATASET, {"$select": "dos_id,current_entity_name,initial_dos_filing_date,entity_type,county,jurisdiction",
                              "$where": f"current_entity_name in ({inlist})", "$limit": 1000})
        found += rows
        print(f"  queried {min(i + 40, len(pairs)):,}/{len(pairs):,}, matched {len(found):,}", end="\r", flush=True)
    if pairs:
        con.execute("INSERT INTO corp_queries SELECT * FROM (SELECT unnest(?) AS legal_name, unnest(?) AS variant)",
                    [[p[0] for p in pairs], [p[1] for p in pairs]])
    if found:
        df = pd.DataFrame(found).reindex(columns=["dos_id", "current_entity_name", "initial_dos_filing_date", "entity_type",
                                                  "county", "jurisdiction"])
        con.execute("INSERT INTO corps SELECT * FROM df")
    con.execute("CREATE OR REPLACE TABLE corps AS SELECT DISTINCT * FROM corps")
    n = con.execute("SELECT count(DISTINCT q.legal_name) FROM corp_queries q JOIN corps c ON c.current_entity_name = q.variant").fetchone()[0]
    total = con.execute("SELECT count(DISTINCT legal_name) FROM corp_queries").fetchone()[0]
    print(f"\n[corps] legal names found in register: {n:,} of {total:,} ({n / max(total, 1):.0%})")
    con.close()

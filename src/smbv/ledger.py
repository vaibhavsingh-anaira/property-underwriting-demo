"""Evidence ledger: every source becomes observations (business, fact, value, source, evidence); facts are then resolved.

Trust: official records (3) > the business's own website (2) > absence of an official record (1.5) > crowd/complaint signals (1).
A fact is in conflict when two sources give different yes/no answers."""
from __future__ import annotations
import pandas as pd
from smbv import normalize as N
from smbv.db import connect, raw
from smbv.ingest import DATASET_URL

TRUST = {"official": 3, "website": 2, "official_absence": 1.5, "crowd": 1, "complaints": 1}
BOOL_FACTS = ["serves_alcohol", "deep_frying", "delivery", "open_after_midnight", "outdoor_seating"]


def _obs(rows, business_id, fact, value, source, kind, evidence, ref, observed_at=None):
    rows.append({"business_id": business_id, "fact": fact, "value": str(value), "source": source, "source_type": kind,
                 "trust": TRUST[kind], "evidence": evidence, "ref": ref, "observed_at": observed_at})


def observations(con) -> pd.DataFrame:
    b = con.execute("SELECT * FROM businesses").df()
    links = con.execute("SELECT * FROM links").df()
    rows: list[dict] = []
    lk = {s: g.set_index("business_id") for s, g in links.groupby("source")}

    # liquor licence (official) or its absence
    lic = pd.read_parquet(raw("liquor_licences")).set_index("licensepermitid")
    ll = lk.get("liquor_licences", pd.DataFrame())
    for r in b.itertuples():
        if r.business_id in ll.index:
            l = ll.loc[r.business_id]
            x = lic.loc[l.source_key]
            _obs(rows, r.business_id, "serves_alcohol", "yes", "NYS Liquor Authority", "official",
                 f"Active licence {l.source_key}: {x.description}, class {x['class']}, '{x.legalname}' at {x.actualaddressofpremises}; "
                 f"expires {str(x.expirationdate)[:10]} (matched by {l.method}, score {l.score:.0f})",
                 f"https://data.ny.gov/resource/9s3h-dpkz.json?licensepermitid={l.source_key}", str(x.lastissuedate)[:10])
            _obs(rows, r.business_id, "licence_first_issued", str(x.originalissuedate)[:10], "NYS Liquor Authority", "official",
                 f"Original issue date of licence {l.source_key}", f"https://data.ny.gov/resource/9s3h-dpkz.json?licensepermitid={l.source_key}")
        else:
            _obs(rows, r.business_id, "serves_alcohol", "no", "NYS Liquor Authority", "official_absence",
                 "No active on-premises licence found at this name and address", DATASET_URL["liquor_licences"])

    # outdoor dining licence (official)
    d = pd.read_parquet(raw("dining_out"))
    d["key"] = d.business_legal_name.fillna("") + "|" + d.street.fillna("")
    d = d.drop_duplicates("key").set_index("key")
    for bid, l in lk.get("dining_out", pd.DataFrame()).iterrows():
        x = d.loc[l.source_key]
        _obs(rows, bid, "outdoor_seating", "yes", "NYC Dining Out licence", "official",
             f"{x.license_type} licence ({x.license_status}) for '{x.business_legal_name}' at {x.street}, issued {str(x.license_issue_date)[:10]}",
             f"https://data.cityofnewyork.us/resource/fpeh-f7ci.json?bbl={x.bbl}", str(x.license_issue_date)[:10])

    # OpenStreetMap (crowd)
    o = pd.read_parquet(raw("osm")).set_index("osm_id")
    for bid, l in lk.get("osm", pd.DataFrame()).iterrows():
        x = o.loc[l.source_key]
        ref = f"https://www.openstreetmap.org/{l.source_key}"
        if x.amenity in ("bar", "pub", "biergarten", "nightclub"):
            _obs(rows, bid, "serves_alcohol", "yes", "OpenStreetMap", "crowd", f"Mapped as amenity={x.amenity}", ref)
        late = N.closes_after_midnight(x.opening_hours)
        if late is not None:
            _obs(rows, bid, "open_after_midnight", "yes" if late else "no", "OpenStreetMap", "crowd", f"opening_hours={x.opening_hours}", ref)
        for tag, fact in (("outdoor_seating", "outdoor_seating"), ("delivery", "delivery")):
            v = getattr(x, tag)
            if v in ("yes", "no"):
                _obs(rows, bid, fact, v, "OpenStreetMap", "crowd", f"{tag}={v}", ref)

    # website facts (LLM, verified quotes only)
    wf = con.execute("SELECT * FROM web_facts WHERE is_this_business AND value IN ('yes','no')").df() \
        if con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='web_facts'").fetchone()[0] else pd.DataFrame()
    for r in wf.itertuples():
        _obs(rows, r.business_id, r.fact, r.value, "Business website", "website", f'"{r.quote}" (read by {r.model})', r.url)

    # late-night noise complaints, only where the restaurant is the only one on its tax lot
    c = pd.read_parquet(raw("complaints_311"))
    c = c[(c.complaint_type == "Noise - Commercial") & (c.location_type == "Club/Bar/Restaurant")]
    c["hour"] = pd.to_datetime(c.created_date).dt.hour
    c["bbl"] = c.bbl.map(N.bbl)
    since = c.created_date.min()[:10] if len(c) else ""
    late = c[c.hour.between(0, 4)].groupby("bbl").agg(n=("unique_key", "size"), last=("created_date", "max"))
    solo = b[b.tenants_in_lot == 1].set_index("bbl")
    for bbl, x in late[late.n >= 2].iterrows():
        if bbl in solo.index:
            _obs(rows, solo.loc[bbl].business_id, "open_after_midnight", "yes", "NYC 311 complaints", "complaints",
                 f"{x.n} bar/restaurant noise complaints filed between 00:00 and 05:00 since {since}; last {str(x['last'])[:10]}",
                 f"https://data.cityofnewyork.us/resource/erm2-nwe9.json?bbl={bbl}&complaint_type=Noise%20-%20Commercial")

    # inspection history (official)
    ins = pd.read_parquet(raw("inspections"))
    ins = ins[ins.inspection_date > "1901"]
    ins["d"] = pd.to_datetime(ins.inspection_date)
    g = ins.groupby("camis")
    first = g.d.min()
    last3y = ins[ins.d >= ins.d.max() - pd.Timedelta(days=1095)]
    closures = last3y[last3y.action.str.contains("closed", case=False, na=False)].groupby("camis").d.nunique()
    crit = last3y[last3y.critical_flag == "Critical"].groupby("camis").size()
    grade = ins.dropna(subset=["grade"]).sort_values("d").groupby("camis").last()
    for r in b.itertuples():
        ref = f"https://data.cityofnewyork.us/resource/43nn-pn8j.json?camis={r.business_id}"
        _obs(rows, r.business_id, "first_inspection", str(first.get(r.business_id))[:10], "NYC Health inspections", "official",
             "Earliest inspection on record", ref)
        _obs(rows, r.business_id, "closures_3y", int(closures.get(r.business_id, 0)), "NYC Health inspections", "official",
             "Distinct inspection dates with a closure action in the last 3 years", ref)
        _obs(rows, r.business_id, "critical_violations_3y", int(crit.get(r.business_id, 0)), "NYC Health inspections", "official",
             "Critical violations cited in the last 3 years", ref)
        if r.business_id in grade.index:
            gr = grade.loc[r.business_id]
            _obs(rows, r.business_id, "last_grade", gr.grade, "NYC Health inspections", "official", f"Grade on {str(gr.d)[:10]}", ref)

    # building (official, building-level): PLUTO, DOB/ECB violations, permits
    pl = pd.read_parquet(raw("pluto"))
    pl["bbl"] = pl.bbl.map(N.bbl)
    pl["lat"], pl["lon"] = pd.to_numeric(pl.latitude, errors="coerce"), pd.to_numeric(pl.longitude, errors="coerce")
    pl = pl.dropna(subset=["bbl"]).drop_duplicates("bbl").set_index("bbl")
    by_block = {k: g for k, g in pl.dropna(subset=["lat"]).groupby(pl.dropna(subset=["lat"]).index.str[:6])}

    def pluto_lot(r):
        """Exact lot, else (condo billing lots 75xx, unit lots) the nearest lot on the same block within 60 m."""
        if r.bbl in pl.index:
            return r.bbl, "PLUTO lot"
        g = by_block.get(str(r.bbl)[:6]) if r.bbl else None
        if g is None or not len(g):
            return None, None
        d = ((g.lat - r.lat) ** 2 + ((g.lon - r.lon) * 0.76) ** 2) ** 0.5 * 111000
        return (d.idxmin(), f"nearest PLUTO lot on the block ({d.min():.0f} m)") if d.min() <= 60 else (None, None)
    dob = pd.read_parquet(raw("dob_violations"))
    dob_open = dob[dob.disposition_date.isna()].groupby("bin").size()
    ecb = pd.read_parquet(raw("ecb_violations"))
    ecb_open = ecb[ecb.ecb_violation_status.str.upper().eq("ACTIVE")].groupby("bin").size()
    for r in b.itertuples():
        lot, how = pluto_lot(r)
        if lot:
            x = pl.loc[lot]
            ref = f"https://data.cityofnewyork.us/resource/64uk-42ks.json?$where=bbl={lot}"
            for fact, val, ev in (("year_built", x.yearbuilt, f"yearbuilt, {how} {lot}"), ("floors", x.numfloors, f"numfloors, {how} {lot}"),
                                  ("building_class", x.bldgclass, f"bldgclass, {how} {lot}")):
                if pd.notna(val) and str(val) not in ("0", "0.0", ""):
                    _obs(rows, r.business_id, fact, str(val).replace(".0", ""), "NYC PLUTO (tax lot)", "official", ev, ref)
        if pd.notna(r.bin):
            _obs(rows, r.business_id, "building_open_dob_violations", int(dob_open.get(r.bin, 0)), "NYC Buildings (DOB)", "official",
                 "Open DOB violations on the whole building (not specific to this business)",
                 f"https://data.cityofnewyork.us/resource/3h2n-5cm9.json?bin={r.bin}")
            _obs(rows, r.business_id, "building_active_ecb_violations", int(ecb_open.get(r.bin, 0)), "NYC Buildings (ECB)", "official",
                 "Active ECB violations on the whole building (not specific to this business)",
                 f"https://data.cityofnewyork.us/resource/6bgk-3dad.json?bin={r.bin}")

    # fire summonses attributed by respondent name (official)
    fs = pd.read_parquet(raw("fire_summonses")).drop_duplicates("ticket_number").set_index("ticket_number")
    for bid, grp in links[links.source == "fire_summonses"].groupby("business_id"):
        x = fs.loc[grp.source_key]
        charges = x.charge_1_code_description.dropna().value_counts().head(3)
        _obs(rows, bid, "fire_summonses", len(grp), "FDNY summonses (OATH)", "official",
             "; ".join(f"{k} ×{v}" for k, v in charges.items()) or "summonses on record",
             f"https://data.cityofnewyork.us/resource/jz4z-kudi.json?ticket_number={grp.source_key.iloc[0]}")

    # legal entity formation (official)
    corps = con.execute("""SELECT n.business_id, c.dos_id, c.current_entity_name, c.initial_dos_filing_date, c.entity_type
        FROM legal_names n JOIN corp_queries q ON q.legal_name = n.legal_name JOIN corps c ON c.current_entity_name = q.variant""").df() \
        if con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='corps'").fetchone()[0] else pd.DataFrame()
    for r in corps.drop_duplicates(["business_id", "dos_id"]).itertuples():
        _obs(rows, r.business_id, "entity_formed", str(r.initial_dos_filing_date)[:10], "NYS Dept of State register", "official",
             f"{r.current_entity_name} ({r.entity_type}), DOS ID {r.dos_id}", f"https://data.ny.gov/resource/n9v6-gdp6.json?dos_id={r.dos_id}")
    return pd.DataFrame(rows)


def resolve(obs: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (bid, fact), g in obs.groupby(["business_id", "fact"], sort=False):
        g = g.sort_values("trust", ascending=False)
        top = g.iloc[0]
        values = set(g.value) if fact in BOOL_FACTS else {top.value}
        out.append({"business_id": bid, "fact": fact, "value": top.value, "source": top.source, "n_sources": len(g),
                    "conflict": fact in BOOL_FACTS and values >= {"yes", "no"},
                    "disagreeing": "; ".join(sorted(f"{r.source}={r.value}" for r in g.itertuples() if r.value != top.value))})
    return pd.DataFrame(out)


def run() -> None:
    con = connect()
    obs = observations(con)
    facts = resolve(obs)
    # register explicitly: 'SELECT * FROM facts' would read the existing table, not the DataFrame of the same name
    con.register("obs_df", obs)
    con.register("facts_df", facts)
    con.execute("CREATE OR REPLACE TABLE observations AS SELECT * FROM obs_df")
    con.execute("CREATE OR REPLACE TABLE facts AS SELECT * FROM facts_df")
    n = facts.business_id.nunique()
    print(f"[ledger] observations: {len(obs):,} | facts: {len(facts):,} for {n:,} businesses | "
          f"conflicts: {facts.conflict.sum():,} ({facts[facts.conflict].business_id.nunique():,} businesses)")
    con.close()

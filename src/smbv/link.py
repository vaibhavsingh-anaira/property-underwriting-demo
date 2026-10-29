"""Entity resolution: one row per inspected food business, linked to records in every other source.

Every link records how it was made (method) and how strong it is (score, distance) so the app can show it."""
from __future__ import annotations
from collections import defaultdict
import pandas as pd
from rapidfuzz import fuzz
from smbv import normalize as N
from smbv.config import BOROUGHS
from smbv.db import connect, raw

ON_PREMISES = r"Liquor Store|Wholesale|Grocery|Drug|Distill|Winery|Brewer|Warehouse|Importer|Solicitor|Wine Store|" \
              r"Off-Premises|Salesm|Broker|Manufact|Bottle|Agent|Farm|Mfr|Industrial"


def businesses() -> pd.DataFrame:
    ins = pd.read_parquet(raw("inspections"))
    ins = ins[ins.inspection_date > "1901"]
    b = ins.sort_values("inspection_date").groupby("camis").last().reset_index()
    b["lat"], b["lon"] = pd.to_numeric(b.latitude, errors="coerce"), pd.to_numeric(b.longitude, errors="coerce")
    b["bbl"] = b.bbl.map(N.bbl)
    b = b[b.lat > 1].rename(columns={"camis": "business_id", "dba": "name", "building": "house", "zipcode": "zip",
                                       "cuisine_description": "cuisine"})
    b["nm"], b["num"], b["st"] = b.name.map(N.name), b.house.map(N.house), b.street.map(N.street)
    b["zip5"] = b.zip.str[:5]
    b["tenants_in_lot"] = b.bbl.map(b.groupby("bbl").size())
    return b[["business_id", "name", "house", "street", "zip", "boro", "phone", "cuisine", "bin", "bbl", "lat", "lon",
              "nm", "num", "st", "zip5", "tenants_in_lot"]]


def _geo_index(df: pd.DataFrame) -> dict:
    idx = defaultdict(list)
    for r in df.itertuples():
        idx[N.grid(r.lat, r.lon)].append(r)
    return idx


def _near(idx: dict, lat: float, lon: float, max_m: float):
    ci, cj = N.grid(lat, lon)
    k = int(max_m // 85) + 1  # cells are ~111 m north-south, ~84 m east-west at NYC latitude
    for di in range(-k, k + 1):
        for dj in range(-k, k + 1):
            for r in idx.get((ci + di, cj + dj), ()):
                d = N.meters(lat, lon, r.lat, r.lon)
                if d <= max_m:
                    yield r, d


def _pair(a: str, b: str) -> float:
    """token_set_ratio, but a match on generic words alone ('BAKERY', 'PIZZA') is capped below every threshold."""
    s = fuzz.token_set_ratio(a, b)
    da, db = N.distinctive(a), N.distinctive(b)
    if not da or not db:                       # an all-generic name: require near-identical full strings
        return s if fuzz.ratio(a, b) >= 90 else min(s, 60)
    if da & db or fuzz.ratio(" ".join(sorted(da)), " ".join(sorted(db))) >= 85:
        return s
    return min(s, 60)


def _score(nm: str, *others: str) -> float:
    return max((_pair(nm, o) for o in others if o), default=0) if nm else 0


def link_liquor(b: pd.DataFrame) -> list[dict]:
    lic = pd.read_parquet(raw("liquor_licences"))
    lic = lic[~lic.description.str.contains(ON_PREMISES, case=False, na=False)].copy()
    ll = lic.georeference.map(N.lon_lat)
    lic["lon"], lic["lat"] = ll.str[0].astype(float), ll.str[1].astype(float)
    lic[["num", "st"]] = lic.actualaddressofpremises.apply(lambda a: pd.Series(N.split_address(a)))
    lic["zip5"] = lic.zipcode.str[:5]
    lic["nm_d"], lic["nm_l"] = lic.dba.map(N.name), lic.legalname.map(N.name)
    by_addr = defaultdict(list)  # house number + street; ZIP codes disagree between datasets, so distance checks instead
    for r in lic.itertuples():
        by_addr[(r.num, r.st)].append(r)
    geo = _geo_index(lic.dropna(subset=["lat"]))
    chain = b.nm.map(b.nm.value_counts()) > 1  # names on several premises: location matches only when nearly co-located
    out = []
    for r, is_chain in zip(b.itertuples(), chain):
        same_addr = [x for x in by_addr.get((r.num, r.st), ())
                     if x.lat != x.lat or N.meters(r.lat, r.lon, x.lat, x.lon) <= 300]  # same street in another borough
        best = max(((_score(r.nm, x.nm_d, x.nm_l), x, None) for x in same_addr), key=lambda t: t[0], default=(0, None, None))
        method = "name+address" if best[0] >= 80 else None
        if not method:  # identical address and a shared distinctive word ('TOMI JAZZ' / 'TOMI NEW YORK INC')
            street_words = set(r.st.split())  # 'MADISON CLUB' at Madison Ave must not match 'OBIKA NY MADISON LLC'
            mine = {w for w in N.distinctive(r.nm) if len(w) >= 4} - street_words
            shared = [x for x in same_addr if mine & ((N.distinctive(x.nm_d) | N.distinctive(x.nm_l)) - street_words)]
            if len(shared) == 1:
                best, method = (_score(r.nm, shared[0].nm_d, shared[0].nm_l), shared[0], None), "address+shared name word"
        if not method:
            cand = max(((_score(r.nm, x.nm_d, x.nm_l), x, d) for x, d in _near(geo, r.lat, r.lon, 30 if is_chain else 60)),
                       key=lambda t: t[0], default=(0, None, None))
            if cand[0] >= 90:
                best, method = cand, "name+location"
        if not method and not is_chain:  # same name on another frontage of a large building (Le Bernardin: 155 W 51 St / 787 7th Ave)
            cand = max(((_score(r.nm, x.nm_d, x.nm_l), x, d) for x, d in _near(geo, r.lat, r.lon, 200)),
                       key=lambda t: t[0], default=(0, None, None))
            if cand[0] >= 95 and len(r.nm) >= 6:
                best, method = cand, "exact name+location (200 m)"
        if method:
            out.append({"business_id": r.business_id, "source": "liquor_licences", "source_key": best[1].licensepermitid,
                        "method": method, "score": best[0], "distance_m": best[2]})
    return out


def link_osm(b: pd.DataFrame) -> list[dict]:
    o = pd.read_parquet(raw("osm")).dropna(subset=["lat", "name"])
    o["nm"] = o.name.map(N.name)
    geo, out = _geo_index(o), []
    for r in b.itertuples():
        cand = max(((_score(r.nm, x.nm), x, d) for x, d in _near(geo, r.lat, r.lon, 80)),
                   key=lambda t: (t[0], -t[2]), default=(0, None, None))
        if cand[0] >= 85:
            out.append({"business_id": r.business_id, "source": "osm", "source_key": cand[1].osm_id,
                        "method": "name+location", "score": cand[0], "distance_m": cand[2]})
    df = pd.DataFrame(out)  # one OSM venue -> its single best business (chains sit close together)
    return df.sort_values(["score", "distance_m"], ascending=[False, True]).drop_duplicates("source_key").to_dict("records") if out else []


def link_dining(b: pd.DataFrame) -> list[dict]:
    d = pd.read_parquet(raw("dining_out"))
    d["lat"], d["lon"] = pd.to_numeric(d.latitude, errors="coerce"), pd.to_numeric(d.longitude, errors="coerce")
    d["key"] = d.business_legal_name.fillna("") + "|" + d.street.fillna("")
    d["nm_a"], d["nm_l"] = d.assumed_name_s.map(N.name), d.business_legal_name.map(N.name)
    by_lot = defaultdict(list)
    for r in d.itertuples():
        by_lot[r.bbl].append(r)
    geo, out = _geo_index(d.dropna(subset=["lat"])), []
    for r in b.itertuples():
        cands = [(_score(r.nm, x.nm_a, x.nm_l), x, None) for x in by_lot.get(r.bbl, ())]
        cands += [(_score(r.nm, x.nm_a, x.nm_l), x, dist) for x, dist in _near(geo, r.lat, r.lon, 40)]
        best = max(cands, key=lambda t: t[0], default=(0, None, None))
        if best[0] >= 85:
            out.append({"business_id": r.business_id, "source": "dining_out", "source_key": best[1].key,
                        "method": "name+lot" if best[2] is None else "name+location", "score": best[0], "distance_m": best[2]})
    return out


def _summons_links(b: pd.DataFrame, legal_names: dict[str, list[str]]) -> list[dict]:
    f = pd.read_parquet(raw("fire_summonses")).drop_duplicates("ticket_number")  # ticket_number is unique; guard only
    boro = {v["upper"]: v["num"] for v in BOROUGHS.values()}
    by_lot = defaultdict(list)  # OATH keys: borough name, 5-digit block, 4-digit lot -> 10-digit BBL
    for r in f.itertuples():
        by_lot[f"{boro.get(r.violation_location_borough, '?')}{str(r.violation_location_block_no).zfill(5)}"
               f"{str(r.violation_location_lot_no).zfill(4)}"].append(r)
    out = []
    for r in b.dropna(subset=["bbl"]).itertuples():
        bbl = str(r.bbl)
        if len(bbl) != 10:
            continue
        names = [r.nm, *[N.name(x) for x in legal_names.get(r.business_id, [])]]
        for x in by_lot.get(bbl, ()):
            s = _score(N.name(x.respondent_last_name), *names)
            if s >= 85:
                out.append({"business_id": r.business_id, "source": "fire_summonses", "source_key": x.ticket_number,
                            "method": "respondent name+lot", "score": s, "distance_m": None})
    return out


def link_ppp(b: pd.DataFrame, legal_names: dict[str, list[str]]) -> list[dict]:
    """PPP loans by borrower name + street address (the loan data has no coordinates). Every matching loan is kept
    (a business can have a first and a second draw)."""
    p = pd.read_parquet(raw("ppp"))
    p[["num", "st"]] = p.BorrowerAddress.apply(lambda a: pd.Series(N.split_address(a)))
    p["nm"] = p.BorrowerName.map(N.name)
    by_addr = defaultdict(list)
    for r in p.itertuples():
        by_addr[(r.num, r.st)].append(r)
    out = []
    for r in b.itertuples():
        names = [r.nm, *[N.name(x) for x in legal_names.get(r.business_id, [])]]
        for x in by_addr.get((r.num, r.st), ()):
            s = _score(x.nm, *names)
            if s >= 85:
                out.append({"business_id": r.business_id, "source": "ppp", "source_key": x.LoanNumber,
                            "method": "borrower name+address", "score": s, "distance_m": None})
    return out


def run() -> None:
    con = connect()
    b = businesses()
    print(f"[link] businesses in scope: {len(b):,}")
    links = []
    for fn in (link_liquor, link_osm, link_dining):
        rows = fn(b)
        links += rows
        print(f"[link] {fn.__name__[5:]}: {len(rows):,} businesses linked ({len(rows)/len(b):.0%})")
    lk = pd.DataFrame(links)
    lic = pd.read_parquet(raw("liquor_licences")).set_index("licensepermitid").legalname
    dine = pd.read_parquet(raw("dining_out"))
    dine_legal = dict(zip(dine.business_legal_name.fillna("") + "|" + dine.street.fillna(""), dine.business_legal_name))
    legal = defaultdict(list)
    for r in lk.itertuples():
        if r.source == "liquor_licences" and isinstance(lic.get(r.source_key), str):
            legal[r.business_id].append(lic[r.source_key])
        if r.source == "dining_out" and dine_legal.get(r.source_key):
            legal[r.business_id].append(dine_legal[r.source_key])
    s = _summons_links(b, legal)
    print(f"[link] fire summonses attributed to a business: {len(s):,} across {len({x['business_id'] for x in s}):,} businesses")
    lk = pd.concat([lk, pd.DataFrame(s)], ignore_index=True)
    try:
        pp = link_ppp(b, legal)
        print(f"[link] PPP loans: {len(pp):,} across {len({x['business_id'] for x in pp}):,} businesses "
              f"({len({x['business_id'] for x in pp}) / len(b):.0%})")
        lk = pd.concat([lk, pd.DataFrame(pp)], ignore_index=True)
    except FileNotFoundError:
        print("[link] PPP loans not ingested (smbv ingest --only ppp); skipped")
    con.execute("CREATE OR REPLACE TABLE businesses AS SELECT * FROM b")
    con.execute("CREATE OR REPLACE TABLE links AS SELECT * FROM lk")
    ln = pd.DataFrame([{"business_id": k, "legal_name": n} for k, v in legal.items() for n in dict.fromkeys(v)])
    con.execute("CREATE OR REPLACE TABLE legal_names AS SELECT * FROM ln")
    con.close()

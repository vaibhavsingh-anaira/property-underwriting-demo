"""Download every source into data/raw/<name>.parquet. Re-running replaces the file (idempotent)."""
from __future__ import annotations
import io
import json
import time
import pandas as pd
import requests
from smbv.config import load, scope_values, sql_list, socrata_token
from smbv.db import raw

# name: (domain, dataset id, columns, where-clause template). Placeholders are filled from the configured scope.
SOURCES = {
    "inspections": ("data.cityofnewyork.us", "43nn-pn8j",
                    "camis,dba,boro,building,street,zipcode,phone,cuisine_description,inspection_date,action,"
                    "violation_code,violation_description,critical_flag,score,grade,inspection_type,bin,bbl,latitude,longitude",
                    "boro in ({title})"),
    "liquor_licences": ("data.ny.gov", "9s3h-dpkz",
                        "licensepermitid,premisescounty,type,class,description,legalname,dba,actualaddressofpremises,"
                        "zipcode,originalissuedate,lastissuedate,expirationdate,georeference",
                        # all five NYC counties regardless of scope: the state records some premises under the wrong
                        # county (e.g. a Manhattan bar filed under Kings), so county is not trusted; matching uses address/location
                        "premisescounty in ('New York','Kings','Queens','Bronx','Richmond')"),
    "complaints_311": ("data.cityofnewyork.us", "erm2-nwe9",
                       "unique_key,created_date,complaint_type,descriptor,location_type,incident_address,bbl,latitude,longitude",
                       "borough in ({upper_311}) and created_date >= '{since}' and complaint_type in "
                       "('Food Establishment','Food Poisoning','Noise - Commercial')"),
    "pluto": ("data.cityofnewyork.us", "64uk-42ks",
              "bbl,address,bldgclass,landuse,yearbuilt,yearalter1,yearalter2,numfloors,bldgarea,comarea,retailarea,numbldgs,ownername,latitude,longitude,"
              "firm07_flag,pfirm15_flag",
              "borough in ({abbr})"),
    "dob_violations": ("data.cityofnewyork.us", "3h2n-5cm9",
                       "isn_dob_bis_viol,bin,issue_date,violation_type,violation_category,description,disposition_date",
                       "boro in ({num})"),
    "ecb_violations": ("data.cityofnewyork.us", "6bgk-3dad",
                       "ecb_violation_number,bin,issue_date,ecb_violation_status,severity,violation_type,"
                       "violation_description,respondent_name,penality_imposed,balance_due",
                       "boro in ({num})"),
    "dob_permits": ("data.cityofnewyork.us", "rbx6-tga4",
                    "job_filing_number,work_permit,bin,work_type,job_description,issued_date,owner_business_name,permit_status",
                    "upper(borough) in ({upper_311}) and issued_date >= '{since}'"),
    "fdny_inspections": ("data.cityofnewyork.us", "kfgh-h6re",
                         "bbl,bldg_current_bin,insp_inspect_dt_fk,insptn_typ_cd_fk,insptn_ops_detail",
                         "borough in ({abbr})"),
    "fire_summonses": ("data.cityofnewyork.us", "jz4z-kudi",
                       "ticket_number,issuing_agency,violation_date,hearing_date,respondent_last_name,violation_location_borough,violation_location_block_no,"
                       "violation_location_lot_no,violation_location_house,violation_location_street_name,hearing_result,"
                       "charge_1_code_description,total_violation_amount,balance_due",
                       "issuing_agency='FIRE DEPARTMENT OF NYC' and violation_location_borough in ({upper})"),
    "dining_out": ("data.cityofnewyork.us", "fpeh-f7ci",
                   "business_legal_name,assumed_name_s,street,borough,postcode,license_type,license_status,"
                   "license_issue_date,license_expiration_date,latitude,longitude,bin,bbl",
                   "borough in ({title})"),
    # liquor licence applications not yet decided, and licences no longer active (change alerts)
    "sla_pending": ("data.ny.gov", "f8i8-k2gm",
                    "application_id,premises_county,description,legalname,actual_address_of_premises,zip_code,received_date,status",
                    "premises_county in ('New York','Kings','Queens','Bronx','Richmond')"),
    "sla_inactive": ("data.ny.gov", "6dg3-2z7i",
                     "license_permit_id,premises_county,description,legalname,actual_address_of_premises,zip_code,"
                     "original_issue_date,expiration_date",
                     "premises_county in ('New York','Kings','Queens','Bronx','Richmond')"),
}
DATASET_URL = {k: f"https://{d}/d/{i}" for k, (d, i, _, _) in SOURCES.items()} | {
    "ppp": "https://data.sba.gov/dataset/ppp-foia", "wcb": "https://data.ny.gov/d/jshw-gkgu",
    "evac": "https://data.cityofnewyork.us/d/epne-qv9x"}
# Deterministic order for the paged fallback (only used above `single_request_max` rows).
ORDER = {"inspections": "camis,inspection_date,violation_code", "liquor_licences": "licensepermitid", "complaints_311": "unique_key",
         "pluto": "bbl", "dob_violations": "isn_dob_bis_viol", "ecb_violations": "ecb_violation_number",
         "dob_permits": "job_filing_number,work_permit", "fdny_inspections": "bbl,insp_inspect_dt_fk,insptn_typ_cd_fk",
         "fire_summonses": "ticket_number", "dining_out": "business_legal_name,street",
         "sla_pending": "application_id", "sla_inactive": "license_permit_id"}


def _where(template: str) -> str:
    cfg = load()
    return template.format(
        title=sql_list(scope_values("title")), county=sql_list(scope_values("county")),
        abbr=sql_list(scope_values("abbr")), num=sql_list(scope_values("num")),
        upper=sql_list(scope_values("upper")),
        upper_311=sql_list([b.upper() for b in scope_values("title")]),
        since=cfg["scope"]["since"])


def _request(url: str, params: dict, tries: int = 5) -> requests.Response:
    headers = {"X-App-Token": t} if (t := socrata_token()) else {}
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=900)
            if r.status_code == 200:
                return r
            if r.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
        except requests.RequestException:
            if i == tries - 1:
                raise
        time.sleep(2 ** i)
    raise RuntimeError(f"gave up on {url}")


def _get(url: str, params: dict) -> list[dict]:
    return _request(url, params).json()


def socrata(name: str) -> int:
    """One consistent snapshot: a single CSV request for the whole filtered result, checked against the server's count.

    Offset paging ordered by :id is NOT stable on these portals (pages overlap and skip rows), so it is not used.
    Above `single_request_max` rows the download pages on a real unique column and is checked the same way."""
    domain, ds, cols, where = SOURCES[name]
    base, w = f"https://{domain}/resource/{ds}", _where(where)
    expected = int(_get(base + ".json", {"$select": "count(*) AS n", "$where": w})[0]["n"])
    cap = load()["socrata"]["single_request_max"]
    if expected <= cap:
        frames = [pd.read_csv(io.StringIO(_request(base + ".csv", {"$select": cols, "$where": w, "$limit": expected + 1000}).text),
                              dtype=str, keep_default_na=False, na_values=[""])]
    else:
        page, frames, offset = load()["socrata"]["page_size"], [], 0
        while offset < expected:
            frames.append(pd.read_csv(io.StringIO(_request(base + ".csv", {"$select": cols, "$where": w, "$order": ORDER[name],
                                                                          "$limit": page, "$offset": offset}).text),
                                      dtype=str, keep_default_na=False, na_values=[""]))
            offset += page
            print(f"  {name}: {offset:,}/{expected:,}", end="\r", flush=True)
    df = pd.concat(frames, ignore_index=True).reindex(columns=cols.split(",")).astype("string")
    drift = abs(len(df) - expected) / max(expected, 1)
    if drift > 0.001:  # live datasets can move a few rows between the count and the download, never more
        raise RuntimeError(f"{name}: downloaded {len(df):,} rows but the server reports {expected:,}")
    df.to_parquet(raw(name), index=False)
    print(f"  {name}: {len(df):,} rows (server count {expected:,}) -> {raw(name)}")
    return len(df)


OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def osm() -> int:
    s, w, n, e = load()["scope"]["osm_bbox"]
    q = (f'[out:json][timeout:180];(node["amenity"~"^(restaurant|bar|pub|cafe|fast_food|biergarten|nightclub)$"]({s},{w},{n},{e});'
         f'way["amenity"~"^(restaurant|bar|pub|cafe|fast_food|biergarten|nightclub)$"]({s},{w},{n},{e}););out center tags;')
    for url in OVERPASS:
        try:
            r = requests.post(url, data={"data": q}, headers={"User-Agent": "smbv/0.1 (research)"}, timeout=300)
            elements = r.json()["elements"]
            break
        except Exception as ex:  # busy server: try the next mirror
            print(f"  osm: {url} failed ({type(ex).__name__})")
    else:
        raise RuntimeError("all Overpass endpoints failed")
    keep = ["name", "amenity", "website", "contact:website", "opening_hours", "cuisine", "delivery", "takeaway",
            "outdoor_seating", "addr:housenumber", "addr:street", "phone", "brand"]
    df = pd.DataFrame([{"osm_id": f'{x["type"]}/{x["id"]}', "lat": x.get("lat", x.get("center", {}).get("lat")),
                        "lon": x.get("lon", x.get("center", {}).get("lon")),
                        **{k.replace(":", "_"): x.get("tags", {}).get(k) for k in keep},
                        "tags_json": json.dumps(x.get("tags", {}))} for x in elements])
    df.to_parquet(raw("osm"), index=False)
    print(f"  osm: {len(df):,} venues -> {raw('osm')}")
    return len(df)


PPP_BASE = "https://data.sba.gov/sites/default/files/distribution/SBA-OCA-2022-07-001/"
PPP_FILES = ["public_150k_plus_240930.csv", *[f"public_up_to_150k_{i}_240930.csv" for i in range(1, 13)]]
PPP_COLS = ["LoanNumber", "DateApproved", "BorrowerName", "BorrowerAddress", "BorrowerCity", "BorrowerZip", "ProjectCountyName",
            "JobsReported", "NAICSCode", "PAYROLL_PROCEED", "CurrentApprovalAmount", "BusinessAgeDescription", "BusinessType"]


def ppp() -> int:
    """SBA Paycheck Protection Program loans (2020-21), food service (NAICS 722*) in the scope's counties.
    Streamed file by file (about 5.5 GB in total); only the matching rows are kept."""
    counties = {c.upper() for c in scope_values("county")}
    frames = []
    for f in PPP_FILES:
        for chunk in pd.read_csv(PPP_BASE + f, dtype=str, usecols=PPP_COLS + ["ProjectState"], chunksize=200_000,
                                 encoding="latin-1"):
            frames.append(chunk[(chunk.ProjectState == "NY") & chunk.NAICSCode.fillna("").str.startswith("722")
                                & chunk.ProjectCountyName.str.upper().isin(counties)][PPP_COLS])
        print(f"  ppp: {f} done, {sum(len(x) for x in frames):,} loans kept", flush=True)
    df = pd.concat(frames, ignore_index=True).drop_duplicates("LoanNumber").astype("string")
    df.to_parquet(raw("ppp"), index=False)
    print(f"  ppp: {len(df):,} loans -> {raw('ppp')}")
    return len(df)


def wcb() -> int:
    """NY Workers' Compensation Board claims, accommodation and food services, injured in the scope's counties: an industry
    benchmark only (the dataset has no employer name)."""
    counties = sql_list([c.upper() for c in scope_values("county")])
    rows = _get("https://data.ny.gov/resource/jshw-gkgu.json", {
        "$select": "wcio_cause_of_injury_desc AS cause, count(*) AS n",
        "$where": f"industry_desc='ACCOMMODATION AND FOOD SERVICES' AND injured_in_county_name in ({counties})",
        "$group": "wcio_cause_of_injury_desc", "$order": "n DESC", "$limit": 5000})
    df = pd.DataFrame(rows).astype({"n": int})
    df.to_parquet(raw("wcb"), index=False)
    print(f"  wcb: {df.n.sum():,} claims in {len(df):,} cause groups -> {raw('wcb')}")
    return len(df)


def evac() -> int:
    """NYC Hurricane Evacuation Zones (official polygons, zones 1-6)."""
    r = _request("https://data.cityofnewyork.us/resource/epne-qv9x.geojson", {"$limit": 50000})
    n = len(r.json()["features"])
    path = raw("evac").replace(".parquet", ".geojson")
    with open(path, "w") as f:
        f.write(r.text)
    print(f"  evac: {n} zone polygons -> {path}")
    return n


EXTRA = {"osm": osm, "ppp": ppp, "wcb": wcb, "evac": evac}


def run(only: list[str] | None = None) -> None:
    for name in only or [*SOURCES, *EXTRA]:
        print(f"[ingest] {name}")
        EXTRA[name]() if name in EXTRA else socrata(name)

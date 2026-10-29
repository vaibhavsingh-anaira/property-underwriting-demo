from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from smbv.config import load
from smbv.db import connect, raw
from smbv.ledger import BOOL_FACTS

app = FastAPI(title="SMB risk verification")
T = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
LABEL = {"serves_alcohol": "Serves alcohol", "deep_frying": "Deep frying", "delivery": "Delivery",
         "open_after_midnight": "Open after midnight", "outdoor_seating": "Outdoor seating", "first_inspection": "First health inspection",
         "licence_first_issued": "Liquor licence first issued", "entity_formed": "Legal entity formed", "last_grade": "Last health grade",
         "closures_3y": "Health closures (3 yrs)", "critical_violations_3y": "Critical violations (3 yrs)", "fire_summonses": "FDNY summonses",
         "year_built": "Year built", "floors": "Floors", "building_class": "Building class",
         "building_open_dob_violations": "Open DOB violations (whole building)", "building_active_ecb_violations": "Active ECB violations (whole building)",
         "ppp_jobs": "Employees (PPP jobs reported)", "ppp_industry": "Industry code (PPP NAICS)", "licence_type": "Liquor licence type",
         "bar_signals": "Bar indicators (licence type, OSM tag, PPP code)", "change_alerts_12m": "Changes in the last 12 months",
         "extinguisher_summonses": "FDNY fire extinguisher summonses", "kitchen_fire_permits": "Kitchen fire work permits (whole building)",
         "operator_locations": "NYC licences held by the operator", "flood_zone": "FEMA 1% flood zone (tax lot)",
         "evacuation_zone": "Hurricane evacuation zone"}
GROUPS = {"Application facts": BOOL_FACTS,
          "Business history": ["first_inspection", "licence_first_issued", "entity_formed", "last_grade", "closures_3y", "critical_violations_3y", "fire_summonses"],
          "Building (tax lot / building-level)": ["year_built", "floors", "building_class", "building_open_dob_violations", "building_active_ecb_violations"],
          "Size and class": ["ppp_jobs", "ppp_industry", "licence_type", "bar_signals"],
          "Change alerts": ["change_alerts_12m"],
          "Fire, flood and operator": ["extinguisher_summonses", "kitchen_fire_permits", "flood_zone", "evacuation_zone", "operator_locations"]}


def _q(sql: str, *args):
    con = connect(read_only=True)
    try:
        return con.execute(sql, list(args)).df()
    finally:
        con.close()


@lru_cache
def _osm_sites() -> dict:
    o = pd.read_parquet(raw("osm"))
    site = o.website.fillna(o.contact_website)
    return {k: v for k, v in zip(o.osm_id, site) if isinstance(v, str) and v}


@lru_cache
def _benchmark() -> dict:
    """Workers' comp claims for accommodation and food services in the scope's counties (industry-level, no employer)."""
    try:
        w = pd.read_parquet(raw("wcb")).sort_values("n", ascending=False)
    except FileNotFoundError:
        return {}
    w["cause"] = w.cause.fillna("Not recorded")
    total = int(w.n.sum())
    return {"total": total, "rows": [{"cause": r.cause, "n": int(r.n), "share": r.n / total} for r in w.head(8).itertuples()]}


def _website(bid: str, links: list[dict], page: dict | None) -> dict:
    """The website checked for this business, or why none was checked."""
    if page:
        status = "read" if (page["words"] or 0) >= load()["crawl"]["min_words"] else "fetched, too little text to read"
        return {"url": page["final_url"] or page["url"], "status": status, **page}
    osm = next((l["source_key"] for l in links if l["source"] == "osm"), None)
    url = _osm_sites().get(osm) if osm else None
    if url:
        return {"url": url, "status": f"not checked: outside the {load()['crawl']['max_sites']}-site demo sample"}
    return {"url": None, "status": "no website found (none listed on OpenStreetMap)" if osm else "no website found (not on OpenStreetMap)"}


def _profile(bid: str) -> dict:
    b = _q("SELECT * FROM businesses WHERE business_id = ?", bid).iloc[0].to_dict()
    facts = _q("SELECT * FROM facts WHERE business_id = ?", bid).set_index("fact").to_dict("index")
    obs = _q("SELECT * FROM observations WHERE business_id = ? ORDER BY trust DESC", bid)
    links = _q("SELECT * FROM links WHERE business_id = ? ORDER BY source", bid).to_dict("records")
    page = _q("SELECT url, final_url, method, words, fetched_at, note FROM web_pages WHERE business_id = ?", bid).to_dict("records")
    groups = {g: [{"fact": f, "label": LABEL[f], **facts.get(f, {}), "obs": obs[obs.fact == f].to_dict("records")}
                  for f in fs] for g, fs in GROUPS.items()}
    page = page[0] if page else None
    return {"b": b, "groups": groups, "links": links, "page": page, "site": _website(bid, links, page), "bench": _benchmark()}


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", only_conflicts: bool = False):
    stats = _q("""SELECT (SELECT count(*) FROM businesses) AS businesses, (SELECT count(*) FROM observations) AS observations,
        (SELECT count(DISTINCT business_id) FROM facts WHERE conflict) AS with_conflicts,
        (SELECT count(*) FROM web_pages) AS sites, (SELECT count(DISTINCT business_id) FROM web_facts) AS extracted""").iloc[0].to_dict()
    where = "WHERE (b.name ILIKE ? OR b.street ILIKE ? OR b.business_id = ?)" if q else "WHERE 1=1"
    where += " AND c.n > 0" if only_conflicts else ""
    args = [f"%{q}%", f"%{q}%", q] if q else []
    rows = _q(f"""SELECT b.business_id, b.name, b.house || ' ' || b.street AS address, b.cuisine, coalesce(c.n, 0)::INT AS conflicts, coalesce(s.n, 0) AS sources
        FROM businesses b LEFT JOIN (SELECT business_id, sum(conflict::INT) n FROM facts GROUP BY 1) c USING (business_id)
        LEFT JOIN (SELECT business_id, count(DISTINCT source) n FROM observations GROUP BY 1) s USING (business_id)
        {where} ORDER BY conflicts DESC, sources DESC, b.name LIMIT 60""", *args).to_dict("records")
    return T.TemplateResponse(request, "home.html", {"stats": stats, "rows": rows, "q": q, "only_conflicts": only_conflicts})


@app.get("/docs/smb-basic-check.pdf")
def prd_pdf():
    return FileResponse(Path(__file__).parents[3] / "docs" / "smb-basic-check.pdf", media_type="application/pdf")


@app.get("/b/{bid}", response_class=HTMLResponse)
def business(request: Request, bid: str):
    return T.TemplateResponse(request, "business.html", {**_profile(bid), "maps_live": load()["maps_live"]["enabled"], "verdicts": None})


@app.post("/b/{bid}/verify", response_class=HTMLResponse)
async def verify(request: Request, bid: str):
    form = await request.form()
    p = _profile(bid)
    verdicts = []
    for f in BOOL_FACTS:
        claim = form.get(f)
        if claim not in ("yes", "no"):
            continue
        fact = next(x for x in p["groups"]["Application facts"] if x["fact"] == f)
        support = [o for o in fact["obs"] if o["value"] == claim]
        against = [o for o in fact["obs"] if o["value"] in ("yes", "no") and o["value"] != claim]
        strong_against = [o for o in against if o["trust"] >= 2]
        verdict = ("Contradicted by records" if strong_against else "Weak contradiction" if against and not support
                   else "Consistent" if support else "No evidence")
        verdicts.append({"label": LABEL[f], "claim": claim, "verdict": verdict, "against": against, "support": support})
    return T.TemplateResponse(request, "business.html", {**p, "maps_live": load()["maps_live"]["enabled"], "verdicts": verdicts,
                                                         "claims": dict(form)})


@app.get("/b/{bid}/reviews", response_class=HTMLResponse)
def reviews(request: Request, bid: str):
    from smbv.maps_live import review_insight
    b = _q("SELECT * FROM businesses WHERE business_id = ?", bid).iloc[0]
    try:
        r = review_insight(b["name"], f"{b['house']} {b['street']}", float(b["lat"]), float(b["lon"]))
    except Exception as e:
        r = {"text": f"Live lookup failed: {type(e).__name__}", "sources": []}
    return T.TemplateResponse(request, "reviews.html", {"r": r})

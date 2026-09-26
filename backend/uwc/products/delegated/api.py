"""HTTP endpoints for Delegated Authority Control (/api/delegated/…)."""
from __future__ import annotations

from fastapi import APIRouter, Body, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import actions as A
from . import views as V
from .refdata import COVERHOLDERS

router = APIRouter(prefix="/api/delegated", tags=["delegated"])


def _rt():
    from uwc.api import LOCK, RT
    return RT, LOCK


def _uid(x):
    from uwc.api import uid_of
    return uid_of(x) if x else "u_claire"


def _ch(ch):
    if ch not in COVERHOLDERS:
        raise HTTPException(404, "coverholder not found")


@router.get("/overview")
def overview(month: str | None = None):
    RT, LOCK = _rt()
    with LOCK:
        return V.overview(RT.delegated, RT, month)


@router.get("/coverholders")
def coverholders():
    RT, LOCK = _rt()
    with LOCK:
        from .refdata import ORDER
        return [V.summary(RT.delegated, RT, ch) for ch in ORDER]


@router.get("/coverholders/{ch}")
def coverholder(ch: str):
    _ch(ch)
    RT, LOCK = _rt()
    with LOCK:
        return V.detail(RT.delegated, RT, ch)


@router.get("/breaches")
def breaches(ch: str | None = None, status: str | None = None, family: str | None = None, month: str | None = None, subject: str | None = None,
             query: str | None = None, q: str | None = None):
    RT, LOCK = _rt()
    with LOCK:
        return V.register(RT.delegated, RT, {"ch": ch, "status": status or "open", "family": family, "month": month, "subject": subject, "query": query, "q": q})


@router.get("/breaches/{key:path}")
def breach(key: str):
    RT, LOCK = _rt()
    with LOCK:
        try:
            return V.policy_detail(RT.delegated, RT, key)
        except KeyError:
            raise HTTPException(404, "not in the breach register")


def _run(fn):
    try:
        return fn()
    except (ValueError, KeyError, PermissionError) as e:
        raise HTTPException(409, str(e))


@router.post("/actions/decide")
def decide(b: dict = Body(...), x_user_id: str | None = Header(None)):
    RT, LOCK = _rt()
    with LOCK:
        out = _run(lambda: A.decide(RT, b["exc_ids"], b["decision"], _uid(x_user_id), b.get("note", "")))
        return {"message": f"{len(out)} exception(s) {b['decision'].lower()}d", "count": len(out)}


@router.post("/coverholders/{ch}/query")
def query(ch: str, b: dict = Body(default={}), x_user_id: str | None = Header(None)):
    _ch(ch)
    RT, LOCK = _rt()
    with LOCK:
        q = _run(lambda: A.raise_query(RT, ch, _uid(x_user_id), month=b.get("month"), exc_ids=b.get("exc_ids"), kind=b.get("kind", "breach")))
        return {"message": f"Query {q['query_id']} sent — {len(q['items'])} item(s), reply due {q['due']}", "query": q}


@router.post("/coverholders/{ch}/commission")
def commission(ch: str, x_user_id: str | None = Header(None)):
    _ch(ch)
    RT, LOCK = _rt()
    with LOCK:
        e = _run(lambda: A.post_commission(RT, ch, _uid(x_user_id)))
        return {"message": f"Debit note {e['entry_id']} posted — ${e['amount']:,.2f}", "entry": e}


@router.post("/coverholders/{ch}/restrict")
def restrict(ch: str, b: dict = Body(...), x_user_id: str | None = Header(None)):
    _ch(ch)
    RT, LOCK = _rt()
    with LOCK:
        v = _run(lambda: A.restrict_zone(RT, ch, b["zone"], b.get("mode", "Refer"), _uid(x_user_id)))
        return {"message": f"Endorsement No. {v['number']} issued — {b['zone']} {b.get('mode', 'Refer').lower()} from {v['effective']}", "doc_id": v["doc_id"]}


@router.post("/coverholders/{ch}/amend")
def amend(ch: str, x_user_id: str | None = Header(None)):
    _ch(ch)
    RT, LOCK = _rt()
    with LOCK:
        v = _run(lambda: A.amend(RT, ch, _uid(x_user_id)))
        return {"message": f"Endorsement No. {v['number']} issued, effective {v['effective']}", "doc_id": v["doc_id"]}


@router.get("/coverholders/{ch}/amendment")
def amendment_preset(ch: str):
    return A.AMENDMENTS.get(ch)


@router.post("/coverholders/{ch}/audit")
def audit(ch: str, x_user_id: str | None = Header(None)):
    _ch(ch)
    RT, LOCK = _rt()
    with LOCK:
        a = A.request_audit(RT, ch, _uid(x_user_id))
        return {"message": f"Audit {a['audit_id']} requested — report due {a['report_due']}", "audit": a}


@router.post("/coverholders/{ch}/report")
def report(ch: str, b: dict = Body(default={}), x_user_id: str | None = Header(None)):
    _ch(ch)
    RT, LOCK = _rt()
    with LOCK:
        m = b.get("month") or V.latest_month(RT.delegated, ch)
        r = _run(lambda: A.issue_report(RT, ch, m, _uid(x_user_id)))
        return {"message": f"Authority report {r['report_id']} issued", "report": r}


@router.get("/bordereaux")
def bordereaux(ch: str | None = None):
    RT, LOCK = _rt()
    with LOCK:
        return V.bordereaux(RT.delegated, RT, ch)


@router.get("/bordereaux/{doc_id}")
def bordereau(doc_id: str):
    RT, LOCK = _rt()
    with LOCK:
        if doc_id not in RT.delegated["bdx"]:
            raise HTTPException(404, "bordereau not found")
        return V.bordereau_detail(RT.delegated, RT, doc_id)


@router.get("/aggregates")
def aggregates():
    RT, LOCK = _rt()
    with LOCK:
        from . import engine as E
        from .refdata import ORDER
        st = RT.delegated
        out = []
        for ch in ORDER:
            d = {"ch": ch, "name": COVERHOLDERS[ch]["short"], "scenario": COVERHOLDERS[ch]["scenario"], "zones": E.aggregates(st, ch, RT.clock), "capacity": E.capacity(st, ch, RT.clock),
                 "history": [{"month": m, "zones": {z["zone"]: z["util"] for z in E.aggregates(st, ch, "2026-04-30" if m == "2026-04" else V.month_end(m))}} for m in ["2026-04"] + E.months_of(st, ch)],
                 "restrictions": [r for r in st["restrictions"] if r["ch"] == ch], "prevented": [p for p in st["prevented"] if p["ch"] == ch]}
            out.append(d)
        return out


@router.get("/referrals")
def referrals(ch: str | None = None):
    RT, LOCK = _rt()
    with LOCK:
        return [r for r in RT.delegated["referrals"] if (not ch or r["ch"] == ch) and r["requested"] <= RT.clock][::-1]


# ---------------------------------------------------------------------------- your data (real)
@router.get("/sandbox/authorities")
def sandbox_authorities():
    RT, LOCK = _rt()
    with LOCK:
        return [{"id": ch, "name": c["name"], "agreement": c["agreement"], "doc_id": RT.delegated["authority"][ch][0]["doc_id"]} for ch, c in COVERHOLDERS.items()]


@router.post("/sandbox")
async def sandbox(bordereau: UploadFile = File(...), authority: str | None = None, baa: UploadFile | None = File(None)):
    from . import sandbox as SB
    if not bordereau.filename.lower().endswith((".xlsx", ".csv")):
        raise HTTPException(400, "Upload an .xlsx or .csv bordereau")
    data = await bordereau.read()
    pdf = await baa.read() if baa else None
    RT, LOCK = _rt()
    with LOCK:
        try:
            return SB.analyse(RT, bordereau.filename, data, authority, pdf)
        except ValueError as e:
            raise HTTPException(422, str(e))


@router.get("/sandbox/samples/{name}")
def sample(name: str):
    RT, LOCK = _rt()
    files = {"meridian": "da_meridian_202607_risk", "ridgeway": "da_ridgeway_202606_risk", "northfield": "da_northfield_202607_risk", "baa": "da_meridian_baa"}
    if name not in files:
        raise HTTPException(404, "unknown sample")
    with LOCK:
        d = RT.store.docs.get(files[name])
        if not d:
            raise HTTPException(404, "sample not available")
        return FileResponse(d["abs_path"], filename=f"sample_{d['filename']}")

"""Bordereau mapper and validator — the real thing, used for the demo coverholders and for uploaded files.

1. Header detection: the row in the first 15 with the most recognisable headers is the header band;
   title bands above it and totals rows below are recorded and skipped.
2. Mapping: every header is matched to a Lloyd's CRS v5.2 field — exact CRS label (1.00), known synonym
   (0.95), fuzzy (similarity × 0.9, accepted at similarity ≥ 0.80). Unmapped columns and missing mandatory fields are listed.
3. Validation: types (money, %, date, state, zip, year), placeholders, arithmetic (commission % × gross =
   commission amount, gross − commission = net), date order, limit ≤ TIV, duplicates, reference numbers.
Every value keeps its cell reference, so each issue and each authority check opens the file at the cell.
"""
from __future__ import annotations

import csv
import difflib
import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from .refdata import CLAIM_FIELDS, EXPOSURE_FIELDS, PREMIUM_FIELDS, RISK_FIELDS, STATE_NAMES, STATES, TXN_MAP

METHOD = "Bordereau mapper v1 (header-band detection · CRS v5.2 synonym map with confidence · type, arithmetic, date-order and duplicate checks)"
FIELDSETS = {"risk": RISK_FIELDS, "premium": PREMIUM_FIELDS, "claims": CLAIM_FIELDS, "exposure": EXPOSURE_FIELDS}
_norm = lambda s: re.sub(r"[\s_]+", " ", str(s).strip().lower())
PLACEHOLDERS = {"tbd", "n/a", "na", "-", "--", "unknown", "?", "tba", "pending"}


# ============================================================================ header mapping
def match_header(text: str, fields: dict, fuzzy: bool = True) -> tuple[str | None, float, str]:
    t = _norm(text)
    if not t or len(t) > 60:
        return None, 0.0, "blank"
    for f, (label, *_rest, syns) in fields.items():
        if t == _norm(label):
            return f, 1.0, "CRS label"
    for f, (label, *_rest, syns) in fields.items():
        if t in syns:
            return f, 0.95, "synonym"
    if not fuzzy:
        return None, 0.0, "unmapped"
    best = (None, 0.0)
    for f, (label, *_rest, syns) in fields.items():
        for s in [_norm(label)] + syns:
            r = difflib.SequenceMatcher(None, t, s).ratio()
            if r > best[1]:
                best = (f, r)
    if best[1] >= 0.8:
        return best[0], round(best[1] * 0.9, 2), "fuzzy"
    return None, round(best[1] * 0.9, 2), "unmapped"


def _read(path: Path) -> tuple[str, list[list[Any]]]:
    if path.suffix.lower() == ".csv":
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        return "Sheet1", [list(r) for r in csv.reader(io.StringIO(text))]
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    for w in wb.worksheets:
        if w.sheet_state == "visible":
            ws = w
            break
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    name = ws.title
    wb.close()
    return name, rows


# ============================================================================ value parsing
def _money(v):
    if v is None or v == "":
        return None, None
    if isinstance(v, bool):
        return None, "type"
    if isinstance(v, (int, float)):
        return float(v), None
    s = str(v).strip()
    if s.lower() in PLACEHOLDERS:
        return None, "placeholder"
    neg = s.startswith("(") and s.endswith(")")
    m = re.sub(r"[,$\s()]", "", s)
    mult = 1.0
    if m.lower().endswith("m"):
        mult, m = 1e6, m[:-1]
    elif m.lower().endswith("k"):
        mult, m = 1e3, m[:-1]
    try:
        x = float(m) * mult
        return (-x if neg else x), None
    except ValueError:
        return None, "type"


def _pct(v):
    if v is None or v == "":
        return None, None
    if isinstance(v, (int, float)):
        x = float(v)
        return (x / 100, "scaled") if x > 1 else (x, None)
    s = str(v).strip()
    if s.lower() in PLACEHOLDERS:
        return None, "placeholder"
    m = re.match(r"^(-?[\d.]+)\s*%?$", s)
    if not m:
        return None, "type"
    x = float(m.group(1))
    return (x / 100, None if "%" in s else "scaled") if (x > 1 or "%" in s) else (x, None)


DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%y", "%d-%b-%Y", "%d %b %Y", "%Y/%m/%d"]


def _date(v):
    if v is None or v == "":
        return None, None
    if isinstance(v, datetime):
        return v.date().isoformat(), None
    if isinstance(v, date):
        return v.isoformat(), None
    s = str(v).strip()
    if s.lower() in PLACEHOLDERS:
        return None, "placeholder"
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date().isoformat(), ("text" if f != "%Y-%m-%d" else None)
        except ValueError:
            pass
    return None, "type"


def _state(v):
    if v is None or str(v).strip() == "":
        return None, None
    s = str(v).strip()
    if s.upper() in STATES:
        return s.upper(), None
    if s.lower() in STATE_NAMES:
        return STATE_NAMES[s.lower()], "name"
    return None, "type"


def _zip(v):
    if v is None or str(v).strip() == "":
        return None, None
    if isinstance(v, (int, float)):
        s = str(int(v))
        return s.zfill(5), ("leading_zero" if len(s) < 5 else None)
    s = str(v).strip()
    return (s[:5], None) if re.match(r"^\d{5}(-\d{4})?$", s) else (None, "type")


def _int(v):
    if v is None or v == "":
        return None, None
    try:
        return int(float(str(v).replace(",", ""))), None
    except ValueError:
        return None, "placeholder" if str(v).strip().lower() in PLACEHOLDERS else "type"


def _year(v):
    x, note = _int(v)
    if x is not None and (x < 1800 or x > 2027):
        return None, "implausible"
    return x, note


def _enum(v):
    if v is None or str(v).strip() == "":
        return None, None
    t = _norm(v)
    return (TXN_MAP[t], None) if t in TXN_MAP else (None, "type")


def _text(v):
    if v is None:
        return None, None
    s = str(v).strip()
    if s == "":
        return None, None
    return (None, "placeholder") if s.lower() in PLACEHOLDERS else (s, None)


PARSERS = {"money": _money, "pct": _pct, "date": _date, "state": _state, "zip": _zip, "int": _int, "year": _year, "enum": _enum, "text": _text}


# ============================================================================ parse + validate
def parse_file(path: Path, kind: str, expect: dict | None = None) -> dict:
    """Parse one bordereau. `expect` may carry {umr, agreement_no, period_end} for reference checks."""
    fields = FIELDSETS[kind]
    sheet, grid = _read(path)
    out: dict = {"kind": kind, "sheet": sheet, "method": METHOD, "mapping": [], "missing": [], "issues": [], "rows": [], "header_row": None,
                 "skipped_rows": [], "stats": {}}
    iss = out["issues"]
    best = None
    for r in range(min(15, len(grid))):
        hits = sum(1 for v in grid[r] if v is not None and match_header(str(v), fields, fuzzy=False)[0])
        if hits >= 4 and (best is None or hits > best[1]):
            best = (r, hits)
    if not best:
        iss.append({"code": "NO_HEADER", "severity": "HIGH", "label": "No header band found in the first 15 rows", "cell": "A1", "field": None, "row": None})
        return out
    hr = best[0]
    out["header_row"] = hr + 1
    for r in range(hr):
        if any(v not in (None, "") for v in grid[r]):
            out["skipped_rows"].append({"row": r + 1, "reason": "Title band above header"})
    cols: dict[str, int] = {}
    for ci, v in enumerate(grid[hr]):
        if v is None or str(v).strip() == "":
            continue
        f, conf, how = match_header(str(v), fields)
        letter = get_column_letter(ci + 1)
        if f and f in cols:
            out["mapping"].append({"col": letter, "header": str(v), "field": None, "label": None, "confidence": conf, "method": f"duplicate of {fields[f][0]}"})
            continue
        out["mapping"].append({"col": letter, "header": str(v), "field": f, "label": fields[f][0] if f else None, "confidence": conf if f else 0.0, "method": how})
        if f:
            cols[f] = ci
            if how == "fuzzy":
                iss.append({"code": "LOW_CONFIDENCE_MAPPING", "severity": "LOW", "label": f"Header '{v}' mapped to {fields[f][0]} by similarity ({conf:.2f}) — confirm",
                            "cell": f"{letter}{hr + 1}", "field": f, "row": hr + 1})
        else:
            iss.append({"code": "UNMAPPED_COLUMN", "severity": "LOW", "label": f"Column '{v}' does not map to a CRS v5.2 field — ignored", "cell": f"{letter}{hr + 1}", "field": None, "row": hr + 1})
    for f, (label, typ, mand, _s) in fields.items():
        if mand and f not in cols:
            out["missing"].append(f)
            iss.append({"code": "MISSING_COLUMN", "severity": "HIGH" if f in ("certificate_ref", "tiv", "limit", "gross_premium", "state", "commission_pct", "incurred", "date_of_loss") else "MEDIUM",
                        "label": f"Mandatory CRS field '{label}' not present in the file", "cell": f"A{hr + 1}", "field": f, "row": hr + 1})
    letters = {f: get_column_letter(ci + 1) for f, ci in cols.items()}
    last = get_column_letter(max(cols.values()) + 1) if cols else "A"
    out["columns"] = letters
    out["last_col"] = last
    fmt_notes: dict[tuple, int] = {}
    fmt_cell: dict[tuple, str] = {}
    seen: dict[tuple, int] = {}
    filled = invalid = cells = 0
    mand_fields = [f for f, x in fields.items() if x[2]]
    for r in range(hr + 1, len(grid)):
        raw = grid[r]
        vals = {f: (raw[ci] if ci < len(raw) else None) for f, ci in cols.items()}
        if all(v in (None, "") for v in vals.values()):
            continue
        first = next((x for x in raw if x not in (None, "")), "")
        key_f = "claim_ref" if kind == "claims" else "county" if kind == "exposure" else "certificate_ref"
        if (isinstance(first, str) and "total" in first.lower()) or (key_f in vals and vals.get(key_f) in (None, "") and kind != "exposure"
                                                                     and sum(1 for v in vals.values() if isinstance(v, (int, float))) >= 2):
            out["skipped_rows"].append({"row": r + 1, "reason": "Totals / summary row"})
            iss.append({"code": "TOTALS_ROW", "severity": "LOW", "label": f"Row {r + 1} is a totals row — excluded", "cell": f"A{r + 1}", "field": None, "row": r + 1})
            continue
        row: dict[str, Any] = {"_r": r + 1, "_cells": {f: f"{letters[f]}{r + 1}" for f in cols}}
        for f, v in vals.items():
            label, typ, mand, _s = fields[f]
            val, note = PARSERS[typ](v)
            cell = f"{letters[f]}{r + 1}"
            cells += 1
            if note in ("type", "placeholder", "implausible"):
                invalid += 1
                sev = "HIGH" if f in ("tiv", "limit", "gross_premium", "certificate_ref") else "MEDIUM"
                iss.append({"code": "PLACEHOLDER" if note == "placeholder" else "INVALID_VALUE", "severity": sev,
                            "label": f"{label}: '{v}' is not a valid {typ}" + (" (placeholder)" if note == "placeholder" else ""), "cell": cell, "field": f, "row": r + 1})
            elif note:
                fmt_notes[(f, note)] = fmt_notes.get((f, note), 0) + 1
                fmt_cell.setdefault((f, note), cell)
            if val is None and mand and note is None:
                iss.append({"code": "BLANK_MANDATORY", "severity": "HIGH" if f in ("state", "tiv", "limit", "gross_premium", "certificate_ref") else "MEDIUM",
                            "label": f"{label} blank", "cell": cell, "field": f, "row": r + 1})
            if val is not None and mand:
                filled += 1
            row[f] = val
        for f in mand_fields:
            if f not in cols:
                cells += 1
        # row-level logic
        if kind == "risk":
            _risk_checks(row, iss, letters, expect)
        elif kind == "premium":
            _premium_checks(row, iss, letters)
        elif kind == "claims":
            if row.get("paid") is not None and row.get("reserve") is not None and row.get("incurred") is not None and abs(row["paid"] + row["reserve"] - row["incurred"]) > 2:
                iss.append({"code": "ARITH_INCURRED", "severity": "MEDIUM", "label": f"Paid {row['paid']:,.0f} + reserve {row['reserve']:,.0f} ≠ incurred {row['incurred']:,.0f}",
                            "cell": row["_cells"].get("incurred"), "field": "incurred", "row": r + 1})
        if expect and kind != "exposure":
            for f in ("umr", "agreement_no"):
                if row.get(f) and expect.get(f) and row[f] != expect[f]:
                    iss.append({"code": "WRONG_REFERENCE", "severity": "MEDIUM", "label": f"{fields[f][0]} '{row[f]}' ≠ agreement {expect[f]}", "cell": row["_cells"].get(f), "field": f, "row": r + 1})
        k = (row.get("certificate_ref") or row.get("claim_ref") or row.get("county"), row.get("transaction_type"), row.get("gross_premium") if kind != "claims" else row.get("incurred"),
             row.get("state") if kind == "exposure" else None)
        if k[0] and k in seen:
            row["_duplicate_of"] = seen[k]
            iss.append({"code": "DUPLICATE", "severity": "MEDIUM", "label": f"Row {r + 1} duplicates row {seen[k]} ({k[0]}) — excluded from checks", "cell": f"A{r + 1}", "field": None, "row": r + 1})
        elif k[0]:
            seen[k] = r + 1
        out["rows"].append(row)
    for (f, note), n in fmt_notes.items():
        first_cell = fmt_cell[(f, note)]
        msg = {"text": f"{n} {fields[f][0]} value(s) stored as text dates (MM/DD/YY) — parsed", "scaled": f"{n} {fields[f][0]} value(s) stated as whole numbers — scaled to %",
               "name": f"{n} state name(s) converted to postal codes", "leading_zero": f"{n} zip code(s) lost their leading zero in Excel — restored"}.get(note, f"{n} {note}")
        iss.append({"code": "FORMAT_NORMALISED", "severity": "LOW", "label": msg, "cell": first_cell, "field": f, "row": None})
    n = len(out["rows"])
    total_mand = n * len(mand_fields) or 1
    conf = [m["confidence"] for m in out["mapping"] if m["field"]]
    logic = len({i["row"] for i in iss if i["code"] in ("ARITH_NET", "ARITH_COMMISSION", "DATE_ORDER", "LIMIT_GT_TIV", "BOUND_AFTER_INCEPTION", "ARITH_INCURRED")})
    completeness = filled / total_mand
    validity = 1 - invalid / max(1, cells)
    mapping_conf = (sum(conf) / len(conf)) * (len([f for f in mand_fields if f in cols]) / max(1, len(mand_fields))) if conf else 0
    consistency = 1 - logic / max(1, n)
    out["stats"] = {"rows": n, "completeness": round(completeness, 4), "validity": round(validity, 4), "mapping_confidence": round(mapping_conf, 4),
                    "consistency": round(consistency, 4), "mapped": len(cols), "columns": len([m for m in out["mapping"]]),
                    "dq_score": round(100 * (0.45 * completeness + 0.25 * validity + 0.20 * mapping_conf + 0.10 * consistency), 1)}
    return out


def _risk_checks(row, iss, letters, expect):
    r = row["_r"]
    c = row["_cells"]
    if row.get("inception") and row.get("expiry") and row["expiry"] <= row["inception"]:
        iss.append({"code": "DATE_ORDER", "severity": "HIGH", "label": f"Expiry {row['expiry']} is not after inception {row['inception']}", "cell": c.get("expiry"), "field": "expiry", "row": r})
    if row.get("limit") and row.get("tiv") and row["limit"] > row["tiv"] * 1.001:
        iss.append({"code": "LIMIT_GT_TIV", "severity": "MEDIUM", "label": f"Limit {row['limit']:,.0f} exceeds TIV {row['tiv']:,.0f}", "cell": c.get("limit"), "field": "limit", "row": r})
    if row.get("written_date") and row.get("inception") and row.get("transaction_type") in ("NEW", "RENEWAL") and row["written_date"] > row["inception"]:
        iss.append({"code": "BOUND_AFTER_INCEPTION", "severity": "MEDIUM", "label": f"Bound {row['written_date']} after inception {row['inception']} (backdated cover)", "cell": c.get("written_date"), "field": "written_date", "row": r})
    if expect and expect.get("period_end") and row.get("written_date") and row.get("transaction_type") in ("NEW", "RENEWAL"):
        if row["written_date"][:7] != expect["period_end"][:7]:
            iss.append({"code": "OUT_OF_PERIOD", "severity": "LOW", "label": f"Bound {row['written_date']} outside the reporting month", "cell": c.get("written_date"), "field": "written_date", "row": r})


def _premium_checks(row, iss, letters):
    r = row["_r"]
    c = row["_cells"]
    g, p, a, n, t = row.get("gross_premium"), row.get("commission_pct"), row.get("commission_amount"), row.get("net_premium"), row.get("taxes") or 0
    if g is not None and p is not None and a is not None and abs(g * p - a) > max(2.0, abs(g) * 0.002):
        iss.append({"code": "ARITH_COMMISSION", "severity": "MEDIUM", "label": f"Commission {p * 100:.1f}% × gross {g:,.0f} = {g * p:,.0f}, reported {a:,.0f}", "cell": c.get("commission_amount"), "field": "commission_amount", "row": r})
    if g is not None and a is not None and n is not None and abs(g - a - n) > 2.0:
        iss.append({"code": "ARITH_NET", "severity": "MEDIUM", "label": f"Gross {g:,.0f} − commission {a:,.0f} = {g - a:,.0f}, net reported {n:,.0f}", "cell": c.get("net_premium"), "field": "net_premium", "row": r})

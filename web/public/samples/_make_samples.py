"""Generate viewer-gallery sample files (fictional data, watermarked SAMPLE).

Run:  cd backend && uv run python ../web/public/samples/_make_samples.py
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent
RNG = np.random.default_rng(7)
manifest: dict = {}


# ============================================================== PDF
def make_pdf() -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    W, H = letter
    path = OUT / "declarations.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setTitle("Commercial Property Declarations — SAMPLE")
    highlights = []
    L, R = 54, W - 54

    def watermark():
        c.saveState()
        c.setFillColorRGB(0.85, 0.87, 0.9)
        c.setFont("Helvetica-Bold", 96)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "SAMPLE")
        c.restoreState()

    def header(title: str, page: int):
        watermark()
        c.setFillColorRGB(0.07, 0.1, 0.18)
        c.rect(0, H - 64, W, 64, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(L, H - 32, "NORTHGATE SPECIALTY INSURANCE CO.")
        c.setFont("Helvetica", 9)
        c.drawString(L, H - 47, "Commercial Property · Fictional carrier for demonstration")
        c.drawRightString(R, H - 32, "Policy NSP-CP-2025-004418")
        c.drawRightString(R, H - 47, f"Page {page} of 3")
        c.setFillColorRGB(0.07, 0.1, 0.18)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(L, H - 100, title)
        c.setStrokeColorRGB(0.8, 0.83, 0.88)
        c.line(L, H - 110, R, H - 110)

    def row(y: float, label: str, value: str, hl: str | None = None, page: int = 1):
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.35, 0.4, 0.5)
        c.drawString(L, y, label)
        c.setFillColorRGB(0.07, 0.1, 0.18)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(L + 220, y, value)
        c.setStrokeColorRGB(0.92, 0.93, 0.95)
        c.line(L, y - 6, R, y - 6)
        if hl:
            vw = c.stringWidth(value, "Helvetica-Bold", 10)
            # top-left origin bbox in PDF points: [x0, top, x1, bottom]
            highlights.append({"page": page, "bbox": [round(L + 216, 1), round(H - (y + 11), 1), round(L + 224 + vw, 1), round(H - (y - 4), 1)], "label": hl, "page_size": [W, H]})

    def footer():
        c.setFont("Helvetica", 7.5)
        c.setFillColorRGB(0.5, 0.55, 0.62)
        c.drawString(L, 36, "SAMPLE — fictional document generated for the Anaira Underwriting Control demo. Not an insurance contract.")

    # ---- page 1
    header("Commercial Property Declarations", 1)
    y = H - 140
    for lab, val, hl in [
        ("Named insured", "ABC Manufacturing, Inc.", None),
        ("Mailing address", "4100 Industrial Pkwy, Columbus, OH 43219", None),
        ("Policy period", "08/15/2025 to 08/15/2026 12:01 AM standard time", None),
        ("Producer", "Harbor Risk Partners LLC", None),
        ("Coverage basis", "Blanket, replacement cost", None),
        ("Total insured value", "$120,400,000", "TIV · $120.4M"),
        ("Policy limit", "$250,000,000 per occurrence loss limit", None),
        ("Business income limit", "$15,000,000", "BI limit · $15M"),
        ("Coinsurance", "Waived — agreed value endorsement CP 99 01", None),
        ("Annual premium", "$1,184,500", None),
    ]:
        row(y, lab, val, hl, 1)
        y -= 24
    c.setFont("Helvetica-Bold", 11)
    c.drawString(L, y - 14, "Scheduled locations")
    y -= 36
    c.setFont("Helvetica-Bold", 8.5)
    cols = [L, L + 40, L + 230, L + 330, L + 420]
    for x, t in zip(cols, ["Loc", "Address", "Occupancy", "Construction", "TIV"]):
        c.drawString(x, y, t)
    c.setFont("Helvetica", 8.5)
    locs = [
        ("1", "4100 Industrial Pkwy, Columbus OH", "Metal fabrication", "Non-comb.", "$38,200,000"),
        ("2", "88 Commerce Dr, Reno NV", "Warehouse", "Joisted masonry", "$21,750,000"),
        ("3", "1200 Port Blvd, Houston TX", "Distribution", "Non-comb.", "$29,900,000"),
        ("4", "15 Harbor Rd, Savannah GA", "Assembly", "Masonry non-comb.", "$18,300,000"),
        ("5", "602 Valley Ln, Fresno CA", "Warehouse", "Tilt-up", "$12,250,000"),
    ]
    for r_ in locs:
        y -= 16
        for x, t in zip(cols, r_):
            c.drawString(x, y, t)
    footer()
    c.showPage()

    # ---- page 2
    header("Deductibles & Sublimits", 2)
    y = H - 140
    for lab, val, hl in [
        ("All other perils (AOP)", "$100,000 per occurrence", None),
        ("Named storm", "2% of TIV per location, $250,000 minimum", "Named storm ded · 2%"),
        ("Wind / hail (non-named)", "1% of TIV per location, $100,000 minimum", None),
        ("Flood — zones A & V", "$500,000 per occurrence", None),
        ("Flood — all other zones", "$250,000 per occurrence", None),
        ("Earthquake", "5% of TIV per location, $250,000 minimum", None),
        ("Flood sublimit", "$25,000,000 annual aggregate", None),
        ("Earthquake sublimit", "$25,000,000 annual aggregate", None),
        ("Equipment breakdown", "Included to policy limit", None),
        ("Spoilage", "$250,000", None),
        ("Debris removal", "25% of loss, $5,000,000 max", None),
        ("Ordinance or law (B+C)", "$10,000,000", None),
    ]:
        row(y, lab, val, hl, 2)
        y -= 24
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0.35, 0.4, 0.5)
    c.drawString(L, y - 10, "Percentage deductibles apply separately to each scheduled location per the Statement of Values on file.")
    footer()
    c.showPage()

    # ---- page 3
    header("Forms, Protective Safeguards & Subjectivities", 3)
    y = H - 140
    for lab, val, hl in [
        ("CP 00 10 10 12", "Building and Personal Property Coverage Form", None),
        ("CP 00 30 10 12", "Business Income (and Extra Expense)", None),
        ("CP 10 30 09 17", "Causes of Loss — Special Form", None),
        ("CP 04 11 09 17", "Protective Safeguards — P-1 sprinkler, P-2 alarm", "Protective safeguards"),
        ("NSI 14 02", "Named Storm Deductible Endorsement", None),
        ("NSI 22 07", "Occupancy Warranty — no lithium-ion storage > 5% floor area", None),
    ]:
        row(y, lab, val, hl, 3)
        y -= 24
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0.07, 0.1, 0.18)
    c.drawString(L, y - 14, "Subjectivities")
    c.setFont("Helvetica", 9.5)
    for i, s in enumerate([
        "1. Updated roof-replacement schedule for Reno (Loc 2) within 60 days of binding.",
        "2. Confirmation of central-station monitoring at Savannah (Loc 4).",
        "3. Signed SOV reflecting 2026 values prior to issuance.",
    ]):
        c.drawString(L, y - 36 - i * 16, s)
    footer()
    c.showPage()
    c.save()
    manifest["pdf"] = {"url": "/samples/declarations.pdf", "highlights": highlights}


# ============================================================== XLSX payload
def col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def make_sov() -> None:
    headers = ["Loc #", "Bldg #", "Location name", "Street", "City", "State", "Zip", "Occupancy", "Construction",
               "Year built", "Stories", "Sq ft", "Roof year", "Sprinklered", "Building value", "Contents", "BI / 12 mo",
               "Total TIV", "% of TIV", "Internal notes"]
    widths = [6, 6, 26, 24, 14, 6, 7, 18, 16, 9, 7, 10, 9, 10, 14, 13, 13, 14, 8, 22]
    cities = [("Columbus", "OH", "43219"), ("Reno", "NV", "89502"), ("Houston", "TX", "77029"), ("Savannah", "GA", "31408"),
              ("Fresno", "CA", "93725"), ("Tampa", "FL", "33619"), ("Memphis", "TN", "38118"), ("Joliet", "IL", "60436"),
              ("Charlotte", "NC", "28208"), ("Phoenix", "AZ", "85043")]
    occs = ["Metal fabrication", "Warehouse", "Distribution", "Assembly", "Office", "Plastics molding", "Cold storage"]
    cons = ["Non-combustible", "Joisted masonry", "Masonry non-comb.", "Tilt-up concrete", "Steel frame"]
    streets = ["Industrial Pkwy", "Commerce Dr", "Port Blvd", "Harbor Rd", "Valley Ln", "Logistics Way", "Enterprise Ave", "Rail Spur Rd"]
    cells: dict = {}
    money = '"$"#,##0'
    cells["A1"] = {"v": "ABC Manufacturing, Inc. — Statement of Values, 2026 renewal", "t": "s", "bold": True, "fill": "FF111A2E"}
    cells["A2"] = {"v": "Values in USD · Replacement cost · As of 07/15/2026 · Prepared by Harbor Risk Partners", "t": "s"}
    for i, h in enumerate(headers):
        cells[f"{col_letter(i + 1)}3"] = {"v": h, "t": "s", "bold": True, "fill": "FFD9E1F2"}
    first, n = 4, 46
    last = first + n - 1
    for k in range(n):
        r = first + k
        city, st, z = cities[k % len(cities)]
        loc = k + 1
        bv = int(RNG.integers(8, 60)) * 250_000
        cv = int(bv * RNG.uniform(0.15, 0.5) / 1000) * 1000
        bi = int(bv * RNG.uniform(0.05, 0.25) / 1000) * 1000
        yb = int(RNG.integers(1968, 2019))
        roof = int(RNG.integers(max(yb, 1995), 2025))
        if loc == 11:
            city, st, z, roof = "Reno", "NV", "89502", 2011
        vals = [loc, 1, f"{city} {occs[k % len(occs)].split()[0]} {'Plant' if k % 3 == 0 else 'Facility'}",
                f"{100 + k * 37} {streets[k % len(streets)]}", city, st, z, occs[k % len(occs)], cons[k % len(cons)],
                yb, int(RNG.integers(1, 4)), int(RNG.integers(20, 400)) * 500, roof,
                "Yes" if k % 5 else "Partial", bv, cv, bi, None, None, "" if k % 9 else "Confirm values w/ insured"]
        for i, v in enumerate(vals):
            col = col_letter(i + 1)
            addr = f"{col}{r}"
            if v is None:
                continue
            cell = {"v": v, "t": "n" if isinstance(v, (int, float)) else "s"}
            if col in "OPQ":
                cell["num_fmt"] = money
            if col == "L":
                cell["num_fmt"] = "#,##0"
            if col == "J" or col == "M":
                cell["num_fmt"] = "0"
            cells[addr] = cell
        tiv = bv + cv + bi
        cells[f"R{r}"] = {"v": tiv, "t": "f", "f": f"=O{r}+P{r}+Q{r}", "num_fmt": money}
    tot_r = last + 1
    total = sum(cells[f"R{first + k}"]["v"] for k in range(n))
    for k in range(n):
        r = first + k
        cells[f"S{r}"] = {"v": round(cells[f"R{r}"]["v"] / total, 5), "t": "f", "f": f"=R{r}/R${tot_r}", "num_fmt": "0.0%"}
    cells[f"C{tot_r}"] = {"v": "TOTAL", "t": "s", "bold": True, "fill": "FFF2F2F2"}
    for col in "OPQR":
        s = sum(cells[f"{col}{first + k}"]["v"] for k in range(n))
        cells[f"{col}{tot_r}"] = {"v": s, "t": "f", "f": f"=SUM({col}{first}:{col}{last})", "bold": True, "fill": "FFF2F2F2", "num_fmt": money}
    cells[f"S{tot_r}"] = {"v": 1, "t": "f", "f": f"=SUM(S{first}:S{last})", "bold": True, "fill": "FFF2F2F2", "num_fmt": "0.0%"}
    # highlight fill on a changed row (broker's yellow)
    for i in range(len(headers)):
        a = f"{col_letter(i + 1)}{first + 45}"
        if a in cells:
            cells[a]["fill"] = "FFFFF2CC"
    sheet = {
        "name": "Locations", "hidden": False, "max_row": tot_r + 2, "max_col": len(headers), "cells": cells,
        "merges": ["A1:T1", "A2:T2"], "hidden_rows": [20, 21, 22], "hidden_cols": ["T"],
        "col_widths": {col_letter(i + 1): w for i, w in enumerate(widths)}, "freeze": "D4",
    }
    cells[f"A{tot_r + 2}"] = {"v": "Rows 20–22 hidden by broker (sold locations — excluded from totals?)", "t": "s"}

    b_cells = {"A1": {"v": "Loc #", "t": "s", "bold": True, "fill": "FFD9E1F2"}, "B1": {"v": "Bldg", "t": "s", "bold": True, "fill": "FFD9E1F2"},
               "C1": {"v": "Description", "t": "s", "bold": True, "fill": "FFD9E1F2"}, "D1": {"v": "Values ($000s)", "t": "s", "bold": True, "fill": "FFD9E1F2"},
               "E1": {"v": "Updated", "t": "s", "bold": True, "fill": "FFD9E1F2"}}
    for k in range(12):
        r = k + 2
        b_cells[f"A{r}"] = {"v": k + 1, "t": "n"}
        b_cells[f"B{r}"] = {"v": 1 + k % 2, "t": "n"}
        b_cells[f"C{r}"] = {"v": ["Main plant", "Annex", "Warehouse", "Office"][k % 4], "t": "s"}
        b_cells[f"D{r}"] = {"v": int(RNG.integers(2000, 40000)), "t": "n", "num_fmt": "#,##0"}
        b_cells[f"E{r}"] = {"v": f"2026-0{1 + k % 7}-15", "t": "d"}
    buildings = {"name": "Buildings", "hidden": False, "max_row": 13, "max_col": 5, "cells": b_cells, "merges": [], "hidden_rows": [],
                 "hidden_cols": [], "col_widths": {"C": 18, "D": 14, "E": 12}, "freeze": "A2"}
    lookup = {"name": "_lookup", "hidden": True, "max_row": 6, "max_col": 2,
              "cells": {f"A{i + 1}": {"v": c_, "t": "s"} for i, c_ in enumerate(cons)} | {f"B{i + 1}": {"v": i + 1, "t": "n"} for i in range(5)},
              "merges": [], "hidden_rows": [], "hidden_cols": [], "col_widths": {"A": 20}, "freeze": None}
    (OUT / "sov_payload.json").write_text(json.dumps({"sheets": [sheet, buildings, lookup]}))
    manifest["xlsx"] = {"anchor": {"doc_id": None, "kind": "xlsx", "sheet": "Locations", "cell": "M14", "range": "A14:S14"}}


# ============================================================== EML payload
def make_eml() -> None:
    text = (
        "Hi Maya,\n\n"
        "Attached is the 2026 renewal submission for ABC Manufacturing. A few headline changes from expiring:\n\n"
        "  • Total insured values increased to $151.2M following the annual appraisal update.\n"
        "  • The insured acquired the Tampa distribution center (Loc 47) in March 2026 — 1 story, tilt-up, fully sprinklered.\n"
        "  • The roof at Reno was replaced in 2019 per the facilities team; the SOV still shows 2011, we'll correct it.\n"
        "  • Business income is now $15M at the Columbus plant after the new line came online.\n\n"
        "The insured is hoping to hold the 2% named storm deductible given their loss history. Loss runs through 06/30 are attached — "
        "no property losses above $250K in the last five years.\n\n"
        "Let me know if you need anything else ahead of the quote.\n\n"
        "Best,\nJordan Pike\nSenior Vice President · Harbor Risk Partners LLC\n(614) 555-0142\n\n"
        "— SAMPLE: fictional message generated for demonstration —"
    )
    payload = {
        "from": "Jordan Pike <jpike@harbor-risk.example>",
        "to": ["Maya Chen <mchen@northgate-specialty.example>"],
        "cc": ["Property Submissions <submissions@northgate-specialty.example>"],
        "subject": "RE: ABC Manufacturing — 2026 renewal submission",
        "date": "2026-07-18T14:32:00-04:00",
        "text": text,
        "html": None,
        "attachments": [
            {"filename": "ABC_SOV_2026.xlsx", "doc_id": "doc_sample_sov", "size_bytes": 184_220, "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            {"filename": "ABC_LossRuns_2021-2026.pdf", "doc_id": "doc_sample_lossrun", "size_bytes": 412_880, "content_type": "application/pdf"},
            {"filename": "Reno_roof_invoice_2019.pdf", "doc_id": None, "size_bytes": 96_310, "content_type": "application/pdf"},
            {"filename": "Tampa_site_photos.zip", "doc_id": None, "size_bytes": 8_420_110, "content_type": "application/zip"},
        ],
        "highlights": [
            {"text": "increased to $151.2M", "field_code": "tiv_total", "obs_id": "obs_sample_tiv"},
            {"text": "acquired the Tampa distribution center (Loc 47) in March 2026", "field_code": "location_added", "obs_id": "obs_sample_tampa"},
            {"text": "roof at Reno was replaced in 2019", "field_code": "roof_year", "obs_id": "obs_sample_roof"},
            {"text": "$15M", "field_code": "bi_limit", "obs_id": "obs_sample_bi"},
            {"text": "2% named storm deductible", "field_code": "named_storm_ded_pct", "obs_id": "obs_sample_ns"},
        ],
    }
    (OUT / "eml_payload.json").write_text(json.dumps(payload, indent=1))


# ============================================================== GLB writer
class Glb:
    def __init__(self):
        self.nodes: list[dict] = []
        self.meshes: list[dict] = []
        self.materials: list[dict] = []
        self.accessors: list[dict] = []
        self.views: list[dict] = []
        self.blob = bytearray()
        self.roots: list[int] = []
        self._mat_cache: dict = {}

    def _view(self, data: bytes, target: int) -> int:
        while len(self.blob) % 4:
            self.blob.append(0)
        off = len(self.blob)
        self.blob.extend(data)
        self.views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": target})
        return len(self.views) - 1

    def material(self, rgba, rough=0.85, metal=0.0) -> int:
        key = (tuple(round(x, 3) for x in rgba), rough, metal)
        if key in self._mat_cache:
            return self._mat_cache[key]
        m = {"pbrMetallicRoughness": {"baseColorFactor": list(rgba), "metallicFactor": metal, "roughnessFactor": rough}}
        if rgba[3] < 1:
            m["alphaMode"] = "BLEND"
            m["doubleSided"] = True
        self.materials.append(m)
        self._mat_cache[key] = len(self.materials) - 1
        return self._mat_cache[key]

    def mesh(self, prims: list[tuple[np.ndarray, np.ndarray, int]]) -> int:
        """prims: list of (vertices Nx3, faces Mx3, material index); flat-shaded."""
        out = []
        for verts, faces, mat in prims:
            tri = verts[faces]  # M x 3 x 3
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            pos = tri.reshape(-1, 3).astype(np.float32)
            nor = np.repeat(n, 3, axis=0).astype(np.float32)
            idx = np.arange(len(pos), dtype=np.uint32)
            pv = self._view(pos.tobytes(), 34962)
            self.accessors.append({"bufferView": pv, "componentType": 5126, "count": len(pos), "type": "VEC3",
                                   "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
            pa = len(self.accessors) - 1
            nv = self._view(nor.tobytes(), 34962)
            self.accessors.append({"bufferView": nv, "componentType": 5126, "count": len(nor), "type": "VEC3"})
            na = len(self.accessors) - 1
            iv = self._view(idx.tobytes(), 34963)
            self.accessors.append({"bufferView": iv, "componentType": 5125, "count": len(idx), "type": "SCALAR"})
            ia = len(self.accessors) - 1
            out.append({"attributes": {"POSITION": pa, "NORMAL": na}, "indices": ia, "material": mat})
        self.meshes.append({"primitives": out})
        return len(self.meshes) - 1

    def node(self, name: str, parent: int | None = None, mesh: int | None = None, t=(0, 0, 0), extras: dict | None = None) -> int:
        n: dict = {"name": name}
        if any(t):
            n["translation"] = [float(x) for x in t]
        if mesh is not None:
            n["mesh"] = mesh
        if extras:
            n["extras"] = extras
        self.nodes.append(n)
        i = len(self.nodes) - 1
        if parent is None:
            self.roots.append(i)
        else:
            self.nodes[parent].setdefault("children", []).append(i)
        return i

    def write(self, path: Path, scene_extras: dict | None = None):
        while len(self.blob) % 4:
            self.blob.append(0)
        gltf = {"asset": {"version": "2.0", "generator": "anaira-sample-gen"}, "scene": 0,
                "scenes": [{"nodes": self.roots, **({"extras": scene_extras} if scene_extras else {})}],
                "nodes": self.nodes, "meshes": self.meshes, "materials": self.materials,
                "accessors": self.accessors, "bufferViews": self.views, "buffers": [{"byteLength": len(self.blob)}]}
        js = json.dumps(gltf, separators=(",", ":")).encode()
        js += b" " * ((4 - len(js) % 4) % 4)
        total = 12 + 8 + len(js) + 8 + len(self.blob)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(js), 0x4E4F534A))
            f.write(js)
            f.write(struct.pack("<II", len(self.blob), 0x004E4942))
            f.write(bytes(self.blob))


def box(sx, sy, sz, cx=0.0, cy=0.0, cz=0.0):
    """Axis-aligned box; y is up, (cx, cz) centre, cy = bottom."""
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy, cy + sy
    z0, z1 = cz - sz / 2, cz + sz / 2
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], dtype=np.float64)
    f = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [3, 7, 6], [3, 6, 2], [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5]])
    return v, f


def merge(parts):
    vs, fs, off = [], [], 0
    for v, f in parts:
        vs.append(v)
        fs.append(f + off)
        off += len(v)
    return np.vstack(vs), np.vstack(fs)


def gable(sx, rise, sz, cy):
    """Gabled roof prism along x."""
    x0, x1, z0, z1 = -sx / 2, sx / 2, -sz / 2, sz / 2
    v = np.array([[x0, cy, z0], [x1, cy, z0], [x1, cy, z1], [x0, cy, z1], [x0, cy + rise, 0], [x1, cy + rise, 0]], dtype=np.float64)
    f = np.array([[0, 1, 2], [0, 2, 3], [0, 4, 5], [0, 5, 1], [3, 2, 5], [3, 5, 4], [0, 3, 4], [1, 5, 2]])
    return v, f


FT = 0.3048
WALL = (0.86, 0.88, 0.91, 1.0)
ROOF = (0.55, 0.59, 0.66, 1.0)


def make_warehouse() -> None:
    g = Glb()
    L_, Wd, Hh = 110.0, 64.0, 34 * FT  # 34 ft clear height shell
    site = g.node("SITE")
    g.node("SLAB", site, g.mesh([(*box(L_ + 10, 0.3, Wd + 10, cy=-0.3), g.material((0.78, 0.8, 0.83, 1)))]))
    shell_mat = g.material((0.8, 0.84, 0.9, 0.18))
    t = 0.3
    walls = merge([box(L_, Hh, t, cz=-Wd / 2), box(L_, Hh, t, cz=Wd / 2), box(t, Hh, Wd, cx=-L_ / 2), box(t, Hh, Wd, cx=L_ / 2)])
    b1 = g.node("B-1", site, None, extras={"label": "Redline Logistics DC — Building 1", "stories": 1, "construction": "Tilt-up concrete",
                                           "occupancy": "Warehouse — lithium-ion battery storage", "tiv": 48_600_000, "roof_year": 2016,
                                           "height_ft": 34, "sprinkler": "ESFR K-17 · design 20 ft storage"})
    g.node("B-1_SHELL", b1, g.mesh([(*walls, shell_mat)]), extras={"transparent": True})
    g.node("ROOF-B-1", b1, g.mesh([(*box(L_ + 0.6, 0.4, Wd + 0.6, cy=Hh), g.material((0.6, 0.64, 0.7, 0.14)))]),
           extras={"transparent": True})
    # racks: 10 double rows running along x
    upr = g.material((0.2, 0.36, 0.72, 1), rough=0.5, metal=0.4)
    beam = g.material((0.93, 0.47, 0.13, 1), rough=0.6, metal=0.3)
    load = g.material((0.78, 0.66, 0.48, 1))
    load_hi = g.material((0.84, 0.36, 0.25, 1))
    rack_len, rack_d = 84.0, 2.4
    for i in range(10):
        z = -Wd / 2 + 7 + i * 5.6
        over = i >= 3  # racks 04-10 stacked to 28 ft
        hft = 28 if over else 20
        levels = 5 if over else 4
        lh = hft * FT / levels
        parts_u, parts_b, parts_l = [], [], []
        for k in range(15):
            x = -rack_len / 2 + k * rack_len / 14
            parts_u += [box(0.1, hft * FT, 0.1, cx=x, cz=z - rack_d / 2), box(0.1, hft * FT, 0.1, cx=x, cz=z + rack_d / 2)]
        for lv in range(levels):
            y = lv * lh
            parts_b += [box(rack_len, 0.12, 0.08, cy=y + 0.1, cz=z - rack_d / 2), box(rack_len, 0.12, 0.08, cy=y + 0.1, cz=z + rack_d / 2)]
            for k in range(14):
                x = -rack_len / 2 + (k + 0.5) * rack_len / 14
                if RNG.random() < 0.88:
                    parts_l.append(box(rack_len / 14 - 0.5, lh * 0.72, rack_d - 0.3, cx=x, cy=y + 0.24, cz=z))
        name = f"RACK-{i + 1:02d}"
        extras = {"label": f"Rack row {i + 1:02d}", "height_ft": hft, "commodity": "Li-ion battery modules (Class IV+)" if over else "Palletized general merchandise",
                  "levels": levels}
        if over:
            extras["flag"] = "Storage 28 ft exceeds sprinkler design (20 ft)"
        rn = g.node(name, b1, None, extras=extras)
        g.node(f"{name}_frame", rn, g.mesh([(*merge(parts_u), upr), (*merge(parts_b), beam)]))
        g.node(f"{name}_loads", rn, g.mesh([(*merge(parts_l), load_hi if over else load)]))
    g.node("SPRINKLER_DESIGN_PLANE", b1, g.mesh([(*box(L_ - 1, 0.05, Wd - 1, cy=20 * FT), g.material((0.07, 0.64, 0.64, 0.3)))]),
           extras={"label": "Sprinkler design storage height", "height_ft": 20, "design": "ESFR K-17 @ 35 psi · max 20 ft storage / 25 ft ceiling",
                   "transparent": True})
    # dock doors (small detail)
    dock = g.material((0.3, 0.33, 0.4, 1))
    doors = merge([box(3.0, 3.2, 0.15, cx=-L_ / 2 + 8 + k * 7, cz=Wd / 2 + 0.2) for k in range(13)])
    g.node("DOCK_DOORS", b1, g.mesh([(*doors, dock)]))
    g.write(OUT / "warehouse.glb")


def make_campus() -> None:
    g = Glb()
    site = g.node("SITE")
    g.node("PARKING", site, g.mesh([(*box(220, 0.15, 170, cx=10, cz=5, cy=-0.15), g.material((0.84, 0.85, 0.87, 1)))]))
    specs = [
        ("B-1", "Main manufacturing plant", 1, "Non-combustible", "Metal fabrication", 38_200_000, 2014, 38, (-50, -35), (90, 55), None),
        ("B-2", "Reno warehouse", 1, "Joisted masonry", "Warehouse", 21_750_000, 2011, 28, (55, -40), (60, 42), "Roof year conflict: SOV 2011 vs engineering 2019"),
        ("B-3", "Office & R&D", 3, "Steel frame", "Office", 14_300_000, 2020, 44, (60, 25), (40, 26), None),
        ("B-4", "Assembly hall", 2, "Masonry non-comb.", "Assembly", 18_300_000, 2008, 32, (-45, 30), (55, 38), "Roof age 18 yrs"),
        ("B-5", "Tampa distribution center", 1, "Tilt-up concrete", "Distribution", 29_900_000, 2023, 36, (5, 70), (80, 30), "New location — not in CAT run"),
        ("B-6", "Utility / boiler house", 1, "Non-combustible", "Utility", 3_450_000, 1999, 22, (-5, -2), (18, 14), None),
    ]
    for name, label, stories, cons, occ, tiv, roof_year, hft, (cx, cz), (sx, sz), flag in specs:
        h = hft * FT
        extras = {"label": label, "stories": stories, "construction": cons, "occupancy": occ, "tiv": tiv, "roof_year": roof_year, "height_ft": hft}
        if flag:
            extras["flag"] = flag
        bn = g.node(name, site, None, t=(cx, 0, cz), extras=extras)
        body = [box(sx, h, sz)]
        # window bands for multistorey
        prims = [(*merge(body), g.material(WALL))]
        if stories > 1:
            bands = merge([box(sx + 0.1, 1.0, sz + 0.1, cy=(s + 0.45) * h / stories) for s in range(stories)])
            prims.append((*bands, g.material((0.36, 0.47, 0.6, 1), rough=0.3, metal=0.2)))
        g.node(f"{name}_body", bn, g.mesh(prims))
        if name in ("B-4", "B-6"):
            roof = gable(sx + 1, 4.0, sz + 1, h)
        else:
            roof = box(sx + 0.4, 0.5, sz + 0.4, cy=h)
        hvac = merge([box(3, 1.5, 2.5, cx=-sx / 4 + k * sx / 6, cy=h + 0.5, cz=0) for k in range(3)]) if name not in ("B-4", "B-6") else None
        rp = [(*roof, g.material(ROOF))]
        if hvac is not None:
            rp.append((*hvac, g.material((0.7, 0.72, 0.75, 1), rough=0.5, metal=0.5)))
        g.node(f"ROOF-{name}", bn, g.mesh(rp), extras={"label": f"Roof — {label}", "roof_year": roof_year})
    g.write(OUT / "campus.glb")


# ============================================================== aerial PNGs
def make_aerials() -> None:
    Wp, Hp = 1100, 700
    base = RNG.normal(0, 1, (Hp // 4, Wp // 4, 3))
    noise = np.array(Image.fromarray(((base * 18) + 128).clip(0, 255).astype(np.uint8)).resize((Wp, Hp), Image.BICUBIC)).astype(np.float32) - 128

    def draw(year: int) -> Image.Image:
        img = Image.new("RGB", (Wp, Hp), (118, 138, 96))
        d = ImageDraw.Draw(img)
        # fields
        d.rectangle([0, 0, 380, 250], fill=(134, 146, 98))
        d.rectangle([760, 460, Wp, Hp], fill=(108, 130, 88))
        # roads
        d.rectangle([0, 300, Wp, 340], fill=(92, 94, 98))
        d.rectangle([520, 0, 552, Hp], fill=(92, 94, 98))
        for x in range(0, Wp, 40):
            d.rectangle([x, 318, x + 18, 321], fill=(222, 206, 120))
        # parking
        d.rectangle([80, 360, 480, 520], fill=(126, 128, 132))
        for x in range(90, 480, 16):
            d.line([x, 368, x, 400], fill=(220, 220, 220), width=1)
            d.line([x, 480, x, 512], fill=(220, 220, 220), width=1)
        rng = np.random.default_rng(3)
        for _ in range(38):
            x, y = int(rng.integers(92, 470)), int(rng.choice([372, 484]))
            col = tuple(int(c) for c in rng.integers(40, 230, 3))
            d.rectangle([x, y, x + 9, y + 20], fill=col)
        # main plant roof
        roof_col = (186, 190, 196) if year < 2024 else (228, 231, 235)
        d.rectangle([600, 60, 1020, 270], fill=roof_col, outline=(150, 152, 158), width=3)
        for k in range(6):
            d.rectangle([640 + k * 60, 110, 668 + k * 60, 132], fill=(150, 154, 160))
        if year < 2024:  # staining on old roof
            d.ellipse([780, 150, 900, 220], fill=(160, 158, 150))
        # warehouse
        d.rectangle([600, 380, 740, 640], fill=(200, 196, 188), outline=(150, 150, 150), width=3)
        # office
        d.rectangle([90, 560, 300, 670], fill=(170, 108, 90), outline=(120, 80, 70), width=3)
        # trees
        for _ in range(70):
            x, y = int(rng.integers(0, 380)), int(rng.integers(0, 290))
            r = int(rng.integers(8, 20))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(56 + int(rng.integers(0, 20)), 86 + int(rng.integers(0, 20)), 52))
        if year >= 2024:
            # expansion building + solar array + new drive
            d.rectangle([770, 400, 1060, 640], fill=(222, 224, 228), outline=(150, 152, 158), width=3)
            d.rectangle([740, 500, 770, 530], fill=(92, 94, 98))
            for r_ in range(4):
                for c_ in range(9):
                    x0, y0 = 616 + c_ * 44, 150 + r_ * 26
                    if 780 <= x0 <= 900 and r_ in (1, 2):
                        continue
                    d.rectangle([x0, y0, x0 + 38, y0 + 20], fill=(38, 52, 84), outline=(80, 96, 130))
        arr = np.array(img).astype(np.float32) + noise * 0.55
        out = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
        d2 = ImageDraw.Draw(out)
        d2.text((12, Hp - 22), f"SAMPLE · synthetic aerial · {year}-06", fill=(255, 255, 255))
        return out

    draw(2021).save(OUT / "aerial_2021.png", optimize=True)
    draw(2025).save(OUT / "aerial_2025.png", optimize=True)


# ============================================================== CSV / JSON / YAML
def make_tables() -> None:
    perils = ["WS", "WS", "WS", "FL", "EQ", "SCS", "WF"]
    lines = ["EventID,Peril,Rate,MeanLoss,SDi,SDc,ExpValue"]
    for i in range(420):
        p = perils[i % len(perils)]
        rate = float(RNG.lognormal(-7.6, 1.1))
        loss = float(RNG.lognormal(13.2, 1.35))
        lines.append(f"{100000 + i * 13},{p},{rate:.7f},{loss:.0f},{loss * 0.6:.0f},{loss * 0.3:.0f},{loss * 4:.0f}")
    (OUT / "cat_elt.csv").write_text("\n".join(lines) + "\n")

    cols = ["PortNumber", "AccNumber", "LocNumber", "LocName", "StreetAddress", "City", "AreaCode", "PostalCode", "Latitude", "Longitude",
            "OccupancyCode", "ConstructionCode", "YearBuilt", "NumberOfStoreys", "BuildingTIV", "OtherTIV", "ContentsTIV", "BITIV", "LocCurrency"]
    places = [("Columbus", "OH", "43219", 39.99, -82.93), ("Reno", "NV", "89502", 39.5, -119.77), ("Houston", "TX", "77029", 29.76, -95.26),
              ("Savannah", "GA", "31408", 32.1, -81.18), ("Fresno", "CA", "93725", 36.68, -119.73), ("Tampa", "FL", "33619", 27.93, -82.37)]
    rows = [",".join(cols)]
    for i in range(30):
        c_, st, z, la, lo = places[i % len(places)]
        bv = int(RNG.integers(20, 200)) * 100_000
        name = f'"{c_} Facility {i + 1}, Bldg {1 + i % 2}"'
        rows.append(",".join(str(x) for x in ["NSP", "ABC-MFG", i + 1, name, f"{100 + i * 11} Industrial Pkwy", c_, st, z,
                                               round(la + RNG.normal(0, 0.05), 5), round(lo + RNG.normal(0, 0.05), 5),
                                               [1150, 1050, 1100][i % 3], [5050, 5100, 5200][i % 3], int(RNG.integers(1965, 2022)),
                                               int(RNG.integers(1, 4)), bv, 0, int(bv * 0.3), int(bv * 0.12), "USD"]))
    (OUT / "oed_locations.csv").write_text("\n".join(rows) + "\n")

    rps = [10, 25, 50, 100, 250, 500, 1000]
    oep = [2.1e6, 5.8e6, 9.9e6, 15.6e6, 24.8e6, 32.0e6, 40.5e6]
    ep = {
        "run_id": "cat_sample_current", "vendor": "MockCat (stand-in for Moody's RMS / Verisk)", "model_version": "MockCat 23.1 (sample)",
        "basis": "Carrier share, net of deductibles", "perils": ["WS", "FL", "EQ", "SCS"],
        "oep": [{"rp": r, "loss": round(v)} for r, v in zip(rps, oep)],
        "aep": [{"rp": r, "loss": round(v * (1.18 - 0.02 * k))} for k, (r, v) in enumerate(zip(rps, oep))],
        "compare": [{"label": "As bound 2025", "oep": [{"rp": r, "loss": round(v * 0.78)} for r, v in zip(rps, oep)]}],
        "aal_total": 1_412_000,
    }
    (OUT / "ep_curve.json").write_text(json.dumps(ep, indent=2))

    (OUT / "rule_named_storm.yaml").write_text("""# SAMPLE rule — carrier guideline, fictional
rule_id: cat_terms.named_storm_ded_floor
version: 3
family: cat_terms
title: Named storm deductible below tier floor
effective_from: 2026-01-01
effective_to: null
applies_to: location
scope:
  lob: commercial_property
  states: [FL, TX, LA, MS, AL, GA, SC, NC]
when: >
  location.wind_tier in ['T1', 'T2'] &&
  terms.named_storm_ded_pct < tier_floor(location.wind_tier)
outcome: REFER
severity: HIGH
expected: "Named storm deductible >= 3% for Tier 1-2 wind locations"
referral_level: 3
impact_method: rarc_terms_delta   # priced via model re-run, elasticity fallback
source: "Northgate CP Guidelines 2026 §4.2.1 (fictional)"
tests:
  - name: tier1_at_2pct_refers
    fixture: { location: { wind_tier: T1 }, terms: { named_storm_ded_pct: 0.02 } }
    expect: REFER
  - name: tier1_at_3pct_passes
    fixture: { location: { wind_tier: T1 }, terms: { named_storm_ded_pct: 0.03 } }
    expect: PASS
  - name: inland_not_applicable
    fixture: { location: { wind_tier: null }, terms: { named_storm_ded_pct: 0.01 } }
    expect: NOT_APPLICABLE
""")

    def ring(lon, lat, rx, ry, n=28, wobble=0.12):
        pts = []
        for k in range(n):
            a = 2 * math.pi * k / n
            f = 1 + wobble * math.sin(3 * a) + wobble * 0.5 * math.cos(5 * a)
            pts.append([round(lon + rx * f * math.cos(a), 4), round(lat + ry * f * math.sin(a), 4)])
        pts.append(pts[0])
        return [pts]

    feats = []
    def poly(layer, tier, label, coords):
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": coords}, "properties": {"layer": layer, "tier": tier, "label": label}})
    poly("wind", "T1", "Gulf Coast — Tier 1 wind", [[[-97.5, 25.8], [-93.5, 29.3], [-89.0, 30.2], [-84.5, 29.8], [-82.8, 27.5], [-81.2, 25.0], [-80.0, 25.4], [-80.3, 27.9], [-81.4, 30.8], [-79.0, 33.3], [-76.0, 35.2], [-75.4, 35.9], [-77.2, 34.2], [-80.6, 32.1], [-81.6, 31.0], [-82.3, 28.8], [-82.6, 28.2], [-84.4, 30.3], [-89.1, 30.9], [-93.8, 30.1], [-97.4, 28.0], [-97.5, 25.8]]])
    poly("wind", "T2", "South Atlantic — Tier 2 wind", ring(-78.5, 36.5, 2.2, 1.4))
    poly("flood", "A", "Mississippi floodplain", [[[-91.3, 29.9], [-90.2, 30.5], [-90.6, 32.4], [-90.9, 34.8], [-89.8, 36.9], [-90.4, 38.6], [-91.2, 38.4], [-91.6, 36.6], [-91.9, 34.4], [-91.6, 32.2], [-91.9, 30.6], [-91.3, 29.9]]])
    poly("flood", "A", "Houston bayous", ring(-95.3, 29.8, 0.6, 0.45))
    poly("eq", "Zone 4", "San Andreas corridor", [[[-124.2, 40.4], [-121.4, 38.9], [-119.6, 36.2], [-117.0, 34.0], [-115.4, 32.6], [-116.6, 32.4], [-118.4, 33.7], [-120.8, 35.4], [-122.8, 37.4], [-124.4, 39.8], [-124.2, 40.4]]])
    poly("eq", "Zone 3", "New Madrid seismic zone", ring(-89.6, 36.4, 1.4, 1.0))
    poly("wildfire", "Very high", "Sierra foothills WUI", ring(-120.4, 38.6, 1.1, 0.9))
    poly("wildfire", "High", "Front Range WUI", ring(-105.3, 39.6, 0.8, 0.7))
    for name, lon, lat in [("Columbus plant", -82.93, 39.99), ("Reno warehouse", -119.77, 39.5), ("Houston DC", -95.26, 29.76), ("Tampa DC (new)", -82.37, 27.93)]:
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"label": name}})
    (OUT / "hazards.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))


if __name__ == "__main__":
    make_pdf()
    make_sov()
    make_eml()
    make_warehouse()
    make_campus()
    make_aerials()
    make_tables()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:28s} {p.stat().st_size:>10,d}")

"""Layout-aware PDF extraction (pdfplumber): key–value pairs and tables with
exact bounding boxes (PDF points, top-left origin) and section context."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

METHOD = "Layout extractor v1 (pdfplumber words · baseline grouping · column-aware key–value & table parsing)"


@dataclass
class KV:
    label: str
    value: str
    page: int
    bbox: tuple[float, float, float, float]
    page_size: tuple[float, float]
    section: str | None


@dataclass
class Table:
    headers: list[str]
    rows: list[list[tuple[str, tuple[float, float, float, float] | None]]]
    page: int
    page_size: tuple[float, float]
    section: str | None


@dataclass
class Extracted:
    kvs: list[KV] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    paragraphs: list[tuple[str, int, tuple, str | None]] = field(default_factory=list)  # (text, page, bbox, section)
    pages: int = 0


def _lines(words: list[dict]) -> list[list[dict]]:
    words = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    lines: list[list[dict]] = []
    for w in words:
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= 2.2:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(l, key=lambda w: w["x0"]) for l in lines]


def _bbox(ws: list[dict]) -> tuple[float, float, float, float]:
    return (round(min(w["x0"] for w in ws), 1), round(min(w["top"] for w in ws), 1), round(max(w["x1"] for w in ws), 1), round(max(w["bottom"] for w in ws), 1))


def _text(ws: list[dict]) -> str:
    return " ".join(w["text"] for w in ws)


def _is_section(line: list[dict]) -> bool:
    t = _text(line)
    return all("Bold" in w.get("fontname", "") for w in line) and 9.5 <= line[0].get("size", 0) <= 11.5 and t.upper() == t and len(t) > 3


def _groups(line: list[dict], gap: float = 7.0) -> list[list[dict]]:
    gs: list[list[dict]] = []
    for w in line:
        if gs and w["x0"] - gs[-1][-1]["x1"] <= gap:
            gs[-1].append(w)
        else:
            gs.append([w])
    return gs


def extract(path: Path, table_headers: list[list[str]] | None = None) -> Extracted:
    out = Extracted()
    table_headers = table_headers or []
    with pdfplumber.open(path) as pdf:
        out.pages = len(pdf.pages)
        section = None
        for pi, page in enumerate(pdf.pages, 1):
            psize = (float(page.width), float(page.height))
            words = [w for w in page.extract_words(extra_attrs=["size", "fontname"], keep_blank_chars=False, use_text_flow=False)
                     if w.get("size", 0) < 40 and w["top"] > 60 and w["top"] < psize[1] - 40]
            lines = _lines(words)
            i = 0
            while i < len(lines):
                line = lines[i]
                if _is_section(line):
                    section = _text(line)
                    i += 1
                    continue
                gtexts = [_text(g) for g in _groups(line)]
                matched = next((h for h in table_headers if len(h) <= len(gtexts) and all(x in gtexts for x in h[: min(3, len(h))])), None)
                if matched and all("Bold" in w.get("fontname", "") for w in line):
                    hdr_groups = _groups(line)
                    centers = [((g[0]["x0"] + g[-1]["x1"]) / 2, _text(g)) for g in hdr_groups]
                    bounds = [g[0]["x0"] for g in hdr_groups]
                    rows = []
                    j = i + 1
                    while j < len(lines) and not _is_section(lines[j]) and not all("Bold" in w.get("fontname", "") for w in lines[j]):
                        if abs(lines[j][0]["top"] - lines[j - 1][0]["top"]) > 17:
                            break
                        cells: list[list[dict]] = [[] for _ in centers]
                        for w in lines[j]:
                            # nearest column: left boundary <= word start, else nearest centre
                            idx = max((k for k, b in enumerate(bounds) if w["x0"] >= b - 4), default=0)
                            cx = (w["x0"] + w["x1"]) / 2
                            near = min(range(len(centers)), key=lambda k: abs(centers[k][0] - cx))
                            if re.match(r"^\$[\d,\.]+$|^\d{1,3}(,\d{3})+$|^[\d\.]+%$", w["text"]) and near != idx and abs(centers[near][0] - cx) < abs(centers[idx][0] - cx):
                                idx = near
                            cells[idx].append(w)
                        rows.append([(_text(c), _bbox(c) if c else None) for c in cells])
                        j += 1
                    out.tables.append(Table([c[1] for c in centers], rows, pi, psize, section))
                    i = j
                    continue
                # key-value: label groups end with ':'; the value is the following group
                gs = _groups(line, gap=7)
                emitted = False
                for n, g in enumerate(gs):
                    t = _text(g)
                    if t.endswith(":") and n + 1 < len(gs) and not _text(gs[n + 1]).endswith(":"):
                        out.kvs.append(KV(t[:-1], _text(gs[n + 1]), pi, _bbox(gs[n + 1]), psize, section))
                        emitted = True
                if not emitted and len(line) > 3:
                    out.paragraphs.append((_text(line), pi, _bbox(line), section))
                i += 1
    return out


def money(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"-?\$?\s?([\d,]+(?:\.\d+)?)", s.replace("−", "-"))
    if not m or s.strip() in ("—", "-"):
        return None
    return float(m.group(1).replace(",", ""))


def pct(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"([\d\.]+)\s?%", s)
    return float(m.group(1)) / 100 if m else None

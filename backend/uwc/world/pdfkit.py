"""Small reportlab layout kit for realistic carrier / vendor documents.

Layout conventions matter for extraction: key–value blocks render the label and
value on the same baseline; tables have a single header row.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

W, H = letter
M = 48  # margin

THEMES = {
    "carrier": {"brand": "NORTHGATE", "sub": "Specialty Insurance Co.", "color": HexColor("#12325c")},
    "engineering": {"brand": "NORTHGATE", "sub": "Risk Engineering Services", "color": HexColor("#0e6e6e")},
    "appraisal": {"brand": "CRESTVIEW", "sub": "Valuation Services LLC", "color": HexColor("#5b3a1e")},
    "alarm": {"brand": "SENTRYLINE", "sub": "Alarm & Monitoring", "color": HexColor("#7a1f2b")},
    "hood": {"brand": "CLEANVENT", "sub": "Kitchen Exhaust Services", "color": HexColor("#3d5a1f")},
    "fire": {"brand": "CITY FIRE MARSHAL", "sub": "Fire Prevention Bureau", "color": HexColor("#8a2d0a")},
    "broker": {"brand": "BROKER", "sub": "", "color": HexColor("#333333")},
}


class Pdf:
    def __init__(self, path: Path, theme: str = "carrier", doc_title: str = "", doc_ref: str = ""):
        self.path = path
        self.c = canvas.Canvas(str(path), pagesize=letter)
        self.c.setTitle(doc_title)
        self.c.setAuthor(THEMES[theme]["brand"])
        self.theme = THEMES[theme]
        self.doc_title = doc_title
        self.doc_ref = doc_ref
        self.page = 1
        self.y = H - M
        self._page_start()

    # ---------------------------------------------------------------- chrome
    def _page_start(self):
        c = self.c
        col = self.theme["color"]
        c.setFillColor(col)
        c.rect(0, H - 6, W, 6, stroke=0, fill=1)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(M, H - 34, self.theme["brand"])
        c.setFont("Helvetica", 8.5)
        c.setFillColor(HexColor("#555555"))
        c.drawString(M, H - 46, self.theme["sub"])
        c.setFont("Helvetica", 8)
        c.drawRightString(W - M, H - 34, self.doc_title)
        if self.doc_ref:
            c.drawRightString(W - M, H - 46, self.doc_ref)
        c.setStrokeColor(HexColor("#d8dce3"))
        c.line(M, H - 56, W - M, H - 56)
        # watermark
        c.saveState()
        c.setFillColor(Color(0.85, 0.2, 0.2, alpha=0.07))
        c.setFont("Helvetica-Bold", 90)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "SAMPLE")
        c.restoreState()
        self.y = H - 80

    def _page_end(self):
        c = self.c
        c.setFont("Helvetica", 7.5)
        c.setFillColor(HexColor("#888888"))
        c.drawString(M, 28, "Fictional demo document · Anaira Underwriting Control showcase · not a real policy or record")
        c.drawRightString(W - M, 28, f"Page {self.page}")

    def new_page(self):
        self._page_end()
        self.c.showPage()
        self.page += 1
        self._page_start()

    def need(self, h: float):
        if self.y - h < 60:
            self.new_page()

    def save(self):
        self._page_end()
        self.c.save()

    # ---------------------------------------------------------------- blocks
    def title(self, text: str, sub: str | None = None):
        self.need(40)
        self.c.setFillColor(HexColor("#111111"))
        self.c.setFont("Helvetica-Bold", 16)
        self.c.drawString(M, self.y, text)
        self.y -= 18
        if sub:
            self.c.setFont("Helvetica", 9.5)
            self.c.setFillColor(HexColor("#555555"))
            self.c.drawString(M, self.y, sub)
            self.y -= 14
        self.y -= 6

    def section(self, text: str):
        self.need(34)
        self.y -= 6
        self.c.setFillColor(self.theme["color"])
        self.c.setFont("Helvetica-Bold", 10.5)
        self.c.drawString(M, self.y, text.upper())
        self.y -= 5
        self.c.setStrokeColor(HexColor("#d8dce3"))
        self.c.line(M, self.y, W - M, self.y)
        self.y -= 14

    def kv(self, pairs: Sequence[tuple[str, str]], cols: int = 2, label_w: float = 128):
        colw = (W - 2 * M) / cols
        rows = (len(pairs) + cols - 1) // cols
        self.need(rows * 14 + 4)
        for i, (k, v) in enumerate(pairs):
            r, ci = divmod(i, cols)
            x = M + ci * colw
            y = self.y - r * 14
            self.c.setFont("Helvetica", 8.5)
            self.c.setFillColor(HexColor("#666666"))
            self.c.drawString(x, y, f"{k}:")
            self.c.setFont("Helvetica-Bold", 9)
            self.c.setFillColor(HexColor("#111111"))
            self.c.drawString(x + label_w, y, str(v))
        self.y -= rows * 14 + 6

    def para(self, text: str, size: float = 9, color: str = "#222222", leading: float = 12.5):
        from reportlab.lib.utils import simpleSplit
        for block in text.split("\n"):
            lines = simpleSplit(block, "Helvetica", size, W - 2 * M) or [""]
            for ln in lines:
                self.need(leading)
                self.c.setFont("Helvetica", size)
                self.c.setFillColor(HexColor(color))
                self.c.drawString(M, self.y, ln)
                self.y -= leading
        self.y -= 4

    def table(self, headers: Sequence[str], rows: Iterable[Sequence[str]], widths: Sequence[float] | None = None,
              size: float = 7.8, align_right: set[int] | None = None, zebra: bool = True):
        widths = list(widths or [(W - 2 * M) / len(headers)] * len(headers))
        scale = (W - 2 * M) / sum(widths)
        widths = [w * scale for w in widths]
        align_right = align_right or set()
        rh = size + 6.5

        def header():
            self.need(rh * 2)
            self.c.setFillColor(HexColor("#eef1f5"))
            self.c.rect(M, self.y - 4, W - 2 * M, rh, stroke=0, fill=1)
            self.c.setFont("Helvetica-Bold", size)
            self.c.setFillColor(HexColor("#333333"))
            x = M
            for i, h in enumerate(headers):
                if i in align_right:
                    self.c.drawRightString(x + widths[i] - 4, self.y, h)
                else:
                    self.c.drawString(x + 3, self.y, h)
                x += widths[i]
            self.y -= rh

        header()
        for ri, row in enumerate(rows):
            if self.y - rh < 60:
                self.new_page()
                header()
            if zebra and ri % 2 == 1:
                self.c.setFillColor(HexColor("#f8f9fb"))
                self.c.rect(M, self.y - 4, W - 2 * M, rh, stroke=0, fill=1)
            self.c.setFont("Helvetica", size)
            self.c.setFillColor(HexColor("#111111"))
            x = M
            for i, cell in enumerate(row):
                txt = str(cell)
                maxc = int(widths[i] / (size * 0.5))
                if len(txt) > maxc:
                    txt = txt[: maxc - 1] + "…"
                if i in align_right:
                    self.c.drawRightString(x + widths[i] - 4, self.y, txt)
                else:
                    self.c.drawString(x + 3, self.y, txt)
                x += widths[i]
            self.y -= rh
        self.y -= 8

    def signature(self, name: str, title: str, date: str):
        self.need(50)
        self.y -= 10
        self.c.setStrokeColor(HexColor("#999999"))
        self.c.line(M, self.y, M + 180, self.y)
        self.y -= 12
        self.c.setFont("Helvetica", 8.5)
        self.c.setFillColor(HexColor("#333333"))
        self.c.drawString(M, self.y, f"{name} · {title} · {date}")
        self.y -= 16

    def image(self, path: Path, w: float, h: float, caption: str | None = None):
        self.need(h + 20)
        self.c.drawImage(str(path), M, self.y - h, width=w, height=h)
        self.y -= h + 4
        if caption:
            self.c.setFont("Helvetica-Oblique", 7.5)
            self.c.setFillColor(HexColor("#666666"))
            self.c.drawString(M, self.y - 6, caption)
            self.y -= 14


def money(x: float | None) -> str:
    if x is None:
        return "—"
    return f"${x:,.0f}"


def pctf(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.1f}%".replace(".0%", "%")

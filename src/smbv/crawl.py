"""Fetch each linked business's own website (URL from OpenStreetMap). Respects robots.txt; incremental."""
from __future__ import annotations
import asyncio
import concurrent.futures as cf
import html
import re
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import pandas as pd
import requests
from smbv.config import load
from smbv.db import connect, raw

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 smbv-research"
COLUMNS = ["business_id", "url", "final_url", "menu_url", "status", "method", "words", "text", "fetched_at", "note"]


def _text(page_html: str) -> str:
    t = re.sub(r"(?s)<(script|style|noscript)[^>]*>.*?</\1>", " ", page_html)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def _allowed(url: str) -> bool:
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = requests.get(urljoin(url, "/robots.txt"), headers={"User-Agent": UA}, timeout=8)
        if r.status_code >= 400:
            return True
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, url)
    except requests.RequestException:
        return True


def fetch(business_id: str, url: str) -> dict:
    url = url if url.startswith("http") else "http://" + url
    row = dict.fromkeys(COLUMNS)
    row.update(business_id=business_id, url=url, method="http", fetched_at=datetime.now(timezone.utc).isoformat(), words=0)
    if not _allowed(url):
        row.update(note="disallowed by robots.txt")
        return row
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        row.update(status=r.status_code, final_url=r.url)
        text = _text(r.text)
        m = re.search(r'href="([^"#]*menu[^"#]*)"', r.text, re.I)
        if m:
            menu = urljoin(r.url, m.group(1))
            if urlparse(menu).netloc == urlparse(r.url).netloc and _allowed(menu):
                mr = requests.get(menu, headers={"User-Agent": UA}, timeout=15)
                text += "\n[MENU PAGE] " + _text(mr.text)
                row["menu_url"] = menu
        row.update(text=text[:80000], words=len(text.split()))
    except requests.RequestException as e:
        row.update(note=type(e).__name__)
    return row


async def _render(rows: list[dict]) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(user_agent=UA)
        sem = asyncio.Semaphore(6)

        async def one(row):
            async with sem:
                page = await ctx.new_page()
                try:
                    resp = await page.goto(row["url"], timeout=25000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2500)
                    text = await page.inner_text("body")
                    links = await page.eval_on_selector_all("a", "els => els.map(e => e.href).filter(h => /menu/i.test(h))")
                    same = [h for h in links if urlparse(h).netloc == urlparse(page.url).netloc][:1]
                    if same:
                        await page.goto(same[0], timeout=20000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(2000)
                        text += "\n[MENU PAGE] " + await page.inner_text("body")
                        row["menu_url"] = same[0]
                    text = " ".join(text.split())
                    if len(text.split()) > (row["words"] or 0):
                        row.update(text=text[:80000], words=len(text.split()), method="headless",
                                   status=resp.status if resp else row["status"], final_url=page.url)
                except Exception as e:
                    row["note"] = (row["note"] or "") + f" headless:{type(e).__name__}"
                finally:
                    await page.close()
        await asyncio.gather(*(one(r) for r in rows))
        await browser.close()


def run() -> None:
    cfg, con = load()["crawl"], connect()
    con.execute("CREATE TABLE IF NOT EXISTS web_pages (" + ", ".join(
        f"{c} {'INTEGER' if c in ('status', 'words') else 'VARCHAR'}" for c in COLUMNS) + ")")
    osm = pd.read_parquet(raw("osm"))[["osm_id", "website", "contact_website"]]
    osm["site"] = osm.website.fillna(osm.contact_website)
    todo = con.execute("SELECT l.business_id, l.source_key AS osm_id FROM links l WHERE l.source='osm' "
                       "AND l.business_id NOT IN (SELECT business_id FROM web_pages) ORDER BY hash(l.business_id)").df()
    todo = todo.merge(osm, on="osm_id").dropna(subset=["site"])
    if cfg["max_sites"]:
        done = con.execute("SELECT count(*) FROM web_pages").fetchone()[0]
        todo = todo.head(max(cfg["max_sites"] - done, 0))
    print(f"[crawl] fetching {len(todo):,} websites")
    with cf.ThreadPoolExecutor(cfg["workers"]) as ex:
        rows = list(ex.map(fetch, todo.business_id, todo.site))
    thin = [r for r in rows if (r["words"] or 0) < cfg["min_words"] and r["note"] != "disallowed by robots.txt"]
    if cfg["headless_fallback"] and thin:
        print(f"[crawl] rendering {len(thin):,} thin or failed sites with headless Chromium")
        asyncio.run(_render(thin))
    df = pd.DataFrame(rows, columns=COLUMNS)
    if len(df):
        con.execute("INSERT INTO web_pages SELECT * FROM df")
    s = con.execute(f"SELECT count(*), avg((words >= {cfg['min_words']})::INT), avg((method='headless')::INT) FROM web_pages").fetchone()
    print(f"[crawl] pages stored: {s[0]:,} | with {cfg['min_words']}+ words: {s[1]:.0%} | rendered headless: {s[2]:.0%}")
    con.close()

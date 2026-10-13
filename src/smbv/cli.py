from __future__ import annotations
import argparse


def main() -> None:
    p = argparse.ArgumentParser(prog="smbv", description="Small-business risk verification pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest", help="download real source data"); s.add_argument("--only", nargs="*")
    sub.add_parser("link", help="resolve businesses across sources")
    sub.add_parser("corps", help="look up legal entities in the NY company register")
    sub.add_parser("crawl", help="fetch business websites")
    sub.add_parser("extract", help="LLM fact extraction from website text")
    sub.add_parser("ledger", help="build observations and resolve facts")
    sub.add_parser("evaluate", help="write reports/evaluation.md")
    sub.add_parser("all", help="run every stage in order")
    s = sub.add_parser("serve", help="demo app"); s.add_argument("--port", type=int, default=8800)
    a = p.parse_args()
    from smbv import ingest, link, corps, crawl, extract, ledger, evaluate
    stages = {"ingest": lambda: ingest.run(getattr(a, "only", None)), "link": link.run, "corps": corps.run,
              "crawl": crawl.run, "extract": extract.run, "ledger": ledger.run, "evaluate": evaluate.run}
    if a.cmd == "all":
        for name in ["ingest", "link", "corps", "crawl", "extract", "ledger", "evaluate"]:
            stages[name]()
    elif a.cmd == "serve":
        import uvicorn
        uvicorn.run("smbv.web.app:app", host="0.0.0.0", port=a.port)
    else:
        stages[a.cmd]()


if __name__ == "__main__":
    main()

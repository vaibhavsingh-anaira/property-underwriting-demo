from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
BOROUGHS = {  # one borough, every spelling the source datasets use
    "MANHATTAN": {"title": "Manhattan", "upper": "MANHATTAN", "abbr": "MN", "num": "1", "county": "New York"},
    "BROOKLYN": {"title": "Brooklyn", "upper": "BROOKLYN", "abbr": "BK", "num": "3", "county": "Kings"},
    "QUEENS": {"title": "Queens", "upper": "QUEENS", "abbr": "QN", "num": "4", "county": "Queens"},
    "BRONX": {"title": "Bronx", "upper": "BRONX", "abbr": "BX", "num": "2", "county": "Bronx"},
    "STATEN ISLAND": {"title": "Staten Island", "upper": "STATEN IS", "abbr": "SI", "num": "5", "county": "Richmond"},
}


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@lru_cache
def load() -> dict:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    local = Path(os.environ.get("SMBV_CONFIG", ROOT / "config.local.yaml"))  # override file (e.g. a test run)
    if local.exists():
        cfg = _merge(cfg, yaml.safe_load(local.read_text()))
    cfg["data_path"] = (ROOT / cfg["data_dir"]).resolve()
    (cfg["data_path"] / "raw").mkdir(parents=True, exist_ok=True)
    return cfg


def scope_values(key: str) -> list[str]:
    return [BOROUGHS[b][key] for b in load()["scope"]["boroughs"]]


def sql_list(values: list[str]) -> str:
    return ",".join("'" + v.replace("'", "''") + "'" for v in values)


def socrata_token() -> str | None:
    return os.environ.get(load()["socrata"]["app_token_env"])

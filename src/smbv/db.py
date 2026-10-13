from __future__ import annotations
import duckdb
from smbv.config import load


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(load()["data_path"] / "smbv.duckdb"), read_only=read_only)


def raw(name: str) -> str:
    return str(load()["data_path"] / "raw" / f"{name}.parquet")

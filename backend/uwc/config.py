import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
WORLD_DIR = DATA_DIR / "world"          # generated, immutable evidence
DOCS_DIR = WORLD_DIR / "docs"
RUNTIME_DIR = Path(os.environ["UWC_RUNTIME_DIR"]) if os.environ.get("UWC_RUNTIME_DIR") else DATA_DIR / "runtime"  # files produced while the demo runs; override for isolated test runs
LEDGER_DB = RUNTIME_DIR / "ledger.sqlite"
RULES_DIR = Path(__file__).resolve().parent / "rules"

DEMO_START = date(2026, 8, 1)
DEMO_END = date(2027, 2, 28)
CARRIER = "Northgate Specialty Insurance Co."
SEED = 20260801

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


def resolve_doc_path(doc: dict) -> Path:
    """Resolve a document record to a file on disk, always relative to this checkout.

    World docs carry `path` relative to WORLD_DIR. Runtime-generated docs carry `rel_path`
    relative to RUNTIME_DIR — never an absolute path, so persisted state (the pickle/sqlite
    snapshot) stays portable across machines and checkout locations. `abs_path` remains only
    for ephemeral, request-scoped docs (e.g. a sandbox upload) that are never persisted.
    """
    if "rel_path" in doc:
        return RUNTIME_DIR / doc["rel_path"]
    if doc.get("abs_path"):
        return Path(doc["abs_path"])
    return WORLD_DIR / doc["path"]

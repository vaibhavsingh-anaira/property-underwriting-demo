"""Product registry. One shared core (evidence ledger, extraction, rule engine, authority, demo runtime),
three products on top of it. Each product module implements the same interface so the pipeline,
stage workspaces, playbooks, player, briefs and mocks console work identically for all of them.

Product module interface (module-level names):

    ID: str                          "renewal" | "decision" | "delegated"
    META: dict                       {id, name, short, tagline, description, subject_label}
    PIPE: list[tuple]                (code, name, group, component, mode REAL|MOCK, description, port|None)
    GROUPS: list[str]                pipeline column headings, in order
    REAL_CORE / MOCK_CORE: list[str] default "real vs stand-in" lines for briefs
    router: fastapi.APIRouter | None product-specific endpoints (handlers import RT, LOCK from uwc.api lazily)

    init(rt)                         create empty state on rt (called from Runtime._fresh; must be picklable)
    build_world(rt)                  populate state as of the demo start (called once per reset, after the
                                     renewal world has advanced to DEMO_START, before the snapshot is saved)
    on_day(rt, ds)                   daily hook while the clock advances (no-op until build_world has run)
    handle_event(rt, e)              dynamic events whose type starts with f"{ID}."
    pipeline_counts(rt) -> {code: [(label, value)]}
    subjects(rt) -> [{id, label}]    what the stage workspace can be loaded with (accounts, cases, coverholders)
    build_stage(rt, code, subject) -> StageView dict (same shape as uwc.stages.build)
    run_stage(rt, code, subject) -> str
    playbooks(rt) -> [playbook]      each: {id, product, account_id, account_name, scenario, title, aspects,
                                     intro, outro, brief, steps: [{code, label, action, say, params}]}
    run_step(rt, playbook, step) -> str
    facts(rt, subject) -> [{label, value}]   live engine figures for the brief panel
    mocks(rt) -> [{port, name, stands_in_for, status, records, last_sync}]
    rule_fired(rt, rule_id) -> int
    reevaluate_all(rt)               after a rule is published
    backtest(rt, old_rule, new_rule) -> {control_set, accounts, before, after, added, removed}
"""
from __future__ import annotations

import importlib
import os

from uwc.products import renewal

MODULES: dict = {"renewal": renewal}
# UWC_PRODUCTS="renewal,decision" limits which products load (isolated development / tests)
_enabled = [x.strip() for x in os.environ.get("UWC_PRODUCTS", "decision,delegated").split(",")]
for _name in [n for n in ("decision", "delegated") if n in _enabled]:
    try:
        MODULES[_name] = importlib.import_module(f"uwc.products.{_name}")
    except ModuleNotFoundError as _e:  # product not installed yet
        if _e.name != f"uwc.products.{_name}":
            raise


def get(pid: str | None):
    return MODULES.get(pid or "renewal") or MODULES["renewal"]


def metas() -> list[dict]:
    return [m.META for m in MODULES.values()]


def all_playbooks(rt) -> list[dict]:
    out = []
    for m in MODULES.values():
        for p in m.playbooks(rt):
            out.append({**p, "product": m.ID})
    return out


def find_playbook(rt, pid: str) -> dict:
    for p in all_playbooks(rt):
        if p["id"] == pid:
            return p
    raise KeyError(pid)

"""Rule engine: versioned YAML rules with CEL-style `when` expressions.

Expressions are compiled to a restricted Python AST (whitelisted node types,
no private attributes, only whitelisted functions) and evaluated against
read-only context objects. Missing data never raises: comparisons involving
null make the rule NOT_APPLICABLE (and the completeness rules catch the gap).
"""
from __future__ import annotations

import ast
import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from uwc.config import RULES_DIR


class Ctx:
    """Attribute access over dicts; missing → None."""
    __slots__ = ("_d",)

    def __init__(self, d: dict | None):
        object.__setattr__(self, "_d", d or {})

    def __getattr__(self, k: str):
        v = self._d.get(k)
        return Ctx(v) if isinstance(v, dict) else v


class NA(Exception):
    pass


def _cmp_guard(op, a, b):
    if a is None or b is None:
        raise NA()
    return op(a, b)


FUNCS = {
    "has": lambda x: x is not None and x != [] and x != "",
    "size": lambda x: len(x) if x is not None else 0,
    "abs": abs, "min": min, "max": max,
    "coalesce": lambda *xs: next((x for x in xs if x is not None), None),
}
ALLOWED = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
           ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Name, ast.Load,
           ast.Attribute, ast.Constant, ast.List, ast.Tuple, ast.Call, ast.IfExp, ast.Subscript)


def cel_to_py(expr: str) -> str:
    s = expr.replace("&&", " and ").replace("||", " or ")
    s = re.sub(r"!(?!=)", " not ", s)
    s = re.sub(r"\btrue\b", "True", s)
    s = re.sub(r"\bfalse\b", "False", s)
    s = re.sub(r"\bnull\b", "None", s)
    return s.strip()


class _Guard(ast.NodeTransformer):
    """Rewrite ordered comparisons to go through _cmp_guard (null-safe)."""
    OPS = {ast.Lt: "lt", ast.LtE: "le", ast.Gt: "gt", ast.GtE: "ge"}

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in self.OPS:
            op = self.OPS[type(node.ops[0])]
            return ast.Call(func=ast.Name(id="_cmp", ctx=ast.Load()),
                            args=[ast.Attribute(value=ast.Name(id="_op", ctx=ast.Load()), attr=op, ctx=ast.Load()), node.left, node.comparators[0]], keywords=[])
        return node


def compile_expr(expr: str):
    tree = ast.parse(cel_to_py(expr), mode="eval")
    for n in ast.walk(tree):
        if not isinstance(n, ALLOWED):
            raise ValueError(f"Disallowed syntax: {type(n).__name__}")
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            raise ValueError("Private attributes are not allowed")
        if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in FUNCS):
            raise ValueError("Only whitelisted functions: " + ", ".join(FUNCS))
    tree = ast.fix_missing_locations(_Guard().visit(tree))
    return compile(tree, "<rule>", "eval")


import operator as _operator


def evaluate(code, env: dict[str, Any]) -> bool | None:
    ns = {"__builtins__": {}, "_cmp": _cmp_guard, "_op": _operator, **FUNCS}
    ns.update({k: (Ctx(v) if isinstance(v, dict) else v) for k, v in env.items()})
    try:
        return bool(eval(code, ns))
    except NA:
        return None
    except (TypeError, AttributeError, ZeroDivisionError):
        return None


@dataclass
class Rule:
    rule_id: str
    version: int
    family: str
    title: str
    applies_to: str
    when: str
    outcome: str
    severity: str
    expected: str
    observed: str
    effective_from: str
    effective_to: str | None = None
    referral_level: int | None = None
    impact: str = "none"
    source: str = ""
    origin: str = "standard_library"
    scope: dict = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    action: str | None = None
    tests: list[dict] = field(default_factory=list)
    description: str = ""
    passes: list[int] = field(default_factory=lambda: [1, 2, 3])
    product: str = "renewal"   # renewal | decision | delegated — which product's engine evaluates it
    code: Any = None
    yaml_text: str = ""

    def active(self, d: str) -> bool:
        return self.effective_from <= d and (self.effective_to is None or d <= self.effective_to)


RULE_KEYS = {"id", "version", "family", "title", "applies_to", "when", "outcome", "severity", "expected", "observed", "effective_from",
             "effective_to", "referral_level", "impact", "source", "origin", "scope", "evidence", "action", "tests", "description", "passes", "product"}


def rule_from_dict(d: dict, text: str | None = None) -> Rule:
    unknown = set(d) - RULE_KEYS
    if unknown:
        raise ValueError(f"Unknown keys: {', '.join(sorted(unknown))}")
    r = Rule(rule_id=d["id"], version=int(d.get("version", 1)), family=d["family"], title=d["title"], applies_to=d["applies_to"], when=d["when"],
             outcome=d["outcome"], severity=d["severity"], expected=d.get("expected", ""), observed=d.get("observed", ""),
             effective_from=str(d.get("effective_from", "2020-01-01")), effective_to=(str(d["effective_to"]) if d.get("effective_to") else None),
             referral_level=d.get("referral_level"), impact=d.get("impact", "none"), source=d.get("source", ""), origin=d.get("origin", "standard_library"),
             scope=d.get("scope", {}) or {}, evidence=d.get("evidence", []) or [], action=d.get("action"), tests=d.get("tests", []) or [],
             description=d.get("description", ""), passes=d.get("passes", [1, 2, 3]), product=d.get("product", "renewal"))
    r.code = compile_expr(r.when)
    r.yaml_text = text if text is not None else yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120)
    return r


def load_rules() -> dict[str, Rule]:
    """Renewal rules from uwc/rules/, plus each enabled product's rules from uwc/products/<id>/rules/."""
    import os
    out: dict[str, Rule] = {}
    enabled = [x.strip() for x in os.environ.get("UWC_PRODUCTS", "decision,delegated").split(",")]
    files = sorted(Path(RULES_DIR).glob("*.yaml"))
    for pid in ("decision", "delegated"):
        if pid in enabled:
            files += sorted((Path(RULES_DIR).parent / "products" / pid / "rules").glob("*.yaml"))
    for p in files:
        docs = yaml.safe_load(p.read_text())
        for d in docs:
            text = yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120)
            r = rule_from_dict(d, text)
            out[r.rule_id] = r
    return out


def run_tests(r: Rule) -> list[dict]:
    res = []
    for t in r.tests:
        env = copy.deepcopy(t.get("fixture", {}))
        try:
            v = evaluate(r.code, env)
            actual = "NOT_APPLICABLE" if v is None else (r.outcome if v else "PASS")
            res.append({"name": t.get("name", "test"), "expected": t["expect"], "actual": actual, "pass": actual == t["expect"], "error": None})
        except Exception as e:  # noqa: BLE001
            res.append({"name": t.get("name", "test"), "expected": t["expect"], "actual": "ERROR", "pass": False, "error": str(e)})
    return res


def fmt(template: str, env: dict) -> str:
    """Render {expr} placeholders in observed/expected text."""
    def rep(m):
        expr = m.group(1)
        fn = None
        if expr.startswith(("usd(", "pct(", "num(")):
            fn, expr = expr[:3], expr[4:-1]
        code = compile_expr(expr)
        ns = {"__builtins__": {}, "_cmp": _cmp_guard, "_op": _operator, **FUNCS}
        ns.update({k: (Ctx(v) if isinstance(v, dict) else v) for k, v in env.items()})
        try:
            v = eval(code, ns)
        except Exception:  # noqa: BLE001
            return "—"
        if v is None:
            return "—"
        if fn == "usd":
            return f"${v:,.0f}"
        if fn == "pct":
            return f"{v * 100:.1f}%".replace(".0%", "%")
        if fn == "num":
            return f"{v:,.0f}"
        if isinstance(v, Ctx):
            return "—"
        return str(v)
    return re.sub(r"\{([^{}]+)\}", rep, template)

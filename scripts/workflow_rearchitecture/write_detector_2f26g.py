"""Slice 2F-26G — AST-based model-field write detection (D-08 repair).

Slice 2F-26F used a regex that included `\\.is_active\\s*=`. That pattern also
matches the equality operator in `Model.is_active == True` inside a SELECT
predicate, so a pure read was reported as a mutation.

This module walks the AST and recognises only genuine mutations. Equality and
comparison operators (`==`, `!=`, `<=`, `>=`, `is`, `in`) are never
assignments in the grammar, so they cannot be confused for one.

A regex fallback is retained ONLY for source that cannot be parsed (e.g.
dynamically generated). It is explicitly LOWER confidence, excludes every
comparison operator, and — per WS10 — cannot independently justify canonical
mutation inclusion.
"""
from __future__ import annotations

import ast
import inspect
import re

# ── Persisting call names ───────────────────────────────────────────────────
_PERSIST_CALLS = {"add", "delete", "add_all", "merge", "commit", "flush"}
_MODEL_FIELD_HINT = re.compile(
    r"(status|is_active|is_enabled|deleted_at|archived_at|state|is_deleted|"
    r"counter|updated_at|revoked_at|cancelled_at|balance|amount|quantity)$")

# Lower-confidence fallback: assignment `=` NOT followed by another `=`, and
# NOT preceded by a comparison operator. Explicitly excludes == != <= >= :=
_ASSIGN_FALLBACK = re.compile(
    r"(?<![=!<>:])=(?!=)")


def _dedent(s):
    ls = s.splitlines()
    if not ls:
        return s
    i = len(ls[0]) - len(ls[0].lstrip())
    return "\n".join(l[i:] if len(l) >= i else l for l in ls)


def _target_str(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "?"


def ast_writes(fn_or_src):
    """List of write-evidence records found in the AST.

    Each record: {node_type, target, field, qualified, persistence, branch}.
    Only real mutations are returned; comparisons never appear.
    """
    if isinstance(fn_or_src, str):
        src = fn_or_src
        qual = "<src>"
    else:
        try:
            src = inspect.getsource(fn_or_src)
        except Exception:
            return []
        qual = getattr(fn_or_src, "__qualname__", getattr(fn_or_src, "__name__", "?"))
    try:
        tree = ast.parse(_dedent(src))
    except SyntaxError:
        return _regex_fallback(src, qual)

    out = []

    def branch_of(node):
        return getattr(node, "_branch", "")

    for node in ast.walk(tree):
        # Assign / AnnAssign / AugAssign onto an attribute (model field)
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
            kind = "Assign"
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            kind = "AnnAssign"
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
            kind = "AugAssign"
        else:
            targets = []
            kind = None
        for t in targets:
            if isinstance(t, ast.Attribute):
                out.append({"node_type": kind, "target": _target_str(t),
                            "field": t.attr, "qualified": qual,
                            "persistence": "attribute assignment", "branch": ""})
            elif isinstance(t, ast.Subscript):
                # dict/collection item -- only a model write if the object is a
                # mapped collection; recorded but low weight (not a field set on
                # a model instance). Skipped to avoid serialized[...] = x reads.
                pass

        if isinstance(node, ast.Call):
            f = node.func
            # setattr(model, "field", value)
            if isinstance(f, ast.Name) and f.id == "setattr" and len(node.args) >= 2:
                fld = node.args[1]
                fldname = fld.value if isinstance(fld, ast.Constant) else "?"
                out.append({"node_type": "setattr", "target": _target_str(node.args[0]),
                            "field": fldname, "qualified": qual,
                            "persistence": "setattr", "branch": ""})
            # db.add / db.delete / session.flush / .values(...)  etc.
            if isinstance(f, ast.Attribute):
                if f.attr in _PERSIST_CALLS:
                    out.append({"node_type": "Call", "target": _target_str(f),
                                "field": "", "qualified": qual,
                                "persistence": f".{f.attr}()", "branch": ""})
                if f.attr == "values":  # update(Model).values(is_active=False)
                    kws = [k.arg for k in node.keywords if k.arg]
                    if kws:
                        out.append({"node_type": "Call", "target": "update().values",
                                    "field": "|".join(kws), "qualified": qual,
                                    "persistence": "SQLAlchemy update().values()",
                                    "branch": ""})
                if f.attr in ("update", "delete") and isinstance(f.value, ast.Call):
                    out.append({"node_type": "Call", "target": _target_str(f),
                                "field": "", "qualified": qual,
                                "persistence": f"ORM bulk .{f.attr}()", "branch": ""})
    return out


def _regex_fallback(src, qual):
    """Lower-confidence: only when the AST cannot be built."""
    hits = []
    for i, line in enumerate(src.splitlines(), 1):
        code = line.split("#", 1)[0]
        # must be an attribute assignment, never a comparison
        if re.search(r"\.\w+\s*" + _ASSIGN_FALLBACK.pattern, code) and "==" not in code:
            hits.append({"node_type": "regex_fallback", "target": code.strip()[:60],
                         "field": "", "qualified": qual,
                         "persistence": "REGEX_FALLBACK_LOW_CONFIDENCE", "branch": ""})
    return hits


def writes_model(fn_or_src):
    """True iff a genuine mutation is present. Comparisons excluded by grammar."""
    return bool(ast_writes(fn_or_src))


def confidence(fn_or_src):
    ws = ast_writes(fn_or_src)
    if not ws:
        return "NONE"
    if all(w["node_type"] == "regex_fallback" for w in ws):
        return "LOW_REGEX_FALLBACK"
    return "HIGH_AST"


if __name__ == "__main__":
    POS = ["model.is_active = False", "setattr(model, 'is_active', False)",
           "update(Model).values(is_active=False)", "model.counter += 1",
           "db.delete(model)"]
    NEG = ["x = Model.is_active == True", "if Model.is_active != False: pass",
           "q = query.where(Model.is_active == True)", "r = model.is_active",
           "serialized['is_active'] = model.is_active",
           "y = a <= b", "z = (n := compute())"]
    print("POSITIVE (expect write):")
    for s in POS:
        print(f"  {writes_model(s)!s:6} {s}")
    print("NEGATIVE (expect no write):")
    for s in NEG:
        print(f"  {writes_model(s)!s:6} {s}")

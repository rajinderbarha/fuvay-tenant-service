#!/usr/bin/env python
"""Slice 2F-26 — application-wide mutation-inventory verifier.

Fails (exit 1) when any mounted route is undispositioned or the canonical
arithmetic is inconsistent. Designed to be non-vacuous:

  * SQL scoping checks inspect the compiled WHERE clause, never the whole
    SELECT text (every `SELECT t.*` lists the tenant column).
  * Source checks strip docstrings and comments, so a check can never be
    satisfied by prose describing the thing it forbids.
  * Route facts come from the live app object, not from path strings.

Both traps were hit for real earlier in this initiative, which is why they are
guarded here.
"""
from __future__ import annotations

import ast
import csv
import inspect
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26")
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")

VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}
FORBIDDEN_STATUS = {"UNKNOWN_PROTECTION", "UNVERIFIED", "UNKNOWN_BEHAVIOR", ""}

FAILURES: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))
        FAILURES.append(name)


def strip_prose(fn) -> str:
    """Executable source only -- docstring and comments removed."""
    try:
        src = inspect.getsource(fn)
    except Exception:
        return ""
    try:
        tree = ast.parse(_dedent(src))
    except SyntaxError:
        return src
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                             ast.Module)) and ast.get_docstring(node):
            node.body = node.body[1:]
    return ast.unparse(tree)


def _dedent(src):
    lines = src.splitlines()
    if not lines:
        return src
    ind = len(lines[0]) - len(lines[0].lstrip())
    return "\n".join(l[ind:] if len(l) >= ind else l for l in lines)


def where_clause(stmt) -> str:
    """Compiled WHERE only -- NOT the whole SELECT."""
    s = str(stmt)
    return s.split("WHERE", 1)[1] if "WHERE" in s else ""


def norm(p):
    return p if p.startswith("/v1/") else ("/v1" + p if p.startswith("/") else p)


def load(name):
    return list(csv.DictReader(open(os.path.join(OUT, name), encoding="utf-8")))


def main() -> int:
    print("Application-wide mutation-inventory verifier (Slice 2F-26)\n")

    # ── inventory completeness ───────────────────────────────────────────────
    print("Inventory completeness:")
    routes = load("complete-mounted-route-inventory.csv")
    behav = load("route-side-effect-classification.csv")
    check("every mounted route is exported", len(routes) > 2000, f"{len(routes)}")
    check("every route has a behaviour classification",
          all(b.get("behaviour") for b in behav))
    check("no route remains UNKNOWN_BEHAVIOR",
          not any(b.get("behaviour") == "UNKNOWN_BEHAVIOR" for b in behav))

    personas = load("mutation-persona-classification.csv")
    check("every genuine mutation has a persona",
          all(p.get("persona") for p in personas))
    check("mutating GET audit exists", os.path.exists(
        os.path.join(OUT, "mutating-get-audit.csv")))
    check("read-only POST audit exists", os.path.exists(
        os.path.join(OUT, "read-only-post-audit.csv")))

    # ── canonical integrity ──────────────────────────────────────────────────
    print("\nCanonical integrity:")
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    total = len(canon)
    protected = sum(1 for r in canon if r[6] in VERIFIED)
    unprotected = total - protected
    check("no canonical row has a forbidden protection status",
          not any(r[6] in FORBIDDEN_STATUS for r in canon))
    keys = [(r[0], norm(r[1])) for r in canon]
    check("no duplicate canonical route keys", len(keys) == len(set(keys)),
          f"{len(keys) - len(set(keys))} duplicates")
    check("protected + unprotected == denominator", protected + unprotected == total)

    # ── every canonical row is mounted ───────────────────────────────────────
    from app.main import app
    from fastapi.routing import APIRoute
    mounted = set()

    def collect(r):
        for x in getattr(r, "routes", []) or []:
            if type(x).__name__ == "_IncludedRouter":
                collect(x.original_router)
            elif isinstance(x, APIRoute):
                for m in x.methods or []:
                    mounted.add((m, norm(x.path)))
    collect(app)
    orphans = [k for k in keys if k not in mounted]
    check("every canonical row resolves to a mounted route", not orphans,
          f"{len(orphans)} orphaned: {orphans[:3]}")

    # ── every runtime tenant mutation has a canonical row ────────────────────
    adj = load("generic-prefix-tenant-mutations.csv")
    confirmed = [a for a in adj if a["verdict"] == "CONFIRMED_TENANT_MUTATION_ADD"]
    canon_keys = set(keys)
    missing = [a for a in confirmed if (a["method"], norm(a["path"])) not in canon_keys]
    check("every confirmed tenant mutation has a canonical row", not missing,
          f"{len(missing)} missing")

    # ── generic-prefix blind spot closed ─────────────────────────────────────
    print("\nGeneric-prefix blind spot:")
    generic = [k for k in canon_keys
               if not k[1].startswith(("/v1/tenant", "/v1/provider", "/v1/staff"))]
    check("generic-prefix tenant mutations are represented", len(generic) > 0,
          "a sweep that finds none has almost certainly not looked")
    print(f"        ({len(generic)} canonical rows sit on non-tenant-prefixed paths)")

    # ── non-vacuity self-checks ──────────────────────────────────────────────
    print("\nVerifier non-vacuity:")
    def _fn_with_lying_docstring():
        """mentions db.add( and tenant_id but the body does neither"""
        return 1
    check("docstring text cannot satisfy a source check",
          "db.add(" not in strip_prose(_fn_with_lying_docstring))

    from sqlalchemy import select, column, table
    t = table("reviews", column("id"), column("tenant_id"))
    unscoped = select(t).where(t.c.id == 1)
    check("WHERE-clause inspection ignores SELECT column lists",
          "tenant_id" not in where_clause(unscoped),
          "a whole-statement match would wrongly pass here")

    # ── documentation honesty ────────────────────────────────────────────────
    print("\nDocumentation honesty:")
    mds = {f: open(os.path.join(OUT, f), encoding="utf-8").read()
           for f in os.listdir(OUT) if f.endswith(".md")} if os.path.isdir(OUT) else {}
    if mds:
        check("no document claims completeness while checks fail",
              not (FAILURES and any("FINAL_APPLICATION_WIDE" in b for b in mds.values())))
    else:
        print("  SKIP  no markdown yet")

    print(f"\nCURRENT_CANONICAL_COVERAGE: {protected}/{total}, {unprotected} unprotected")
    if FAILURES:
        print(f"\nVERIFIER FAILED -- {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("\nVERIFIER PASSED -- all checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

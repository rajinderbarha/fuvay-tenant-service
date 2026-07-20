#!/usr/bin/env python
"""Legacy Review Engine authorization verifier — Slice 2F-25A.

Slice 2F-25 reported "runtime verification exits zero" while three mounted
read routes were knowingly unscoped and `create_request` had no parent
ownership proof. A verifier that passes with known gaps open is worse than no
verifier, because it launders an incomplete result as a clean one.

This verifier therefore checks the ACTUAL conditions and exits NON-ZERO on any
of them. Run:

    python scripts/workflow_rearchitecture/verify_legacy_review.py

Exit 0 only when every check passes.
"""
from __future__ import annotations

import inspect
import os
import sys

# Allow running the verifier directly from anywhere in the repo.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))
        FAILURES.append(name)


def _code(fn) -> str:
    """Executable source only — docstrings and comments stripped.

    Two earlier slices wrote assertions that matched explanatory prose instead
    of code (2F-24 matched `Depends(get_current_user)` inside a comment
    describing its removal; 2F-25A matched `ServiceJob` inside a docstring
    saying it is NOT used). Verifier checks must never be satisfiable by
    documentation.
    """
    src = inspect.getsource(fn)
    if src.count('"""') >= 2:
        head, _, rest = src.partition('"""')
        _, _, body = rest.partition('"""')
        src = head + body
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))


def main() -> int:
    from app.engines.review.service import ReviewService
    from app.engines.review import router as R

    print("Legacy review engine verifier (Slice 2F-25A)\n")

    # ── Mutations: scoped lookup, no primary-key-only authorization ─────────
    print("Mutation authorization:")
    for m in ("submit_reply", "flag_review"):
        src = _code(getattr(ReviewService, m))
        check(f"{m} uses the scoped lookup", "_get_review_scoped" in src)
        check(f"{m} has no primary-key-only lookup",
              "select(Review).where(Review.id == review_id)" not in src)

    print("\nRoute personas:")
    for fn in ("submit_reply", "flag_review", "create_request"):
        src = _code(getattr(R, fn))
        check(f"{fn} uses the scope-aware tenant permission",
              "require_tenant_mutation_permission" in src)
    check("resolve_flag remains platform-admin only",
          "require_super_admin" in _code(R.resolve_flag))

    # ── Reads: none may remain unscoped ────────────────────────────────────
    print("\nRead scoping (the three 2F-25 residuals):")
    check("get_aggregate is tenant scoped",
          "ReviewAggregate.tenant_id == self.actor_tenant_id"
          in _code(ReviewService.get_aggregate),
          "aggregate read must not be a cross-tenant reputation oracle")
    check("get_review_request is relationship scoped",
          "ReviewRequest.tenant_id == self.actor_tenant_id"
          in _code(ReviewService.get_review_request)
          and "ReviewRequest.customer_id == self.actor_id"
          in _code(ReviewService.get_review_request))
    check("list_by_customer restricts non-customer principals to their tenant",
          "Review.tenant_id == self.actor_tenant_id"
          in _code(ReviewService.list_by_customer))
    check("get_review is scoped",
          "_get_review_scoped" in _code(ReviewService.get_review))

    # ── Client tenant authority ────────────────────────────────────────────
    print("\nTenant authority:")
    for m in ("list_by_tenant", "list_by_staff", "list_review_requests",
              "list_recent_reviews", "create_review_request"):
        check(f"{m} pins the tenant to the principal",
              "_effective_tenant" in _code(getattr(ReviewService, m)))

    # ── create_request parent ownership ────────────────────────────────────
    print("\ncreate_request parent ownership:")
    src = _code(ReviewService.create_review_request)
    check("parent Job is resolved", "field_ops.models import Job" in src)
    check("Job lookup is tenant scoped", "FieldOpsJob.tenant_id == tenant_id" in src)
    check("customer is derived from the Job", "customer_id = job.customer_id" in src)
    check("client customer substitution is rejected", "CUSTOMER_MISMATCH" in src)
    check("no pipeline identifier is adapted",
          "ServiceJob" not in src and "ServiceBooking" not in src)
    check("ownership precedes the duplicate check",
          src.index("FieldOpsJob.job_number") < src.index("ReviewRequest.job_id == job_id"),
          "otherwise the global duplicate lookup leaks foreign job numbers")

    # ── Internal caller (the 2F-25 regression) ─────────────────────────────
    print("\nInternal job-close caller:")
    from app.engines.field_ops import service as fo
    fo_src = inspect.getsource(fo)
    check("field_ops passes tenant context", "actor_tenant_id=job.tenant_id" in fo_src,
          "without it, 2F-25's pinning silently breaks every job close")
    check("field_ops marks itself a trusted internal caller",
          "trusted_internal=True" in fo_src)

    # ── Legacy 410 ─────────────────────────────────────────────────────────
    print("\nLegacy retirement:")
    check("POST /v1/reviews still returns 410", "410" in inspect.getsource(R.create_review))
    check("no mounted route calls create_review", "s.create_review(" not in inspect.getsource(R))

    # ── Documentation honesty ──────────────────────────────────────────────
    print("\nDocumentation honesty:")
    import os
    docs_root = os.path.join(os.path.dirname(__file__), "..", "..", "docs",
                             "workflow-rearchitecture")
    slice_dir = os.path.abspath(os.path.join(docs_root, "phase-02a-slice-02f25a"))
    if os.path.isdir(slice_dir):
        bodies = {fn: open(os.path.join(slice_dir, fn), encoding="utf-8").read()
                  for fn in os.listdir(slice_dir) if fn.endswith(".md")}
        check("no document claims application-wide coverage completeness",
              not any("FINAL_APPLICATION_WIDE_COVERAGE" in b for b in bodies.values()))
        check("coverage is labelled CURRENT_CANONICAL_COVERAGE",
              any("CURRENT_CANONICAL_COVERAGE" in b for b in bodies.values()))
    else:
        print("  SKIP  slice documentation not yet written")

    print()
    if FAILURES:
        print(f"VERIFIER FAILED — {len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("VERIFIER PASSED — all checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

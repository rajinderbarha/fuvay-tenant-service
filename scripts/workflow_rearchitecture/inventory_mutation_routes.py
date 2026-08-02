"""Phase 2A Slice 2F — exhaustive runtime mutation-route inventory.

Walks the live FastAPI app's route tree (same _IncludedRouter recursion as
list_routes.py) and, for every POST/PUT/PATCH/DELETE route, captures:
  - method, path
  - endpoint function name, module (-> source file)
  - dependency names attached to the route (best-effort, from route.dependant)
  - a first-pass automated classification from the path prefix
  - a guard_status derived from the dependency names (Slice 2F-1, Workstream 12)

This is read-only: does not touch the database, does not bind a network
port, does not mutate anything. Safe to run repeatedly.

Usage:
    PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py > mutation_routes.json
    PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --module app.engines.tenant_engine.router
    PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.tenant_engine.router
        (exits 1 if any route in that module has guard_status UNVERIFIED_NO_GUARD or
         PERMISSION_ONLY_NOT_SCOPE_AWARE; exits 0 otherwise -- a module-scoped
         fail-closed check, not the platform-wide 185-route bar Slice 2F could not
         meet in one pass)
"""
from __future__ import annotations
import argparse
import json
import sys


MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Guard statuses a module-scoped verification treats as "closed" -- i.e. not
# a gap. PLATFORM_ADMIN_MUTATION and CALLBACK_OR_WEBHOOK routes are exempt by
# design (super_admin is exempt from the access_scope check anyway; public/
# webhook routes have no tenant-side access_scope concept).
ACCEPTED_GUARD_STATUSES = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE",
    "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE",
    "PLATFORM_ADMIN_ONLY",
    "PUBLIC_NO_AUTH",
    # Slice 2F-10: customer self-service routes are a genuinely different
    # authorization model than tenant/staff mutations -- there is no
    # tenant access_scope concept for an ordinary customer account, so
    # "not scope-aware" is correct, not a gap, for a route gated by
    # require_customer. Ownership (customer/complaint/booking/proposal)
    # is enforced at the service layer instead, verified separately by
    # Slice 2F-10's own direct IDOR test matrix -- this tool only
    # confirms the router-level role gate, not full ownership closure.
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED",
}

# (module, endpoint_name) pairs manually reviewed and confirmed to be
# FALSE_POSITIVE mutation-method routes -- a POST/PUT/etc HTTP verb used
# only because the endpoint accepts a request body, with no actual write
# performed (confirmed by reading the handler source, not guessed). These
# are exempted from --verify-module's fail-closed check on that specific
# basis, not because their guard is weak.
CONFIRMED_FALSE_POSITIVE_ROUTES = {
    ("app.engines.provider_portal.router", "preview_matching_inputs"),
    # Slice 2F-7: customer-own-address mutations, gated by
    # CUSTOMER_ADDRESS_*_OWN (granted only to the "customer" role) -- not a
    # tenant-facing mutation at all, so tenant access-scope enforcement is
    # not applicable (mirrors the same reasoning already used for
    # PLATFORM_ADMIN_ONLY routes: the guard is role-appropriate, just a
    # different persona than "tenant mutation"). Confirmed via
    # app/core/permissions.py's ROLE_PERMISSIONS.
    ("app.engines.serviceability.router", "create_my_address"),
    ("app.engines.serviceability.router", "update_my_address"),
    ("app.engines.serviceability.router", "delete_my_address"),
    ("app.engines.serviceability.router", "set_default_address"),
    # Slice 2F-7: serviceability check/matching/available-services queries.
    # check_serviceability writes only a ServiceabilityAuditLog row as a
    # side effect of a read-like query; matching_tenants and
    # available_services perform no DB write at all. Gated by
    # SERVICEABILITY_CHECK/MATCH/AVAILABLE_SERVICES, granted to tenant_owner
    # and customer (a query capability, not a tenant-coverage mutation) --
    # not a tenant-facing coverage/service-area mutation requiring the
    # access-scope guard. See docs/workflow-rearchitecture/phase-02a-slice-02f7/
    # matching-serviceability-impact.md for full evidence.
    ("app.engines.serviceability.router", "check_serviceability"),
    ("app.engines.serviceability.router", "matching_tenants"),
    ("app.engines.serviceability.router", "available_services"),
    # Slice 2F-8: admin_catalog.tenant_router's price-preview endpoint is a
    # synchronous, non-async computation (compute_symmetric_customer_price_tiers)
    # with no self.db access at all -- confirmed via direct source read of
    # TenantCatalogService.price_options_preview. It takes client-supplied
    # numbers and returns a computed Low/Mid/High preview; no tenant record is
    # read or written. Same disposition as provider_portal's
    # preview_matching_inputs false positive above.
    ("app.engines.admin_catalog.tenant_router", "preview_tenant_price_options"),
    # Slice 2F-15A: booking_preflight is a POST-verb query endpoint (serviceability
    # + pricing + SLA check) with zero self.db.add/db.commit calls anywhere in
    # BookingService.run_booking_preflight -- confirmed via direct source read.
    # It exists as POST only because it accepts a request body (address/service
    # criteria), not because it mutates any Booking or other persisted row.
    ("app.engines.booking.router", "booking_preflight"),
}

# Slice 2F-15C (supersedes 2F-15B's map): per-route persona classification for
# app.engines.booking.router, reconciled by hand from ROLE_PERMISSIONS grants
# (app/core/permissions.py). Each of the 11 mounted routes gets EXACTLY ONE
# coverage persona (Workstream 9) -- no combined/dual labels:
#   CUSTOMER_SELF_SERVICE_MUTATION  -- reachable by the customer persona for
#                                      their own booking (even if a tenant_owner
#                                      can also reach the same route on the
#                                      customer's behalf -- that tenant-side
#                                      reachability is a secondary fact, not
#                                      this route's primary classification)
#   TENANT_PROVIDER_MUTATION        -- tenant_owner/staff-only, no customer path
#   PLATFORM_INTERNAL_MUTATION      -- super_admin only
#   FALSE_POSITIVE_NON_MUTATION     -- no persistence, not a real mutation
# 2F-15B had classified create_booking/cancel_booking/request_reschedule as
# TENANT_PROVIDER_MUTATION while ALSO reporting them as a customer-self-service
# subset -- a contradiction (claiming exclusion while counting them inside the
# tenant denominator). 2F-15C corrects this: those 3 routes are now
# CUSTOMER_SELF_SERVICE_MUTATION and are EXCLUDED from the tenant-facing
# denominator entirely; only the 6 genuinely tenant/provider-only routes below
# enter the canonical tenant X/Y count.
BOOKING_ROUTE_PERSONA = {
    "booking_preflight":     "FALSE_POSITIVE_NON_MUTATION",
    "create_booking":        "CUSTOMER_SELF_SERVICE_MUTATION",
    "cancel_booking":        "CUSTOMER_SELF_SERVICE_MUTATION",
    "confirm_booking":       "TENANT_PROVIDER_MUTATION",
    "reject_booking":        "TENANT_PROVIDER_MUTATION",
    "convert_to_job":        "TENANT_PROVIDER_MUTATION",
    "request_reschedule":    "CUSTOMER_SELF_SERVICE_MUTATION",
    "accept_reschedule":     "TENANT_PROVIDER_MUTATION",
    "reject_reschedule":     "TENANT_PROVIDER_MUTATION",
    "add_note":              "TENANT_PROVIDER_MUTATION",
    "void_booking":          "PLATFORM_INTERNAL_MUTATION",
}
# Routes classified CUSTOMER_SELF_SERVICE_MUTATION above that are ALSO
# reachable by a tenant_owner acting on the customer's behalf (same route,
# same permission, dual-granted) -- tracked for transparency only, never used
# to re-include these routes in the tenant denominator.
BOOKING_ALSO_TENANT_REACHABLE_CUSTOMER_ROUTES = {"create_booking", "cancel_booking", "request_reschedule"}

# (module, endpoint_name) pairs manually reviewed and confirmed to be
# genuinely PLATFORM_ADMIN_ONLY despite showing PERMISSION_ONLY_NOT_SCOPE_AWARE
# guard_status -- gated by require_permission(P.ADMIN_JOBS_*), a permission
# granted only to the platform-only `admin_operations` role (never granted
# to any tenant-scoped role), so a tenant access_scope check is not
# applicable (same reasoning as require_super_admin's exemption). Confirmed
# by reading app/core/permissions.py's ROLE_PERMISSIONS, Slice 2F-3B.
CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES = {
    ("app.engines.execution.home_service_router", "admin_force_close"),
    ("app.engines.execution.home_service_router", "admin_override_status"),
    ("app.engines.execution.home_service_router", "admin_void"),
    # Slice 2F-5A/5B: finance_hub.admin_router confirmed to have NO tenant
    # persona at all -- every mutation is gated by a FINANCE_* permission
    # that is either (a) granted to admin_finance (a platform-only role) or
    # (b) granted to no role except via super_admin's P.ALL wildcard
    # (an interim-policy-ratified, intentional disposition, not a gap to
    # guard against with a tenant access-scope check). See
    # docs/workflow-rearchitecture/phase-02a-slice-02f5b/finance-hub-permission-matrix.csv
    # for the full per-route evidence.
    ("app.engines.finance_hub.admin_router", "approve_deposit"),
    ("app.engines.finance_hub.admin_router", "reject_deposit"),
    ("app.engines.finance_hub.admin_router", "record_offline_deposit"),
    ("app.engines.finance_hub.admin_router", "refund_deposit"),
    ("app.engines.finance_hub.admin_router", "adjust_deposit"),
    ("app.engines.finance_hub.admin_router", "refund_topup"),
    ("app.engines.finance_hub.admin_router", "retry_credit"),
    ("app.engines.finance_hub.admin_router", "approve_payout"),
    ("app.engines.finance_hub.admin_router", "reject_payout"),
    ("app.engines.finance_hub.admin_router", "mark_processing"),
    ("app.engines.finance_hub.admin_router", "mark_completed"),
    ("app.engines.finance_hub.admin_router", "mark_failed"),
    ("app.engines.finance_hub.admin_router", "approve_claim"),
    ("app.engines.finance_hub.admin_router", "reject_claim"),
    ("app.engines.finance_hub.admin_router", "assign_reviewer"),
    ("app.engines.finance_hub.admin_router", "request_documents"),
    ("app.engines.finance_hub.admin_router", "settle_claim"),
    # Slice 2F-5C: package_commerce.admin_router confirmed to have NO tenant
    # persona -- every mutation is gated by a PACKAGES_*/FINANCE_USAGE_CREDITS_*
    # permission that is either (a) granted to admin_finance (the 2 credit-
    # wallet adapter routes) or (b) granted to no role except via super_admin's
    # P.ALL wildcard (all 12 package-lifecycle routes + admin_purchase_package).
    # See docs/workflow-rearchitecture/phase-02a-slice-02f5c/
    # package-commerce-permission-matrix.csv for full per-route evidence.
    ("app.engines.package_commerce.admin_router", "create_package"),
    ("app.engines.package_commerce.admin_router", "update_package"),
    ("app.engines.package_commerce.admin_router", "delete_package"),
    ("app.engines.package_commerce.admin_router", "activate_package"),
    ("app.engines.package_commerce.admin_router", "deactivate_package"),
    ("app.engines.package_commerce.admin_router", "clone_package"),
    ("app.engines.package_commerce.admin_router", "create_package_feature"),
    ("app.engines.package_commerce.admin_router", "update_package_feature"),
    ("app.engines.package_commerce.admin_router", "delete_package_feature"),
    ("app.engines.package_commerce.admin_router", "create_package_limit"),
    ("app.engines.package_commerce.admin_router", "update_package_limit"),
    ("app.engines.package_commerce.admin_router", "delete_package_limit"),
    ("app.engines.package_commerce.admin_router", "admin_purchase_package"),
    ("app.engines.package_commerce.admin_router", "admin_topup_wallet"),
    ("app.engines.package_commerce.admin_router", "admin_adjust_wallet"),
    # Slice 2F-7: serviceability.router's 4 admin routes, gated by
    # require_permission(P.PLATFORM_ADMIN), a permission granted to no role
    # but super_admin (via P.ALL) -- confirmed via app/core/permissions.py.
    ("app.engines.serviceability.router", "admin_create_service_area"),
    ("app.engines.serviceability.router", "admin_update_service_area"),
    ("app.engines.serviceability.router", "admin_delete_service_area"),
    ("app.engines.serviceability.router", "admin_serviceability_test"),
    # Service-area coverage-approval workflow: same require_permission(P.PLATFORM_ADMIN)
    # pattern as the 4 routes above -- genuinely platform-wide admin review/
    # coverage-management actions with no single tenant scope (an admin
    # reviews requests across ALL tenants), not a missed tenant-scoping gap.
    ("app.engines.serviceability.router", "admin_start_review"),
    ("app.engines.serviceability.router", "admin_decide_service_area_request"),
    ("app.engines.serviceability.router", "admin_suspend_coverage"),
    ("app.engines.serviceability.router", "admin_reactivate_coverage"),
    ("app.engines.serviceability.router", "admin_revoke_coverage"),
}

# (method, path) -> adjudicated disposition, populated by Slice 2F-3A's
# route-overlap investigation. A (method, path) pair mounted from more than
# one module is only acceptable if it appears here; --verify-overlap fails
# closed on any UNADJUDICATED duplicate. See
# docs/workflow-rearchitecture/phase-02a-slice-02f3a/canonical-route-disposition.csv
# for the full evidence trail behind each entry.
ADJUDICATED_ROUTE_OVERLAPS = {
    ("POST", "/v1/staff/service-jobs/{job_id}/accept"): {
        "winning_module": "app.engines.home_service_assignment.staff_router",
        "shadowed_module": "app.engines.execution.home_service_router",
        "disposition": "DISCONNECTED",
    },
    ("POST", "/v1/staff/service-jobs/{job_id}/reject"): {
        "winning_module": "app.engines.home_service_assignment.staff_router",
        "shadowed_module": "app.engines.execution.home_service_router",
        "disposition": "DISCONNECTED",
    },
}


def guard_status(dependency_names: list[str]) -> str:
    """Classifies a route's guard based on its dependency names.

    require_tenant_mutation_permission()'s inner check is renamed
    `require_tenant_mutation_{permission}` (app/core/permissions.py); plain
    require_permission() is renamed `require_{permission}` -- distinct
    prefixes let this tool tell the two apart without source parsing.
    require_tenant_owner_mutation (Slice 2F-2) is the role-gated analogue --
    a plain (non-factory) function, so its name is literally
    `require_tenant_owner_mutation`, not a dynamic rename.
    """
    if any(n.startswith("require_tenant_mutation_") for n in dependency_names):
        return "TENANT_MUTATION_PERMISSION_SCOPE_AWARE"
    if "require_tenant_owner_mutation" in dependency_names:
        return "TENANT_MUTATION_ROLE_SCOPE_AWARE"
    if "require_staff_or_above_mutation" in dependency_names:
        return "STAFF_EXECUTION_ROLE_SCOPE_AWARE"
    if "require_staff_or_technician_only" in dependency_names:
        # Slice 2F-14: field_ops staff/technician execution dependency
        # (app/dependencies/auth.py) -- deliberately NARROWER than
        # require_staff_or_above_mutation (excludes tenant_owner/super_admin
        # entirely; this is a staff/technician self-service execution
        # surface, not a tenant-oversight one). Same STAFF_EXECUTION_ROLE_SCOPE_AWARE
        # tier: a role gate appropriate for assignment-checked execution
        # mutations (object ownership enforced in the service layer via
        # _get_job_for_staff_action/_assert_assigned), not a tenant
        # access-scope concept (staff/technician accounts don't carry one).
        return "STAFF_EXECUTION_ROLE_SCOPE_AWARE"
    if "require_owner_or_office_staff_mutation" in dependency_names:
        # Slice 2F-6A: role-gated analogue of require_staff_or_above_mutation
        # that deliberately excludes technician (tenant_owner/staff only) --
        # same TENANT_MUTATION_ROLE_SCOPE_AWARE tier as require_tenant_owner_mutation,
        # just a wider (2-role) admitted set.
        return "TENANT_MUTATION_ROLE_SCOPE_AWARE"
    if "require_super_admin" in dependency_names:
        return "PLATFORM_ADMIN_ONLY"
    if "require_customer" in dependency_names:
        # Slice 2F-10: canonical customer-role dependency (app/dependencies/auth.py),
        # already used across customer_credits, compliance, profile, and media
        # customer routers -- a role gate, not a tenant-mutation permission,
        # so "not scope-aware" correctly does not apply here.
        return "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED"
    if any(n.startswith("require_") for n in dependency_names):
        return "PERMISSION_ONLY_NOT_SCOPE_AWARE"
    if "get_current_user" in dependency_names:
        return "AUTHENTICATED_ONLY_NO_PERMISSION_CHECK"
    return "PUBLIC_NO_AUTH"


def _dependency_names(route) -> list[str]:
    """Best-effort extraction of dependency callable names from a route's
    dependant tree (FastAPI internal structure) -- used to detect which
    require_* guard(s) are attached, without needing source-line parsing."""
    names = []
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return names

    def _walk(d):
        call = getattr(d, "call", None)
        if call is not None:
            n = getattr(call, "__name__", None) or getattr(call, "__qualname__", None)
            if n:
                names.append(n)
        for sub in getattr(d, "dependencies", []) or []:
            _walk(sub)

    _walk(dependant)
    return names


def classify_prefix(path: str) -> str:
    """First-pass automated classification purely from the path prefix.
    This is deliberately mechanical/exhaustive (every route gets one),
    NOT a claim of final, human-reviewed classification -- see
    tenant-mutation-endpoint-inventory.csv for which of these were then
    manually reviewed/corrected."""
    if path.startswith("/v1/admin/"):
        return "PLATFORM_ADMIN_MUTATION"
    if path.startswith("/v1/staff/"):
        return "TENANT_TECHNICIAN_MUTATION"
    if path.startswith("/v1/provider/") or path.startswith("/v1/tenant/") or path.startswith("/v1/tenants/"):
        return "TENANT_USER_MUTATION"
    if path.startswith("/v1/customer/") or path.startswith("/v1/customers/") or path.startswith("/v1/me/"):
        return "CUSTOMER_MUTATION"
    if path.startswith("/v1/public/"):
        return "CALLBACK_OR_WEBHOOK"
    if path.startswith("/v1/auth/"):
        return "UNVERIFIED"  # login/register/etc -- not a tenant-data mutation per se, needs review
    if path.startswith("/v1/webhooks/") or "callback" in path:
        return "CALLBACK_OR_WEBHOOK"
    return "UNVERIFIED"


def walk(router):
    out = []
    for r in getattr(router, "routes", []):
        if type(r).__name__ == "_IncludedRouter":
            out.extend(walk(r.original_router))
        else:
            path = getattr(r, "path", None)
            methods = sorted(getattr(r, "methods", None) or [])
            if not path:
                continue
            mutation_methods = [m for m in methods if m in MUTATION_METHODS]
            if not mutation_methods:
                continue
            endpoint = getattr(r, "endpoint", None)
            module = getattr(endpoint, "__module__", None) if endpoint else None
            name = getattr(endpoint, "__name__", None) if endpoint else None
            dep_names = _dependency_names(r)
            out.append({
                "methods": mutation_methods,
                "path": path,
                "endpoint_name": name,
                "module": module,
                "dependency_names": dep_names,
                "auto_classification": classify_prefix(path),
                "guard_status": guard_status(dep_names),
            })
    return out


def _parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--module", default=None,
                    help="Only include routes whose endpoint __module__ equals this dotted path "
                         "(e.g. app.engines.tenant_engine.router).")
    p.add_argument("--verify-module", default=None,
                    help="Like --module, but exits 1 (fail-closed) if any matching route's "
                         "guard_status is not in the accepted set for that module, instead of "
                         "printing the JSON inventory. Prints a short summary either way.")
    p.add_argument("--verify-overlap", nargs="+", default=None, metavar="MODULE",
                    help="Slice 2F-3A: given 2+ dotted module paths, finds every (method, path) "
                         "pair mounted from more than one of them, and exits 1 if any such "
                         "overlap is not present in ADJUDICATED_ROUTE_OVERLAPS. Exits 0 if every "
                         "overlap found has a recorded disposition (or no overlap exists).")
    return p.parse_args()


def main():
    args = _parse_args()
    try:
        from app.main import app
    except Exception as e:
        print(json.dumps({"error": f"import failed: {e!r}"}))
        sys.exit(1)

    routes = walk(app.router if hasattr(app, "router") else app)
    routes.sort(key=lambda r: r["path"])

    if args.verify_overlap:
        target_modules = set(args.verify_overlap)
        scoped = [r for r in routes if r["module"] in target_modules]
        by_key: dict[tuple[str, str], list[dict]] = {}
        for r in scoped:
            for m in r["methods"]:
                by_key.setdefault((m, r["path"]), []).append(r)
        overlaps = {k: v for k, v in by_key.items() if len(v) > 1}
        unadjudicated = {k: v for k, v in overlaps.items() if k not in ADJUDICATED_ROUTE_OVERLAPS}
        print(json.dumps({
            "modules_checked": sorted(target_modules),
            "overlaps_found": len(overlaps),
            "overlaps_adjudicated": len(overlaps) - len(unadjudicated),
            "unadjudicated_overlaps": [
                {"method": k[0], "path": k[1],
                 "modules": [r["module"] for r in v]}
                for k, v in unadjudicated.items()
            ],
        }, indent=2))
        sys.exit(1 if unadjudicated else 0)

    target_module = args.module or args.verify_module
    if target_module:
        routes = [r for r in routes if r["module"] == target_module]

    if args.verify_module:
        _exempt = CONFIRMED_FALSE_POSITIVE_ROUTES | CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES
        unverified = [
            r for r in routes
            if r["guard_status"] not in ACCEPTED_GUARD_STATUSES
            and (r["module"], r["endpoint_name"]) not in _exempt
        ]
        result = {
            "module": target_module,
            "total_routes": len(routes),
            "unverified_count": len(unverified),
            "unverified_routes": [
                {"method": r["methods"], "path": r["path"], "endpoint_name": r["endpoint_name"],
                 "guard_status": r["guard_status"]}
                for r in unverified
            ],
        }
        # Slice 2F-15C (extends 2F-15B): for app.engines.booking.router
        # specifically, break the total down by coverage persona
        # (Workstream 12/9) instead of a single combined mutation count --
        # guard_status alone cannot distinguish a customer-self-service route
        # from a tenant-only one. Each route has exactly ONE persona; only
        # TENANT_PROVIDER_MUTATION routes count toward the tenant-facing
        # denominator (Workstream 10/11).
        if target_module == "app.engines.booking.router":
            persona_counts: dict[str, int] = {}
            unclassified = []
            for r in routes:
                persona = BOOKING_ROUTE_PERSONA.get(r["endpoint_name"])
                if persona is None:
                    unclassified.append(r["endpoint_name"])
                    continue
                persona_counts.setdefault(persona, 0)
                persona_counts[persona] += 1
            result["persona_breakdown"] = persona_counts
            result["tenant_denominator_count"] = persona_counts.get("TENANT_PROVIDER_MUTATION", 0)
            result["also_tenant_reachable_customer_routes"] = sorted(
                BOOKING_ALSO_TENANT_REACHABLE_CUSTOMER_ROUTES)
            result["unclassified_routes"] = unclassified
            # Documentation-vs-code drift check (Workstream 12): every
            # mounted route must have an explicit persona entry; the
            # false-positive-classified set here must exactly match
            # CONFIRMED_FALSE_POSITIVE_ROUTES for this module; no customer or
            # platform route may leak into the tenant denominator count.
            fp_in_persona_map = {name for name, p in BOOKING_ROUTE_PERSONA.items()
                                  if p == "FALSE_POSITIVE_NON_MUTATION"}
            fp_in_exempt_set = {name for (mod, name) in CONFIRMED_FALSE_POSITIVE_ROUTES
                                 if mod == target_module}
            tenant_denominator_routes = {name for name, p in BOOKING_ROUTE_PERSONA.items()
                                          if p == "TENANT_PROVIDER_MUTATION"}
            leaked_customer = tenant_denominator_routes & BOOKING_ALSO_TENANT_REACHABLE_CUSTOMER_ROUTES
            drift = (unclassified or fp_in_persona_map != fp_in_exempt_set or leaked_customer)
            if drift:
                result["persona_drift_detected"] = True
                unverified = unverified + [{"drift": "persona classification does not match "
                                             "runtime route set, false-positive exemptions, or "
                                             "a customer/platform route leaked into the tenant "
                                             "denominator"}]
                result["unverified_count"] = len(unverified)
        print(json.dumps(result, indent=2))
        sys.exit(1 if unverified else 0)

    by_class = {}
    by_guard = {}
    for r in routes:
        by_class.setdefault(r["auto_classification"], 0)
        by_class[r["auto_classification"]] += 1
        by_guard.setdefault(r["guard_status"], 0)
        by_guard[r["guard_status"]] += 1

    print(json.dumps({
        "total_mutation_routes": len(routes),
        "by_auto_classification": by_class,
        "by_guard_status": by_guard,
        "routes": routes,
    }, indent=2))


if __name__ == "__main__":
    main()

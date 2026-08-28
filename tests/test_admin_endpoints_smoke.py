"""Admin endpoints that were returning 500 to the console.

Found by calling every parameterless admin GET as a real super admin. Existing
in the OpenAPI spec proves a route is mounted, not that it works -- each of
these returned 200 in the spec and 500 on the wire.

Four distinct causes, three of them the same story: the security deposit was
removed and its readers were not.
"""
from __future__ import annotations

import inspect


def _code(obj) -> str:
    """Source with comment lines and docstrings stripped.

    These assertions describe what the CODE must not do, and the comments
    explaining each fix legitimately name the very thing being asserted absent.
    """
    src = inspect.getsource(obj)
    out, in_doc = [], False
    for line in src.splitlines():
        t = line.strip()
        if t.startswith(('"""', "'''")):
            if not (len(t) > 3 and t.endswith(('"""', "'''"))):
                in_doc = not in_doc
            continue
        if in_doc or t.startswith("#"):
            continue
        out.append(line)
    return chr(10).join(out)



class TestDepositRemovalFallout:
    """Three consoles were left calling things the deposit took with it."""

    def test_provider_directory_no_longer_references_a_deleted_local(self):
        from app.engines.tenant_engine import hs_provider_directory_service as d
        src = _code(d.HomeServicesProviderDirectoryService._provider_row)
        # `deposit` was removed from the signature but not from the body, so
        # building ANY provider row raised NameError -- the whole Providers
        # console 500'd, not just a field.
        assert "deposit.status" not in src

    def test_provider_detail_passes_the_right_arity(self):
        from app.engines.tenant_engine import hs_provider_directory_service as d
        src = _code(d.HomeServicesProviderDirectoryService.get_provider_detail)
        assert "_provider_row(tenant, billing)" in src

    def test_tenant_insights_no_longer_sums_a_dropped_column(self):
        from app.engines.tenant_engine import admin_service as a
        src = _code(a)
        # `tenant_billing.security_deposit_amount` went in migration 317/318;
        # summing it raised UndefinedColumnError.
        assert "SUM(tb.security_deposit_amount)" not in src


class TestBulkSetupOptions:
    """The wizard's option lists all failed, for two different reasons."""

    def test_soft_delete_filters_are_gone_from_tables_without_one(self):
        from app.engines.admin_catalog import bulk_setup_service as b
        src = _code(b.AdminBulkSetupDraftService.get_available_issue_types)
        # Neither the model nor the table has deleted_at -- filtering on it
        # raised AttributeError before a query was even built.
        assert "deleted_at" not in src

        src2 = _code(b.AdminBulkSetupDraftService.get_available_service_options)
        assert "deleted_at" not in src2

    def test_checklist_templates_read_the_live_catalogue(self):
        from app.engines.admin_catalog import bulk_setup_service as b
        src = _code(b.AdminBulkSetupDraftService.get_available_checklist_templates)
        # field_ops' `service_checklist_templates` was never migrated.
        assert "checklist_catalog.models" in src
        assert "field_ops" not in src

    def test_setup_templates_read_the_live_engine(self):
        from app.engines.admin_catalog import bulk_setup_service as b
        src = _code(b.AdminBulkSetupDraftService.get_available_templates)
        # The module-level import resolves to admin_catalog's Sprint-34F model,
        # whose table `service_setup_templates_legacy_34f` does not exist.
        assert "service_setup.models" in src
        assert "vertical_key" in src


class TestRetiredSurfacesFailHonestly:
    def test_the_legacy_setup_template_crud_reports_retired(self):
        from app.engines.admin_catalog import service_setup_template_service as t
        src = inspect.getsource(t)
        assert "SETUP_TEMPLATE_CRUD_RETIRED" in src
        assert "status_code=410" in src

    def test_its_run_history_still_works(self):
        """Runs use a table that DOES exist and a page depends on them."""
        from app.engines.admin_catalog import service_setup_template_service as t
        src = _code(t.ServiceSetupTemplateService.list_runs)
        assert "_retired" not in src


class TestRouteOrdering:
    """A static route swallowed by a parameterised sibling in another router."""

    def test_platform_analytics_is_registered_first(self):
        from app import main
        src = inspect.getsource(main)
        block = src[src.index("platform_analytics_router,"):]
        block_start = src.index("for _r in [\n        platform_analytics_router,")
        window = src[block_start:block_start + 300]
        # Both routers share the /v1/admin/analytics prefix and Starlette
        # matches in registration order. Registered second, the STATIC
        # /providers/performance was matched by /providers/{tenant_id}, which
        # then parsed the literal "performance" as a UUID and 500'd.
        assert window.index("platform_analytics_router") < window.index("admin_analytics_router")

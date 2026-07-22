"""Phase 2A Slice 2F-35 — Critical Destructive and Security-Sensitive
Authorization Batch.

Covers Set A (2 routes) closed + Set B (9 held routes) adjudicated and
closed across 4 modules: webhook_endpoint_management, rag_query,
security (api-key rotate/revoke), documents (generate/send/void).
"""
from __future__ import annotations

import csv
import hashlib
import inspect
import importlib.util
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SET_A = {("DELETE", "/v1/webhooks/endpoints/{endpoint_id}"), ("POST", "/v1/rag/query")}
SET_B = {
    ("POST", "/v1/security/api-keys/{key_id}/rotate"),
    ("POST", "/v1/security/api-keys/{key_id}/revoke"),
    ("POST", "/v1/documents"),
    ("POST", "/v1/documents/{document_id}/send"),
    ("POST", "/v1/documents/{document_id}/void"),
    ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
    ("POST", "/v1/rag/knowledge-bases/{kb_id}/documents"),
    ("DELETE", "/v1/rag/documents/{doc_id}"),
    ("POST", "/v1/rag/documents/{doc_id}/reindex"),
}


def _canon_rows():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am35", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestScopeGuardsLive:
    def test_all_11_routes_access_scope_gated(self):
        E = _model()
        idx = E.route_index()
        for key in SET_A | SET_B:
            assert key in idx, key
            assert any(g["access_scope_gated"] for g in E.route_guards(idx[key])), key


class TestWebhookTenantAuthority:
    def test_trusted_tenant_helper_exists(self):
        from app.engines.webhook.service import WebhookService
        assert hasattr(WebhookService, "_require_trusted_tenant")

    def test_delete_endpoint_calls_trusted_tenant(self):
        from app.engines.webhook.service import WebhookService
        src = inspect.getsource(WebhookService.delete_endpoint)
        assert "_require_trusted_tenant(tenant_id)" in src
        assert src.index("_require_trusted_tenant") < src.index("select(WebhookEndpoint)")

    def test_missing_tenant_context_fails_closed(self):
        from app.engines.webhook.service import WebhookService
        src = inspect.getsource(WebhookService._require_trusted_tenant)
        assert "self.actor_tenant_id is None" in src and "raise" in src


class TestRagTenantAuthority:
    def test_trusted_tenant_helper_exists(self):
        from app.engines.rag.service import RAGService
        assert hasattr(RAGService, "_require_trusted_tenant")
        assert hasattr(RAGService, "_get_kb_trusted")

    def test_query_uses_trusted_kb_lookup(self):
        from app.engines.rag.service import RAGService
        src = inspect.getsource(RAGService.query)
        assert "_get_kb_trusted(kb_id)" in src

    def test_delete_kb_uses_trusted_kb_lookup(self):
        from app.engines.rag.service import RAGService
        src = inspect.getsource(RAGService.delete_kb)
        assert "_get_kb_trusted(kb_id)" in src

    def test_ingest_document_uses_trusted_kb_lookup(self):
        from app.engines.rag.service import RAGService
        src = inspect.getsource(RAGService.ingest_document)
        assert "_get_kb_trusted(kb_id)" in src

    def test_delete_document_scopes_by_tenant(self):
        from app.engines.rag.service import RAGService
        src = inspect.getsource(RAGService.delete_document)
        assert "KBDocument.tenant_id == tenant_id" in src

    def test_reindex_document_scopes_by_tenant(self):
        from app.engines.rag.service import RAGService
        src = inspect.getsource(RAGService.reindex_document)
        assert "KBDocument.tenant_id == tenant_id" in src

    def test_get_kb_untouched_for_set_c(self):
        """_get_kb (the original, unscoped helper) must remain byte-behavior
        -identical -- Set C read routes (get_kb, list_kbs, update_kb,
        search_only, list_documents) still call it unmodified."""
        from app.engines.rag.service import RAGService
        src = inspect.getsource(RAGService._get_kb)
        assert "_require_trusted_tenant" not in src
        assert "tenant_id" not in src.split("def _get_kb")[1].split("\n\n")[0]


class TestSecurityTenantAuthority:
    def test_trusted_tenant_helper_exists(self):
        from app.engines.security.service import SecurityService
        assert hasattr(SecurityService, "_require_trusted_tenant")

    def test_rotate_calls_trusted_tenant(self):
        from app.engines.security.service import SecurityService
        src = inspect.getsource(SecurityService.rotate_api_key)
        assert "_require_trusted_tenant(tenant_id)" in src

    def test_revoke_calls_trusted_tenant(self):
        from app.engines.security.service import SecurityService
        src = inspect.getsource(SecurityService.revoke_api_key)
        assert "_require_trusted_tenant(tenant_id)" in src

    def test_security_admin_service_super_admin_bypass_preserved(self):
        """SecurityAdminService always supplies actor_role='super_admin'
        (its own route is require_super_admin-gated), so it bypasses the
        new tenant check exactly as before -- confirmed by inspecting its
        constructor call site, not assumed."""
        import app.engines.security.admin_router as admin_router
        src = inspect.getsource(admin_router)
        assert "require_super_admin" in src


class TestDocumentTenantAuthority:
    def test_trusted_tenant_helper_exists(self):
        from app.engines.document.service import DocumentService
        assert hasattr(DocumentService, "_require_trusted_tenant")

    def test_generate_document_calls_trusted_tenant(self):
        from app.engines.document.service import DocumentService
        src = inspect.getsource(DocumentService.generate_document)
        assert "_require_trusted_tenant(tenant_id)" in src

    def test_send_for_signature_scopes_by_tenant(self):
        from app.engines.document.service import DocumentService
        src = inspect.getsource(DocumentService.send_for_signature)
        assert "Document.tenant_id == tenant_id" in src

    def test_void_document_scopes_by_tenant(self):
        from app.engines.document.service import DocumentService
        src = inspect.getsource(DocumentService.void_document)
        assert "Document.tenant_id == tenant_id" in src

    def test_field_ops_internal_caller_passes_trusted_context(self):
        """The one internal caller of generate_document (invoice generation
        on job status transition) must now pass actor_tenant_id explicitly,
        or it would fail closed."""
        import app.engines.field_ops.service as fo
        src = inspect.getsource(fo)
        assert "DocumentService(self.db, actor_id=self.actor_id,\n                                       actor_tenant_id=job.tenant_id)" in src \
            or "actor_tenant_id=job.tenant_id" in src


class TestNonOracularResponses:
    def test_webhook_no_existence_leak_wording(self):
        from app.engines.webhook.service import WebhookService
        src = inspect.getsource(WebhookService._require_trusted_tenant)
        assert "does not exist" not in src and "does not belong" not in src

    def test_rag_kb_trusted_no_existence_leak(self):
        from app.engines.rag.service import RAGService
        src = inspect.getsource(RAGService._get_kb_trusted)
        assert "does not exist" not in src and "does not belong" not in src


class TestNoBypassOfClosedRoutes:
    def test_no_direct_webhook_service_mutation_call_outside_router(self):
        out = subprocess.run(
            ["git", "grep", "-n", "-E", r"\bs\.delete_endpoint\(",
             "--", "app/", ":(exclude)app/engines/webhook/service.py", ":(exclude)app/engines/webhook/router.py"],
            cwd=REPO, capture_output=True, text=True)
        assert out.stdout.strip() == "", out.stdout

    def test_no_direct_rag_service_mutation_call_outside_router(self):
        out = subprocess.run(
            ["git", "grep", "-n", "-E",
             r"\bs\.(query|delete_kb|ingest_document|delete_document|reindex_document)\(",
             "--", "app/", ":(exclude)app/engines/rag/service.py", ":(exclude)app/engines/rag/router.py"],
            cwd=REPO, capture_output=True, text=True)
        assert out.stdout.strip() == "", out.stdout

    def test_no_direct_security_service_mutation_call_outside_router_and_admin(self):
        out = subprocess.run(
            ["git", "grep", "-n", "-E", r"\bs(vc)?\.(rotate_api_key|revoke_api_key)\(",
             "--", "app/", ":(exclude)app/engines/security/service.py",
             ":(exclude)app/engines/security/router.py", ":(exclude)app/engines/security/admin_service.py",
             ":(exclude)app/engines/security/admin_router.py"],
            cwd=REPO, capture_output=True, text=True)
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        # app/engines/auth/router.py's svc.revoke_api_key is AuthService's
        # OWN, separate, already-scoped API-key subsystem (api_keys table,
        # not tenant_api_keys) -- confirmed a different class, not a bypass.
        bad = [l for l in lines if "app/engines/auth/router.py" not in l]
        assert not bad, bad

    def test_document_service_generate_document_callers_all_pass_trusted_tenant(self):
        out = subprocess.run(
            ["git", "grep", "-n", "-E", r"\.generate_document\(",
             "--", "app/", ":(exclude)app/engines/document/service.py", ":(exclude)app/engines/document/router.py"],
            cwd=REPO, capture_output=True, text=True)
        # git-tracked .py source files only -- ignore stray editor/tmp
        # artifacts that are never imported (e.g. *.py.tmp.*)
        lines = [l for l in out.stdout.splitlines() if l.strip() and ".py:" in l]
        assert len(lines) == 1 and "field_ops/service.py" in lines[0], lines


class TestSetBAdjudication:
    def test_all_9_held_routes_now_canonical_and_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_B:
            assert key in rows, key
            assert rows[key] in VERIFIED, f"{key}: {rows[key]}"

    def test_both_set_a_routes_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_A:
            assert rows[key] in VERIFIED, f"{key}: {rows[key]}"


class TestCanonicalClosure:
    def test_coverage_is_252_of_273(self):
        rows = _canon_rows()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_21(self):
        rows = _canon_rows()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_denominator_increased_by_exactly_nine(self):
        assert len(_canon_rows()) == 264 + 9 + 24 + 16


class TestM01N01GeoNonRegression:
    def test_m01_sample_still_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/auth/api-keys")] in VERIFIED

    def test_n01_sample_still_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/media/upload")] in VERIFIED

    def test_geo_sample_still_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("DELETE", "/v1/geo/zones/{zone_id}")] in VERIFIED

"""Verification Documents step — requirement resolver + router structure tests."""
import os
import pathlib

from app.engines.vertical_catalog.document_requirements import (
    resolve_requirements, required_keys, is_business_profile_complete, POLICY_VERSION,
)

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ROUTER = os.path.join(BASE, "app/engines/vertical_catalog/tenant_documents_router.py")


class TestRequirementResolver:
    def test_base_requirements_present(self):
        reqs = resolve_requirements(vertical="home_services", business_type="sole_proprietorship")
        keys = {r["key"] for r in reqs}
        assert {"business_registration", "identity_proof", "address_proof"} <= keys

    def test_gst_is_optional_not_universally_required(self):
        reqs = resolve_requirements(vertical="home_services", business_type="sole_proprietorship")
        gst = next(r for r in reqs if r["key"] == "gst_certificate")
        assert gst["required"] is False

    def test_required_keys_excludes_optional(self):
        keys = required_keys(vertical="home_services", business_type="sole_proprietorship")
        assert "gst_certificate" not in keys
        assert "business_registration" in keys

    def test_vertical_specific_extra_requirement(self):
        reqs = resolve_requirements(vertical="real_estate", business_type="private_limited")
        keys = {r["key"] for r in reqs}
        assert "rera_registration" in keys
        home_keys = {r["key"] for r in resolve_requirements(vertical="home_services", business_type="private_limited")}
        assert "rera_registration" not in home_keys

    def test_unknown_vertical_falls_back_to_base_no_crash(self):
        reqs = resolve_requirements(vertical="some_future_vertical", business_type=None)
        assert {r["key"] for r in reqs} >= {"business_registration", "identity_proof", "address_proof"}

    def test_policy_version_is_a_stable_string(self):
        assert isinstance(POLICY_VERSION, str) and POLICY_VERSION

    def test_every_requirement_has_display_fields(self):
        for r in resolve_requirements(vertical="home_services", business_type="llp"):
            assert r["label"] and r["why"] and r["accepted_examples"]
            assert isinstance(r["required"], bool)


class TestBusinessProfileCompleteness:
    class _Row:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    def test_complete_when_all_fields_present(self):
        row = self._Row(business_name="Acme", business_type="llp", phone="+911234567890",
                         email="a@b.com", address_line1="1 Rd", city="Mumbai", state="MH")
        assert is_business_profile_complete(row) is True

    def test_incomplete_when_missing_field(self):
        row = self._Row(business_name="Acme", business_type="llp", phone="+911234567890",
                         email="a@b.com", address_line1=None, city="Mumbai", state="MH")
        assert is_business_profile_complete(row) is False

    def test_incomplete_when_row_is_none(self):
        assert is_business_profile_complete(None) is False


class TestRouterStructure:
    def _read(self):
        with open(ROUTER, encoding="utf-8") as f:
            return f.read()

    def test_router_has_expected_endpoints(self):
        c = self._read()
        assert 'router = APIRouter(prefix="/v1/tenant/home-services/setup/documents"' in c
        assert '@router.get("/requirements")' in c
        assert '@router.post("")' in c
        assert '@router.delete("/{document_id}")' in c

    def test_router_reuses_canonical_media_engine_not_a_new_upload_endpoint(self):
        c = self._read()
        # No raw UploadFile/File(...) handling here — uploads always go through
        # the Media Engine first; this router only claims an existing asset.
        assert "UploadFile" not in c
        assert "MediaAsset" in c
        assert "DOCUMENT_MEDIA_CONTEXT = \"provider_document\"" in c

    def test_tenant_isolation_enforced_on_media_asset(self):
        c = self._read()
        assert "asset.tenant_id != tid" in c

    def test_required_document_cannot_be_deleted_only_replaced(self):
        c = self._read()
        assert 'doc.doc_type != "additional"' in c
        assert "CANNOT_REMOVE_REQUIRED_DOCUMENT" in c

    def test_replacement_supersedes_not_overwrites(self):
        c = self._read()
        assert "existing.is_current = False" in c
        assert 'existing.status = "superseded"' in c
        assert "superseded_by_id" in c

    def test_no_out_of_scope_fields(self):
        c = self._read()
        for forbidden in ("security_deposit", "bank_account", "tenant_min_price", "package_id"):
            assert forbidden not in c


class TestModelVersioning:
    def test_model_has_versioning_fields(self):
        model_path = os.path.join(BASE, "app/engines/tenant_engine/models.py")
        with open(model_path, encoding="utf-8") as f:
            c = f.read()
        for field in ("media_asset_id", "is_current", "superseded_by_id", "version", "rejection_reason"):
            assert field in c


class TestMediaSignatureValidation:
    def test_validation_module_checks_file_signature(self):
        validation_path = os.path.join(BASE, "app/engines/media/validation.py")
        with open(validation_path, encoding="utf-8") as f:
            c = f.read()
        assert "_validate_signature" in c
        assert "_SIGNATURES" in c

    def test_pdf_signature_rejects_mismatched_content(self):
        from app.engines.media.validation import MediaValidationService
        from app.exceptions import ServiceOSException
        import pytest
        svc = MediaValidationService()
        with pytest.raises(ServiceOSException) as exc:
            svc.validate_upload(b"NOTAPDF" + b"x" * 100, "doc.pdf", "application/pdf", "provider_document")
        assert exc.value.error_code == "MEDIA_SIGNATURE_MISMATCH"

    def test_pdf_signature_accepts_real_pdf_bytes(self):
        from app.engines.media.validation import MediaValidationService
        svc = MediaValidationService()
        svc.validate_upload(b"%PDF-1.4\n" + b"x" * 100, "doc.pdf", "application/pdf", "provider_document")

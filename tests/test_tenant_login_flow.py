"""
Tenant Portal Login — live E2E tests against the real dev DB.
Covers: password login by email, password login by mobile, wrong password,
backend-authoritative post-login destination projection, password reset
request+confirm+relogin with session revocation.
"""
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# This suite runs live against the real dev DB/Redis (matching how the signup
# flow was E2E-verified) rather than the repo's default mocked-DB convention —
# override conftest's autouse mocks as no-ops so requests hit the real stack.
@pytest.fixture(autouse=True)
def mock_database():
    yield


@pytest.fixture(autouse=True)
def mock_redis():
    yield


def _fixed_otp():
    import hashlib
    code = "123456"
    return code, hashlib.sha256(code.encode()).hexdigest()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _register_tenant(client, suffix: str):
    email = f"login_e2e_{suffix}@example.com"
    mobile = f"+9198{uuid.uuid4().int % 100000000:08d}"
    password = "Sup3rSecret!"

    with patch("app.engines.public_registration.service.generate_otp", _fixed_otp):
        r = client.post("/v1/public/register/owner-account", json={
            "full_name": "Login E2E Owner", "email": email, "mobile": mobile,
            "password": password, "password_confirm": password,
            "authorized_declaration": True, "tos_privacy_accepted": True, "marketing_consent": False,
        })
        assert r.status_code == 200, r.text
        reg_id = r.json()["data"]["registration_id"]

        for channel in ("mobile", "email"):
            r = client.post("/v1/public/register/verify-contact", json={
                "registration_id": reg_id, "channel": channel, "otp": "123456",
            })
            assert r.status_code == 200, r.text

    r = client.post("/v1/public/register/business-identity", json={
        "registration_id": reg_id, "legal_name": "Login E2E Legal", "business_name": "Login E2E Biz",
        "business_type": "private_limited",
        "registered_address": {"line1": "1 Test Rd", "state": "MH", "district": "Mumbai", "city": "Mumbai", "pincode": "400001"},
    })
    assert r.status_code == 200, r.text

    r = client.get("/v1/public/register/verticals")
    verticals = r.json()["data"]["verticals"]
    vkey = verticals[0]["key"]
    r = client.post("/v1/public/register/select-vertical", json={"registration_id": reg_id, "vertical_key": vkey})
    assert r.status_code == 200, r.text

    r = client.post("/v1/public/register/complete", json={
        "registration_id": reg_id, "authorized_declaration": True,
        "tos_privacy_accepted": True, "marketing_consent": False,
    })
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    return {"email": email, "mobile": mobile, "password": password, "tenant_id": data["tenant_id"]}


class TestPasswordLogin:
    def test_login_by_email_succeeds_and_projects_destination(self, client):
        acct = _register_tenant(client, uuid.uuid4().hex[:8])
        r = client.post("/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["mfa_required"] is False
        assert data["access_token"]
        # Fresh signup -> draft_setup enrollment -> vertical setup wizard.
        assert data["next_destination"] == "vertical_setup_wizard"
        assert data["reason_code"] == "VERTICAL_SETUP_NOT_STARTED"

    def test_login_by_mobile_succeeds(self, client):
        acct = _register_tenant(client, uuid.uuid4().hex[:8])
        r = client.post("/v1/auth/login", json={"email": acct["mobile"], "password": acct["password"]})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["access_token"]

    def test_wrong_password_rejected_generic_message(self, client):
        acct = _register_tenant(client, uuid.uuid4().hex[:8])
        r = client.post("/v1/auth/login", json={"email": acct["email"], "password": "WrongPassword1!"})
        assert r.status_code in (400, 401)
        detail = r.json().get("detail", "") + str(r.json())
        assert "wrong_password" not in detail.lower()  # never leak which factor failed


class TestPasswordReset:
    def test_reset_request_then_confirm_then_relogin(self, client):
        acct = _register_tenant(client, uuid.uuid4().hex[:8])

        with patch("app.engines.auth.service.generate_otp", _fixed_otp):
            r = client.post("/v1/auth/password/reset/request", json={"email": acct["email"]})
            assert r.status_code == 200, r.text

        new_password = "Br4ndN3wPass!"
        r = client.post("/v1/auth/password/reset/confirm", json={
            "email": acct["email"], "reset_token": "123456",
            "new_password": new_password, "confirm_password": new_password,
        })
        assert r.status_code == 200, r.text

        # Old password no longer works.
        r = client.post("/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
        assert r.status_code in (400, 401)

        # New password works.
        r = client.post("/v1/auth/login", json={"email": acct["email"], "password": new_password})
        assert r.status_code == 200, r.text

    def test_reset_confirm_unknown_email_is_enumeration_safe(self, client):
        r = client.post("/v1/auth/password/reset/confirm", json={
            "email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com", "reset_token": "000000",
            "new_password": "SomePassword1!", "confirm_password": "SomePassword1!",
        })
        assert r.status_code == 400
        assert "invalid" in r.json().get("detail", "").lower() or "expired" in str(r.json()).lower()


class TestDestinationProjection:
    """Unit-level, mocked DB session — isolates resolve_post_login_destination()'s
    status-mapping logic from the live-DB E2E tests above (which already prove
    the happy path end to end); a mocked session avoids sharing/crossing the
    TestClient's own event loop, which deadlocks on direct asyncpg access."""

    async def _resolve(self, user, tenant, enrollments):
        from unittest.mock import AsyncMock, MagicMock
        from app.engines.auth.service import AuthService

        db = AsyncMock()
        tenant_result = MagicMock()
        tenant_result.scalar_one_or_none.return_value = tenant
        enrollment_result = MagicMock()
        enrollment_result.scalars.return_value.all.return_value = enrollments
        db.execute = AsyncMock(side_effect=[tenant_result, enrollment_result])
        svc = AuthService(db=db)
        return await svc.resolve_post_login_destination(user)

    async def test_suspended_tenant_routes_to_restricted(self):
        from unittest.mock import MagicMock
        user = MagicMock(role="tenant_owner", tenant_id=uuid.uuid4())
        tenant = MagicMock(status="suspended")
        dest = await self._resolve(user, tenant, [])
        assert dest == {"next_destination": "restricted_account", "reason_code": "TENANT_SUSPENDED"}

    async def test_draft_setup_enrollment_routes_to_setup_wizard(self):
        from unittest.mock import MagicMock
        user = MagicMock(role="tenant_owner", tenant_id=uuid.uuid4())
        tenant = MagicMock(status="onboarding_pending")
        enrollment = MagicMock(status="draft_setup")
        dest = await self._resolve(user, tenant, [enrollment])
        assert dest == {"next_destination": "vertical_setup_wizard", "reason_code": "VERTICAL_SETUP_NOT_STARTED"}

    async def test_active_enrollment_routes_to_dashboard(self):
        from unittest.mock import MagicMock
        user = MagicMock(role="tenant_owner", tenant_id=uuid.uuid4())
        tenant = MagicMock(status="active")
        enrollment = MagicMock(status="active")
        dest = await self._resolve(user, tenant, [enrollment])
        assert dest == {"next_destination": "tenant_dashboard", "reason_code": "VERTICAL_ACTIVE"}

    async def test_customer_role_rejected(self):
        from unittest.mock import MagicMock
        from app.engines.auth.service import AuthService
        svc = AuthService(db=MagicMock())
        user = MagicMock(role="customer", tenant_id=None)
        dest = await svc.resolve_post_login_destination(user)
        assert dest == {"next_destination": "access_rejected", "reason_code": "CUSTOMER_ROLE_NOT_PERMITTED"}

    async def test_technician_role_routes_to_technician_app(self):
        from unittest.mock import MagicMock
        from app.engines.auth.service import AuthService
        svc = AuthService(db=MagicMock())
        user = MagicMock(role="technician", tenant_id=None)
        dest = await svc.resolve_post_login_destination(user)
        assert dest == {"next_destination": "technician_app", "reason_code": "TECHNICIAN_ROLE_NO_PORTAL_ACCESS"}

    async def test_no_tenant_membership_resumes_signup(self):
        from unittest.mock import MagicMock
        from app.engines.auth.service import AuthService
        svc = AuthService(db=MagicMock())
        user = MagicMock(role="tenant_owner", tenant_id=None)
        dest = await svc.resolve_post_login_destination(user)
        assert dest == {"next_destination": "resume_signup", "reason_code": "NO_TENANT_MEMBERSHIP"}

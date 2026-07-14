"""MODULE-L5-04 — tenant service-area cross-tenant isolation (active IDOR fix)."""
import uuid
import pytest

from app.engines.serviceability.service import ServiceabilityService
from app.exceptions import NotFoundException
import e2e.serviceability_isolation_guard as guard


def _svc(role, tenant_id):
    inst = ServiceabilityService.__new__(ServiceabilityService)
    inst.actor_role = role
    inst.actor_tenant_id = tenant_id
    return inst


def test_staff_cannot_reach_other_tenant_area():
    """The active IDOR: staff holds tenant_service_area:read and was NOT confined
    by the old tenant_owner-only gate."""
    a, b = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(NotFoundException):
        _svc("staff", a)._assert_owns_tenant(b)
    _svc("staff", a)._assert_owns_tenant(a)   # own tenant ok


def test_technician_cannot_reach_other_tenant_area():
    a, b = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(NotFoundException):
        _svc("technician", a)._assert_owns_tenant(b)


def test_tenant_owner_still_confined():
    a, b = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(NotFoundException):
        _svc("tenant_owner", a)._assert_owns_tenant(b)


def test_tenant_role_with_no_tenant_denied():
    with pytest.raises(NotFoundException):
        _svc("staff", None)._assert_owns_tenant(uuid.uuid4())


def test_platform_roles_exempt():
    for role in ("super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly"):
        _svc(role, None)._assert_owns_tenant(uuid.uuid4())  # no raise


def test_guard_passes_on_real_repo():
    assert guard.check() == []

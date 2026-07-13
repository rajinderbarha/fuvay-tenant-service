"""MODULE-L5-01D — canonical role registry tests + guard controlled-failures.

Verifies the BLK-01D-1 resolution (Option A): one canonical, enforced role set,
mirrored consistently in auth/constants.py, and a fail-closed guard that detects
drift (an 11th role, a removed role, or a stale mirror).
"""
import importlib

from app.core.permissions import ROLE_PERMISSIONS
from app.engines.auth.constants import ROLES, AUDIENCE
import e2e.canonical_role_registry_guard as guard
import e2e.single_tenant_model_guard as st_guard


CANONICAL = {
    "super_admin", "admin_operations", "admin_finance", "admin_security",
    "admin_readonly", "tenant_owner", "staff", "technician", "customer", "guest",
}


def test_enforced_registry_is_exactly_canonical():
    assert set(ROLE_PERMISSIONS.keys()) == CANONICAL


def test_constants_mirror_matches_canonical():
    assert set(ROLES) == CANONICAL


def test_constants_roles_has_no_duplicates():
    assert len(ROLES) == len(set(ROLES)) == 10


def test_every_canonical_role_has_an_audience():
    # Previously technician + the admin_* roles fell back to the customer
    # audience; each canonical role must now carry an explicit audience.
    for role in CANONICAL:
        assert role in AUDIENCE, f"{role} missing an explicit token audience"


def test_platform_admin_roles_get_admin_audience():
    for role in ("admin_operations", "admin_finance", "admin_security", "admin_readonly"):
        assert AUDIENCE[role] == "serviceos:admin"


def test_guard_passes_on_real_registry():
    assert guard.check() == []


def test_guard_detects_eleventh_role(monkeypatch):
    patched = dict(ROLE_PERMISSIONS)
    patched["rogue_admin"] = ["*"]
    monkeypatch.setattr(guard, "ROLE_PERMISSIONS", patched, raising=False)
    monkeypatch.setattr("app.core.permissions.ROLE_PERMISSIONS", patched, raising=False)
    findings = guard.check()
    assert any("non-canonical" in f for f in findings)


def test_guard_detects_removed_canonical_role(monkeypatch):
    patched = {k: v for k, v in ROLE_PERMISSIONS.items() if k != "admin_security"}
    monkeypatch.setattr("app.core.permissions.ROLE_PERMISSIONS", patched, raising=False)
    findings = guard.check()
    assert any("missing canonical role" in f for f in findings)


def test_guard_detects_stale_constants_mirror(monkeypatch):
    monkeypatch.setattr(
        "app.engines.auth.constants.ROLES",
        ["super_admin", "tenant_owner", "staff", "customer", "guest"],
        raising=False,
    )
    findings = guard.check()
    assert any("constants.py::ROLES drifted" in f for f in findings)


# ── Single-tenant model guard (Decision A) ────────────────────────────────────

def test_single_tenant_guard_passes_on_real_repo():
    assert st_guard.check() == []


def test_single_tenant_guard_detects_switch_route(tmp_path, monkeypatch):
    fake = tmp_path / "engines" / "rogue"
    fake.mkdir(parents=True)
    (fake / "router.py").write_text(
        'router = APIRouter(prefix="/v1/me")\n'
        '@router.post("/switch-tenant")\n'
        'async def switch(): ...\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(st_guard, "ENGINES_DIR", tmp_path / "engines")
    findings = st_guard.check()
    assert any("switch route" in f for f in findings)


def test_single_tenant_guard_detects_membership_model(tmp_path, monkeypatch):
    fake = tmp_path / "engines" / "rogue"
    fake.mkdir(parents=True)
    (fake / "models.py").write_text(
        "class TenantMembership(Base):\n    __tablename__ = 'tenant_memberships'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(st_guard, "ENGINES_DIR", tmp_path / "engines")
    findings = st_guard.check()
    assert any("membership model class" in f for f in findings)

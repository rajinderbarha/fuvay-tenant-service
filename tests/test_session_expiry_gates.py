"""Pages must not render to someone whose session has ended.

Both portals leaked, for different reasons.

SUPER ADMIN
    `usePermissions` collapsed a FAILED /auth/me into `permissions = []` --
    indistinguishable from a real user who holds no permissions. `loading` was
    false and `permissions` was not null, so `RequirePermission` fell through
    to its allow-check, where `requiredPermission === "" ? true` let every
    route with no permission requirement (the Dashboard, self-service pages)
    render to a holder of an expired token. "Needs no permission" was being
    read as "needs no session".

TENANT PORTAL
    The check lived in a useEffect inside TenantLayout, so it ran AFTER the
    first paint -- the provider saw their real data on the way out -- and it
    asked only whether a token STRING existed in localStorage. An expired token
    is still a string, so every page rendered normally until some API call
    happened to 401. A page with no API call simply stayed on screen.
"""
from __future__ import annotations

import pathlib
import re

SA = pathlib.Path("frontend/super-admin")
TP = pathlib.Path("frontend/tenant-portal")


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class TestAdminDistinguishesUnauthenticatedFromUnprivileged:
    def test_the_hook_exposes_an_authenticated_signal(self):
        src = _read(SA / "hooks/usePermissions.ts")
        assert "authenticated" in src

    def test_a_failed_me_is_not_treated_as_empty_permissions(self):
        src = _read(SA / "hooks/usePermissions.ts")
        # The bug was exactly this collapse:
        #   permissions = me.loading ? null : (me.data?.permissions ?? [])
        # A failed fetch produced [], which reads as "resolved, holds nothing".
        assert "authenticated === true ? (me.data?.permissions ?? [])" in src

    def test_permissions_are_null_when_unauthenticated(self):
        """`has()` fails closed only if permissions is null, not []."""
        src = _read(SA / "hooks/usePermissions.ts")
        body = src[src.index("const permissions"):src.index("const has")]
        assert "authenticated" in body


class TestAdminGateRequiresASession:
    def test_no_session_denies_before_any_permission_check(self):
        src = _read(SA / "components/shared/PermissionGate.tsx")
        gate = src[src.index("export function RequirePermission"):]
        auth_check = gate.index("if (!authenticated)")
        allow_check = gate.index('requiredPermission === ""')
        # Order matters: a route requiring "" would otherwise be allowed
        # through before anyone asked whether the caller is signed in.
        assert auth_check < allow_check

    def test_it_renders_no_children_when_unauthenticated(self):
        src = _read(SA / "components/shared/PermissionGate.tsx")
        gate = src[src.index("export function RequirePermission"):]
        window = gate[gate.index("if (!authenticated)"):]
        assert "{children}" not in window[:400]

    def test_it_clears_the_session_and_redirects(self):
        src = _read(SA / "components/shared/PermissionGate.tsx")
        assert "clearSession" in src

    def test_it_still_waits_rather_than_denying_while_loading(self):
        """Denying during the in-flight fetch would bounce a valid admin."""
        src = _read(SA / "components/shared/PermissionGate.tsx")
        gate = src[src.index("export function RequirePermission"):]
        assert "authenticated === null" in gate


class TestTenantGateAsksTheServer:
    def test_the_gate_exists_and_wraps_every_route(self):
        assert (TP / "components/shared/RequireSession.tsx").exists()
        layout = _read(TP / "app/(tenant)/layout.tsx")
        assert "<RequireSession>" in layout
        assert "<LegalReacceptanceGate>{children}</LegalReacceptanceGate>" in layout
        assert "</RequireSession>" in layout

    def test_it_verifies_with_the_server_not_localstorage_alone(self):
        src = _read(TP / "components/shared/RequireSession.tsx")
        # A token string existing proves nothing -- an expired one is still a
        # string. Only the server can say whether it is still accepted.
        assert "authApi.me()" in src

    def test_it_withholds_children_until_confirmed(self):
        src = _read(TP / "components/shared/RequireSession.tsx")
        # Children are reachable through exactly ONE branch, and that branch is
        # conditioned on the confirmed state.
        assert src.count("{children}") == 1
        assert 'if (state === "authenticated") return <>{children}</>;' in src

    def test_a_rejection_clears_the_session(self):
        src = _read(TP / "components/shared/RequireSession.tsx")
        assert "clearSession()" in src

    def test_no_token_short_circuits_without_a_request(self):
        src = _read(TP / "components/shared/RequireSession.tsx")
        assert "serviceos_tenant_token" in src


class TestTheOldLeakyCheckIsGone:
    def test_tenant_layout_no_longer_gates_on_a_token_string(self):
        src = _read(TP / "components/layout/TenantLayout.tsx")
        # The old effect: const token = localStorage.getItem(...);
        #                 if (!token) { window.location.href = "/login"; }
        # It ran after the first paint and accepted any string.
        assert 'if (!token) { window.location.href = "/login"; return; }' not in src

    def test_the_forced_password_redirect_survives(self):
        """That check was in the same effect and is unrelated to expiry."""
        src = _read(TP / "components/layout/TenantLayout.tsx")
        assert "serviceos_force_pw_change" in src


class TestTheBackendContractTheGatesRelyOn:
    def test_me_is_authenticated_only(self):
        """Both gates treat a non-200 from /auth/me as 'no session', so that
        endpoint must actually require one."""
        from app.engines.auth import router as auth_router
        import inspect
        src = inspect.getsource(auth_router)
        idx = src.find('"/me"')
        assert idx != -1
        window = src[idx:idx + 500]
        assert "get_current_user" in window or "Depends" in window


class TestOnlyARefusalEndsASession:
    """The other half of the contract, and a defect the first fix shipped with.

    Withholding content is only half-right if the guard also throws away good
    sessions. The first version treated ANY rejected /auth/me as "signed out",
    so a network blip, a 500, or a request aborted by clicking a link logged a
    valid user out. A browser test caught it: me() rejected with "Failed to
    fetch" -- not a 401 -- and the guard cleared the session.
    """

    def test_tenant_only_clears_on_an_authentication_rejection(self):
        src = _read(TP / "components/shared/RequireSession.tsx")
        assert 'err.code === "UNAUTHORIZED"' in src
        # Every clearSession() must sit behind a refusal or a missing token,
        # never behind a bare catch.
        assert "isAuthRejection(err)" in src

    def test_tenant_ignores_failures_caused_by_navigating_away(self):
        """A navigation aborts in-flight requests; that is not a rejection."""
        src = _read(TP / "components/shared/RequireSession.tsx")
        assert "pagehide" in src and "beforeunload" in src
        assert "if (cancelled || leaving) return;" in src

    def test_tenant_retries_before_giving_up(self):
        src = _read(TP / "components/shared/RequireSession.tsx")
        assert "MAX_RETRIES" in src
        assert '"unavailable"' in src

    def test_admin_authenticated_is_three_valued(self):
        """null (cannot tell) must be distinct from false (refused)."""
        src = _read(SA / "hooks/usePermissions.ts")
        assert 'me.errorCode === "UNAUTHORIZED"' in src
        assert "unreachable" in src

    def test_useapi_exposes_the_error_code(self):
        """Without it the hook cannot tell a 401 from a 500 -- the message
        string alone does not distinguish them."""
        src = _read(SA / "hooks/useApi.ts")
        assert "errorCode: string | null;" in src
        assert "setErrorCode(e instanceof ServiceOSError ? e.code : null);" in src

    def test_admin_gate_does_not_clear_the_session_when_unreachable(self):
        src = _read(SA / "components/shared/PermissionGate.tsx")
        head = src[src.index("export function RequirePermission"):]
        block = head[head.index("if (unreachable)"):head.index("if (loading ||")]
        assert "clearSession" not in block
        assert "Try again" in block

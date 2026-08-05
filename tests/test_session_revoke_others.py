"""Regression: "Sign out all other sessions" was implemented by calling
logout_all(user_id, "") -- but logout_all revokes EVERY session
unconditionally (no exception for the current one); passing an empty jti
only skipped blacklisting a specific access token, it never protected the
caller's own UserSession row from being marked revoked_at too. So the one
button whose entire point is "sign out everywhere ELSE" was silently
signing the user out of their own current session as well -- directly
contradicting the feature's own requirement that it must preserve the
current session.

Found and fixed while building the Personal Account & Security page
(spec section 9: "'Sign out all other sessions' must preserve the current
session"). Live-verified against real UserSession rows: current session
revoked_at stayed None, the other session was revoked.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
SERVICE = os.path.join(BASE, "app/engines/auth/service.py")
ROUTER = os.path.join(BASE, "app/engines/auth/router.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestRevokeOtherSessionsPreservesCurrent:
    def test_new_method_exists_and_excludes_current_session(self):
        c = _read(SERVICE)
        assert "async def revoke_other_sessions" in c
        start = c.index("async def revoke_other_sessions")
        end = c.index("async def introspect_token")
        block = c[start:end]
        assert "UserSession.id != uuid.UUID(current_session_id)" in block

    def test_router_no_longer_calls_the_broken_logout_all_path(self):
        c = _read(ROUTER)
        start = c.index("async def revoke_all_other_sessions")
        end = c.index("@_me_security_router.get", start) if "@_me_security_router.get" in c[start:] else len(c)
        block = c[start:min(end, start + 600)]
        assert "svc.logout_all(user.user_id" not in block
        assert "svc.revoke_other_sessions(user.user_id, user.session_id)" in block

    def test_logout_all_itself_unchanged_still_revokes_everything(self):
        """logout_all is the REAL full-logout-everywhere primitive (a
        different, legitimate action) -- this fix must not weaken it."""
        c = _read(SERVICE)
        start = c.index("async def logout_all")
        end = c.index("async def revoke_other_sessions")
        block = c[start:end]
        assert "for session in sessions:" in block
        assert "session.revoked_at = utcnow()" in block

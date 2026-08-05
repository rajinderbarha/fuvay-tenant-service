"""Regression: Edit profile (team-members PUT) must accept and validate the
new max_concurrent_jobs field so the directory's capacity ring stays
editable, not just readable.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ROUTER = os.path.join(BASE, "app/engines/provider_portal/router.py")


def _read():
    with open(ROUTER, encoding="utf-8") as f:
        return f.read()


class TestUpdateTeamMemberCapacity:
    def test_max_concurrent_jobs_is_an_allowed_update_field(self):
        c = _read()
        start = c.index("async def update_team_member")
        end = c.index("async def delete_team_member")
        block = c[start:end]
        assert '"max_concurrent_jobs"' in block

    def test_max_concurrent_jobs_is_validated_positive(self):
        c = _read()
        start = c.index("async def update_team_member")
        end = c.index("async def delete_team_member")
        block = c[start:end]
        assert "INVALID_CAPACITY" in block
        assert "payload[\"max_concurrent_jobs\"] < 1" in block

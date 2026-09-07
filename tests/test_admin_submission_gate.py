"""Approval visibility and direct-action guard, with no external database."""
import sqlite3
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from app.engines.provider_portal.admin_router import _QUEUE_BASE_WHERE, _require_submitted_review


@pytest.mark.parametrize('verification,enrollment,submitted,visible', [
    ('not_started', 'draft', None, False),
    ('pending', 'draft', None, False),
    ('pending', 'submitted', None, False),
    ('pending', 'submitted', '2026-09-07', True),
    ('changes_requested', 'changes_requested', '2026-09-07', True),
    ('pending', 'draft_setup', '2026-09-07', False),
    ('rejected', 'rejected', '2026-09-07', True),
])
def test_queue_requires_explicit_submission(verification, enrollment, submitted, visible):
    with sqlite3.connect(':memory:') as db:
        db.executescript('''CREATE TABLE tenants(id TEXT, vertical TEXT, status TEXT, verification_status TEXT, terminated_at TEXT, archived_at TEXT);
        CREATE TABLE verticals(id TEXT, key TEXT);
        CREATE TABLE tenant_vertical_enrollments(tenant_id TEXT, vertical_id TEXT, status TEXT, submitted_at TEXT);
        INSERT INTO verticals VALUES ('v', 'home_services');''')
        db.execute("INSERT INTO tenants VALUES ('t','home_services','under_review',?,NULL,NULL)", (verification,))
        db.execute("INSERT INTO tenant_vertical_enrollments VALUES ('t','v',?,?)", (enrollment, submitted))
        assert bool(db.execute('SELECT t.id FROM tenants t WHERE ' + _QUEUE_BASE_WHERE).fetchone()) is visible


@pytest.mark.asyncio
@pytest.mark.parametrize('submitted', [False, True])
async def test_direct_review_actions_require_pending_submission(submitted):
    row = MagicMock()
    row.scalar.return_value = 'tenant' if submitted else None
    db = MagicMock(execute=AsyncMock(return_value=row))
    if submitted:
        await _require_submitted_review(db, uuid.uuid4())
    else:
        with pytest.raises(HTTPException) as error:
            await _require_submitted_review(db, uuid.uuid4())
        assert error.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize('action', ['verify_tenant', 'reject_verification', 'request_changes'])
async def test_legacy_admin_actions_cannot_review_drafts(action):
    from types import SimpleNamespace
    from app.engines.tenant_engine.admin_service import AdminTenantService
    from unittest.mock import patch
    service = AdminTenantService(db=MagicMock(), request_id='test', actor_id=str(uuid.uuid4()), actor_role='super_admin')
    service._get_tenant = AsyncMock(return_value=SimpleNamespace(vertical='home_services', verification_status='pending'))
    service._audit = AsyncMock()
    with patch('app.engines.provider_portal.admin_router._require_submitted_review', AsyncMock(side_effect=HTTPException(409, 'Not submitted'))):
        with pytest.raises(HTTPException):
            args = () if action == 'verify_tenant' else ('Please update',)
            await getattr(service, action)(uuid.uuid4(), *args)
    service._audit.assert_not_awaited()

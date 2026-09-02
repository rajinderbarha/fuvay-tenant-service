"""Regression coverage for provider-owned technician screening policy."""
from __future__ import annotations

import inspect
import uuid

import pytest


def test_assignment_engine_has_no_technician_document_gate():
    from app.engines.home_service_assignment import service

    source = inspect.getsource(service.HomeServiceJobAssignmentService)
    assert "required_documents_missing" not in source
    assert "member_has_verified_required_documents" not in source


@pytest.mark.asyncio
async def test_compatibility_helper_passes_roster_members_without_document_queries():
    from app.engines.home_service_assignment.team_readiness_service import (
        members_with_verified_required_documents,
    )

    class NoDatabaseAccess:
        async def execute(self, *_args, **_kwargs):
            raise AssertionError("technician document state must not be queried")

    member_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    result = await members_with_verified_required_documents(
        NoDatabaseAccess(), uuid.uuid4(), member_ids
    )
    assert result == set(member_ids)


def test_mobile_profile_declares_no_required_technician_documents():
    from app.engines.home_service_assignment.mobile_profile_service import (
        REQUIRED_DOCUMENT_TYPES,
    )

    assert REQUIRED_DOCUMENT_TYPES == []

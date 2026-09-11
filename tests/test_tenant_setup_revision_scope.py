from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from sqlalchemy.dialects import postgresql

from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision


def _revision_result(revision: int):
    result = MagicMock()
    result.scalars.return_value.all.return_value = [revision]
    return result


@pytest.mark.asyncio
async def test_targeted_revision_only_drafts_selected_tenant_services():
    tenant_service_id = uuid.uuid4()
    db = MagicMock()
    affected = MagicMock(rowcount=1)
    db.execute = AsyncMock(side_effect=[_revision_result(12), affected])

    revision, count = await bump_tenant_setup_revision(
        db, uuid.uuid4(), affected_tenant_service_ids={tenant_service_id}
    )

    statement = db.execute.await_args_list[1].args[0]
    sql = str(statement.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    ))
    assert "tenant_services.id IN" in sql
    assert str(tenant_service_id) in sql
    assert (revision, count) == (12, 1)


@pytest.mark.asyncio
async def test_empty_targeted_revision_drafts_no_provider_services():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_revision_result(13))

    revision, count = await bump_tenant_setup_revision(
        db, uuid.uuid4(), affected_tenant_service_ids=set()
    )

    assert db.execute.await_count == 1
    assert (revision, count) == (13, 0)

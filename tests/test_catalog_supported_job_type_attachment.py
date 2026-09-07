import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
from app.exceptions import ServiceOSException

@pytest.mark.asyncio
@pytest.mark.parametrize("active,key", [(False, "installation"), (True, "unwired_custom_task")])
async def test_unsupported_or_inactive_types_cannot_be_added_to_service_family(active, key):
    service_id, jt_id = uuid.uuid4(), uuid.uuid4()
    svc_result, jt_result = MagicMock(), MagicMock()
    svc_result.scalar_one_or_none.return_value = SimpleNamespace(id=service_id)
    jt_result.scalar_one_or_none.return_value = SimpleNamespace(id=jt_id, key=key, is_active=active)
    db = MagicMock(execute=AsyncMock(side_effect=[svc_result, jt_result]), commit=AsyncMock())
    with pytest.raises(ServiceOSException) as exc:
        await JobTypeBlueprintService(db).add_job_type_to_service(service_id, {"job_type_id": str(jt_id)})
    assert exc.value.error_code == "JOB_TYPE_NOT_RUNTIME_SUPPORTED"
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_supported_installation_attaches_only_the_selected_type():
    from unittest.mock import patch
    from app.engines.admin_catalog.models import MasterServiceJobType
    service_id, jt_id = uuid.uuid4(), uuid.uuid4()
    def result(row):
        value = MagicMock()
        value.scalar_one_or_none.return_value = row
        return value
    jt = SimpleNamespace(id=jt_id, key="installation", is_active=True)
    db = MagicMock(execute=AsyncMock(side_effect=[result(SimpleNamespace(id=service_id)), result(jt), result(None)]), commit=AsyncMock(), refresh=AsyncMock())
    with patch.object(MasterServiceJobType, "to_dict", return_value={"job_type_id": str(jt_id)}), \
         patch("app.engines.admin_catalog.job_type_blueprint_service._job_type_dict", return_value={"key": "installation"}):
        saved = await JobTypeBlueprintService(db).add_job_type_to_service(service_id, {"job_type_id": str(jt_id)})
    assert saved["job_type"]["key"] == "installation"
    db.add.assert_called_once()
    assert db.add.call_args.args[0].job_type_id == jt_id
    db.commit.assert_awaited_once()

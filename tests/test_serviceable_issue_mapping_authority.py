import uuid

from sqlalchemy.dialects import postgresql

from app.engines.home_service_booking.offering_catalog_service import (
    _serviceable_issue_rows_query,
)


def test_problem_catalog_uses_canonical_mapping_not_nullable_legacy_owner():
    """Global/legacy problem rows may have no direct master_service_id.

    Their active ServiceIssueMapping is the canonical service relationship,
    so customer and Instagram discovery must not require both columns.
    """
    master_service_id = uuid.uuid4()
    sql = str(_serviceable_issue_rows_query([master_service_id]).compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))

    assert (
        "service_issue_mappings.master_service_id = master_services.id" in sql
        or "master_services.id = service_issue_mappings.master_service_id" in sql
    )
    assert "master_services.id IN" in sql
    assert "master_issue_types.master_service_id IN" not in sql

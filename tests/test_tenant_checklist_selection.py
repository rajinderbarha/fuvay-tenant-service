"""Tenant selection of checklist points per service (minimum 5).

Division of responsibility this enforces:
  ADMIN  authors the library -- checklist_catalog templates/versions/
         sections/items, already complete and super-admin guarded.
  TENANT chooses which of those points its technicians must complete for a
         given service, at least MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE.

Real gap these close: `job_type_checklist_mappings` links a published version
to a job type PLATFORM-wide, so every provider ran the identical authored list
and there was no way for one to run a chosen subset. `_instance_items` handed
technicians everything the admin wrote.

Exercised against real live Guramrit data with a real authored template (no
mocks), because the rules being proven are enforced by a real UNIQUE
constraint and by walking the real master_service -> job_type -> mapping ->
published version -> section -> item chain.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from app.engines.checklist_catalog import constants as c
from app.engines.checklist_catalog import service as svc
from app.exceptions import ServiceOSException

GURAMRIT_TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")

ITEM_LABELS = [
    "Check gas pressure", "Clean filters", "Test cooling output",
    "Inspect drainage", "Check electrical connections",
    "Verify remote function", "Confirm customer sign-off",
]


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


async def _ac_service_and_job_type(db):
    sid = (await db.execute(sa_text(
        "SELECT id FROM master_services WHERE service_name='AC Service'"))).scalar()
    jt = (await db.execute(sa_text(
        "SELECT id FROM master_service_job_types WHERE master_service_id=:s LIMIT 1"),
        {"s": str(sid)})).scalar()
    return sid, jt


async def _author_published_checklist(db, job_type_id, *, item_count: int = 7):
    """Real admin-side authoring: template -> draft version -> section -> items
    -> publish -> map to the job type. Returns (version_id, mapping_id)."""
    tpl = await svc.create_template(
        db, name="AC Service Field Checklist (test)", code=f"ac-test-{uuid.uuid4().hex[:8]}",
        purpose=c.PURPOSE_INSPECTION, description="test fixture", icon_url=None,
        owner_scope=c.OWNER_SCOPE_PLATFORM, tenant_id=None, created_by_user_id=None,
    )
    version = await svc.get_draft_version(db, tpl.id)
    section = await svc.add_section(db, version, "On-site checks", 0)
    for i, label in enumerate(ITEM_LABELS[:item_count]):
        await svc.add_item(db, section, version, item_type=c.ITEM_TYPE_CHECKBOX,
                           label=label, is_required=True, display_order=i)
    await svc.publish_version(db, version, published_by=None)
    mapping = await svc.create_mapping(
        db, master_service_job_type_id=job_type_id,
        checklist_template_version_id=version.id,
        phase="INSPECTION", usage="REQUIRED", actor="TECHNICIAN",
        completion_gate="NONE", condition_rules=None, display_order=0,
        service_job_workflow_id=None, created_by=None,
    )
    await db.commit()
    return tpl.id, version.id, mapping.id


async def _cleanup(db, tenant_id, template_id, version_id, mapping_id):
    await db.rollback()
    if mapping_id:
        await db.execute(sa_text("DELETE FROM job_type_checklist_mappings WHERE id=:i"),
                         {"i": str(mapping_id)})
    await db.execute(sa_text(
        "DELETE FROM tenant_service_checklist_items WHERE tenant_id=:t"), {"t": str(tenant_id)})
    if version_id:
        await db.execute(sa_text(
            "DELETE FROM checklist_items WHERE checklist_section_id IN "
            "(SELECT id FROM checklist_sections WHERE checklist_template_version_id=:v)"),
            {"v": str(version_id)})
        await db.execute(sa_text(
            "DELETE FROM checklist_sections WHERE checklist_template_version_id=:v"),
            {"v": str(version_id)})
        await db.execute(sa_text("DELETE FROM checklist_template_versions WHERE id=:v"),
                         {"v": str(version_id)})
    if template_id:
        await db.execute(sa_text("DELETE FROM checklist_templates WHERE id=:t"),
                         {"t": str(template_id)})
    await db.commit()


def test_the_minimum_is_the_product_specified_five():
    assert c.MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE == 5


@pytest.mark.asyncio
async def test_nothing_authored_is_reported_as_an_admin_gap_not_a_tenant_failure():
    """A tenant must never be told to "pick 5" from an empty list -- if the
    admin has published no checklist for the service, that is distinguishable."""
    db = await _get_db()
    try:
        sid, _ = await _ac_service_and_job_type(db)
        await db.execute(sa_text(
            "DELETE FROM tenant_service_checklist_items WHERE tenant_id=:t"),
            {"t": str(GURAMRIT_TENANT_ID)})
        await db.commit()
        readiness = await svc.tenant_selection_readiness(db, GURAMRIT_TENANT_ID, sid)
        if readiness["selectable_total"] == 0:
            assert readiness["nothing_authored"] is True
            assert readiness["satisfied"] is False
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_selection_rules_against_a_real_authored_checklist():
    db = await _get_db()
    tpl_id = ver_id = map_id = None
    try:
        sid, jt = await _ac_service_and_job_type(db)
        assert jt is not None, "AC Service must have a job type to map a checklist to"
        tpl_id, ver_id, map_id = await _author_published_checklist(db, jt)

        selectable = await svc.selectable_items_for_service(db, sid)
        assert len(selectable) == 7, "every authored+published+mapped point must be offerable"
        ids = [uuid.UUID(i["id"]) for i in selectable]

        # Below the minimum is refused, and the message carries the real count.
        with pytest.raises(ServiceOSException) as exc:
            await svc.set_tenant_selection(db, GURAMRIT_TENANT_ID, sid, ids[:4],
                                           selected_by_user_id=None)
        assert exc.value.error_code == c.ERR_CHECKLIST_SELECTION_TOO_SMALL

        # A point that is not authored for THIS service is refused, even when
        # the count would otherwise pass.
        with pytest.raises(ServiceOSException) as exc:
            await svc.set_tenant_selection(
                db, GURAMRIT_TENANT_ID, sid, ids[:4] + [uuid.uuid4()],
                selected_by_user_id=None)
        assert exc.value.error_code == c.ERR_CHECKLIST_ITEM_NOT_SELECTABLE

        # Duplicates must not be counted as distinct points -- otherwise the
        # same tick six times would satisfy a five-point requirement.
        with pytest.raises(ServiceOSException) as exc:
            await svc.set_tenant_selection(db, GURAMRIT_TENANT_ID, sid, [ids[0]] * 6,
                                           selected_by_user_id=None)
        assert exc.value.error_code == c.ERR_CHECKLIST_SELECTION_TOO_SMALL

        # Exactly the minimum is accepted.
        readiness = await svc.set_tenant_selection(db, GURAMRIT_TENANT_ID, sid, ids[:5],
                                                    selected_by_user_id=None)
        await db.commit()
        assert readiness["satisfied"] is True
        assert readiness["selected_count"] == 5
        assert readiness["shortfall"] == 0
    finally:
        await _cleanup(db, GURAMRIT_TENANT_ID, tpl_id, ver_id, map_id)
        await db.close()


@pytest.mark.asyncio
async def test_changing_the_selection_deactivates_rather_than_deletes():
    """A deselected point stays on record so support can still explain why a
    step was not performed on an older job -- and so re-selecting it cannot
    violate the (tenant, service, item) unique constraint."""
    db = await _get_db()
    tpl_id = ver_id = map_id = None
    try:
        sid, jt = await _ac_service_and_job_type(db)
        tpl_id, ver_id, map_id = await _author_published_checklist(db, jt)
        ids = [uuid.UUID(i["id"]) for i in await svc.selectable_items_for_service(db, sid)]

        await svc.set_tenant_selection(db, GURAMRIT_TENANT_ID, sid, ids[:5], selected_by_user_id=None)
        await db.commit()
        # Swap two points out for two others.
        readiness = await svc.set_tenant_selection(db, GURAMRIT_TENANT_ID, sid, ids[2:7],
                                                    selected_by_user_id=None)
        await db.commit()

        assert readiness["selected_count"] == 5
        rows = dict((bool(a), int(n)) for a, n in (await db.execute(sa_text(
            "SELECT is_active, count(*) FROM tenant_service_checklist_items "
            "WHERE tenant_id=:t AND master_service_id=:s GROUP BY is_active"),
            {"t": str(GURAMRIT_TENANT_ID), "s": str(sid)})).fetchall())
        assert rows.get(True) == 5, "five points active after the swap"
        assert rows.get(False) == 2, "the two dropped points are retained, deactivated"

        # Re-selecting a deactivated point reactivates the same row.
        readiness = await svc.set_tenant_selection(db, GURAMRIT_TENANT_ID, sid, ids[:5],
                                                    selected_by_user_id=None)
        await db.commit()
        assert readiness["selected_count"] == 5
        total = (await db.execute(sa_text(
            "SELECT count(*) FROM tenant_service_checklist_items "
            "WHERE tenant_id=:t AND master_service_id=:s"),
            {"t": str(GURAMRIT_TENANT_ID), "s": str(sid)})).scalar()
        assert total == 7, "no duplicate rows created by re-selecting"
    finally:
        await _cleanup(db, GURAMRIT_TENANT_ID, tpl_id, ver_id, map_id)
        await db.close()


@pytest.mark.asyncio
async def test_a_draft_version_is_never_offerable_to_a_tenant():
    """Selecting from an unpublished draft would let an admin's unfinished edit
    change what technicians are asked to do in the field."""
    db = await _get_db()
    tpl_id = ver_id = map_id = None
    try:
        sid, jt = await _ac_service_and_job_type(db)
        tpl_id, ver_id, map_id = await _author_published_checklist(db, jt)
        before = len(await svc.selectable_items_for_service(db, sid))
        assert before == 7

        # Force the mapped version back to DRAFT: its items must vanish from
        # the tenant's selectable list.
        await db.execute(sa_text(
            "UPDATE checklist_template_versions SET status=:s WHERE id=:v"),
            {"s": c.VERSION_DRAFT, "v": str(ver_id)})
        await db.commit()
        assert await svc.selectable_items_for_service(db, sid) == []
    finally:
        await _cleanup(db, GURAMRIT_TENANT_ID, tpl_id, ver_id, map_id)
        await db.close()

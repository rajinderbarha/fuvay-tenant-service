"""Complete structural release manifest. Never includes provider-owned prices."""
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, or_
from datetime import datetime, timezone
from app.engines.admin_catalog.models import (
    MasterServiceJobType, ServiceJobWorkflow, ServiceJobDimension, CatalogDimension, CatalogDimensionValue,
    CatalogQuestion, CatalogQuestionRule, CatalogQuestionOption, ServiceIssueMapping,
    ServiceOptionMapping, MasterServiceType, MasterServiceBrand, ServiceType, Brand, MasterServiceOption, MasterIssueType,
)
from app.engines.checklist_catalog.models import JobTypeChecklistMapping, ChecklistTemplateVersion, ChecklistSection, ChecklistItem, ChecklistTemplate
from app.engines.checklist_catalog.constants import VERSION_PUBLISHED
from app.exceptions import ServiceOSException


def structural_row(row):
    # Audit timestamps are not structural changes; IDs and content are.
    return jsonable_encoder({c.name: getattr(row, c.name) for c in row.__table__.columns
        if c.name not in {'created_at', 'updated_at', 'created_by', 'updated_by', 'created_by_user_id', 'updated_by_user_id'}})


async def build_release_manifest(db, service_id):
    async def rows(model, predicate):
        records = (await db.execute(select(model).where(predicate).order_by(model.id))).scalars().all()
        return [structural_row(row) for row in records]
    links = select(MasterServiceJobType.id).where(MasterServiceJobType.master_service_id == service_id)
    questions = select(CatalogQuestion.id).where(CatalogQuestion.master_service_id == service_id)
    dimensions = select(ServiceJobDimension.dimension_id).where(ServiceJobDimension.master_service_id == service_id)
    manifest = {}
    for key, model in [('job_types', MasterServiceJobType), ('dimensions', ServiceJobDimension),
                       ('questions', CatalogQuestion), ('problems', ServiceIssueMapping), ('options', ServiceOptionMapping),
                       ('type_mappings', MasterServiceType), ('brand_mappings', MasterServiceBrand)]:
        manifest[key] = await rows(model, model.master_service_id == service_id)
    manifest['workflows'] = await rows(ServiceJobWorkflow, (ServiceJobWorkflow.master_service_id == service_id) & ServiceJobWorkflow.is_current.is_(True))
    manifest['question_options'] = await rows(CatalogQuestionOption, CatalogQuestionOption.question_id.in_(questions))
    manifest['question_rules'] = await rows(CatalogQuestionRule, CatalogQuestionRule.question_id.in_(questions))
    manifest['dimension_definitions'] = await rows(CatalogDimension, CatalogDimension.id.in_(dimensions))
    manifest['dimension_values'] = await rows(CatalogDimensionValue, CatalogDimensionValue.dimension_id.in_(dimensions))
    manifest['checklists'] = await rows(JobTypeChecklistMapping, JobTypeChecklistMapping.master_service_job_type_id.in_(links))
    for key, model, mapping, field in [
        ('types', ServiceType, MasterServiceType, MasterServiceType.service_type_id),
        ('brands', Brand, MasterServiceBrand, MasterServiceBrand.brand_id),
        ('option_definitions', MasterServiceOption, ServiceOptionMapping, ServiceOptionMapping.service_option_id),
        ('problem_definitions', MasterIssueType, ServiceIssueMapping, ServiceIssueMapping.issue_type_id),
    ]:
        manifest[key] = await rows(model, model.id.in_(select(field).where(mapping.master_service_id == service_id)))
    versions = select(JobTypeChecklistMapping.checklist_template_version_id).where(JobTypeChecklistMapping.master_service_job_type_id.in_(links))
    sections = select(ChecklistSection.id).where(ChecklistSection.checklist_template_version_id.in_(versions))
    manifest['checklist_versions'] = await rows(ChecklistTemplateVersion, ChecklistTemplateVersion.id.in_(versions))
    manifest['checklist_sections'] = await rows(ChecklistSection, ChecklistSection.checklist_template_version_id.in_(versions))
    manifest['checklist_items'] = await rows(ChecklistItem, ChecklistItem.checklist_section_id.in_(sections))
    return manifest


async def validate_release(db, service_id):
    from app.engines.admin_catalog.dimension_service import CatalogDimensionService
    from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
    links = (await db.execute(select(MasterServiceJobType).where(
        MasterServiceJobType.master_service_id == service_id, MasterServiceJobType.is_active.is_(True)))).scalars().all()
    blockers = []
    if not links:
        blockers.append('Add at least one active job type.')
    for link in links:
        readiness = await CatalogDimensionService(db).get_blueprint_readiness(service_id, link.job_type_id)
        blockers.extend(f'{link.job_type_id}: {check["detail"] or check["label"]}' for check in readiness['checks'] if not check['passed'])
        review = await JobTypeBlueprintService(db).review_workflow_steps(service_id, link.job_type_id)
        blockers.extend(f'{link.job_type_id}: {error}' for error in review['errors'])
        workflow = await JobTypeBlueprintService(db).get_workflow(service_id, link.job_type_id)
        now = datetime.now(timezone.utc)
        mappings = (await db.execute(select(JobTypeChecklistMapping).where(
            JobTypeChecklistMapping.master_service_job_type_id == link.id,
            JobTypeChecklistMapping.status == 'active', JobTypeChecklistMapping.usage != 'DISABLED',
            or_(JobTypeChecklistMapping.effective_from.is_(None), JobTypeChecklistMapping.effective_from <= now),
            or_(JobTypeChecklistMapping.effective_until.is_(None), JobTypeChecklistMapping.effective_until >= now)))).scalars().all()
        if workflow.get('checklist_required') and not mappings:
            blockers.append(f'{link.job_type_id}: Workflow requires a checklist but none is mapped.')
        for mapping in mappings:
            version = await db.get(ChecklistTemplateVersion, mapping.checklist_template_version_id)
            if not version or version.status != VERSION_PUBLISHED:
                blockers.append(f'{link.job_type_id}: A mapped checklist version is not published.')
            elif not (template := await db.get(ChecklistTemplate, version.checklist_template_id)) or template.status != 'active':
                blockers.append(f'{link.job_type_id}: A mapped checklist template is archived or missing.')
    if blockers:
        raise ServiceOSException('BLUEPRINT_RELEASE_INCOMPLETE', 'Complete blueprint setup before publishing.', status_code=422,
                                 context={'blockers': blockers})

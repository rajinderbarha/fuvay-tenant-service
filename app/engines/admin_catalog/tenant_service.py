"""Admin Catalog — Tenant Service Enablement.

Tenants enable master services from the admin catalog.
Tenant cannot change job_type, cannot price below admin min, cannot select
unsupported brands/types.
"""
from __future__ import annotations
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterService, ServiceCategory, ServiceGroup, ServicePricingRule,
    TenantService, TenantServiceType, TenantServiceBrand,
    MasterServiceType, MasterServiceBrand, ServiceType, Brand,
    ServiceBlueprintVersion, MasterServiceJobType, ServiceJobWorkflow,
    ServiceJobDimension, CatalogDimension, JobTypeDefinition,
    ServiceOptionMapping, TenantSupportedServiceOption,
)
from app.engines.serviceability.models import TenantServiceArea, TenantServiceAreaService
from app.engines.entitlement.service import entitlement_service
from app.engines.tenant_engine.models import TenantSettings
from app.exceptions import ServiceOSException, NotFoundException

utcnow = lambda: datetime.now(timezone.utc)


# Pricing behavior is structural and Admin-owned. For these workflows the
# provider charges one visit/inspection fee; Type and Brand remain routing
# dimensions and must never create a second price matrix.
INSPECTION_PRICING_BEHAVIORS = {
    "inspection_required", "inspection_quote", "visit_fee_plus_quote",
    "quote", "custom_quote",
}


def project_tenant_blueprint(
    master: MasterService | None,
    workflow: dict | None,
    dimension_rules: dict[str, dict] | None = None,
) -> dict:
    """Canonical tenant-facing projection of Admin-owned service rules.

    Type/Brand requirements are owned by the normalized dimension blueprint
    when one exists for this service/job-type.  The MasterService booleans are
    retained only as a compatibility fallback for catalog rows that have not
    been migrated to dimensions yet.
    """
    dimension_rules = dimension_rules or {}

    def _dimension_required(key: str, legacy: bool) -> bool:
        rule = dimension_rules.get(key)
        if rule is None:
            return legacy
        return bool(
            rule.get("enabled")
            and rule.get("show_during_tenant_setup")
            and rule.get("required")
        )

    type_required = _dimension_required("type", bool(master and master.is_type_required))
    brand_required = _dimension_required("brand", bool(master and master.is_brand_required))
    return {
        "type_mode": "required" if type_required else "optional",
        "brand_mode": "required" if brand_required else "optional",
        "requires_issue_type": bool(master and master.requires_issue_type),
        "requires_checklist": bool(workflow.get("checklist_required")) if workflow else bool(master and master.requires_checklist),
        "requires_estimate_approval": bool(workflow.get("quote_approval_required")) if workflow else bool(
            master and master.pricing_model in {"inspection_based", "inspection_quote", "quote"}
        ),
        "requires_technician": bool(workflow.get("technician_required")) if workflow else True,
        "requires_schedule": bool(workflow.get("schedule_required")) if workflow else bool(master and master.requires_schedule),
        "requires_service_area": bool(workflow.get("service_area_required")) if workflow else bool(master and master.requires_address),
        "requires_availability": bool(workflow.get("availability_required")) if workflow else bool(master and master.requires_schedule),
        "pricing_behavior": (
            workflow.get("pricing_behavior") or (master.pricing_model if master else None)
            if workflow else (master.pricing_model if master else None)
        ),
        "workflow_version": workflow.get("version_number") if workflow else None,
        "source": "service_job_workflow" if workflow else "master_service_legacy",
    }


class TenantCatalogService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_tenant_id(self, tenant_id_raw) -> uuid.UUID:
        # Slice 2F-8: enable_service/disable_service accept an optional
        # `tenant_id` query parameter (originally intended to let a platform
        # role act on a specific tenant's behalf), but this method previously
        # used ANY supplied tenant_id_raw unconditionally -- a tenant_owner
        # (who legitimately holds TENANT_UPDATE) could pass a foreign
        # tenant_id and enable/disable a service for a tenant they do not
        # belong to. Mirrors the FINAL-L5-05Q pattern already used in
        # serviceability's admin router: a non-platform actor's supplied
        # tenant_id must match their own actor_tenant_id, or the request is
        # rejected outright.
        if tenant_id_raw:
            candidate = tenant_id_raw if isinstance(tenant_id_raw, uuid.UUID) else uuid.UUID(str(tenant_id_raw))
            if (self.actor_role not in self.PLATFORM_ROLES
                    and self.actor_tenant_id is not None
                    and candidate != self.actor_tenant_id):
                raise ServiceOSException(
                    "PERMISSION_DENIED",
                    "Cannot act on another tenant's catalog.",
                    status_code=403,
                )
            return candidate
        if self.actor_tenant_id:
            return self.actor_tenant_id
        raise ServiceOSException("TENANT_NOT_FOUND", "tenant_id is required.", status_code=422)

    # ═══════════════════════════════════════════════════════════
    # Available Services (from admin master catalog)
    # ═══════════════════════════════════════════════════════════

    async def get_home_services_category_id(self) -> uuid.UUID:
        res = await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.vertical_type == "home_services"))
        cat = res.scalars().first()
        if not cat:
            raise ServiceOSException("HOME_SERVICES_CATEGORY_NOT_FOUND",
                "No Home Services category is configured.", status_code=422)
        return cat.id

    async def _dimension_rules(
        self, master_service_id: uuid.UUID, job_type_id: uuid.UUID | None,
    ) -> dict[str, dict]:
        """Return exact job-type setup dimensions, falling back to the
        service-wide (NULL job_type_id) blueprint only when an exact row does
        not exist.  This is the same ownership model used by Catalog Workspace.
        """
        rows = (await self.db.execute(
            select(ServiceJobDimension, CatalogDimension)
            .join(CatalogDimension, CatalogDimension.id == ServiceJobDimension.dimension_id)
            .where(
                ServiceJobDimension.master_service_id == master_service_id,
                or_(ServiceJobDimension.job_type_id == job_type_id, ServiceJobDimension.job_type_id.is_(None))
                if job_type_id else ServiceJobDimension.job_type_id.is_(None),
            )
        )).all()
        by_key: dict[str, tuple[bool, dict]] = {}
        for config, dimension in rows:
            exact = job_type_id is not None and config.job_type_id == job_type_id
            previous = by_key.get(dimension.key)
            if previous is None or (exact and not previous[0]):
                by_key[dimension.key] = (exact, config.to_dict())
        return {key: value for key, (_, value) in by_key.items()}

    async def _published_workflow(
        self, master_service_id: uuid.UUID, job_type_id: uuid.UUID | None,
    ) -> dict | None:
        if not job_type_id:
            return None
        row = (await self.db.execute(
            select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == master_service_id,
                ServiceJobWorkflow.job_type_id == job_type_id,
                ServiceJobWorkflow.is_current.is_(True),
                ServiceJobWorkflow.status == "published",
            ).order_by(ServiceJobWorkflow.version_number.desc()).limit(1)
        )).scalar_one_or_none()
        return row.to_dict() if isinstance(row, ServiceJobWorkflow) else None

    async def _tenant_setup_blueprint(self, master: MasterService, job_type_id: uuid.UUID | None) -> dict:
        workflow = await self._published_workflow(master.id, job_type_id)
        dimensions = await self._dimension_rules(master.id, job_type_id)
        return project_tenant_blueprint(master, workflow, dimensions)

    async def _setup_rule_revision(self, master_service_id: uuid.UUID,
                                   job_type_id: uuid.UUID) -> int:
        revision = (await self.db.execute(
            select(MasterServiceJobType.setup_rules_revision).where(
                MasterServiceJobType.master_service_id == master_service_id,
                MasterServiceJobType.job_type_id == job_type_id,
            )
        )).scalar_one_or_none()
        if revision is None:
            raise ServiceOSException(
                "JOB_TYPE_NOT_AVAILABLE",
                "The selected job type is not configured for this service.", status_code=422,
            )
        return int(revision)

    async def _resolve_active_job_type(
        self, master_service_id: uuid.UUID, requested_job_type_id: object,
    ) -> JobTypeDefinition:
        if not requested_job_type_id:
            active_ids = (await self.db.execute(
                select(MasterServiceJobType.job_type_id).where(
                    MasterServiceJobType.master_service_id == master_service_id,
                    MasterServiceJobType.is_active.is_(True),
                ).limit(2)
            )).scalars().all()
            if len(active_ids) != 1:
                raise ServiceOSException(
                    "JOB_TYPE_REQUIRED",
                    "job_type_id is required when this service has more than one job type.",
                    status_code=422,
                )
            requested_job_type_id = active_ids[0]
        try:
            job_type_id = uuid.UUID(str(requested_job_type_id))
        except (TypeError, ValueError, AttributeError):
            raise ServiceOSException("INVALID_JOB_TYPE_ID", "job_type_id must be a valid UUID.", status_code=422)
        row = (await self.db.execute(
            select(JobTypeDefinition)
            .join(MasterServiceJobType, MasterServiceJobType.job_type_id == JobTypeDefinition.id)
            .where(
                MasterServiceJobType.master_service_id == master_service_id,
                MasterServiceJobType.job_type_id == job_type_id,
                MasterServiceJobType.is_active.is_(True),
                JobTypeDefinition.is_active.is_(True),
            )
        )).scalar_one_or_none()
        if not row:
            raise ServiceOSException(
                "JOB_TYPE_NOT_AVAILABLE",
                "The selected job type is not active for this service.", status_code=422,
            )
        return row

    async def list_available_services(self, tenant_id_raw=None, category_id: uuid.UUID | None = None) -> dict:
        """All active master services — with is_enabled flag per tenant.
        category_id is optional and additive (existing callers unaffected);
        the Home Services Setup Wizard always passes the Home Services
        category id so it never sees another vertical's catalog."""
        tenant_id = self._require_tenant_id(tenant_id_raw)

        stmt = select(MasterService).where(
            MasterService.is_active == True,
            MasterService.deleted_at.is_(None),
        )
        if category_id:
            stmt = stmt.where(MasterService.category_id == category_id)
        svc_res = await self.db.execute(stmt.order_by(MasterService.display_order, MasterService.service_name))
        services = svc_res.scalars().all()

        # Load the current published workflow once for every visible master
        # service.  Setup and the operational workspace both consume this
        # same projection, so an old workflow row or renamed field can no
        # longer make their Admin-blueprint cards disagree.
        workflows_by_pair: dict[tuple[uuid.UUID, uuid.UUID], dict] = {}
        # Load exact normalized workflows in bulk; services without an active
        # published workflow fail closed and are not tenant-configurable.
        workflow_service_ids = {service.id for service in services}
        if workflow_service_ids:
            workflow_rows = (await self.db.execute(
                select(ServiceJobWorkflow).where(
                    ServiceJobWorkflow.master_service_id.in_(workflow_service_ids),
                    ServiceJobWorkflow.is_current.is_(True),
                    ServiceJobWorkflow.status == "published",
                ).order_by(ServiceJobWorkflow.version_number.desc())
            )).scalars().all()
            for workflow_row in workflow_rows:
                workflows_by_pair.setdefault(
                    (workflow_row.master_service_id, workflow_row.job_type_id),
                    workflow_row.to_dict(),
                )

        job_types_by_service: dict[uuid.UUID, list[JobTypeDefinition]] = {}
        setup_revision_by_pair: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
        if services:
            link_rows = (await self.db.execute(
                select(MasterServiceJobType, JobTypeDefinition)
                .join(JobTypeDefinition, JobTypeDefinition.id == MasterServiceJobType.job_type_id)
                .where(
                    MasterServiceJobType.master_service_id.in_([s.id for s in services]),
                    MasterServiceJobType.is_active.is_(True),
                    JobTypeDefinition.is_active.is_(True),
                )
                .order_by(MasterServiceJobType.display_order, JobTypeDefinition.display_order)
            )).all()
            for link, job_type in link_rows:
                job_types_by_service.setdefault(link.master_service_id, []).append(job_type)
                setup_revision_by_pair[(link.master_service_id, job_type.id)] = link.setup_rules_revision

        # Load normalized tenant-setup dimension rules in one query. Catalog
        # lists can contain thousands of services, so per-row dimension
        # lookups here would turn this endpoint into an N+1 bottleneck.
        dimension_rules_by_scope: dict[tuple[uuid.UUID, uuid.UUID | None], dict[str, dict]] = {}
        if services:
            dimension_rows = (await self.db.execute(
                select(ServiceJobDimension, CatalogDimension)
                .join(CatalogDimension, CatalogDimension.id == ServiceJobDimension.dimension_id)
                .where(ServiceJobDimension.master_service_id.in_([s.id for s in services]))
            )).all()
            for config, dimension in dimension_rows:
                dimension_rules_by_scope.setdefault(
                    (config.master_service_id, config.job_type_id), {}
                )[dimension.key] = config.to_dict()

        # Which ones the tenant has already enabled
        enabled_res = await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.is_enabled == True,
                TenantService.deleted_at.is_(None),
            ))
        enabled_rows = enabled_res.scalars().all()
        enabled_by_pair = {(ts.master_service_id, ts.job_type_id): ts for ts in enabled_rows}

        # Group names for the setup page's grouping (one query, not N).
        group_ids = {s.service_group_id for s in services if s.service_group_id}
        group_names: dict = {}
        if group_ids:
            grp_res = await self.db.execute(
                select(ServiceGroup.id, ServiceGroup.name).where(ServiceGroup.id.in_(group_ids))
            )
            group_names = {gid: name for gid, name in grp_res.all()}

        projected_services = []
        for s in services:
            job_types = job_types_by_service.get(s.id, [])
            per_job_type = []
            admin_blockers = []
            for job_type in job_types:
                workflow = workflows_by_pair.get((s.id, job_type.id))
                dimensions = dict(dimension_rules_by_scope.get((s.id, None), {}))
                dimensions.update(dimension_rules_by_scope.get((s.id, job_type.id), {}))
                projected = project_tenant_blueprint(s, workflow, dimensions)
                per_job_type.append({
                    "job_type_id": str(job_type.id), "job_type_key": job_type.key,
                    "job_type_label": job_type.label,
                    "workflow_id": workflow.get("id") if workflow else None,
                    **projected,
                })
                if not workflow:
                    admin_blockers.append({
                        "code": "MISSING_PUBLISHED_WORKFLOW", "job_type_id": str(job_type.id),
                        "message": f"{job_type.label} has no published workflow.",
                    })
            if not per_job_type:
                admin_blockers.append({"code": "NO_ACTIVE_JOB_TYPES", "message": "No active job type is configured."})
            for job_type_row in per_job_type:
                enabled_row = enabled_by_pair.get((s.id, uuid.UUID(job_type_row["job_type_id"])))
                row_blockers = [b for b in admin_blockers if b.get("job_type_id") == job_type_row["job_type_id"]]
                projected_services.append({
                "offering_key": f"{s.id}:{job_type_row['job_type_id']}",
                "service_id": str(s.id),
                "category_id": str(s.category_id),
                "service_name": s.service_name,
                # Real bug fixed here: the Services & Pricing setup page groups
                # the catalog by service group, but this response never carried
                # the grouping keys -- so every service fell into one unnamed
                # bucket and the grouping silently did nothing.
                "service_group_id": str(s.service_group_id) if s.service_group_id else None,
                "service_group_name": group_names.get(s.service_group_id),
                "description": s.description,
                # icon_url/image_url are real MasterService columns the admin
                # console sets (and the icon picker now uploads to), but they
                # were absent from this projection -- so the tenant's Services
                # & Pricing setup page could never show the admin-set service
                # icon, silently falling back to a generic placeholder.
                "icon_url": s.icon_url,
                "image_url": s.image_url,
                "job_type": job_type_row["job_type_key"],
                "job_type_id": job_type_row["job_type_id"],
                "job_type_label": job_type_row["job_type_label"],
                "job_types": [job_type_row],
                "pricing_model": job_type_row["pricing_behavior"],
                "base_price": float(s.base_price),
                "min_price": float(s.min_price) if s.min_price else None,
                "max_price": float(s.max_price) if s.max_price else None,
                "visit_fee": float(s.visit_fee),
                "is_brand_required": job_type_row["brand_mode"] == "required",
                "is_type_required": job_type_row["type_mode"] == "required",
                "requires_issue_type": job_type_row["requires_issue_type"],
                "requires_checklist": job_type_row["requires_checklist"],
                "requires_estimate_approval": job_type_row["requires_estimate_approval"],
                "requires_technician": job_type_row["requires_technician"],
                "requires_schedule": job_type_row["requires_schedule"],
                "requires_service_area": job_type_row["requires_service_area"],
                "requires_availability": job_type_row["requires_availability"],
                "workflow_version": job_type_row["workflow_version"],
                "blueprint_source": job_type_row["source"],
                "admin_ready": not row_blockers,
                "admin_blockers": row_blockers,
                "setup_rules_revision": setup_revision_by_pair[(s.id, uuid.UUID(job_type_row["job_type_id"]))],
                "tenant_setup_rules_revision": enabled_row.setup_rules_revision if enabled_row else None,
                "setup_update_required": bool(enabled_row and enabled_row.setup_rules_revision != setup_revision_by_pair[(s.id, uuid.UUID(job_type_row["job_type_id"]))]),
                "tenant_override_allowed": s.tenant_override_allowed,
                "is_active": s.is_active,
                "is_enabled": enabled_row is not None,
                })
        return {"services": projected_services}

    # ═══════════════════════════════════════════════════════════
    # Service Requirements (READ-ONLY view of admin-authored catalog)
    # ═══════════════════════════════════════════════════════════

    async def get_service_requirements(self, master_service_id: uuid.UUID,
                                       tenant_id_raw=None,
                                       job_type_id: uuid.UUID | None = None) -> dict:
        """Read-only view of the Problems, Questions and Checklists the admin
        has attached to one of THIS tenant's enabled services.

        Closes a genuine visibility gap: admin authors these per
        (master_service, job_type) in the Catalog Workspace, and they drive
        what the customer is asked at booking and what the technician must
        complete on site -- but the tenant, who has to train the technician
        and set the customer's expectations, had no way to see any of it.

        Strictly read-only and strictly scoped: the tenant must already have
        this service enabled, so this cannot be used to enumerate catalog
        content for services they don't offer. Reuses the same services the
        admin console reads (ServiceOptionService.list_service_issue_mappings,
        CatalogQuestionService.list_questions, checklist_catalog mappings) --
        no second projection of the same data.
        """
        from app.engines.admin_catalog.service_option_service import ServiceOptionService
        from app.engines.admin_catalog.question_service import CatalogQuestionService
        from app.engines.checklist_catalog.models import (
            JobTypeChecklistMapping, ChecklistTemplateVersion, ChecklistTemplate, ChecklistSection, ChecklistItem,
        )

        tenant_id = self._require_tenant_id(tenant_id_raw)

        # Scope gate: only services this tenant has actually enabled.
        enabled = (await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == master_service_id,
                *( [TenantService.job_type_id == job_type_id] if job_type_id else [] ),
                TenantService.is_enabled == True,  # noqa: E712
                TenantService.deleted_at.is_(None),
            )
        )).scalars().first()
        if not enabled:
            raise ServiceOSException(
                "SERVICE_NOT_ENABLED",
                "You can only view requirements for services you have enabled.",
                status_code=403)
        resolved_job_type_id = job_type_id or enabled.job_type_id

        service = await self.db.get(MasterService, master_service_id)
        if not service:
            raise NotFoundException("MasterService", str(master_service_id))

        # Read-only use: no actor/request context is needed because
        # list_service_issue_mappings performs no writes and no audit.
        option_service = ServiceOptionService(
            self.db, actor_id=None, actor_role=None, request_id="—", tenant_id=tenant_id,
        )
        problems = await option_service.list_service_issue_mappings(master_service_id, resolved_job_type_id)
        option_mappings = await option_service.list_service_option_mappings(
            master_service_id, resolved_job_type_id,
        )
        questions_res = await CatalogQuestionService(self.db).list_questions(
            master_service_id, resolved_job_type_id,
        )

        # Checklists resolve through the (master_service, job_type) child
        # record, then the published template VERSION -> template.
        job_type_ids = (await self.db.execute(
            select(MasterServiceJobType.id).where(
                MasterServiceJobType.master_service_id == master_service_id,
                    MasterServiceJobType.job_type_id == resolved_job_type_id,
                    MasterServiceJobType.is_active.is_(True),
            )
        )).scalars().all()
        checklists: list[dict] = []
        if job_type_ids:
            rows = (await self.db.execute(
                select(JobTypeChecklistMapping, ChecklistTemplate, ChecklistTemplateVersion)
                .join(ChecklistTemplateVersion,
                      JobTypeChecklistMapping.checklist_template_version_id == ChecklistTemplateVersion.id)
                .join(ChecklistTemplate,
                      ChecklistTemplateVersion.checklist_template_id == ChecklistTemplate.id)
                .where(
                    JobTypeChecklistMapping.master_service_job_type_id.in_(job_type_ids),
                    JobTypeChecklistMapping.status == "active",
                    JobTypeChecklistMapping.usage != "DISABLED",
                    ChecklistTemplateVersion.status == "PUBLISHED",
                    ChecklistTemplate.status == "active",
                )
                .order_by(JobTypeChecklistMapping.display_order)
            )).all()
            for mapping, template, version in rows:
                content = (await self.db.execute(select(ChecklistItem, ChecklistSection.title).join(
                    ChecklistSection, ChecklistItem.checklist_section_id == ChecklistSection.id,
                ).where(ChecklistSection.checklist_template_version_id == version.id)
                  .order_by(ChecklistSection.display_order, ChecklistItem.display_order, ChecklistItem.id))).all()
                checklists.append({
                    "mapping_id": str(mapping.id),
                    "template_name": template.name,
                    "template_code": template.code,
                    "purpose": template.purpose,
                    "icon_url": template.icon_url,
                    "version_number": version.version_number,
                    "phase": getattr(mapping, "phase", None),
                    "status": mapping.status,
                    "usage": mapping.usage, "actor": mapping.actor, "completion_gate": mapping.completion_gate,
                    "items": [{"id": str(item.id), "label": item.label, "section_title": section_title,
                               "item_type": item.item_type, "is_required": item.is_required,
                               "evidence_required": item.evidence_required, "help_text": item.help_text}
                              for item, section_title in content],
                })

        return {
            "master_service_id": str(master_service_id),
            "job_type_id": str(resolved_job_type_id),
            "service_name": service.service_name,
            "problems": [
                {
                    "issue_type_id": str(p["issue_type"]["id"]),
                    "name": p["issue_type"].get("name"),
                    "description": p["issue_type"].get("description"),
                    "severity": p["issue_type"].get("severity"),
                    "is_common": p.get("is_common"),
                    "requires_photo": p.get("requires_photo"),
                    "requires_description": p.get("requires_description"),
                }
                for p in problems if p.get("issue_type")
            ],
            "questions": [
                {
                    "question_id": q["id"],
                    "label": q.get("label"),
                    "input_type": q.get("input_type"),
                    "required": q.get("required"),
                    "customer_visible": q.get("customer_visible"),
                    "help_text": q.get("help_text"),
                    "options": [o.get("label") for o in (q.get("options") or [])],
                }
                for q in questions_res.get("questions", [])
            ],
            "service_options": [
                {
                    "mapping_id": mapping["id"],
                    "service_option_id": mapping["service_option_id"],
                    "name": mapping["option"].get("name"),
                    "description": mapping["option"].get("description"),
                    "usage": mapping.get("usage"),
                    "customer_selectable": mapping.get("customer_selectable"),
                    "technician_selectable": mapping.get("technician_selectable"),
                    "quantity_supported": mapping.get("quantity_supported"),
                    "minimum_quantity": mapping.get("minimum_quantity"),
                    "maximum_quantity": mapping.get("maximum_quantity"),
                    "measurement_unit": mapping.get("measurement_unit") or mapping["option"].get("unit"),
                }
                for mapping in option_mappings
                if mapping.get("status") == "active" and mapping.get("usage") != "DISABLED"
            ],
            "checklists": checklists,
            "tenant_editable": False,
            "note": ("Configured centrally by the platform. These drive what the customer is "
                     "asked when booking and what your technician must complete on site."),
        }

    # ═══════════════════════════════════════════════════════════
    # Enabled Services (tenant's active list)
    # ═══════════════════════════════════════════════════════════

    async def list_enabled_services(self, tenant_id_raw=None, category_id: uuid.UUID | None = None) -> dict:
        tenant_id = self._require_tenant_id(tenant_id_raw)
        stmt = (
            select(
                TenantService,
                MasterService.service_name,
                JobTypeDefinition.label.label("job_type_label"),
                ServiceGroup.name.label("service_group_name"),
            )
            .join(MasterService, MasterService.id == TenantService.master_service_id)
            .outerjoin(JobTypeDefinition, JobTypeDefinition.id == TenantService.job_type_id)
            .outerjoin(ServiceGroup, ServiceGroup.id == MasterService.service_group_id)
            .where(
            TenantService.tenant_id == tenant_id,
            TenantService.is_enabled == True,
            TenantService.deleted_at.is_(None),
        )
        )
        if category_id:
            stmt = stmt.where(TenantService.category_id == category_id)
        rows = (await self.db.execute(stmt.order_by(
            ServiceGroup.display_order,
            MasterService.display_order,
            MasterService.service_name,
            JobTypeDefinition.display_order,
            TenantService.created_at,
        ))).all()
        return {"services": [
            self._ts_dict(
                ts,
                service_name=service_name,
                job_type_label=job_type_label,
                service_group_name=service_group_name,
            )
            for ts, service_name, job_type_label, service_group_name in rows
        ]}

    async def list_home_services_available(self, tenant_id_raw=None) -> dict:
        cat_id = await self.get_home_services_category_id()
        return await self.list_available_services(tenant_id_raw, category_id=cat_id)

    async def list_home_services_enabled(self, tenant_id_raw=None) -> dict:
        cat_id = await self.get_home_services_category_id()
        return await self.list_enabled_services(tenant_id_raw, category_id=cat_id)

    async def get_enabled_service(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        return self._ts_dict(ts)

    async def get_home_services_pricing_policy(self, tenant_id_raw=None) -> dict:
        """Provider-owned prices that apply once across Home Services.

        Consultation is intentionally provider-wide: creating one price per
        service/type/brand would be duplicate configuration and would produce
        inconsistent customer prices for the same expert consultation.
        """
        tenant_id = self._require_tenant_id(tenant_id_raw)
        settings = (await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )).scalar_one_or_none()
        extra = dict(settings.extra or {}) if settings else {}
        home_services = dict(extra.get("home_services") or {})
        fee = home_services.get("consultation_fee")
        return {
            "consultation_fee": float(fee) if fee is not None else None,
            "currency": settings.currency if settings else "INR",
            "scope": "provider_all_home_services",
        }

    async def update_home_services_pricing_policy(self, data: dict, tenant_id_raw=None) -> dict:
        tenant_id = self._require_tenant_id(tenant_id_raw)
        fee = _decimal_or_none(data.get("consultation_fee"))
        if fee is None:
            raise ServiceOSException(
                "CONSULTATION_FEE_REQUIRED", "Consultation fee is required.", status_code=422)
        if fee <= 0:
            raise ServiceOSException(
                "INVALID_CONSULTATION_FEE", "Consultation fee must be greater than zero.", status_code=422)

        settings = (await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if settings is None:
            settings = TenantSettings(tenant_id=tenant_id)
            self.db.add(settings)
            await self.db.flush()

        extra = dict(settings.extra or {})
        home_services = dict(extra.get("home_services") or {})
        home_services["consultation_fee"] = float(fee)
        extra["home_services"] = home_services
        settings.extra = extra
        await self.db.flush()
        return await self.get_home_services_pricing_policy(tenant_id)

    # ═══════════════════════════════════════════════════════════
    # Enable Service
    # ═══════════════════════════════════════════════════════════

    async def enable_service(self, data: dict, tenant_id_raw=None) -> dict:
        tenant_id = self._require_tenant_id(tenant_id_raw)
        svc_id_raw = data.get("master_service_id")
        if not svc_id_raw:
            raise ServiceOSException("MASTER_SERVICE_NOT_FOUND", "master_service_id is required.", status_code=422)
        svc_id = uuid.UUID(str(svc_id_raw))

        # Load master service
        svc_res = await self.db.execute(
            select(MasterService).where(MasterService.id == svc_id, MasterService.deleted_at.is_(None)))
        svc = svc_res.scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(svc_id))
        if not svc.is_active:
            raise ServiceOSException("MASTER_SERVICE_INACTIVE", "Service is not active.", status_code=422)

        # Check category active
        cat_res = await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.id == svc.category_id))
        cat = cat_res.scalar_one_or_none()
        if not cat or not cat.is_active:
            raise ServiceOSException("SERVICE_CATEGORY_INACTIVE", "Service category is inactive.", status_code=422)
        provider_owns_prices = cat.vertical_type == "home_services"

        # FINAL-L5-04B: tenant must hold an ACTIVE entitlement for the
        # service_group this service belongs to before it can configure it.
        # This is a real backend enforcement point, not just a hidden menu
        # item — see FINAL_L5_04B_SERVICE_SETUP_ENFORCEMENT_REPORT.md.
        if svc.service_group_id:
            has_entitlement = await entitlement_service.has_category_entitlement(
                self.db, tenant_id, svc.service_group_id
            )
            if not has_entitlement:
                has_entitlement = await entitlement_service.ensure_registration_category_access(
                    self.db, tenant_id=tenant_id, category_id=svc.service_group_id,
                    actor_id=self.actor_id, actor_role=self.actor_role, request_id=self.request_id,
                )
            if not has_entitlement:
                raise ServiceOSException(
                    "CATEGORY_NOT_ENTITLED",
                    "Access to this service group is not active for your workspace. Ask an administrator to review Home Services category access. Technician-seat plans do not unlock service categories.",
                    status_code=403,
                )

        job_type = await self._resolve_active_job_type(svc_id, data.get("job_type_id"))
        setup_rules_revision = await self._setup_rule_revision(svc_id, job_type.id)

        # Check not already enabled for this exact Job Type.
        existing = await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == svc_id,
                TenantService.job_type_id == job_type.id,
                TenantService.deleted_at.is_(None),
            ))
        existing_ts = existing.scalar_one_or_none()
        if existing_ts and existing_ts.is_enabled:
            raise ServiceOSException("TENANT_SERVICE_ALREADY_ENABLED", "Service is already enabled for this tenant.", status_code=409)

        if existing_ts:
            # Re-enable
            existing_ts.is_enabled = True
            ts = existing_ts
        else:
            # Validate price overrides
            tenant_base  = _decimal_or_none(data.get("tenant_base_price"))
            tenant_min   = _decimal_or_none(data.get("tenant_min_price"))
            tenant_max   = _decimal_or_none(data.get("tenant_max_price"))
            tenant_visit = _decimal_or_none(data.get("tenant_visit_fee"))
            warranty_days = self._validate_warranty_days(data.get("warranty_days", 5))

            # ``tenant_base_price`` is the legacy/public API spelling for an
            # exact fixed price.  Publish and customer price resolution use
            # the canonical min/max pair, so accepting only base_price without
            # filling that pair created a service that saved successfully but
            # could never publish.  Preserve the alias while normalizing it to
            # the single pricing authority.
            if tenant_base is not None and tenant_min is None and tenant_max is None:
                tenant_min = tenant_base
                tenant_max = tenant_base

            # MODULE-L5-03: `is not None`, not truthiness — Decimal('0') is falsy,
            # so the old `any([...])`/`if tenant_min and ...` skipped validation
            # when a tenant set price 0, storing a floor-bypassing value.
            if any(v is not None for v in (tenant_base, tenant_min, tenant_max, tenant_visit)):
                if not provider_owns_prices and not svc.tenant_override_allowed:
                    raise ServiceOSException("TENANT_SERVICE_OVERRIDE_NOT_ALLOWED",
                        "Price override is not allowed for this service.", status_code=422)
                self._validate_price_overrides(svc, tenant_base, tenant_min, tenant_max, tenant_visit)

            job_type_id = job_type.id
            blueprint = await self._tenant_setup_blueprint(svc, job_type_id)
            if isinstance(svc, MasterService) and blueprint["source"] != "service_job_workflow":
                raise ServiceOSException(
                    "SERVICE_BLUEPRINT_INCOMPLETE",
                    f"{job_type.label} is not ready for tenant setup. An administrator must publish its workflow.",
                    status_code=422,
                )
            latest_blueprint = (await self.db.execute(
                select(ServiceBlueprintVersion).where(
                    ServiceBlueprintVersion.master_service_id == svc.id,
                    ServiceBlueprintVersion.status == "published",
                ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1)
            )).scalar_one_or_none()
            ts = TenantService(
                tenant_id=tenant_id,
                master_service_id=svc_id,
                category_id=svc.category_id,
                job_type=job_type.key,
                job_type_id=job_type_id,
                is_enabled=True,
                tenant_display_name=data.get("tenant_display_name"),
                tenant_description=data.get("tenant_description"),
                tenant_base_price=tenant_base,
                tenant_min_price=tenant_min,
                tenant_max_price=tenant_max,
                tenant_visit_fee=tenant_visit,
                warranty_days=warranty_days,
                override_allowed=provider_owns_prices or svc.tenant_override_allowed,
                requires_brand=blueprint["brand_mode"] == "required",
                requires_type=blueprint["type_mode"] == "required",
                is_active=True,
                blueprint_version_id=latest_blueprint.id if latest_blueprint else None,
                setup_rules_revision=setup_rules_revision,
            )
            self.db.add(ts)

        # Re-enabling an existing row must also adopt the current authoritative
        # setup contract; otherwise a tenant could retain obsolete type/brand
        # requirements indefinitely simply by disabling and enabling again.
        if existing_ts:
            existing_ts.override_allowed = provider_owns_prices or svc.tenant_override_allowed
            job_type_id = job_type.id
            blueprint = await self._tenant_setup_blueprint(svc, job_type_id)
            if isinstance(svc, MasterService) and blueprint["source"] != "service_job_workflow":
                raise ServiceOSException(
                    "SERVICE_BLUEPRINT_INCOMPLETE",
                    f"{job_type.label} is not ready for tenant setup. An administrator must publish its workflow.",
                    status_code=422,
                )
            existing_ts.job_type_id = job_type_id
            existing_ts.requires_brand = blueprint["brand_mode"] == "required"
            existing_ts.requires_type = blueprint["type_mode"] == "required"
            latest_blueprint = (await self.db.execute(
                select(ServiceBlueprintVersion).where(
                    ServiceBlueprintVersion.master_service_id == svc.id,
                    ServiceBlueprintVersion.status == "published",
                ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1)
            )).scalar_one_or_none()
            existing_ts.blueprint_version_id = latest_blueprint.id if latest_blueprint else existing_ts.blueprint_version_id
            existing_ts.setup_rules_revision = setup_rules_revision
            if "warranty_days" in data:
                existing_ts.warranty_days = self._validate_warranty_days(data["warranty_days"])

        await self.db.flush()
        return self._ts_dict(ts)

    def _validate_price_overrides(self, svc, tenant_base, tenant_min, tenant_max, tenant_visit) -> None:
        """Validate provider-owned price amounts.

        Admin owns workflow and monetization policy, not provider service
        prices. Legacy MasterService min/max values must therefore never act
        as hidden tenant price constraints.
        """
        for lbl, val in (("tenant_min_price", tenant_min), ("tenant_max_price", tenant_max),
                         ("tenant_base_price", tenant_base), ("tenant_visit_fee", tenant_visit)):
            if val is not None and not val.is_finite():
                raise ServiceOSException("TENANT_PRICE_INVALID",
                    f"{lbl} must be a finite amount.", status_code=422)
            if val is not None and val < 0:
                raise ServiceOSException("TENANT_PRICE_NEGATIVE",
                    f"{lbl} cannot be negative.", status_code=422)
            if val == 0 and lbl != "tenant_visit_fee":
                raise ServiceOSException("TENANT_PRICE_INVALID",
                    f"{lbl} must be greater than zero. Leave an optional amount empty instead of using zero.", status_code=422)
        if tenant_min is not None and tenant_max is not None and tenant_min > tenant_max:
            raise ServiceOSException(
                "INVALID_PRICE_RANGE", "Minimum price cannot exceed maximum price.", status_code=422,
            )

    async def update_enabled_service(self, tenant_service_id: uuid.UUID, data: dict) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Same compatibility normalization as enable_service: an exact base
        # price is represented canonically as min == max everywhere that
        # validates, publishes, or quotes the service.
        data = dict(data)
        if (data.get("tenant_base_price") is not None
                and "tenant_min_price" not in data
                and "tenant_max_price" not in data):
            data["tenant_min_price"] = data["tenant_base_price"]
            data["tenant_max_price"] = data["tenant_base_price"]

        # Home Services prices belong to the provider. Older enrollments copied
        # a false admin override flag even when no admin price existed.
        category = await self.db.get(ServiceCategory, ts.category_id)
        provider_owns_prices = category is not None and category.vertical_type == "home_services"
        if not provider_owns_prices and not ts.override_allowed:
            for field in ("tenant_base_price", "tenant_min_price", "tenant_max_price", "tenant_visit_fee"):
                if data.get(field) is not None:
                    raise ServiceOSException("TENANT_SERVICE_OVERRIDE_NOT_ALLOWED",
                        "Price override is not allowed for this service.", status_code=422)

        # Validate the effective provider-owned range on every update path;
        # partial updates must not create a negative or inverted range.
        svc = (await self.db.execute(
            select(MasterService).where(MasterService.id == ts.master_service_id)
        )).scalar_one_or_none()
        eff = {}
        for field in ("tenant_base_price", "tenant_min_price", "tenant_max_price", "tenant_visit_fee"):
            if field in data:
                eff[field] = _decimal_or_none(data[field])
            else:
                eff[field] = getattr(ts, field)
        self._validate_price_overrides(svc, eff["tenant_base_price"], eff["tenant_min_price"],
                                       eff["tenant_max_price"], eff["tenant_visit_fee"])

        for field in ("tenant_display_name", "tenant_description"):
            if field in data and data[field] is not None:
                setattr(ts, field, data[field])
        for field in ("tenant_base_price", "tenant_min_price", "tenant_max_price", "tenant_visit_fee"):
            if field in data:
                setattr(ts, field, eff[field])
        if "tenant_emergency_surcharge" in data:
            value = _decimal_or_none(data["tenant_emergency_surcharge"])
            if value is not None and value < 0:
                raise ServiceOSException(
                    "TENANT_PRICE_NEGATIVE", "Emergency surcharge cannot be negative.", status_code=422,
                )
            ts.tenant_emergency_surcharge = value
        if "warranty_days" in data:
            ts.warranty_days = self._validate_warranty_days(data["warranty_days"])

        if provider_owns_prices:
            ts.override_allowed = True

        await self.db.flush()
        return self._ts_dict(ts)

    async def disable_service(self, data: dict = None, tenant_id_raw=None) -> dict:
        tenant_id = self._require_tenant_id(tenant_id_raw)
        svc_id_raw = (data or {}).get("master_service_id")
        if not svc_id_raw:
            raise ServiceOSException("MASTER_SERVICE_NOT_FOUND", "master_service_id is required.", status_code=422)
        svc_id = uuid.UUID(str(svc_id_raw))
        job_type_id_raw = (data or {}).get("job_type_id")
        if not job_type_id_raw:
            raise ServiceOSException("JOB_TYPE_REQUIRED", "job_type_id is required.", status_code=422)
        job_type_id = uuid.UUID(str(job_type_id_raw))
        res = await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == svc_id,
                TenantService.job_type_id == job_type_id,
                TenantService.deleted_at.is_(None),
            ))
        ts = res.scalar_one_or_none()
        if not ts:
            raise ServiceOSException("TENANT_SERVICE_NOT_ENABLED", "Service is not enabled for this tenant.", status_code=404)
        ts.is_enabled = False
        await self.db.flush()
        return {"disabled": True, "tenant_service_id": str(ts.id)}

    # ═══════════════════════════════════════════════════════════
    # Tenant Supported Types
    # ═══════════════════════════════════════════════════════════

    async def get_tenant_service_types(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        # This endpoint is the setup candidate list, not merely the tenant's
        # already-selected rows. Start from the Admin mapping and left-join
        # the tenant selection so a new provider sees every allowed type with
        # is_enabled=False instead of an empty setup panel.
        res = await self.db.execute(
            select(MasterServiceType, ServiceType, TenantServiceType)
            .join(ServiceType, ServiceType.id == MasterServiceType.service_type_id)
            .outerjoin(
                TenantServiceType,
                and_(
                    TenantServiceType.tenant_service_id == tenant_service_id,
                    TenantServiceType.service_type_id == MasterServiceType.service_type_id,
                ),
            )
            .where(
                MasterServiceType.master_service_id == ts.master_service_id,
                MasterServiceType.is_active.is_(True),
                ServiceType.is_active.is_(True),
                ServiceType.deleted_at.is_(None),
            )
            .order_by(ServiceType.display_order, ServiceType.name)
        )
        rows = res.all()
        return {"types": [
            {"id": str(tst.id if tst else mst.id),
             "mapping_id": str(tst.id if tst else mst.id),
             "service_type_id": str(mst.service_type_id),
             "name": st.name, "is_enabled": bool(tst and tst.is_enabled),
             "brand_coverage": tst.brand_coverage if tst else None,
             "is_required": bool(mst.is_required),
             "is_default": bool(mst.is_default),
             "tenant_price_adjustment": (
                 float(tst.tenant_price_adjustment)
                 if tst and tst.tenant_price_adjustment is not None else None
             )}
            for mst, st, tst in rows
        ]}

    async def set_tenant_service_types(self, tenant_service_id: uuid.UUID, type_ids: list[str],
                                       brand_coverage_by_type: dict | None = None) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Validate all type_ids are mapped to the master service
        admin_types_res = await self.db.execute(
            select(MasterServiceType)
            .join(ServiceType, ServiceType.id == MasterServiceType.service_type_id)
            .where(
                MasterServiceType.master_service_id == ts.master_service_id,
                MasterServiceType.is_active.is_(True),
                ServiceType.is_active.is_(True),
                ServiceType.deleted_at.is_(None)))
        allowed_type_ids = {str(m.service_type_id) for m in admin_types_res.scalars().all()}

        for tid in type_ids:
            if tid not in allowed_type_ids:
                raise ServiceOSException("SERVICE_TYPE_NOT_SUPPORTED",
                    f"Type {tid} is not mapped to this service by admin.", status_code=422)

        # Validate the entire selection before mutating anything. Coverage is
        # stored on the type, never inferred from a brand price row.
        coverage = {}
        if brand_coverage_by_type is not None:
            if not isinstance(brand_coverage_by_type, dict) or set(brand_coverage_by_type) - set(type_ids):
                raise ServiceOSException("INVALID_BRAND_COVERAGE", "Brand coverage must belong to selected types.", status_code=422)
            allowed = {row["brand_id"] for row in (await self.get_tenant_service_brands(tenant_service_id))["brands"]}
            for tid, value in brand_coverage_by_type.items():
                if not isinstance(value, dict) or value.get("mode") not in {"all", "selected"}:
                    raise ServiceOSException("INVALID_BRAND_COVERAGE", "Choose all or selected brands for each type.", status_code=422)
                ids = value.get("brand_ids", [])
                if not isinstance(ids, list) or any(not isinstance(bid, str) or bid not in allowed for bid in ids):
                    raise ServiceOSException("BRAND_NOT_SUPPORTED", "Select only active brands mapped by admin.", status_code=422)
                if value["mode"] == "selected" and not ids:
                    raise ServiceOSException("MISSING_REQUIRED_BRAND_SELECTION", "Select at least one supported brand for each type, or choose All brands.", status_code=422)
                coverage[tid] = {"mode": value["mode"], "brand_ids": sorted(set(ids)) if value["mode"] == "selected" else []}

        # Deactivate all existing, then upsert new ones
        existing_res = await self.db.execute(
            select(TenantServiceType).where(TenantServiceType.tenant_service_id == tenant_service_id))
        existing_map = {str(x.service_type_id): x for x in existing_res.scalars().all()}

        for tid in type_ids:
            type_uuid = uuid.UUID(tid)
            if tid in existing_map:
                existing_map[tid].is_enabled = True
                if tid in coverage:
                    existing_map[tid].brand_coverage = coverage[tid]
            else:
                tst = TenantServiceType(
                    tenant_id=ts.tenant_id, tenant_service_id=tenant_service_id,
                    service_type_id=type_uuid, is_enabled=True, brand_coverage=coverage.get(tid))
                self.db.add(tst)

        # Disable ones not in new list
        for tid, tst in existing_map.items():
            if tid not in type_ids:
                tst.is_enabled = False

        await self.db.flush()
        return await self.get_tenant_service_types(tenant_service_id)

    # ═══════════════════════════════════════════════════════════
    # Tenant Supported Brands
    # ═══════════════════════════════════════════════════════════

    async def get_tenant_service_brands(self, tenant_service_id: uuid.UUID) -> dict:
        """Active admin candidates with service-wide selection markers.

        Explicit per-type matching coverage is returned by the types endpoint.
        Scoped price rows must never become service-wide support markers.
        """
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        # Like Types, this is the Admin-authorized candidate list with the
        # tenant selection projected onto it. Returning only selected rows
        # made a new service impossible to configure because there was
        # nothing available to select.
        res = await self.db.execute(
            select(MasterServiceBrand, Brand, TenantServiceBrand)
            .join(Brand, Brand.id == MasterServiceBrand.brand_id)
            .outerjoin(
                TenantServiceBrand,
                and_(
                    TenantServiceBrand.tenant_service_id == tenant_service_id,
                    TenantServiceBrand.brand_id == MasterServiceBrand.brand_id,
                    TenantServiceBrand.service_type_id.is_(None),
                ),
            )
            .where(
                MasterServiceBrand.master_service_id == ts.master_service_id,
                MasterServiceBrand.is_active.is_(True),
                MasterServiceBrand.status == "active",
                Brand.is_active.is_(True),
                Brand.deleted_at.is_(None),
            )
            .order_by(MasterServiceBrand.display_order, Brand.display_order, Brand.name)
        )
        rows = res.all()
        return {"brands": [
            {"id": str(tsb.id if tsb else msb.id), "brand_id": str(msb.brand_id),
             "name": b.name, "is_enabled": (
                 True if ts.brand_coverage_mode == "all" else
                 not bool(tsb and tsb.is_enabled) if ts.brand_coverage_mode == "all_except" else
                 bool(tsb and tsb.is_enabled)
             ),
             "tenant_price_adjustment": (
                 float(tsb.tenant_price_adjustment)
                 if tsb and tsb.tenant_price_adjustment is not None else None
             ),
             "can_override_price": msb.can_override_price}
            for msb, b, tsb in rows
        ]}

    async def set_tenant_service_brands(self, tenant_service_id: uuid.UUID, brand_ids: list[str]) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Validate brands are mapped to master service
        admin_brands_res = await self.db.execute(
            select(MasterServiceBrand)
            .join(Brand, Brand.id == MasterServiceBrand.brand_id)
            .where(
                MasterServiceBrand.master_service_id == ts.master_service_id,
                MasterServiceBrand.is_active.is_(True),
                MasterServiceBrand.status == "active",
                Brand.is_active.is_(True),
                Brand.deleted_at.is_(None)))
        allowed_brand_ids = {str(m.brand_id) for m in admin_brands_res.scalars().all()}

        for bid in brand_ids:
            if bid not in allowed_brand_ids:
                raise ServiceOSException("BRAND_NOT_SUPPORTED",
                    f"Brand {bid} is not mapped to this service by admin.", status_code=422)

        existing_res = await self.db.execute(
            select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.service_type_id.is_(None),
            ))
        existing_map = {str(x.brand_id): x for x in existing_res.scalars().all()}

        for bid in brand_ids:
            brand_uuid = uuid.UUID(bid)
            if bid in existing_map:
                existing_map[bid].is_enabled = True
            else:
                tsb = TenantServiceBrand(
                    tenant_id=ts.tenant_id, tenant_service_id=tenant_service_id,
                    brand_id=brand_uuid, is_enabled=True)
                self.db.add(tsb)

        for bid, tsb in existing_map.items():
            if bid not in brand_ids:
                tsb.is_enabled = False

        # This endpoint receives the explicit supported set, never exclusions.
        ts.brand_coverage_mode = "selected"
        await self.db.flush()
        return await self.get_tenant_service_brands(tenant_service_id)

    # ═══════════════════════════════════════════════════════════
    # Home Services Service Setup Wizard — per-type / per-brand pricing
    # (Step 3 / Step 3B), price preview, and publish (Step 6)
    # ═══════════════════════════════════════════════════════════

    async def _is_inspection_pricing(self, ts: TenantService) -> bool:
        master = await self.db.get(MasterService, ts.master_service_id)
        if master is None:
            return False
        blueprint = await self._tenant_setup_blueprint(master, ts.job_type_id)
        return str(blueprint.get("pricing_behavior") or "").lower() in INSPECTION_PRICING_BEHAVIORS

    async def _reject_dimension_price_for_inspection(self, ts: TenantService) -> None:
        if str(ts.job_type).lower() == "consultation":
            raise ServiceOSException(
                "DIMENSION_PRICING_NOT_APPLICABLE",
                "Consultations use your provider-wide fee. Type and Brand affect matching only.",
                status_code=422,
            )
        if await self._is_inspection_pricing(ts):
            raise ServiceOSException(
                "DIMENSION_PRICING_NOT_APPLICABLE",
                "Type and Brand are used for service matching on inspection jobs; set only the visit fee.",
                status_code=422,
            )

    async def _find_admin_pricing_rule(self, master_service_id: uuid.UUID,
                                        service_type_id: uuid.UUID | None,
                                        brand_id: uuid.UUID | None) -> ServicePricingRule | None:
        """Same scoping the admin console writes to (global default rule,
        no tier/city) — the tenant reads the admin-approved floor/ceiling
        from the identical row the admin console's Types & Pricing /
        Brands tabs create."""
        stmt = select(ServicePricingRule).where(
            ServicePricingRule.master_service_id == master_service_id,
            ServicePricingRule.deleted_at.is_(None),
            ServicePricingRule.is_active == True,
            ServicePricingRule.tier_id.is_(None),
            ServicePricingRule.city.is_(None),
        )
        stmt = stmt.where(ServicePricingRule.service_type_id == service_type_id) if service_type_id \
            else stmt.where(ServicePricingRule.service_type_id.is_(None))
        stmt = stmt.where(ServicePricingRule.brand_id == brand_id) if brand_id \
            else stmt.where(ServicePricingRule.brand_id.is_(None))
        return (await self.db.execute(stmt)).scalars().first()

    async def get_type_pricing_for_setup(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        res = await self.db.execute(
            select(TenantServiceType, ServiceType)
            .join(ServiceType, ServiceType.id == TenantServiceType.service_type_id)
            .where(TenantServiceType.tenant_service_id == tenant_service_id,
                   TenantServiceType.is_enabled == True))
        rows = res.all()
        out = []
        for tst, st in rows:
            rule = await self._find_admin_pricing_rule(ts.master_service_id, tst.service_type_id, None)
            admin_floor = float(rule.min_price) if rule and rule.min_price is not None else None
            admin_ceiling = float(rule.max_price) if rule and rule.max_price is not None else None
            fee_pct = float(rule.platform_fee_percent) if rule and rule.platform_fee_percent is not None else 0.0
            tenant_min = float(tst.tenant_min_price) if tst.tenant_min_price is not None else None
            tenant_max = float(tst.tenant_max_price) if tst.tenant_max_price is not None else None
            preview = (
                {
                    "provider_min_price": tenant_min,
                    "provider_max_price": tenant_max,
                    "customer_min_price": tenant_min,
                    "customer_max_price": tenant_max,
                    "payment_mode": "customer_pays_provider_directly",
                }
                if tenant_min is not None and tenant_max is not None else None
            )
            out.append({
                "tenant_service_type_id": str(tst.id), "service_type_id": str(tst.service_type_id),
                "name": st.name,
                "admin_floor_price": admin_floor, "admin_ceiling_price": admin_ceiling,
                "platform_fee_percent": fee_pct,
                "tenant_min_price": tenant_min, "tenant_max_price": tenant_max,
                "customer_price_preview": preview,
            })
        return {"types": out}

    async def set_type_pricing(self, tenant_service_id: uuid.UUID, service_type_id: uuid.UUID,
                                tenant_min_price, tenant_max_price) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        await self._reject_dimension_price_for_inspection(ts)
        res = await self.db.execute(
            select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == tenant_service_id,
                TenantServiceType.service_type_id == service_type_id,
                TenantServiceType.is_enabled == True))
        tst = res.scalar_one_or_none()
        if not tst:
            raise ServiceOSException("SERVICE_TYPE_NOT_SUPPORTED",
                "This type is not selected for this service.", status_code=422)

        tmin = _decimal_or_none(tenant_min_price)
        tmax = _decimal_or_none(tenant_max_price)
        if tmin is None or tmax is None:
            raise ServiceOSException("PRICE_RANGE_REQUIRED",
                "Both minimum and maximum price are required.", status_code=422)
        if tmin > tmax:
            raise ServiceOSException("INVALID_PRICE_RANGE",
                "Minimum price cannot exceed maximum price.", status_code=422)
        if tmin < 0 or tmax < 0:
            raise ServiceOSException("TENANT_PRICE_NEGATIVE",
                "Service prices cannot be negative.", status_code=422)
        if tmin == 0 or tmax == 0:
            raise ServiceOSException("TENANT_PRICE_INVALID",
                "Service prices must be greater than zero.", status_code=422)

        tst.tenant_min_price = tmin
        tst.tenant_max_price = tmax
        await self.db.flush()
        return await self.get_type_pricing_for_setup(tenant_service_id)

    async def clear_type_pricing(self, tenant_service_id: uuid.UUID,
                                 service_type_id: uuid.UUID) -> dict:
        """Remove only the tenant price override while keeping the Type enabled."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        await self._reject_dimension_price_for_inspection(ts)
        res = await self.db.execute(
            select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == tenant_service_id,
                TenantServiceType.service_type_id == service_type_id,
                TenantServiceType.is_enabled == True))
        tst = res.scalar_one_or_none()
        if not tst:
            raise ServiceOSException("SERVICE_TYPE_NOT_SUPPORTED",
                "This type is not selected for this service.", status_code=422)
        tst.tenant_min_price = None
        tst.tenant_max_price = None
        await self.db.flush()
        return await self.get_type_pricing_for_setup(tenant_service_id)

    async def get_brand_pricing_for_setup(self, tenant_service_id: uuid.UUID,
                                           service_type_id: uuid.UUID | None = None) -> dict:
        """Type-Dependent Brand Pricing (migration 120): brand rows are now
        scoped by service_type_id. For a type-based service, callers must
        pass service_type_id to see/set that type's brand overrides —
        omitting it returns only the service-level (NULL service_type_id)
        rows, which only exist for fixed (non-type-based) services."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        stmt = (
            select(TenantServiceBrand, Brand, MasterServiceBrand)
            .join(Brand, Brand.id == TenantServiceBrand.brand_id)
            .join(MasterServiceBrand, (MasterServiceBrand.master_service_id == ts.master_service_id) &
                  (MasterServiceBrand.brand_id == TenantServiceBrand.brand_id))
            .where(TenantServiceBrand.tenant_service_id == tenant_service_id,
                   TenantServiceBrand.is_enabled == True)
        )
        stmt = stmt.where(TenantServiceBrand.service_type_id == service_type_id) if service_type_id \
            else stmt.where(TenantServiceBrand.service_type_id.is_(None))
        rows = (await self.db.execute(stmt)).all()
        out = []
        for tsb, b, msb in rows:
            rule = await self._find_admin_pricing_rule(ts.master_service_id, service_type_id, tsb.brand_id)
            admin_floor = float(rule.min_price) if rule and rule.min_price is not None else None
            admin_ceiling = float(rule.max_price) if rule and rule.max_price is not None else None
            fee_pct = float(rule.platform_fee_percent) if rule and rule.platform_fee_percent is not None else 0.0
            tenant_min = float(tsb.tenant_min_price) if tsb.tenant_min_price is not None else None
            tenant_max = float(tsb.tenant_max_price) if tsb.tenant_max_price is not None else None
            preview = (
                {
                    "provider_min_price": tenant_min,
                    "provider_max_price": tenant_max,
                    "customer_min_price": tenant_min,
                    "customer_max_price": tenant_max,
                    "payment_mode": "customer_pays_provider_directly",
                }
                if msb.can_override_price and tenant_min is not None and tenant_max is not None else None
            )
            out.append({
                "tenant_service_brand_id": str(tsb.id), "brand_id": str(tsb.brand_id), "name": b.name,
                "service_type_id": str(tsb.service_type_id) if tsb.service_type_id else None,
                "can_override_price": msb.can_override_price, "is_routing_only": msb.is_routing_only,
                "admin_floor_price": admin_floor, "admin_ceiling_price": admin_ceiling,
                "platform_fee_percent": fee_pct,
                "tenant_min_price": tenant_min, "tenant_max_price": tenant_max,
                "customer_price_preview": preview,
            })
        return {"brands": out}

    async def set_brand_pricing(self, tenant_service_id: uuid.UUID, brand_id: uuid.UUID,
                                 tenant_min_price, tenant_max_price,
                                 service_type_id: uuid.UUID | None = None) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        await self._reject_dimension_price_for_inspection(ts)

        # Rule 1/2: type-based services require service_type_id for brand pricing.
        if ts.requires_type and service_type_id is None:
            raise ServiceOSException("SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING",
                "Service type is required when adding brand pricing for a type-based service.",
                status_code=422)

        if service_type_id is not None:
            # Rule 3: the type must actually be enabled for this tenant_service.
            tst_res = await self.db.execute(
                select(TenantServiceType).where(
                    TenantServiceType.tenant_service_id == tenant_service_id,
                    TenantServiceType.service_type_id == service_type_id,
                    TenantServiceType.is_enabled == True))
            if tst_res.scalar_one_or_none() is None:
                raise ServiceOSException("SERVICE_TYPE_NOT_SUPPORTED",
                    "This type is not selected for this service.", status_code=422)

        msb_res = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.master_service_id == ts.master_service_id,
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.is_active == True))
        msb = msb_res.scalar_one_or_none()
        if msb is None:
            raise ServiceOSException("BRAND_NOT_SUPPORTED",
                "This brand is not selected for this service.", status_code=422)
        if not msb.can_override_price:
            raise ServiceOSException("BRAND_OVERRIDE_NOT_ALLOWED",
                "This brand is not configured for price override by admin.", status_code=422)

        tmin = _decimal_or_none(tenant_min_price)
        tmax = _decimal_or_none(tenant_max_price)
        if tmin is None or tmax is None:
            raise ServiceOSException("PRICE_RANGE_REQUIRED",
                "Both minimum and maximum price are required.", status_code=422)
        if tmin > tmax:
            raise ServiceOSException("INVALID_PRICE_RANGE",
                "Minimum price cannot exceed maximum price.", status_code=422)
        if tmin < 0 or tmax < 0:
            raise ServiceOSException("TENANT_PRICE_NEGATIVE",
                "Service prices cannot be negative.", status_code=422)
        if tmin == 0 or tmax == 0:
            raise ServiceOSException("TENANT_PRICE_INVALID",
                "Service prices must be greater than zero.", status_code=422)

        # Upsert scoped by (tenant_service_id, service_type_id, brand_id) —
        # this is the actual fix: previously this looked up by
        # (tenant_service_id, brand_id) only, so Window AC's LG price and
        # Split AC's LG price silently overwrote the same row.
        existing_res = await self.db.execute(
            select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.brand_id == brand_id,
                TenantServiceBrand.service_type_id == service_type_id
                if service_type_id is not None else TenantServiceBrand.service_type_id.is_(None)))
        tsb = existing_res.scalar_one_or_none()
        if tsb is None:
            tsb = TenantServiceBrand(
                tenant_id=ts.tenant_id, tenant_service_id=tenant_service_id,
                service_type_id=service_type_id, brand_id=brand_id, is_enabled=True)
            self.db.add(tsb)

        tsb.tenant_min_price = tmin
        tsb.tenant_max_price = tmax
        await self.db.flush()
        return await self.get_brand_pricing_for_setup(tenant_service_id, service_type_id)

    async def clear_brand_pricing(self, tenant_service_id: uuid.UUID, brand_id: uuid.UUID,
                                  service_type_id: uuid.UUID | None = None) -> dict:
        """Clear a Brand exception without disabling that Brand for matching."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        await self._reject_dimension_price_for_inspection(ts)
        stmt = select(TenantServiceBrand).where(
            TenantServiceBrand.tenant_service_id == tenant_service_id,
            TenantServiceBrand.brand_id == brand_id,
            TenantServiceBrand.service_type_id == service_type_id
            if service_type_id is not None else TenantServiceBrand.service_type_id.is_(None))
        tsb = (await self.db.execute(stmt)).scalar_one_or_none()
        if tsb is not None:
            tsb.tenant_min_price = None
            tsb.tenant_max_price = None
            await self.db.flush()
        return await self.get_brand_pricing_for_setup(tenant_service_id, service_type_id)

    # ── Coverage modes (migration 152) ──────────────────────────────────────
    # ALL / SELECTED_ONLY / ALL_EXCEPT for the Type and Brand dimensions.
    # "selected"/"all_except" both read the SAME TenantServiceType/
    # TenantServiceBrand rows -- only the coverage_mode flag changes whether
    # those rows mean "the supported set" or "the excluded set".
    COVERAGE_MODES = ("all", "selected", "all_except")

    async def set_type_coverage_mode(self, tenant_service_id: uuid.UUID, mode: str) -> dict:
        if mode not in self.COVERAGE_MODES:
            raise ServiceOSException("INVALID_COVERAGE_MODE",
                f"mode must be one of {self.COVERAGE_MODES}.", status_code=422)
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        ts.type_coverage_mode = mode
        await self.db.flush()
        return self._ts_dict(ts)

    async def set_brand_coverage_mode(self, tenant_service_id: uuid.UUID, mode: str) -> dict:
        if mode not in self.COVERAGE_MODES:
            raise ServiceOSException("INVALID_COVERAGE_MODE",
                f"mode must be one of {self.COVERAGE_MODES}.", status_code=422)
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        ts.brand_coverage_mode = mode
        await self.db.flush()
        return self._ts_dict(ts)

    async def is_type_supported(self, ts: TenantService, service_type_id: uuid.UUID) -> bool:
        if ts.type_coverage_mode == "all":
            return True
        r = await self.db.execute(select(TenantServiceType.id).where(
            TenantServiceType.tenant_service_id == ts.id,
            TenantServiceType.service_type_id == service_type_id,
            TenantServiceType.is_enabled == True).limit(1))
        row_exists = r.scalar_one_or_none() is not None
        return (not row_exists) if ts.type_coverage_mode == "all_except" else row_exists

    async def is_brand_supported(self, ts: TenantService, brand_id: uuid.UUID,
                                 service_type_id: uuid.UUID | None = None) -> bool:
        if service_type_id is not None:
            coverage = (await self.db.execute(select(TenantServiceType.brand_coverage).where(
                TenantServiceType.tenant_service_id == ts.id,
                TenantServiceType.service_type_id == service_type_id,
            ))).scalar_one_or_none()
            if coverage is not None:
                if not await self.is_type_supported(ts, service_type_id):
                    return False
                if coverage.get("mode") == "selected" and str(brand_id) not in coverage.get("brand_ids", []):
                    return False
                # Even All brands only covers current, active admin mappings.
                return (await self.db.execute(select(MasterServiceBrand.id).join(
                    Brand, Brand.id == MasterServiceBrand.brand_id,
                ).where(
                    MasterServiceBrand.master_service_id == ts.master_service_id,
                    MasterServiceBrand.brand_id == brand_id,
                    MasterServiceBrand.is_active.is_(True), MasterServiceBrand.status == "active",
                    Brand.is_active.is_(True), Brand.deleted_at.is_(None),
                ).limit(1))).scalar_one_or_none() is not None
        if ts.brand_coverage_mode == "all":
            return True
        r = await self.db.execute(select(TenantServiceBrand.id).where(
            TenantServiceBrand.tenant_service_id == ts.id,
            TenantServiceBrand.brand_id == brand_id,
            TenantServiceBrand.service_type_id.is_(None),
            TenantServiceBrand.is_enabled == True).limit(1))
        row_exists = r.scalar_one_or_none() is not None
        return (not row_exists) if ts.brand_coverage_mode == "all_except" else row_exists

    async def _has_supported_brand(self, ts: TenantService) -> bool:
        """Required brands mean a non-empty effective supported set, not rows.

        ALL needs no marker rows; ALL_EXCEPT rows represent exclusions. Only
        active brands mapped by Admin count, never unrelated tenant records.
        """
        if getattr(ts, "requires_type", False):
            scoped_types = (await self.db.execute(select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == ts.id,
                TenantServiceType.is_enabled.is_(True),
                TenantServiceType.brand_coverage.is_not(None),
            ))).scalars().all()
            if scoped_types:
                candidates = (await self.get_tenant_service_brands(ts.id))["brands"]
                if any((row.brand_coverage or {}).get("mode") == "all" or brand["brand_id"] in (row.brand_coverage or {}).get("brand_ids", [])
                       for row in scoped_types for brand in candidates):
                    return True
        selected = select(TenantServiceBrand.id).where(
            TenantServiceBrand.tenant_service_id == ts.id,
            TenantServiceBrand.brand_id == Brand.id,
            TenantServiceBrand.service_type_id.is_(None),
            TenantServiceBrand.is_enabled.is_(True),
        ).correlate(Brand).exists()
        statement = select(func.count()).select_from(Brand).join(
            MasterServiceBrand, MasterServiceBrand.brand_id == Brand.id,
        ).where(
            MasterServiceBrand.master_service_id == ts.master_service_id,
            MasterServiceBrand.is_active.is_(True), MasterServiceBrand.status == "active",
            Brand.is_active.is_(True), Brand.deleted_at.is_(None),
        )
        if ts.brand_coverage_mode != "all":
            statement = statement.where(~selected if ts.brand_coverage_mode == "all_except" else selected)
        return int((await self.db.execute(statement)).scalar() or 0) > 0

    async def update_last_active_step(self, tenant_service_id: uuid.UUID, step: str) -> dict:
        """Minimal draft/resume pointer: remembers which wizard step the
        tenant was last on, so Save-and-Exit -> resume lands them back
        where they left off."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        ts.last_active_step = step
        await self.db.flush()
        return {"tenant_service_id": str(ts.id), "last_active_step": ts.last_active_step}

    async def validate_for_publish(self, tenant_service_id: uuid.UUID) -> dict:
        """Field-level publish validation (spec section 16 contract). Checks
        every type/brand combination the tenant has marked as SUPPORTED
        (via coverage mode) resolves to a real tenant price -- never invents
        one, never silently allows publishing an unresolvable combination."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        errors: list[dict] = []

        master = (await self.db.execute(
            select(MasterService).where(MasterService.id == ts.master_service_id)
        )).scalar_one_or_none()
        if master is None:
            raise NotFoundException("MasterService", str(ts.master_service_id))
        if isinstance(master, MasterService):
            job_type_id = ts.job_type_id
            blueprint = await self._tenant_setup_blueprint(master, job_type_id)
        else:  # lightweight unit fixture / pre-normalized compatibility row
            blueprint = {
                "type_mode": "required" if ts.requires_type else "optional",
                "brand_mode": "required" if ts.requires_brand else "optional",
                "requires_service_area": False,
                "requires_availability": False,
                "pricing_behavior": (
                    "inspection_required" if str(ts.job_type or "").lower() == "repair" else "fixed"
                ),
            }
        has_authoritative_blueprint = isinstance(master, MasterService)
        latest_setup_revision = (
            await self._setup_rule_revision(ts.master_service_id, ts.job_type_id)
            if has_authoritative_blueprint else ts.setup_rules_revision
        )

        if has_authoritative_blueprint:
            if blueprint["source"] != "service_job_workflow":
                errors.append({
                    "step": "admin_catalog", "job_type_id": str(ts.job_type_id),
                    "dimension_path": {}, "code": "MISSING_PUBLISHED_WORKFLOW",
                    "message": "This job type has no published Admin workflow.",
                })

        # Existing tenant rows store the requirement snapshot they were
        # configured against. If Admin publishes stricter current rules, the
        # validator must use those rules immediately and require a tenant
        # review instead of silently publishing an out-of-date setup.
        requires_type = blueprint["type_mode"] == "required"
        requires_brand = blueprint["brand_mode"] == "required"
        pricing_behavior = str(blueprint.get("pricing_behavior") or "").lower()
        is_inspection_pricing = pricing_behavior in INSPECTION_PRICING_BEHAVIORS
        is_consultation = str(ts.job_type or "").lower() == "consultation"

        if is_consultation:
            settings = (await self.db.execute(
                select(TenantSettings).where(TenantSettings.tenant_id == ts.tenant_id)
            )).scalar_one_or_none()
            fee = ((settings.extra or {}).get("home_services") or {}).get("consultation_fee") if settings else None
            if fee is None or Decimal(str(fee)) <= 0:
                errors.append({
                    "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                    "dimension_path": {}, "code": "MISSING_CONSULTATION_FEE",
                    "message": "Set the provider-wide consultation fee.",
                })
        elif is_inspection_pricing:
            # Inspection/repair pricing is intentionally NOT resolved through
            # Type or Brand. Those dimensions control matching only. The
            # provider collects one visit fee and the eventual work amount is
            # the estimate explicitly approved by the customer.
            if ts.tenant_visit_fee is None or ts.tenant_visit_fee <= 0:
                errors.append({
                    "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                    "dimension_path": {},
                    "code": "MISSING_VISIT_FEE" if has_authoritative_blueprint else "MISSING_TENANT_PRICE",
                    "message": "Set the visit or inspection fee for this service.",
                })
        elif not requires_type and not requires_brand:
            if ts.tenant_min_price is None or ts.tenant_max_price is None:
                errors.append({
                    "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                    "dimension_path": {}, "code": "MISSING_TENANT_PRICE",
                    "message": "Set the provider price for this service.",
                })
        else:
            types_r = await self.db.execute(select(ServiceType.id, ServiceType.name).join(
                MasterServiceType, MasterServiceType.service_type_id == ServiceType.id
            ).where(MasterServiceType.master_service_id == ts.master_service_id,
                    MasterServiceType.is_active == True)) if requires_type else None
            candidate_types = types_r.all() if types_r else [(None, None)]

            brands_r = await self.db.execute(select(Brand.id, Brand.name).join(
                MasterServiceBrand, MasterServiceBrand.brand_id == Brand.id
            ).where(MasterServiceBrand.master_service_id == ts.master_service_id,
                    MasterServiceBrand.is_active.is_(True), MasterServiceBrand.status == "active",
                    Brand.is_active.is_(True), Brand.deleted_at.is_(None))) if requires_brand else None
            candidate_brands = brands_r.all() if brands_r else [(None, None)]

            # A required dimension with zero admin-configured values is
            # itself unpublishable (found live: an empty candidate list made
            # the loops below never execute, vacuously reporting "valid" for
            # a service that literally cannot be priced for anything).
            job_type_label = str(ts.job_type_id) if ts.job_type_id else ts.job_type
            if requires_type and not candidate_types:
                errors.append({
                    "step": "coverage", "job_type_id": job_type_label, "dimension_path": {},
                    "code": "NO_TYPES_CONFIGURED",
                    "message": "This service requires a Type, but no types are configured for it yet.",
                })
            if requires_brand and not candidate_brands:
                errors.append({
                    "step": "coverage", "job_type_id": job_type_label, "dimension_path": {},
                    "code": "NO_BRANDS_CONFIGURED",
                    "message": "Admin must map at least one active brand to this service in the catalog. No supported brands are available for you to select yet.",
                })

            for type_id, type_name in candidate_types:
                if type_id is not None and not await self.is_type_supported(ts, type_id):
                    continue
                for brand_id, brand_name in candidate_brands:
                    if brand_id is not None and not await self.is_brand_supported(ts, brand_id, type_id):
                        continue
                    result = await self.resolve_tenant_price(tenant_service_id, type_id, brand_id)
                    if not result["resolved"]:
                        errors.append({
                            "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                            "dimension_path": {k: v for k, v in
                                (("type", type_name), ("brand", brand_name)) if v is not None},
                            "code": "MISSING_TENANT_PRICE",
                            "message": f"No tenant price resolves for "
                                       f"{' + '.join(v for v in (type_name, brand_name) if v) or 'this service'}.",
                        })

        if (requires_type or requires_brand) and not is_inspection_pricing and not is_consultation:
            selected_types = (await self.db.execute(
                select(TenantServiceType).where(
                    TenantServiceType.tenant_service_id == tenant_service_id,
                    TenantServiceType.is_enabled.is_(True),
                )
            )).scalars().all()
            for selected_type in selected_types:
                has_partial = ((selected_type.tenant_min_price is None)
                               != (selected_type.tenant_max_price is None))
                if has_partial:
                    errors.append({
                        "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                        "dimension_path": {"type_id": str(selected_type.service_type_id)},
                        "code": "INCOMPLETE_TYPE_PRICE_OVERRIDE",
                        "message": "Type override price range is incomplete.",
                    })
            selected_brands = (await self.db.execute(
                select(TenantServiceBrand).where(
                    TenantServiceBrand.tenant_service_id == tenant_service_id,
                    TenantServiceBrand.is_enabled.is_(True),
                )
            )).scalars().all()
            for selected_brand in selected_brands:
                has_partial = ((selected_brand.tenant_min_price is None)
                               != (selected_brand.tenant_max_price is None))
                if has_partial:
                    errors.append({
                        "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                        "dimension_path": {"brand_id": str(selected_brand.brand_id)},
                        "code": "INCOMPLETE_BRAND_PRICE_OVERRIDE",
                        "message": "Brand override price range is incomplete.",
                    })

        # Add-ons are no longer part of provider setup or its completion gates.

        if has_authoritative_blueprint:
            # These are the same normalized setup gates edited by Admin's
            # Tenant Setup Rules tab. Keep them in preflight so Review never
            # reports ready and then fails only when Publish is clicked.
            if requires_type:
                count = int((await self.db.execute(
                    select(func.count()).select_from(TenantServiceType).where(
                        TenantServiceType.tenant_service_id == tenant_service_id,
                        TenantServiceType.is_enabled.is_(True),
                    )
                )).scalar() or 0)
                if count == 0:
                    errors.append({"step": "coverage", "job_type_id": None,
                                   "dimension_path": {"dimension": "type"}, "code": "MISSING_REQUIRED_TYPE_SELECTION",
                                   "message": "Select at least one supported service type."})
            if requires_brand:
                if not any(error["code"] == "NO_BRANDS_CONFIGURED" for error in errors) and not await self._has_supported_brand(ts):
                    errors.append({"step": "coverage", "job_type_id": None,
                                   "dimension_path": {"dimension": "brand"}, "code": "MISSING_REQUIRED_BRAND_SELECTION",
                                   "message": "Select at least one supported brand."})
                if requires_type:
                    scoped_types = (await self.db.execute(select(TenantServiceType, ServiceType.name).join(
                        ServiceType, ServiceType.id == TenantServiceType.service_type_id,
                    ).where(
                        TenantServiceType.tenant_service_id == tenant_service_id,
                        TenantServiceType.is_enabled.is_(True),
                        TenantServiceType.brand_coverage.is_not(None),
                    ))).all()
                    active_brands = None
                    for selected_type, type_name in scoped_types:
                        if active_brands is None:
                            active_brands = (await self.get_tenant_service_brands(tenant_service_id))["brands"]
                        coverage = selected_type.brand_coverage
                        if coverage is None:
                            continue
                        if not any(coverage.get("mode") == "all" or brand["brand_id"] in coverage.get("brand_ids", [])
                                   for brand in active_brands):
                            errors.append({"step": "coverage", "job_type_id": str(ts.job_type_id),
                                           "dimension_path": {"type": type_name},
                                           "code": "MISSING_REQUIRED_BRAND_SELECTION",
                                           "message": f"Select at least one active supported brand for {type_name}."})
            if blueprint["requires_service_area"]:
                count = int((await self.db.execute(
                    select(func.count()).select_from(TenantServiceArea).where(
                        TenantServiceArea.tenant_id == ts.tenant_id,
                        TenantServiceArea.is_active.is_(True),
                    )
                )).scalar() or 0)
                if count == 0:
                    errors.append({"step": "coverage", "job_type_id": None,
                                   "dimension_path": {}, "code": "MISSING_SERVICE_AREA",
                                   "message": "Add at least one active service area."})
            if blueprint["requires_availability"]:
                count = int((await self.db.execute(text(
                    "SELECT count(*) FROM provider_availability_rules "
                    "WHERE tenant_id=:tid AND scope_type='provider' AND is_active=true"
                ), {"tid": str(ts.tenant_id)})).scalar() or 0)
                if count == 0:
                    errors.append({"step": "availability", "job_type_id": None,
                                   "dimension_path": {}, "code": "MISSING_BUSINESS_HOURS",
                                   "message": "Configure at least one active business-hours rule."})

        return {
            "valid": len(errors) == 0,
            "service_name": getattr(master, "service_name", None),
            "job_type": ts.job_type,
            "errors": errors,
            "setup_update_required": bool(
                has_authoritative_blueprint
                and ts.setup_rules_revision != latest_setup_revision
            ),
            "tenant_setup_rules_revision": ts.setup_rules_revision,
            "latest_setup_rules_revision": latest_setup_revision if has_authoritative_blueprint else None,
        }

    async def get_blueprint_update_status(self, tenant_service_id: uuid.UUID) -> dict:
        """Spec section 19: 'Service configuration update required' detection.
        Fails closed -- a tenant setup with no recorded blueprint_version_id
        (pre-versioning legacy row) is reported as update_required=True with
        a null diff, never silently treated as up to date."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        master = await self.db.get(MasterService, ts.master_service_id)
        latest_setup_revision = (
            await self._setup_rule_revision(ts.master_service_id, ts.job_type_id)
            if master else ts.setup_rules_revision
        )
        setup_update_required = bool(
            master and ts.setup_rules_revision != latest_setup_revision
        )
        setup_change = (
            f"Tenant setup rules changed from revision {ts.setup_rules_revision} to {latest_setup_revision}."
            if setup_update_required and master else None
        )

        latest_r = await self.db.execute(
            select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == ts.master_service_id,
                ServiceBlueprintVersion.status == "published",
            ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1))
        latest = latest_r.scalar_one_or_none()

        if not latest:
            return {
                "update_required": setup_update_required, "current_version": None, "latest_version": None,
                "changes": [setup_change] if setup_change else [],
                "current_setup_rules_revision": ts.setup_rules_revision,
                "latest_setup_rules_revision": latest_setup_revision if master else None,
            }

        if ts.blueprint_version_id is None:
            return {
                "update_required": True, "current_version": None,
                "latest_version": latest.version_number,
                "changes": ["No recorded blueprint version for this setup."] + ([setup_change] if setup_change else []),
                "current_setup_rules_revision": ts.setup_rules_revision,
                "latest_setup_rules_revision": latest_setup_revision if master else None,
            }

        if ts.blueprint_version_id == latest.id:
            return {
                "update_required": setup_update_required, "current_version": latest.version_number,
                "latest_version": latest.version_number, "changes": [setup_change] if setup_change else [],
                "current_setup_rules_revision": ts.setup_rules_revision,
                "latest_setup_rules_revision": latest_setup_revision if master else None,
            }

        current_r = await self.db.execute(
            select(ServiceBlueprintVersion).where(ServiceBlueprintVersion.id == ts.blueprint_version_id))
        current = current_r.scalar_one_or_none()

        # Every superseded version between the tenant's version (exclusive)
        # and latest (inclusive), oldest first, so change_summary reads as a
        # chronological changelog rather than just the single latest diff.
        chain_r = await self.db.execute(
            select(ServiceBlueprintVersion.change_summary).where(
                ServiceBlueprintVersion.master_service_id == ts.master_service_id,
                ServiceBlueprintVersion.version_number > (current.version_number if current else 0),
            ).order_by(ServiceBlueprintVersion.version_number))
        changes = [c for c, in chain_r if c]

        return {
            "update_required": True,
            "current_version": current.version_number if current else None,
            "latest_version": latest.version_number,
            "changes": changes + ([setup_change] if setup_change else []),
            "current_setup_rules_revision": ts.setup_rules_revision,
            "latest_setup_rules_revision": latest_setup_revision if master else None,
        }

    async def resolve_tenant_price(self, tenant_service_id: uuid.UUID,
                                    service_type_id: uuid.UUID | None = None,
                                    brand_id: uuid.UUID | None = None) -> dict:
        """Deterministic tenant price resolution -- the single source of
        truth every customer-facing quote must go through. Never invents a
        price, never falls back to another tenant's or the admin's price,
        never silently resolves across tenants. Precedence (most specific
        wins): exact type+brand override -> type-only override -> brand-only
        override (fixed/non-type-based services) -> tenant default -> none.

        Returns the exact contract shape the future wizard/pricing-preview
        API needs (resolved / pricing_model / minimum_price / maximum_price
        / currency / source_rule_id / source / inherited_from_rule_id), or
        {"resolved": False, "reason": "NO_TENANT_PRICE_FOR_COMBINATION"}.
        """
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Coverage gate: an unsupported type/brand (per coverage_mode) must
        # never resolve to a price, regardless of any override row that
        # might technically exist -- "unsupported combinations are never
        # available to customers."
        if service_type_id is not None and not await self.is_type_supported(ts, service_type_id):
            return {"resolved": False, "reason": "COMBINATION_NOT_SUPPORTED"}
        if brand_id is not None and not await self.is_brand_supported(ts, brand_id, service_type_id):
            return {"resolved": False, "reason": "COMBINATION_NOT_SUPPORTED"}

        def _found(rule_id, source: str, min_price, max_price) -> dict:
            return {
                "resolved": True,
                "pricing_model": "FIXED" if min_price == max_price else "RANGE",
                "minimum_price": float(min_price),
                "maximum_price": float(max_price),
                "currency": "INR",
                "source_rule_id": str(rule_id),
                "source": source,
                "inherited_from_rule_id": None,
            }

        # 1. Exact type + brand override.
        if service_type_id is not None and brand_id is not None:
            r = await self.db.execute(select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.service_type_id == service_type_id,
                TenantServiceBrand.brand_id == brand_id,
                TenantServiceBrand.is_enabled == True))
            tsb = r.scalar_one_or_none()
            if tsb and tsb.tenant_min_price is not None and tsb.tenant_max_price is not None:
                return _found(tsb.id, "type_brand_override", tsb.tenant_min_price, tsb.tenant_max_price)

        # 2. Type-only override.
        if service_type_id is not None:
            r = await self.db.execute(select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == tenant_service_id,
                TenantServiceType.service_type_id == service_type_id,
                TenantServiceType.is_enabled == True))
            tst = r.scalar_one_or_none()
            if tst and tst.tenant_min_price is not None and tst.tenant_max_price is not None:
                return _found(tst.id, "type_override", tst.tenant_min_price, tst.tenant_max_price)

        # 3. Brand-only override (service_type_id NULL row -- fixed/non-type-based services).
        if brand_id is not None:
            r = await self.db.execute(select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.service_type_id.is_(None),
                TenantServiceBrand.brand_id == brand_id,
                TenantServiceBrand.is_enabled == True))
            tsb = r.scalar_one_or_none()
            if tsb and tsb.tenant_min_price is not None and tsb.tenant_max_price is not None:
                return _found(tsb.id, "brand_override", tsb.tenant_min_price, tsb.tenant_max_price)

        # 4. Tenant default job-type rule.
        if ts.tenant_min_price is not None and ts.tenant_max_price is not None:
            return _found(ts.id, "tenant_default", ts.tenant_min_price, ts.tenant_max_price)

        # 5. No price resolves -- never invent, never fall back to admin/another tenant.
        return {"resolved": False, "reason": "NO_TENANT_PRICE_FOR_COMBINATION"}

    async def publish_service(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        missing: list[dict] = []

        master = (await self.db.execute(
            select(MasterService).where(MasterService.id == ts.master_service_id)
        )).scalar_one_or_none()
        if master is None:
            raise NotFoundException("MasterService", str(ts.master_service_id))
        if isinstance(master, MasterService):
            blueprint = await self._tenant_setup_blueprint(master, ts.job_type_id)
        else:  # lightweight unit fixture / pre-normalized compatibility row
            blueprint = {
                "type_mode": "required" if ts.requires_type else "optional",
                "brand_mode": "required" if ts.requires_brand else "optional",
                "requires_service_area": False,
                "requires_availability": False,
                "pricing_behavior": None,
                "source": "service_job_workflow",
            }
        requires_type = blueprint["type_mode"] == "required"
        requires_brand = blueprint["brand_mode"] == "required"

        # The preflight endpoint and the mutation must share one readiness
        # authority. In particular, inspection workflows require one visit
        # fee and never require Type/Brand price overrides.
        validation = await self.validate_for_publish(tenant_service_id)
        if not validation["valid"]:
            missing = [{
                "field": error["step"],
                "job_type_id": error.get("job_type_id"),
                "dimension_path": error.get("dimension_path", {}),
                "code": error.get("code"),
                "message": error["message"],
            } for error in validation["errors"]]
            raise ServiceOSException(
                "SERVICE_SETUP_INCOMPLETE",
                f"You must complete {len(missing)} item(s) before publishing.",
                status_code=422,
                context={"missing": missing, "missing_count": len(missing)},
            )

        for blocker in ([] if blueprint["source"] == "service_job_workflow" else [{
            "code": "MISSING_PUBLISHED_WORKFLOW", "job_type_id": str(ts.job_type_id),
            "message": "This job type has no published Admin workflow.",
        }]):
            missing.append({
                "field": "admin_catalog",
                "job_type_id": blocker.get("job_type_id"),
                "code": blocker["code"],
                "message": blocker["message"],
            })

        types_res = await self.db.execute(
            select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == tenant_service_id,
                TenantServiceType.is_enabled == True))
        types = types_res.scalars().all()
        if requires_type and not types:
            missing.append({"field": "types", "message": "Select at least one type."})
        # Any type the tenant selected — required or not — must be priced
        # before publish (ticket rule: "Price range set for every selected type").
        brands_res = await self.db.execute(
            select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.is_enabled == True))
        brands = brands_res.scalars().all()
        if requires_brand and not await self._has_supported_brand(ts):
            missing.append({"field": "brands", "message": "Select at least one supported brand."})
        for b in brands:
            has_partial = (b.tenant_min_price is None) != (b.tenant_max_price is None)
            if has_partial:
                missing.append({"field": f"brand_pricing:{b.brand_id}",
                                 "message": "Brand override price range is incomplete."})

        if blueprint["requires_service_area"]:
            areas_res = await self.db.execute(
                select(func.count()).select_from(TenantServiceArea).where(
                    TenantServiceArea.tenant_id == ts.tenant_id, TenantServiceArea.is_active.is_(True)))
            active_areas = areas_res.scalar_one()
            if active_areas == 0:
                missing.append({"field": "service_areas",
                                 "message": "At least one active service area is required to publish."})

        if blueprint["requires_availability"]:
            availability_count = int((await self.db.execute(text(
                "SELECT count(*) FROM provider_availability_rules "
                "WHERE tenant_id=:tid AND scope_type='provider' AND is_active=true"
            ), {"tid": str(ts.tenant_id)})).scalar() or 0)
            if availability_count == 0:
                missing.append({"field": "availability",
                                 "message": "Configure at least one active business-hours rule."})

        if missing:
            raise ServiceOSException("SERVICE_SETUP_INCOMPLETE",
                f"You must complete {len(missing)} item(s) before publishing.",
                status_code=422, context={"missing": missing, "missing_count": len(missing)})

        ts.setup_status = "published"
        ts.published_at = utcnow()
        ts.is_enabled = True
        ts.requires_type = requires_type
        ts.requires_brand = requires_brand
        ts.setup_rules_revision = (
            await self._setup_rule_revision(ts.master_service_id, ts.job_type_id)
            if isinstance(master, MasterService) else ts.setup_rules_revision
        )
        latest_blueprint = (await self.db.execute(
            select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == ts.master_service_id,
                ServiceBlueprintVersion.status == "published",
            ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1)
        )).scalar_one_or_none()
        ts.blueprint_version_id = latest_blueprint.id if latest_blueprint else ts.blueprint_version_id
        # Coverage in the canonical tenant UI is provider-wide: every active
        # zipcode applies to every service the provider publishes.  Matching,
        # however, reads the normalized tenant_service_area_services table.
        # Materialize those rows here so publishing through Services & Pricing
        # can never leave a service invisible to booking merely because the
        # retired per-area mapping screen was not visited.
        active_area_ids = (await self.db.execute(
            select(TenantServiceArea.id).where(
                TenantServiceArea.tenant_id == ts.tenant_id,
                TenantServiceArea.is_active.is_(True),
            )
        )).scalars().all()
        if active_area_ids:
            active_mappings = (await self.db.execute(
                select(TenantServiceAreaService).where(
                    TenantServiceAreaService.tenant_id == ts.tenant_id,
                    TenantServiceAreaService.service_id == ts.master_service_id,
                    TenantServiceAreaService.job_type == ts.job_type,
                    TenantServiceAreaService.is_available.is_(True),
                )
            )).scalars().all()
            mappings_by_area = {
                mapping.tenant_service_area_id: mapping
                for mapping in active_mappings
            }
            for area_id in active_area_ids:
                existing_mapping = mappings_by_area.get(area_id)
                if existing_mapping is not None:
                    existing_mapping.status = "ACTIVE"
                else:
                    self.db.add(TenantServiceAreaService(
                        tenant_service_area_id=area_id,
                        tenant_id=ts.tenant_id,
                        service_id=ts.master_service_id,
                        job_type=ts.job_type,
                        is_available=True,
                        status="ACTIVE",
                    ))
        await self.db.flush()
        return self._ts_dict(ts)

    async def save_draft(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        if ts.setup_status != "published":
            ts.setup_status = "draft"
            await self.db.flush()
        return self._ts_dict(ts)

    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════

    async def _load_tenant_service(self, tenant_service_id: uuid.UUID) -> TenantService:
        res = await self.db.execute(
            select(TenantService).where(
                TenantService.id == tenant_service_id,
                TenantService.deleted_at.is_(None)))
        ts = res.scalar_one_or_none()
        if not ts:
            raise NotFoundException("TenantService", str(tenant_service_id))
        return ts

    # Platform roles carry no tenant_id (super_admin / admin_* have tenant_id=None
    # per the 01D-R canonical model) and legitimately operate cross-tenant.
    PLATFORM_ROLES = ("super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly")

    def _assert_tenant_owns_ts(self, ts: TenantService) -> None:
        # MODULE-L5-03 hardening: enforce for EVERY tenant-scoped actor, not a
        # fragile allowlist. The old check only covered ("tenant_owner","staff"),
        # so any other tenant role (e.g. technician, or a future tenant role)
        # would bypass the ownership check and fail open. Platform roles have
        # actor_tenant_id=None and are correctly skipped.
        if self.actor_tenant_id and self.actor_role not in self.PLATFORM_ROLES:
            if ts.tenant_id != self.actor_tenant_id:
                raise NotFoundException("TenantService", str(ts.id))

    def _ts_dict(
        self,
        ts: TenantService,
        *,
        service_name: str | None = None,
        job_type_label: str | None = None,
        service_group_name: str | None = None,
    ) -> dict:
        return {
            "tenant_service_id": str(ts.id),
            "tenant_id": str(ts.tenant_id),
            "master_service_id": str(ts.master_service_id),
            "category_id": str(ts.category_id),
            "job_type": ts.job_type,
            "service_name": service_name,
            "job_type_label": job_type_label,
            "service_group_name": service_group_name,
            "is_enabled": ts.is_enabled,
            "tenant_display_name": ts.tenant_display_name,
            "tenant_description": ts.tenant_description,
            "tenant_base_price": float(ts.tenant_base_price) if ts.tenant_base_price else None,
            "tenant_min_price": float(ts.tenant_min_price) if ts.tenant_min_price else None,
            "tenant_max_price": float(ts.tenant_max_price) if ts.tenant_max_price else None,
            "tenant_visit_fee": float(ts.tenant_visit_fee) if ts.tenant_visit_fee else None,
            "tenant_emergency_surcharge": float(ts.tenant_emergency_surcharge) if ts.tenant_emergency_surcharge is not None else None,
            "warranty_days": ts.warranty_days,
            "override_allowed": ts.override_allowed,
            "requires_brand": ts.requires_brand,
            "requires_type": ts.requires_type,
            "is_active": ts.is_active,
            "setup_status": ts.setup_status,
            "published_at": ts.published_at.isoformat() if ts.published_at else None,
            "created_at": ts.created_at.isoformat() if ts.created_at else None,
            "type_coverage_mode": ts.type_coverage_mode,
            "brand_coverage_mode": ts.brand_coverage_mode,
            "last_active_step": ts.last_active_step,
            "job_type_id": str(ts.job_type_id) if ts.job_type_id else None,
            "setup_rules_revision": ts.setup_rules_revision,
        }

    @staticmethod
    def _validate_warranty_days(value) -> int:
        try:
            days = int(value)
        except (TypeError, ValueError):
            raise ServiceOSException(
                "WARRANTY_DAYS_INVALID", "Warranty period must be a whole number of days.", status_code=422,
            )
        if days < 5:
            raise ServiceOSException(
                "WARRANTY_BELOW_PLATFORM_MINIMUM",
                "Warranty period cannot be shorter than the 5-day platform minimum.",
                status_code=422,
            )
        if days > 3650:
            raise ServiceOSException(
                "WARRANTY_DAYS_INVALID", "Warranty period cannot exceed 10 years.", status_code=422,
            )
        return days


def _decimal_or_none(val) -> Decimal | None:
    if val is None:
        return None
    try:
        amount = Decimal(str(val))
    except Exception:
        raise ServiceOSException("TENANT_PRICE_INVALID", "Enter a valid numeric amount.", status_code=422)
    if not amount.is_finite():
        raise ServiceOSException("TENANT_PRICE_INVALID", "Enter a finite numeric amount.", status_code=422)
    return amount

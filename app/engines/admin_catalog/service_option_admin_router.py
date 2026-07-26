"""Sprint 34E — Admin routers for Service Options, Issue Types, Option Groups, and Mappings."""
import uuid
from fastapi import APIRouter, Depends, Query, Request, status

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.service_option_service import ServiceOptionService
from app.schemas.base import ApiResponse, ok
from sqlalchemy.ext.asyncio import AsyncSession

# ── Option Groups ──────────────────────────────────────────────────────────────
grp_router = APIRouter(prefix="/v1/admin/service-option-groups",
                       tags=["Service Option Groups"])

# ── Service Options ────────────────────────────────────────────────────────────
opt_router = APIRouter(prefix="/v1/admin/service-options", tags=["Service Options"])

# ── Issue Types ────────────────────────────────────────────────────────────────
iss_router = APIRouter(prefix="/v1/admin/issue-types-v2", tags=["Issue Types"])

# ── Service Mappings ───────────────────────────────────────────────────────────
map_router = APIRouter(prefix="/v1/admin/master-services", tags=["Service Option Mappings"])

# ── Checklist Items (Phase 2 — master/admin-catalog-level) ─────────────────────
chk_router = APIRouter(prefix="/v1/admin/checklists", tags=["Checklists"])


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> ServiceOptionService:
    return ServiceOptionService(
        db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, request_id=getattr(r.state, "request_id", "—"))


def _rid(r): return getattr(r.state, "request_id", "—")


# ═════════════════════════════════════════════════════════
# OPTION GROUPS
# ═════════════════════════════════════════════════════════

@grp_router.get("", response_model=ApiResponse[list])
async def list_option_groups(r: Request,
                              status_filter: str | None = Query(None, alias="status"),
                              category_id: uuid.UUID | None = Query(None),
                              u: UserContext = Depends(require_super_admin),
                              s: ServiceOptionService = Depends(_svc)):
    return ok(await s.list_option_groups(status_filter, category_id), _rid(r))


@grp_router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_option_group(r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: ServiceOptionService = Depends(_svc)):
    return ok(await s.create_option_group(await r.json()), _rid(r))


@grp_router.put("/{group_id}", response_model=ApiResponse[dict])
async def update_option_group(group_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: ServiceOptionService = Depends(_svc)):
    return ok(await s.update_option_group(group_id, await r.json()), _rid(r))


# ═════════════════════════════════════════════════════════
# SERVICE OPTIONS
# ═════════════════════════════════════════════════════════

@opt_router.get("/summary", response_model=ApiResponse[dict])
async def get_service_options_summary(r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: ServiceOptionService = Depends(_svc)):
    return ok(await s.list_service_options_summary(), _rid(r))


@opt_router.get("", response_model=ApiResponse[dict])
async def list_service_options(r: Request,
                                status_filter: str | None = Query(None, alias="status"),
                                category_id: uuid.UUID | None = Query(None),
                                master_service_id: uuid.UUID | None = Query(None),
                                option_group_id: uuid.UUID | None = Query(None),
                                option_type: str | None = Query(None),
                                mapped: bool | None = Query(None),
                                search: str | None = Query(None),
                                page: int = Query(1, ge=1),
                                page_size: int = Query(50, ge=1, le=200),
                                u: UserContext = Depends(require_super_admin),
                                s: ServiceOptionService = Depends(_svc)):
    return ok(await s.list_service_options(
        status_filter, category_id, master_service_id, option_group_id,
        option_type, mapped, search, page, page_size), _rid(r))


@opt_router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_service_option(r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.create_service_option(await r.json()), _rid(r))


@opt_router.get("/{option_id}", response_model=ApiResponse[dict])
async def get_service_option(option_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: ServiceOptionService = Depends(_svc)):
    return ok(await s.get_service_option(option_id), _rid(r))


@opt_router.put("/{option_id}", response_model=ApiResponse[dict])
async def update_service_option(option_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.update_service_option(option_id, await r.json()), _rid(r))


@opt_router.post("/{option_id}/activate", response_model=ApiResponse[dict])
async def activate_service_option(option_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: ServiceOptionService = Depends(_svc)):
    return ok(await s.activate_service_option(option_id), _rid(r))


@opt_router.post("/{option_id}/deactivate", response_model=ApiResponse[dict])
async def deactivate_service_option(option_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_super_admin),
                                     s: ServiceOptionService = Depends(_svc)):
    return ok(await s.deactivate_service_option(option_id), _rid(r))


@opt_router.post("/{option_id}/archive", response_model=ApiResponse[dict])
async def archive_service_option(option_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: ServiceOptionService = Depends(_svc)):
    return ok(await s.archive_service_option(option_id), _rid(r))


# ═════════════════════════════════════════════════════════
# ISSUE TYPES (v2 with status lifecycle)
# ═════════════════════════════════════════════════════════

@iss_router.get("", response_model=ApiResponse[dict])
async def list_issue_types(r: Request,
                            status_filter: str | None = Query(None, alias="status"),
                            category_id: uuid.UUID | None = Query(None),
                            master_service_id: uuid.UUID | None = Query(None),
                            search: str | None = Query(None),
                            page: int = Query(1, ge=1),
                            page_size: int = Query(50, ge=1, le=200),
                            u: UserContext = Depends(require_super_admin),
                            s: ServiceOptionService = Depends(_svc)):
    return ok(await s.list_issue_types(status_filter, category_id, master_service_id,
                                       search, page, page_size), _rid(r))


@iss_router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_issue_type(r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: ServiceOptionService = Depends(_svc)):
    return ok(await s.create_issue_type(await r.json()), _rid(r))


@iss_router.get("/{issue_id}", response_model=ApiResponse[dict])
async def get_issue_type(issue_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: ServiceOptionService = Depends(_svc)):
    return ok(await s.get_issue_type(issue_id), _rid(r))


@iss_router.put("/{issue_id}", response_model=ApiResponse[dict])
async def update_issue_type(issue_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: ServiceOptionService = Depends(_svc)):
    return ok(await s.update_issue_type(issue_id, await r.json()), _rid(r))


@iss_router.post("/{issue_id}/activate", response_model=ApiResponse[dict])
async def activate_issue_type(issue_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: ServiceOptionService = Depends(_svc)):
    return ok(await s.activate_issue_type(issue_id), _rid(r))


@iss_router.post("/{issue_id}/deactivate", response_model=ApiResponse[dict])
async def deactivate_issue_type(issue_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.deactivate_issue_type(issue_id), _rid(r))


@iss_router.post("/{issue_id}/archive", response_model=ApiResponse[dict])
async def archive_issue_type(issue_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: ServiceOptionService = Depends(_svc)):
    return ok(await s.archive_issue_type(issue_id), _rid(r))


# ═════════════════════════════════════════════════════════
# SERVICE ↔ OPTION MAPPINGS
# ═════════════════════════════════════════════════════════

@map_router.get("/{service_id}/options", response_model=ApiResponse[list])
async def list_service_option_mappings(service_id: uuid.UUID, r: Request,
                                        job_type_id: uuid.UUID | None = Query(None),
                                        u: UserContext = Depends(require_super_admin),
                                        s: ServiceOptionService = Depends(_svc)):
    return ok(await s.list_service_option_mappings(service_id, job_type_id), _rid(r))


@map_router.post("/{service_id}/options", response_model=ApiResponse[dict],
                 status_code=status.HTTP_201_CREATED)
async def add_service_option_mapping(service_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: ServiceOptionService = Depends(_svc)):
    return ok(await s.add_service_option_mapping(service_id, await r.json()), _rid(r))


@map_router.put("/{service_id}/options/{mapping_id}", response_model=ApiResponse[dict])
async def update_service_option_mapping(service_id: uuid.UUID, mapping_id: uuid.UUID,
                                         r: Request,
                                         u: UserContext = Depends(require_super_admin),
                                         s: ServiceOptionService = Depends(_svc)):
    return ok(await s.update_service_option_mapping(mapping_id, await r.json()), _rid(r))


@map_router.delete("/{service_id}/options/{mapping_id}", response_model=ApiResponse[dict])
async def remove_service_option_mapping(service_id: uuid.UUID, mapping_id: uuid.UUID,
                                         r: Request,
                                         u: UserContext = Depends(require_super_admin),
                                         s: ServiceOptionService = Depends(_svc)):
    return ok(await s.remove_service_option_mapping(mapping_id), _rid(r))


# ── Service ↔ Issue Mappings ──────────────────────────────────────────────────

@map_router.get("/{service_id}/issues", response_model=ApiResponse[list])
async def list_service_issue_mappings(service_id: uuid.UUID, r: Request,
                                       job_type_id: uuid.UUID | None = Query(None),
                                       u: UserContext = Depends(require_super_admin),
                                       s: ServiceOptionService = Depends(_svc)):
    return ok(await s.list_service_issue_mappings(service_id, job_type_id), _rid(r))


@map_router.post("/{service_id}/issues", response_model=ApiResponse[dict],
                 status_code=status.HTTP_201_CREATED)
async def add_service_issue_mapping(service_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_super_admin),
                                     s: ServiceOptionService = Depends(_svc)):
    return ok(await s.add_service_issue_mapping(service_id, await r.json()), _rid(r))


@map_router.put("/{service_id}/issues/{mapping_id}", response_model=ApiResponse[dict])
async def update_service_issue_mapping(service_id: uuid.UUID, mapping_id: uuid.UUID,
                                        r: Request,
                                        u: UserContext = Depends(require_super_admin),
                                        s: ServiceOptionService = Depends(_svc)):
    return ok(await s.update_service_issue_mapping(mapping_id, await r.json()), _rid(r))


@map_router.delete("/{service_id}/issues/{mapping_id}", response_model=ApiResponse[dict])
async def remove_service_issue_mapping(service_id: uuid.UUID, mapping_id: uuid.UUID,
                                        r: Request,
                                        u: UserContext = Depends(require_super_admin),
                                        s: ServiceOptionService = Depends(_svc)):
    return ok(await s.remove_service_issue_mapping(mapping_id), _rid(r))


# ── Workflow Mapping Readiness (Phase 2 — readiness check only, not full
#    workflow certification; see PHASE_2_CATALOG_SERVICE_SETUP_AUDIT.md) ───────

@map_router.get("/{service_id}/workflow-mapping-status", response_model=ApiResponse[dict])
async def get_workflow_mapping_status(service_id: uuid.UUID, r: Request,
                                       u: UserContext = Depends(require_super_admin),
                                       db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.engines.admin_catalog.models import MasterWorkflowTemplate, MasterService

    svc = await db.get(MasterService, service_id)
    if not svc:
        from app.exceptions import NotFoundException
        raise NotFoundException("MasterService", str(service_id))

    result = await db.execute(select(MasterWorkflowTemplate).where(
        MasterWorkflowTemplate.master_service_id == service_id,
        MasterWorkflowTemplate.is_active == True))  # noqa: E712
    mapped_templates = result.scalars().all()

    status_value = "mapped" if mapped_templates else "missing_mapping"
    return ok({
        "service_id": str(service_id),
        "service_name": svc.service_name,
        "workflow_mapping_status": status_value,
        "mapped_workflow_count": len(mapped_templates),
        "mapped_workflow_names": [t.name for t in mapped_templates],
        "fix_link": "/admin/workflows/templates",
    }, _rid(r))


# ═════════════════════════════════════════════════════════
# CHECKLIST ITEMS (Phase 2 — master/admin-catalog-level)
# ═════════════════════════════════════════════════════════

@chk_router.get("", response_model=ApiResponse[dict])
async def list_checklist_items(r: Request,
                                status_filter: str | None = Query(None, alias="status"),
                                category_id: uuid.UUID | None = Query(None),
                                master_service_id: uuid.UUID | None = Query(None),
                                search: str | None = Query(None),
                                page: int = Query(1, ge=1),
                                page_size: int = Query(50, ge=1, le=200),
                                u: UserContext = Depends(require_super_admin),
                                s: ServiceOptionService = Depends(_svc)):
    return ok(await s.list_checklist_items(status_filter, category_id, master_service_id,
                                            search, page, page_size), _rid(r))


@chk_router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_checklist_item(r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.create_checklist_item(await r.json()), _rid(r))


@chk_router.post("/seed-defaults", response_model=ApiResponse[dict])
async def seed_default_checklists(r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: ServiceOptionService = Depends(_svc)):
    return ok(await s.seed_default_checklists(), _rid(r))


@chk_router.get("/{item_id}", response_model=ApiResponse[dict])
async def get_checklist_item(item_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: ServiceOptionService = Depends(_svc)):
    return ok(await s.get_checklist_item(item_id), _rid(r))


@chk_router.put("/{item_id}", response_model=ApiResponse[dict])
async def update_checklist_item(item_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.update_checklist_item(item_id, await r.json()), _rid(r))


@chk_router.post("/{item_id}/enable", response_model=ApiResponse[dict])
async def enable_checklist_item(item_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.activate_checklist_item(item_id), _rid(r))


@chk_router.post("/{item_id}/disable", response_model=ApiResponse[dict])
async def disable_checklist_item(item_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: ServiceOptionService = Depends(_svc)):
    return ok(await s.deactivate_checklist_item(item_id), _rid(r))


@chk_router.post("/{item_id}/archive", response_model=ApiResponse[dict])
async def archive_checklist_item(item_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: ServiceOptionService = Depends(_svc)):
    return ok(await s.archive_checklist_item(item_id), _rid(r))

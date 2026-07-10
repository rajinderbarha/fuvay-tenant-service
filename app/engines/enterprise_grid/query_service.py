"""Sprint 26 — Enterprise List Query Service."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field

from app.engines.enterprise_grid.constants import (
    MAX_PAGE_SIZE, MAX_SEARCH_LENGTH,
    ERR_GRID_RESOURCE_NOT_FOUND, ERR_GRID_FILTER_NOT_ALLOWED,
    ERR_GRID_SORT_NOT_ALLOWED, ERR_GRID_INVALID_PAGE, ERR_GRID_INVALID_PAGE_SIZE,
    ERR_GRID_INVALID_DATE_RANGE, ERR_GRID_SEARCH_TOO_LONG, ERR_GRID_ACCESS_DENIED,
    SCOPE_ADMIN_GLOBAL, SCOPE_PROVIDER,
)
from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry


@dataclass
class ValidatedListQuery:
    resource_key:   str
    page:           int
    page_size:      int
    sort_by:        str
    sort_direction: str
    search:         str | None
    filters:        dict  = field(default_factory=dict)
    config:         dict  = field(default_factory=dict)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass
class ListResponseMeta:
    page:         int
    page_size:    int
    total_items:  int
    sort_by:      str
    sort_direction: str
    filters_applied: dict
    resource_key:  str
    has_next:     bool = False
    has_previous: bool = False
    total_pages:  int  = 0

    def to_dict(self) -> dict:
        return {
            "pagination": {
                "page":          self.page,
                "page_size":     self.page_size,
                "total_items":   self.total_items,
                "total_pages":   self.total_pages,
                "has_next":      self.has_next,
                "has_previous":  self.has_previous,
            },
            "sort": {
                "sort_by":        self.sort_by,
                "sort_direction": self.sort_direction,
            },
            "filters_applied":   self.filters_applied,
        }


class EnterpriseListQueryService:
    """Validates and parses enterprise list query params.

    Does NOT execute queries against the DB — that stays in each endpoint.
    Returns ValidatedListQuery which endpoints use to build safe WHERE/ORDER/LIMIT clauses.
    """

    def parse_query_params(self, resource_key: str, raw: dict) -> ValidatedListQuery:
        if not EnterpriseFilterRegistry.resource_exists(resource_key):
            raise ValueError(ERR_GRID_RESOURCE_NOT_FOUND)

        config = EnterpriseFilterRegistry.get_config(resource_key)
        default_sort = config["default_sort"]

        # page / page_size
        try:
            page = int(raw.get("page", 1))
        except (ValueError, TypeError):
            raise ValueError(ERR_GRID_INVALID_PAGE)
        if page < 1:
            raise ValueError(ERR_GRID_INVALID_PAGE)

        try:
            page_size = int(raw.get("page_size", 25))
        except (ValueError, TypeError):
            raise ValueError(ERR_GRID_INVALID_PAGE_SIZE)
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise ValueError(ERR_GRID_INVALID_PAGE_SIZE)

        # sort
        sort_by        = raw.get("sort_by")        or default_sort["sort_by"]
        sort_direction = raw.get("sort_direction") or default_sort["sort_direction"]
        sort_direction = sort_direction.lower()
        if sort_direction not in ("asc", "desc"):
            sort_direction = "desc"
        self.validate_sort(resource_key, sort_by)

        # search
        search = raw.get("search") or None
        if search and len(search) > MAX_SEARCH_LENGTH:
            raise ValueError(ERR_GRID_SEARCH_TOO_LONG)

        # filters
        allowed = set(config["allowed_filters"])
        filters = {}
        date_fields = {"date_from", "date_to", "created_from", "created_to",
                       "updated_from", "updated_to"}
        for k, v in raw.items():
            if k in ("page", "page_size", "sort_by", "sort_direction", "search"):
                continue
            if v is None or v == "":
                continue
            if k not in allowed:
                continue  # silently ignore unknown filters (frontend may send extra)
            if k in date_fields:
                filters[k] = self._parse_date(k, v)
            else:
                filters[k] = v

        # validate date range
        d_from = filters.get("date_from") or filters.get("created_from")
        d_to   = filters.get("date_to")   or filters.get("created_to")
        if d_from and d_to and d_from > d_to:
            raise ValueError(ERR_GRID_INVALID_DATE_RANGE)

        return ValidatedListQuery(
            resource_key   = resource_key,
            page           = page,
            page_size      = page_size,
            sort_by        = sort_by,
            sort_direction = sort_direction,
            search         = search,
            filters        = filters,
            config         = config,
        )

    def validate_filters(self, resource_key: str, filters: dict) -> list[str]:
        """Returns list of invalid filter keys."""
        config  = EnterpriseFilterRegistry.get_config(resource_key)
        allowed = set(config["allowed_filters"])
        return [k for k in filters if k not in allowed]

    def validate_sort(self, resource_key: str, sort_by: str) -> None:
        if not EnterpriseFilterRegistry.validate_sort(resource_key, sort_by):
            raise ValueError(f"{ERR_GRID_SORT_NOT_ALLOWED}: {sort_by}")

    def validate_scope(
        self,
        resource_key: str,
        actor_tenant_id: uuid.UUID | None,
        requested_tenant_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        """Returns effective tenant_id to filter by (None = admin can see all)."""
        scope = EnterpriseFilterRegistry.get_scope_type(resource_key)
        if scope == SCOPE_PROVIDER:
            # provider MUST use their own tenant_id
            return actor_tenant_id
        if scope == SCOPE_ADMIN_GLOBAL:
            # admin can pass tenant_id filter or leave null for all
            return requested_tenant_id
        return actor_tenant_id

    def build_response(
        self,
        vq: ValidatedListQuery,
        items: list,
        total_items: int,
        saved_view_id: str | None = None,
    ) -> dict:
        total_pages = (total_items + vq.page_size - 1) // vq.page_size if total_items > 0 else 0
        return {
            "items":      items,
            "pagination": {
                "page":         vq.page,
                "page_size":    vq.page_size,
                "total_items":  total_items,
                "total_pages":  total_pages,
                "has_next":     vq.page < total_pages,
                "has_previous": vq.page > 1,
            },
            "sort": {
                "sort_by":        vq.sort_by,
                "sort_direction": vq.sort_direction,
            },
            "filters_applied":  vq.filters,
            "available_filters": vq.config.get("allowed_filters", []),
            "available_columns": vq.config.get("available_columns", []),
            "saved_view_id":     saved_view_id,
        }

    def _parse_date(self, key: str, value: str) -> datetime:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            raise ValueError(ERR_GRID_INVALID_DATE_RANGE)

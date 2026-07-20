# CUSTOMER-L5-04 — Filter and Sort Contract

## Real, Implemented

| Concept | Backend key | Type | Values | Default | Serialization | Query mapping | Reset behavior | Tests |
|---|---|---|---|---|---|---|---|---|
| Category service search | `search` (query param on `/offerings`) | text | free text, name substring match | none (unset) | `?search=<value>` | `MasterOffering.name.ilike(f"%{search}%")` | Clearing the field removes the param | Not wired into `CategoryDetailScreen` UI this pass (see known-gaps) — the API client supports it (`categoryApi.listOfferings({ search })`) but no filter input was built, since the sprint's real, higher-value gap was the missing screens themselves |
| Search category scope | `category_id` (query param on `/search`) | id | any real category id | unset (global) | `?category_id=<uuid>` | `MasterOffering.category_id == category_id` filter | N/A this pass — `SearchScreen` always searches globally | `searchQueryKeys` tests cover the key shape for a future scoped-entry-point |

## Explicitly Not Implemented — No Real Backend Support

| Concept | Why absent |
|---|---|
| Brand filter | No brand↔offering linkage exposed on any customer endpoint |
| Service type filter | No `service_types` field on the offering shape |
| Duration filter | `estimated_duration_minutes` exists only on the unrelated `MasterService` shape, not on `MasterOffering` |
| Availability filter | `is_available` is hardcoded `True` for every offering server-side — filtering on it would be filtering on a constant |
| Featured filter | No `featured`/`is_featured` field on the offering shape |
| Any client-selectable sort | The backend's category-offerings endpoint always sorts by `display_order, name`; there is no sort query parameter at all. Building a client-side sort UI over one already-paginated page would violate CUSTOMER-L5-04 §13's "do not sort paginated partial results only on the client" — so none was built. |

No filter or sort control exists in this sprint's UI beyond what the table
above lists as real. This is a deliberate scope decision, not an oversight —
building filter/sort chips for concepts the backend cannot actually serve
would be exactly the kind of fabricated capability this sprint must avoid.

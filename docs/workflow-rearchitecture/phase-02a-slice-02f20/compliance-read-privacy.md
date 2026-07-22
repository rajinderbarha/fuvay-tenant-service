# Compliance Read Privacy

## Every related read (unchanged mechanism, re-verified this slice)
| Read | Tenant isolation | Subject ownership | Foreign/missing privacy-equivalent |
|---|---|---|---|
| `GET /requests` (list_my_requests) | `metadata_json["tenant_id"]` filter | n/a (list) | n/a |
| `GET /requests/{id}` (get_my_request) | same | n/a | YES — `if not req: raise NOT_FOUND` is the SAME branch for both a genuinely missing ID and a real-but-foreign-tenant ID (the WHERE clause excludes the foreign row before the `if not req` check ever distinguishes them) |
| `GET /exports` (list_exports) | via request join | n/a | n/a |
| `GET /exports/{id}` (get_export) | via request join | n/a | YES, same mechanism |
| `GET /exports/{id}/download` | via request join | n/a | YES, same mechanism (also state-mutating, covered separately) |
| `GET /consents` (list_consents) | filtered by `user_id` (self, via `_svc`'s actor context) | n/a | n/a |
| `GET /staff-requests` | `metadata_json["tenant_id"]` + `subject_type in TENANT_STAFF_SUBJECT_TYPES` | n/a | n/a |
| `GET /staff-requests/{id}` | same | n/a | YES, same mechanism |
| `GET /customer-requests` | `metadata_json["related_tenant_id"]` + `subject_type == "customer"` | n/a | n/a |
| `GET /customer-requests/{id}` | same | n/a | YES, same mechanism |

## Internal field filtering
`_tenant_safe_request`/`_customer_limited_view` (both pre-existing,
unchanged) strip `admin_notes` and other platform-internal fields before
returning tenant/customer-facing responses — re-confirmed by code read,
not modified this slice.

## GET routes produce no mutation
Confirmed for every GET EXCEPT `download_export`, which is documented
separately as a state-mutating GET (flagged, not a hidden gap — this
slice's fix explicitly covers it).

## Provider internal routes do not expose unrelated subjects
Confirmed — every list/detail read is scoped by the SAME tenant filter as
the mutation routes; a provider cannot enumerate or view requests
belonging to another tenant through any read route either.

## Customer routes do not expose tenant-internal processing notes
Confirmed via `customer_router.py`'s re-read this slice (out of direct
scope, re-verified only) — customer-facing serializers never include
`admin_notes`/`rejection_reason`/tenant correspondence fields.

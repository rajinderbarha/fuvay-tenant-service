# Shared Tenant-Direction Taxonomy (FROZEN) — Slice 2F-26E

Defined once in `scripts/workflow_rearchitecture/authority_model_2f26e.py`
as `TENANT_DIRECTION`. Manual sheets, classifier output and verifier fixtures
all validate against this single enum. Defect D-03 was two incompatible
vocabularies; there is now one.

| Value | Meaning | Canonical inclusion |
|---|---|---|
| `PRINCIPAL_TENANT` | Tenant is the principal's own, established by guard or handler | in denominator |
| `OBJECT_DERIVED_TENANT` | Tenant carried by the target object row, addressed by id | in denominator |
| `PARENT_DERIVED_TENANT` | Tenant derived from a parent record named in the request | in denominator |
| `CUSTOMER_RELATIONSHIP_TENANT` | Tenant follows the customer's relationship | in denominator |
| `PLATFORM_ADMIN_TARGET_TENANT` | Platform admin acts UPON a named tenant | excluded (platform-admin persona) |
| `CLIENT_ASSERTED_TARGET_TENANT` | Client names the tenant, never compared to the principal's | in denominator |
| `OPTIONAL_FILTER_TENANT` | Tenant narrows results, confers no authority | excluded |
| `CALLBACK_PAYLOAD_TENANT` | Tenant inside a trusted callback payload | in denominator |
| `INTERNAL_CONTEXT_TENANT` | Tenant from an internal caller's context | excluded |
| `GLOBAL_PLATFORM_SCOPE` | No single tenant applies | excluded |
| `NO_TENANT_AUTHORITY_REQUIRED` | Self-scoped or tenant-independent | excluded |
| `REQUIRES_MANUAL_TENANT_ADJUDICATION` | Not determinable from available evidence | blocked from automation |

## Comparison rules

1. Comparison is exact string equality. No aliasing, no fuzzy matching.
2. A value outside the enum is a **verifier failure** (N07), never a silent
   mismatch — that is what made D-03 invisible in 2F-26D.
3. `REQUIRES_MANUAL_TENANT_ADJUDICATION` agrees only with itself, and an
   agreeing abstention never justifies a canonical edit (N10).

## Retired value

`NO_TENANT_SCOPE` (2F-26D manual sheet) is **not** a member. It conflated two
genuinely different situations, and the classifier could never emit it, so
every row carrying it was guaranteed to disagree:

- self-scoped / tenant-independent → `NO_TENANT_AUTHORITY_REQUIRED`
- tenant-owned object addressed by its own id → `OBJECT_DERIVED_TENANT`

Asserted absent by `test_no_tenant_scope_is_not_a_member`.

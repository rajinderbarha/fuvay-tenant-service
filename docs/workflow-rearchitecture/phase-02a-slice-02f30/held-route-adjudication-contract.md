# Held-Route Adjudication Contract - Slice 2F-30

Three held candidates share the selected module boundary and **must** be
adjudicated before N01 closure can be claimed:

| Route | Why it matters |
|---|---|
| `POST /v1/media/upload/initiate` | same MediaService boundary; starts an upload session |
| `POST /v1/media/upload/{session_id}/confirm` | completes the session; ownership must be proven |
| `DELETE /v1/media/tenants/{tenant_id}/files/{file_id}` | **client-asserted tenant delete** - the highest-value adjudication in this module |

Each must resolve to exactly one outcome: `TENANT_PROVIDER_MUTATION_ADD`,
`CUSTOMER_SELF_SERVICE_EXCLUDE`, `PLATFORM_ADMIN_EXCLUDE`,
`PLATFORM_INTERNAL_EXCLUDE`, `PUBLIC_OR_CALLBACK_EXCLUDE`, `READ_ONLY_EXCLUDE`,
`DEPRECATED_OR_DISCONNECTED_EXCLUDE`, or `PRODUCT_DECISION_REQUIRED`.

Any route added must carry mounted-route evidence, genuine side-effect
evidence, tenant/provider persona evidence, a canonical row, a matrix update, a
protection classification, and an honest coverage change. Until then they
affect neither numerator, denominator, queue nor matrix.

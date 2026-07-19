# UX-02 Shared Pattern Reuse Audit

Read `frontend/super-admin/lib/ux02/{types,nav-ia,fixtures}.ts` and
`components/ux02/patterns/{EnterpriseListPage,EnterpriseDetailPage,ReviewApprovalWorkspace}.tsx`.
The list/detail/workspace *shapes* (header + section-nav + action area;
filterable table; queue/detail/context columns) are product-neutral and
were re-implemented locally as `TenantListPage`/`TenantDetailPage`/
`OperationalWorkspace` under `frontend/tenant-portal/components/ux03/patterns/`
rather than imported cross-app (Next.js apps don't share a components tree
across `frontend/super-admin` and `frontend/tenant-portal`; the design-system
package is the only cross-app import boundary). `ReadinessTag` was
similarly re-implemented locally against the tenant `ReadinessState` type.
See design-foundation-compatibility-report.md for the full classification.

import { apiClient } from "../../../api/api-client";

/**
 * Real backend paths verified against
 * app/engines/admin_catalog/service_option_customer_router.py (issue types,
 * service options — "Customer Service Diagnostics") and
 * app/engines/admin_catalog/customer_router.py (brands, service types) —
 * see CUSTOMER-L5-05-contract-matrix.md. All four are category-scoped only
 * (no reliable service-scoped ID bridge exists from `MasterOffering` to
 * `MasterService` — see known-gaps.md).
 */
export const diagnosticsApi = {
  listIssueTypes: (categoryId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/catalog/issue-types?category_id=${encodeURIComponent(categoryId)}`, { signal: options.signal }),

  listServiceOptions: (categoryId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/catalog/service-options?category_id=${encodeURIComponent(categoryId)}`, { signal: options.signal }),

  listBrands: (categoryId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/catalog/master/brands?category_id=${encodeURIComponent(categoryId)}`, { signal: options.signal }),

  listServiceTypes: (categoryId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/catalog/master/service-types?category_id=${encodeURIComponent(categoryId)}`, { signal: options.signal }),
};

import { apiClient } from "../../../api/api-client";
import type { CategoryListResponse } from "./home-api-types";

/**
 * Real backend paths verified against app/engines/customer_flow/router.py —
 * see CUSTOMER-L5-03-backend-contract-audit.md. Auth is optional
 * server-side; the customer app still requires it (route-guards.ts) per
 * product policy for this sprint. Category-detail and offering endpoints
 * live in `features/category/api/category-api.ts` (CUSTOMER-L5-04) — kept
 * out of this file so there is exactly one client per real endpoint, not
 * two competing ones.
 */
export const homeApi = {
  listCategories: (params: { page?: number; pageSize?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set("page", String(params.page));
    if (params.pageSize) query.set("page_size", String(params.pageSize));
    const qs = query.toString();
    return apiClient.get<CategoryListResponse>(`/v1/customer/categories${qs ? `?${qs}` : ""}`);
  },
};

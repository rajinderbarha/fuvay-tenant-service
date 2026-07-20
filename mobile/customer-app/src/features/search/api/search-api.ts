import { apiClient } from "../../../api/api-client";

/**
 * Real backend path verified against
 * app/engines/customer_flow/router.py#customer_search — see
 * CUSTOMER-L5-04-contract-matrix.md. `page`/`pageSize` are accepted by the
 * client for forward-compatibility but the backend does not actually
 * paginate offerings (no `.offset()`) or categories (hard `.limit(5)`), so
 * callers must not rely on a second page returning different results.
 */
export const searchApi = {
  search: (q: string, params: { categoryId?: string; page?: number; pageSize?: number } = {}, options: { signal?: AbortSignal } = {}) => {
    const query = new URLSearchParams();
    query.set("q", q);
    if (params.categoryId) query.set("category_id", params.categoryId);
    if (params.page) query.set("page", String(params.page));
    if (params.pageSize) query.set("page_size", String(params.pageSize));
    return apiClient.get<unknown>(`/v1/customer/search?${query.toString()}`, { signal: options.signal });
  },
};

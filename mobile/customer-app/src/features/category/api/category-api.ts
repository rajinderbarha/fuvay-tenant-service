import { apiClient } from "../../../api/api-client";

/**
 * Real backend paths verified against
 * app/engines/customer_flow/router.py — see
 * CUSTOMER-L5-04-contract-matrix.md. `categoryId` is sent as the path
 * segment; the backend resolves either a slug or a UUID
 * (`_load_visible_category`), but the app only ever passes the stable `id`
 * it already validated from a prior response, never a raw slug typed by a
 * caller (CUSTOMER-L5-04 §6/§40).
 */
export const categoryApi = {
  getCategoryDetail: (categoryId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/categories/${encodeURIComponent(categoryId)}`, { signal: options.signal }),

  listOfferings: (categoryId: string, params: { page?: number; pageSize?: number; search?: string } = {}, options: { signal?: AbortSignal } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set("page", String(params.page));
    if (params.pageSize) query.set("page_size", String(params.pageSize));
    if (params.search) query.set("search", params.search);
    const qs = query.toString();
    return apiClient.get<unknown>(`/v1/customer/categories/${encodeURIComponent(categoryId)}/offerings${qs ? `?${qs}` : ""}`, { signal: options.signal });
  },

  getOfferingDetail: (categoryId: string, offeringId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/categories/${encodeURIComponent(categoryId)}/offerings/${encodeURIComponent(offeringId)}`, {
      signal: options.signal,
    }),
};

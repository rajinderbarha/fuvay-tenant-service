import { categoryApi } from "../../category/api/category-api";

/** Thin re-export — the offering-detail endpoint is category-scoped server-side (see category-api.ts), so there is exactly one client for it. */
export const serviceDetailApi = {
  getOfferingDetail: categoryApi.getOfferingDetail,
};

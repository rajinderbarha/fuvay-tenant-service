import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { categoryApi } from "../api/category-api";
import { parseCategoryDetail, type ValidatedCategoryDetail } from "../domain/category-detail-schema";
import { parseOfferingListPage, type OfferingListPage } from "../domain/offering-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

const OFFERINGS_PAGE_SIZE = 20;

/**
 * Every key includes locale + tenant, the only isolation dimensions this
 * backend contract actually carries (see CUSTOMER-L5-03's identical
 * reasoning for Home) — CUSTOMER-L5-04 §41/§43.
 */
export const categoryQueryKeys = {
  detail: (categoryId: string, locale: string, tenantId: string | undefined) => ["category", "detail", categoryId, locale, tenantId ?? "no-tenant"] as const,
  offerings: (categoryId: string, locale: string, tenantId: string | undefined) =>
    ["category", "offerings", categoryId, locale, tenantId ?? "no-tenant"] as const,
};

export function useCategoryDetail(categoryId: string) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<ValidatedCategoryDetail>({
    queryKey: categoryQueryKeys.detail(categoryId, locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await categoryApi.getCategoryDetail(categoryId, { signal });
      const parsed = parseCategoryDetail(response);
      if (!parsed) {
        logger.warn("category_detail_validation_failed", { categoryId });
        throw new ApiError({ category: "validation_error", message: "Category detail response did not match the expected shape." });
      }
      return parsed;
    },
    enabled: categoryId.length > 0,
    staleTime: 5 * 60_000,
  });
}

/**
 * Cursor-free, page-number pagination (the real backend model — CUSTOMER-L5-04
 * §14). `getNextPageParam` stops once a page returns fewer than
 * `OFFERINGS_PAGE_SIZE` items, since the endpoint never returns a `total`
 * high enough to be a reliable end-of-list signal on its own for offerings
 * (it does return `total`, but pages are requested one at a time and this
 * check is cheaper and correct either way).
 */
export function useCategoryOfferings(categoryId: string) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useInfiniteQuery<OfferingListPage>({
    queryKey: categoryQueryKeys.offerings(categoryId, locale, tenantId),
    queryFn: async ({ pageParam, signal }) => {
      const response = await categoryApi.listOfferings(categoryId, { page: pageParam as number, pageSize: OFFERINGS_PAGE_SIZE }, { signal });
      const parsed = parseOfferingListPage(response);
      if (!parsed) {
        logger.warn("service_list_validation_failed", { categoryId });
        throw new ApiError({ category: "validation_error", message: "Offering list response did not match the expected shape." });
      }
      if (parsed.droppedCount > 0) {
        logger.warn("service_list_items_dropped", { categoryId, droppedCount: parsed.droppedCount });
      }
      return parsed;
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => (lastPage.items.length < OFFERINGS_PAGE_SIZE ? undefined : lastPage.page + 1),
    enabled: categoryId.length > 0,
    staleTime: 5 * 60_000,
  });
}

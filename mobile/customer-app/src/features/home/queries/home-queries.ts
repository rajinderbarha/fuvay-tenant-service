import { useQuery } from "@tanstack/react-query";
import { homeApi } from "../api/home-api";
import { parseCategoryList } from "../domain/category-schema";
import { composeCategorySections, type ComposedCategories } from "../domain/discovery-composer";
import { logger } from "../../../observability/logger";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";

/**
 * Query keys include every isolation dimension this backend contract
 * actually supports (locale, tenant) — CUSTOMER-L5-03 §12. There is no
 * marketplace or region dimension because this backend has no such concept
 * in the categories endpoint (CUSTOMER-L5-03-backend-contract-audit.md);
 * adding a marketplace/region key segment with no corresponding backend
 * parameter would be a key that never actually varies, which is worse than
 * not having it (a false signal of isolation that isn't real).
 */
export const homeQueryKeys = {
  categories: (locale: string, tenantId: string | undefined) => ["home", "categories", locale, tenantId ?? "no-tenant"] as const,
};

export function useHomeCategories() {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<ComposedCategories>({
    queryKey: homeQueryKeys.categories(locale, tenantId),
    queryFn: async () => {
      const response = await homeApi.listCategories({ pageSize: 50 });
      const { valid, droppedCount } = parseCategoryList(response.items);
      if (droppedCount > 0) {
        logger.warn("home_module_validation_failed", { moduleType: "category-grid", droppedCount });
      }
      return composeCategorySections(valid);
    },
    staleTime: 5 * 60_000,
  });
}

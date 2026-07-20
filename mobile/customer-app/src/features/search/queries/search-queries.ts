import { useQuery } from "@tanstack/react-query";
import { searchApi } from "../api/search-api";
import { parseSearchResponse, type SearchResults } from "../domain/search-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

/**
 * Keyed by the normalized query (never raw user keystrokes) plus locale and
 * tenant. No `page` dimension — the backend does not actually paginate this
 * endpoint (search-schema.ts), so there is nothing to key by there.
 */
export const searchQueryKeys = {
  results: (normalizedQuery: string, categoryId: string | undefined, locale: string, tenantId: string | undefined) =>
    ["search", "results", normalizedQuery, categoryId ?? "all-categories", locale, tenantId ?? "no-tenant"] as const,
};

export function useSearchResults(normalizedQuery: string, categoryId: string | undefined, enabled: boolean) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<SearchResults>({
    queryKey: searchQueryKeys.results(normalizedQuery, categoryId, locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await searchApi.search(normalizedQuery, { categoryId, pageSize: 30 }, { signal });
      const parsed = parseSearchResponse(response);
      if (!parsed) {
        logger.warn("search_request_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Search response did not match the expected shape." });
      }
      if (parsed.droppedCount > 0) {
        logger.warn("search_results_items_dropped", { droppedCount: parsed.droppedCount });
      }
      return parsed;
    },
    enabled,
    staleTime: 60_000,
    retry: 1,
  });
}

import { useQuery } from "@tanstack/react-query";
import { searchCustomerCatalog } from "./customerSearchApi";
import { parseCustomerSearchDto, adaptCustomerSearch } from "../adapters/customerSearch";
import { queryKeys } from "../queryKeys";

/** Below this, a query is too broad to be useful and would return most of
 * the catalog on every keystroke. */
const MIN_QUERY_LENGTH = 2;

/**
 * Catalog search for the Home search box.
 *
 * `bookableCategoryIds` comes from the already-loaded Home payload, so
 * reconciling ZIP availability costs no extra request. Disabled until the
 * query is long enough, which also means an empty search box performs no
 * network calls at all.
 */
export function useCustomerSearchQuery(
  rawQuery: string,
  bookableCategoryIds: ReadonlySet<string>,
  zipcode?: string,
) {
  const q = rawQuery.trim();
  return useQuery({
    queryKey: queryKeys.home.search(q, zipcode),
    enabled: q.length >= MIN_QUERY_LENGTH,
    queryFn: async () => {
      const res = await searchCustomerCatalog(q);
      const dto = parseCustomerSearchDto(res.data);
      return adaptCustomerSearch(dto, bookableCategoryIds);
    },
  });
}

export { MIN_QUERY_LENGTH };

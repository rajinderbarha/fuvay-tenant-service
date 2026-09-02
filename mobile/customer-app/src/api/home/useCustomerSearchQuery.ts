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
 * The backend filters exact provider-published services by `zipcode`;
 * `bookableCategoryIds` remains a defensive presentation check. Disabled
 * until the query is long enough, so an empty box performs no requests.
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
      const res = await searchCustomerCatalog(q, zipcode);
      const dto = parseCustomerSearchDto(res.data);
      return adaptCustomerSearch(dto, bookableCategoryIds);
    },
  });
}

export { MIN_QUERY_LENGTH };

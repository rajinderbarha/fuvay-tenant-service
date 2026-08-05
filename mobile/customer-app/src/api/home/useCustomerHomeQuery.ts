import { useQuery } from "@tanstack/react-query";
import { getCustomerHome } from "./customerHomeApi";
import { parseCustomerHomeDto, adaptCustomerHome } from "../adapters/customerHome";
import { queryKeys } from "../queryKeys";

/**
 * Single Home aggregation query (spec: "One Home aggregation query where
 * supported"). ZIP is part of the query key's identity (spec: "Address/ZIP
 * included in query identity") so switching the customer's selected
 * location never serves a stale cached payload for the previous ZIP.
 * Retry/stale-time policy is inherited from the shared queryClient
 * (Phase D: no retry on 4xx, bounded retry on transient failures) --
 * nothing here overrides that.
 */
export function useCustomerHomeQuery(zipcode?: string) {
  return useQuery({
    queryKey: queryKeys.home.aggregate(zipcode),
    queryFn: async () => {
      const res = await getCustomerHome(zipcode);
      const dto = parseCustomerHomeDto(res.data);
      return adaptCustomerHome(dto);
    },
  });
}

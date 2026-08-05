import { useQuery } from "@tanstack/react-query";
import { getGlobalServices } from "./globalServicesApi";
import { adaptGlobalService } from "../../domain/globalServices";
import { queryKeys } from "../queryKeys";

/** Fixed, nationwide promotional list -- no zipcode param, same result
 * for every customer. See queryKeys.globalServices for why the key
 * carries no location identity, unlike useCustomerHomeQuery. */
export function useGlobalServicesQuery() {
  return useQuery({
    queryKey: queryKeys.globalServices(),
    queryFn: async () => {
      const res = await getGlobalServices();
      return res.data.map(adaptGlobalService);
    },
  });
}

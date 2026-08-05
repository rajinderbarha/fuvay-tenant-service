import { useQuery } from "@tanstack/react-query";
import { getCustomerProfile } from "./customerProfileApi";
import { parseCustomerProfileDto, adaptCustomerProfile } from "../adapters/customer";
import { queryKeys } from "../queryKeys";

export function useCustomerProfileQuery() {
  return useQuery({
    queryKey: queryKeys.customerProfile(),
    queryFn: async () => {
      const res = await getCustomerProfile();
      const dto = parseCustomerProfileDto(res.data);
      return adaptCustomerProfile(dto);
    },
    staleTime: 5 * 60_000,
  });
}

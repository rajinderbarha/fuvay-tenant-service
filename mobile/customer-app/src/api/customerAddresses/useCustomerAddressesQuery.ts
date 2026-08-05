import { useQuery } from "@tanstack/react-query";
import { listMyAddresses } from "./customerAddressesApi";
import { adaptCustomerSavedAddress } from "../adapters/customerAddresses";
import { customerAddressQueryKeys } from "./customerAddressQueryKeys";

export function useCustomerAddressesQuery() {
  return useQuery({
    queryKey: customerAddressQueryKeys.list(),
    queryFn: async () => {
      const res = await listMyAddresses();
      // Backend already returns default-first, created_at-desc order
      // (confirmed in ServiceabilityService.list_addresses) -- never
      // re-sorted client-side.
      return res.data.addresses.map(adaptCustomerSavedAddress);
    },
  });
}

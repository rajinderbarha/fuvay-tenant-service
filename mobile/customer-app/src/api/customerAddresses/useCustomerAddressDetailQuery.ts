import { useQuery } from "@tanstack/react-query";
import { getMyAddress } from "./customerAddressesApi";
import { adaptCustomerSavedAddress } from "../adapters/customerAddresses";
import { customerAddressQueryKeys } from "./customerAddressQueryKeys";

/** Edit mode loads the owned address by `addressId` from the canonical
 * API/cache -- never trusts a whole address object passed through
 * navigation params (spec section 5). */
export function useCustomerAddressDetailQuery(addressId: string | undefined) {
  return useQuery({
    queryKey: customerAddressQueryKeys.detail(addressId ?? ""),
    queryFn: async () => {
      const res = await getMyAddress(addressId as string);
      return adaptCustomerSavedAddress(res.data);
    },
    enabled: !!addressId,
  });
}

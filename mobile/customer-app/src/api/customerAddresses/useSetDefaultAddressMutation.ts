import { useMutation, useQueryClient } from "@tanstack/react-query";
import { setDefaultAddress } from "./customerAddressesApi";
import { customerAddressQueryKeys } from "./customerAddressQueryKeys";

/** No optimistic default swap -- waits for the server response (the
 * canonical "exactly one default" invariant is enforced transactionally
 * server-side, see `ServiceabilityService._clear_default` +
 * `set_default_address`), then refetches list/Profile/Home (spec section
 * 7). */
export function useSetDefaultAddressMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (addressId: string) => setDefaultAddress(addressId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerAddressQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ["home", "aggregate"] });
    },
  });
}

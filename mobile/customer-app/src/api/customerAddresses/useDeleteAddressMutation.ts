import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteMyAddress } from "./customerAddressesApi";
import { customerAddressQueryKeys } from "./customerAddressQueryKeys";

/** Server-side soft delete (`is_active=false`); if the deleted address
 * was default, the backend itself reassigns the next address as default
 * (see `ServiceabilityService.delete_address`) -- this hook never invents
 * a new default client-side, it only refetches the canonical result
 * (spec section 8: "Do not invent one client-side"). Confirmed bookings'
 * `address_snapshot` is a separate, immutable column this mutation never
 * touches. */
export function useDeleteAddressMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (addressId: string) => deleteMyAddress(addressId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerAddressQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ["home", "aggregate"] });
    },
  });
}

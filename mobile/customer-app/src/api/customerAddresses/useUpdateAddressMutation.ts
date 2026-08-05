import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateMyAddress } from "./customerAddressesApi";
import { customerAddressQueryKeys } from "./customerAddressQueryKeys";
import { AddressUpdatePayload } from "../../domain/addressForm";

export function useUpdateAddressMutation(addressId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddressUpdatePayload) => updateMyAddress(addressId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerAddressQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: customerAddressQueryKeys.detail(addressId) });
      queryClient.invalidateQueries({ queryKey: ["home", "aggregate"] });
    },
  });
}

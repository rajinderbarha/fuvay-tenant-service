import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createMyAddress } from "./customerAddressesApi";
import { customerAddressQueryKeys } from "./customerAddressQueryKeys";
import { AddressCreatePayload } from "../../domain/addressForm";

export function useCreateAddressMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddressCreatePayload) => createMyAddress(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerAddressQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ["home", "aggregate"] });
    },
  });
}

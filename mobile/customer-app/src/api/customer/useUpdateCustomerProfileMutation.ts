import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateCustomerProfile } from "./customerProfileApi";
import { parseCustomerProfileDto, adaptCustomerProfile } from "../adapters/customer";
import { UpdateCustomerProfileRequest } from "../contracts/customer";
import { queryKeys } from "../queryKeys";

/** Invalidates the ONE shared profile query key (spec section 3: "Do not
 * create a second incompatible profile hook") -- Home and Profile both
 * re-read the same cache entry after a successful edit. Also invalidates
 * Home's aggregation since its greeting reads the same full_name. */
export function useUpdateCustomerProfileMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: UpdateCustomerProfileRequest) => {
      const res = await updateCustomerProfile(body);
      return adaptCustomerProfile(parseCustomerProfileDto(res.data));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customerProfile() });
      queryClient.invalidateQueries({ queryKey: ["home", "aggregate"] });
    },
  });
}

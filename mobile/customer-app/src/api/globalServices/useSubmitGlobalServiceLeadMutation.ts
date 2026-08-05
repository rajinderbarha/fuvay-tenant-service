import { useMutation } from "@tanstack/react-query";
import { submitGlobalServiceLead, SubmitGlobalServiceLeadInput } from "./globalServicesApi";

/** No cache to invalidate on success -- a lead doesn't change anything the
 * customer can see afterward (no booking/job is created); the caller just
 * shows a confirmation state. */
export function useSubmitGlobalServiceLeadMutation() {
  return useMutation({
    mutationFn: (input: SubmitGlobalServiceLeadInput) => submitGlobalServiceLead(input),
  });
}

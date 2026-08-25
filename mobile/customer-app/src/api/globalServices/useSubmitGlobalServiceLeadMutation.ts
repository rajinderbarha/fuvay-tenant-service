import { useMutation } from "@tanstack/react-query";

import { submitGlobalServiceLead, SubmitGlobalServiceLeadInput } from "./globalServicesApi";


export function useSubmitGlobalServiceLeadMutation() {
  return useMutation({
    mutationFn: (input: SubmitGlobalServiceLeadInput) => submitGlobalServiceLead(input),
  });
}

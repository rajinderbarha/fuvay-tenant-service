import { globalServiceLeadDtoSchema, globalServicesListResponseSchema } from "../contracts/globalServices";
import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";


export async function getGlobalServices() {
  const response = await authenticatedRequest({ method: "GET", path: "/v1/customer/global-services" });
  return parseApiSuccess(response.json, globalServicesListResponseSchema);
}

export interface SubmitGlobalServiceLeadInput {
  globalServiceId: string;
  name: string;
  phone: string;
  email?: string;
  zipcode?: string;
  message?: string;
}

export async function submitGlobalServiceLead(input: SubmitGlobalServiceLeadInput) {
  const response = await authenticatedRequest({
    method: "POST",
    path: "/v1/customer/global-services/leads",
    body: {
      global_service_id: input.globalServiceId,
      name: input.name,
      phone: input.phone,
      email: input.email || undefined,
      zipcode: input.zipcode || undefined,
      message: input.message || undefined,
    },
  });
  return parseApiSuccess(response.json, globalServiceLeadDtoSchema);
}

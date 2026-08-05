import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  globalServicesListResponseSchema, globalServiceLeadDtoSchema,
} from "../contracts/globalServices";

/** GET /v1/customer/global-services -- the fixed, nationwide promotional
 * list. Never takes a zipcode param; the backend returns the same active
 * list to every customer (app/engines/global_services/customer_router.py). */
export async function getGlobalServices() {
  const res = await authenticatedRequest({ method: "GET", path: "/v1/customer/global-services" });
  return parseApiSuccess(res.json, globalServicesListResponseSchema);
}

export interface SubmitGlobalServiceLeadInput {
  globalServiceId: string;
  name: string;
  phone: string;
  email?: string;
  zipcode?: string;
  message?: string;
}

/** POST /v1/customer/global-services/leads -- creates a Lead an admin
 * calls the customer back about. No booking/job/payment is created. */
export async function submitGlobalServiceLead(input: SubmitGlobalServiceLeadInput) {
  const res = await authenticatedRequest({
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
  return parseApiSuccess(res.json, globalServiceLeadDtoSchema);
}

import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { customerSearchResponseSchema } from "../contracts/customerSearch";

/** GET /v1/customer/search?q= -- searches customer-visible categories and
 * services (app/engines/customer_flow). Not ZIP-aware; see the adapter. */
export async function searchCustomerCatalog(q: string) {
  const res = await authenticatedRequest({
    method: "GET",
    path: `/v1/customer/search?q=${encodeURIComponent(q)}`,
  });
  return parseApiSuccess(res.json, customerSearchResponseSchema);
}

import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { customerHomeResponseSchema } from "../contracts/customerHome";

/** GET /v1/customer/home?zipcode= -- real, confirmed-mounted aggregation
 * endpoint (app/engines/customer_home/router.py). `zipcode` overrides the
 * customer's default address ZIP for this one request only; omitting it
 * uses the backend's own default-address resolution. */
export async function getCustomerHome(zipcode?: string) {
  const query = zipcode ? `?zipcode=${encodeURIComponent(zipcode)}` : "";
  const res = await authenticatedRequest({ method: "GET", path: `/v1/customer/home${query}` });
  return parseApiSuccess(res.json, customerHomeResponseSchema);
}

import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { customerSearchResponseSchema } from "../contracts/customerSearch";

/** GET /v1/customer/search?q=&zipcode= -- returns only services published by
 * a bookable provider for the customer's selected ZIP. */
export async function searchCustomerCatalog(q: string, zipcode?: string) {
  const zipcodeQuery = zipcode ? `&zipcode=${encodeURIComponent(zipcode)}` : "";
  const res = await authenticatedRequest({
    method: "GET",
    path: `/v1/customer/search?q=${encodeURIComponent(q)}${zipcodeQuery}`,
  });
  return parseApiSuccess(res.json, customerSearchResponseSchema);
}

import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { customerProfileDtoSchema, UpdateCustomerProfileRequest } from "../contracts/customer";

/** GET /v1/customer/profile -- confirmed real route (Phase D audit).
 * Needed because neither GET /v1/customer/home nor GET
 * /v1/auth/access-context return a display name -- the Home greeting
 * ("Good evening, {name}") has no name field in the aggregation payload
 * itself, so this is a genuinely separate, justified query. */
export async function getCustomerProfile() {
  const res = await authenticatedRequest({ method: "GET", path: "/v1/customer/profile" });
  return parseApiSuccess(res.json, customerProfileDtoSchema);
}

/** `PUT /v1/customer/profile` -- confirmed real route
 * (`app/engines/profile/router.py::update_customer_profile`), scoped to
 * full_name/display_name/language/timezone (see contracts/customer.ts for
 * why `phone` is deliberately excluded from this app's edit surface). */
export async function updateCustomerProfile(body: UpdateCustomerProfileRequest) {
  const res = await authenticatedRequest({ method: "PUT", path: "/v1/customer/profile", body });
  return parseApiSuccess(res.json, customerProfileDtoSchema);
}

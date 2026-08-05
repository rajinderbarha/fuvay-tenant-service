/**
 * Only field proven mutable via `PUT /v1/customer/profile` that this
 * screen's design actually surfaces (spec section 3: "If only the
 * customer name can currently be updated, implement only name editing").
 * `display_name`/`language`/`timezone` are real backend-accepted fields
 * too but have no UI in the approved Personal Details design -- not
 * included here to avoid inventing form controls the design doesn't ask
 * for; a future phase can add them deliberately.
 */
export interface EditCustomerProfileForm {
  fullName: string;
}

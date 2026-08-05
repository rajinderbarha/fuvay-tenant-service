/**
 * Derived from confirmed real routes (spec section 6), not assumptions.
 * `canCreate`/`canEdit` are `true` as of the Add/Edit Address phase --
 * `POST`/`PUT /v1/customers/me/addresses[/{id}]` are real backend routes
 * AND a functional Address Form screen (`AddAddress`/`EditAddress`) now
 * exists in this app.
 */
export interface AddressCapabilities {
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canSetDefault: boolean;
}

export function resolveAddressCapabilities(): AddressCapabilities {
  return {
    canCreate: true,
    canEdit: true,
    canDelete: true,
    canSetDefault: true,
  };
}

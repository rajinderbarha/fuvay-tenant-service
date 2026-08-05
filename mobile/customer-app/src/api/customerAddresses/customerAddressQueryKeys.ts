/** Canonical query-key factory shared by Profile's default-address
 * preview, Saved Addresses, and (in a later phase) booking address
 * selection -- matching the same pattern established for
 * `bookingQueryKeys` (spec section 4). */
export const customerAddressQueryKeys = {
  all: ["customer", "addresses"] as const,
  lists: () => [...customerAddressQueryKeys.all, "list"] as const,
  list: () => [...customerAddressQueryKeys.lists()] as const,
  details: () => [...customerAddressQueryKeys.all, "detail"] as const,
  detail: (addressId: string) => [...customerAddressQueryKeys.details(), addressId] as const,
} as const;

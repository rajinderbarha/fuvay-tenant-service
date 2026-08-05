import { CustomerSavedAddress } from "./customerSavedAddress";

/** Single formatted display string -- never re-implemented per screen. */
export function formatSavedAddress(address: CustomerSavedAddress): string {
  const lines = [address.line1, address.line2, address.landmark].filter(
    (v): v is string => typeof v === "string" && v.trim().length > 0,
  );
  const cityLine = `${address.city}, ${address.state} ${address.postalCode}`.trim();
  return [...lines, cityLine].join(", ");
}

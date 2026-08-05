import { CustomerAddressDto } from "../contracts/customerAddresses";
import { CustomerSavedAddress } from "../../domain/customerSavedAddress";
import { parseServerTimestamp } from "../../domain/dates";

/**
 * Add/Edit Address phase (migration 223): the model now has a dedicated
 * `label` column (Home/Work/Other), so `label` and the recipient's full
 * name (`name`) are no longer conflated -- the earlier Saved Addresses
 * phase's gap (single free-text column, `recipientName` always null) is
 * closed.
 */
export function adaptCustomerSavedAddress(dto: CustomerAddressDto): CustomerSavedAddress {
  return {
    id: dto.id,
    label: dto.label,
    recipientName: dto.name,
    mobile: dto.phone,
    line1: dto.address_line_1,
    line2: dto.address_line_2,
    landmark: dto.landmark,
    city: dto.city,
    district: dto.district,
    state: dto.state,
    country: dto.country,
    postalCode: dto.zipcode,
    isDefault: dto.is_default,
    createdAt: parseServerTimestamp(dto.created_at, "created_at"),
    updatedAt: dto.updated_at ? parseServerTimestamp(dto.updated_at, "updated_at") : null,
  };
}

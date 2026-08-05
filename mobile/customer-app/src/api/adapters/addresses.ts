import { AddressDto, addressDtoSchema } from "../contracts/addresses";
import { CustomerAddress } from "../../domain/address";
import { asAddressId } from "../../domain/ids";
import { ContractValidationError } from "../../domain/errors";

export function parseAddressDto(raw: unknown): AddressDto {
  const result = addressDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("AddressDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptAddress(dto: AddressDto): CustomerAddress {
  const hasCoordinates = dto.latitude != null && dto.longitude != null;
  return {
    id: asAddressId(dto.id),
    label: dto.label ?? null,
    line1: dto.line1,
    line2: dto.line2 ?? null,
    city: dto.city ?? null,
    state: dto.state ?? null,
    zipcode: dto.zipcode ?? null,
    coordinates: hasCoordinates ? { latitude: dto.latitude as number, longitude: dto.longitude as number } : null,
    isDefault: dto.is_default ?? false,
  };
}

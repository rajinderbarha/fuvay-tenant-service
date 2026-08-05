import { AddressId } from "./ids";

/** Coordinates are kept as a distinct, optional sub-shape from the display
 * address per Phase D section 20 -- never logged, never assumed present. */
export interface AddressCoordinates {
  latitude: number;
  longitude: number;
}

export interface CustomerAddress {
  id: AddressId;
  label: string | null;
  line1: string;
  line2: string | null;
  city: string | null;
  state: string | null;
  zipcode: string | null;
  coordinates: AddressCoordinates | null;
  isDefault: boolean;
}

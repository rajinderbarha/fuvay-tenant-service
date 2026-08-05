import { ServerTimestamp } from "./dates";

/**
 * Adapted from the real `CustomerAddress` model
 * (`app/engines/serviceability/{models,service}.py`) via
 * `GET /v1/customers/me/addresses` -- confirmed full CRUD + set-default
 * exists and is authorized for the customer role
 * (`P.CUSTOMER_ADDRESS_{READ,CREATE,UPDATE,DELETE}_OWN`). Deliberately
 * distinct from `ReceiptAddress`/`CustomerHome`'s address shape -- a saved
 * address, a temporary Home ZIP override, and a confirmed booking's
 * immutable `address_snapshot` are three different concepts and must
 * never share one domain type (spec section 2).
 */
export interface CustomerSavedAddress {
  id: string;
  label: string | null;
  recipientName: string | null;
  mobile: string | null;
  line1: string;
  line2: string | null;
  landmark: string | null;
  city: string;
  district: string | null;
  state: string;
  country: string;
  postalCode: string;
  isDefault: boolean;
  createdAt: ServerTimestamp;
  updatedAt: ServerTimestamp | null;
}

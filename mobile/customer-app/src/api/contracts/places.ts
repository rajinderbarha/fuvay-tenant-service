import { z } from "zod";

/**
 * Address autocomplete contracts.
 *
 * `configured` is a real field, not a convenience: without it the app cannot tell
 * "no matches for that query" from "this deployment has no Places key", and those
 * need different UI -- the first shows an empty list, the second shows no suggestion
 * affordance at all rather than one that never produces anything.
 */
export const placeSuggestionDtoSchema = z.object({
  place_id: z.string(),
  description: z.string(),
});

export const placeAutocompleteResponseSchema = z.object({
  configured: z.boolean(),
  suggestions: z.array(placeSuggestionDtoSchema),
}).passthrough();

/** Every field is nullable because Google genuinely omits them -- a rural Indian
 * locality often has no postal_code. The form keeps what came back and lets the
 * customer fill the rest; nothing is invented, least of all a PIN code, which
 * decides serviceability. */
export const placeAddressDtoSchema = z.object({
  formatted_address: z.string().nullable(),
  line1: z.string().nullable(),
  city: z.string().nullable(),
  state: z.string().nullable(),
  zipcode: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
}).passthrough();

export const placeDetailResponseSchema = z.object({
  resolved: z.boolean(),
  address: placeAddressDtoSchema.nullable(),
}).passthrough();

export type PlaceSuggestionDto = z.infer<typeof placeSuggestionDtoSchema>;
export type PlaceAddressDto = z.infer<typeof placeAddressDtoSchema>;

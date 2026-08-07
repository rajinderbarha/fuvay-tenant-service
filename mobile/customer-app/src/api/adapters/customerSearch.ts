import { CustomerSearchResponseDto, customerSearchResponseSchema } from "../contracts/customerSearch";
import { CustomerSearchResults, SearchResult } from "../../domain/customerSearch";
import { asCategoryId } from "../../domain/ids";
import { ContractValidationError } from "../../domain/errors";

export function parseCustomerSearchDto(raw: unknown): CustomerSearchResponseDto {
  const result = customerSearchResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("CustomerSearchResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

/**
 * `bookableCategoryIds` comes from the Home payload, which IS ZIP-filtered.
 * The search endpoint is not, so every result is reconciled against that set
 * here. Results that are not bookable are kept (so a search never looks
 * broken or silently empty) but flagged, letting the UI show them as
 * unavailable instead of offering a tap that dead-ends at "no provider
 * available" after several booking steps.
 */
export function adaptCustomerSearch(
  dto: CustomerSearchResponseDto,
  bookableCategoryIds: ReadonlySet<string>,
): CustomerSearchResults {
  const categories: SearchResult[] = dto.categories.map(c => ({
    kind: "category" as const,
    categoryId: asCategoryId(c.id),
    name: c.name,
    slug: c.slug ?? null,
    description: c.description ?? null,
    iconUrl: c.icon_url ?? null,
    bookableHere: bookableCategoryIds.has(c.id),
  }));

  const offerings: SearchResult[] = dto.offerings.map(o => ({
    kind: "offering" as const,
    offeringId: o.id,
    name: o.name,
    slug: o.slug ?? null,
    description: o.description ?? null,
    startingPrice: o.starting_price ?? null,
    categoryId: o.category_id ? asCategoryId(o.category_id) : null,
    bookableHere: o.category_id ? bookableCategoryIds.has(o.category_id) : false,
  }));

  // Bookable first, then categories before individual services: a customer
  // typing "clean" is more likely to want the whole Home Cleaning category
  // than one specific package within it.
  const rank = (r: SearchResult) => (r.bookableHere ? 0 : 2) + (r.kind === "category" ? 0 : 1);
  return {
    query: dto.query,
    results: [...categories, ...offerings].sort((a, b) => rank(a) - rank(b)),
  };
}

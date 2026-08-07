import { CategoryId } from "./ids";

export interface SearchCategoryResult {
  kind: "category";
  categoryId: CategoryId;
  name: string;
  slug: string | null;
  description: string | null;
  iconUrl: string | null;
  /** False when this category is not in the customer's ZIP-filtered
   * `bookable_categories`. Resolved by the caller, never by the server --
   * the search endpoint has no zipcode parameter. */
  bookableHere: boolean;
}

export interface SearchOfferingResult {
  kind: "offering";
  offeringId: string;
  name: string;
  slug: string | null;
  description: string | null;
  startingPrice: number | null;
  categoryId: CategoryId | null;
  /** Same rule as above, resolved via the offering's parent category. */
  bookableHere: boolean;
}

export type SearchResult = SearchCategoryResult | SearchOfferingResult;

export interface CustomerSearchResults {
  query: string;
  results: SearchResult[];
}

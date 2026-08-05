export interface CustomerReview {
  rating: number;
  comment: string | null;
  tags: string[];
  createdAt: string | null;
}

/** Fixed, client-side-only tag vocabulary submitted into the real
 * (unconstrained) `review_tags` backend field -- there is no backend enum
 * for these, so these are UI choices, not backend-proven values. */
export const REVIEW_TAG_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "professional", label: "Professional" },
  { value: "clear_explanation", label: "Clear explanation" },
  { value: "clean_work", label: "Clean work" },
  { value: "on_time", label: "On time" },
];

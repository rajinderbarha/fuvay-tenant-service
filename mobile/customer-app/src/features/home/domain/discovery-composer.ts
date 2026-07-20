import type { ValidatedCategorySummary } from "./category-schema";

export interface HomeCategoryItem {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  iconUrl: string | null;
  bannerUrl: string | null;
  offeringCount: number;
  order: number;
}

export interface ComposedCategories {
  items: HomeCategoryItem[];
  droppedDuplicateCount: number;
}

const MAX_HOME_CATEGORIES = 12;

/**
 * Deduplicates by `id` (keeping the first occurrence — the backend already
 * orders by `display_order`, so the first is the highest-priority one),
 * applies a stable sort by `(display_order, name)` so ties never reorder
 * randomly between renders, and caps the result so Home never renders an
 * unbounded grid.
 */
export function composeCategorySections(categories: ValidatedCategorySummary[]): ComposedCategories {
  const seen = new Set<string>();
  const deduped: ValidatedCategorySummary[] = [];
  let droppedDuplicateCount = 0;

  for (const category of categories) {
    if (seen.has(category.id)) {
      droppedDuplicateCount += 1;
      continue;
    }
    seen.add(category.id);
    deduped.push(category);
  }

  const sorted = [...deduped].sort((a, b) => a.display_order - b.display_order || a.name.localeCompare(b.name));

  const items: HomeCategoryItem[] = sorted.slice(0, MAX_HOME_CATEGORIES).map((category) => ({
    id: category.id,
    name: category.name,
    slug: category.slug,
    description: category.description,
    iconUrl: category.icon_url,
    bannerUrl: category.banner_url,
    offeringCount: category.available_offering_count,
    order: category.display_order,
  }));

  return { items, droppedDuplicateCount };
}

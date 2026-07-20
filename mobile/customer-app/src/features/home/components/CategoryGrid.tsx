import React from "react";
import { View } from "react-native";
import { CategoryCard } from "./CategoryCard";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import type { HomeCategoryItem } from "../domain/discovery-composer";

export interface CategoryGridProps {
  categories: HomeCategoryItem[];
  onSelect: (category: HomeCategoryItem) => void;
  columns?: number;
}

/**
 * A small, bounded grid (Home caps categories at 12 — see
 * discovery-composer.ts) — plain flex-wrap is appropriate here; a true
 * virtualized list is reserved for the future full category-listing screen
 * (CUSTOMER-L5-04), which has no such cap.
 */
export function CategoryGrid({ categories, onSelect, columns = 3 }: CategoryGridProps) {
  const { theme } = useAppTheme();

  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing[4] }}>
      {categories.map((category) => (
        <View key={category.id} style={{ width: `${100 / columns}%` }}>
          <CategoryCard category={category} onPress={onSelect} />
        </View>
      ))}
    </View>
  );
}

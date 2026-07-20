import React from "react";
import { View } from "react-native";
import { AppCard } from "../../../components/primitives/AppCard";
import { AppText } from "../../../components/primitives/AppText";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import type { ValidatedCategorySummary } from "../../home/domain/category-schema";

export interface SearchCategoryResultProps {
  category: ValidatedCategorySummary;
  onPress: (category: ValidatedCategorySummary) => void;
}

export function SearchCategoryResult({ category, onPress }: SearchCategoryResultProps) {
  const { theme } = useAppTheme();
  return (
    <AppCard
      variant="interactive"
      onPress={() => onPress(category)}
      accessibilityLabel={category.name}
      style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[4] }}
    >
      <AppIcon name="home" size="lg" color="iconPrimary" />
      <View style={{ flex: 1 }}>
        <AppText variant="labelLarge">{category.name}</AppText>
      </View>
      <AppIcon name="chevron-forward" size="sm" color="iconSecondary" />
    </AppCard>
  );
}

import React, { useState } from "react";
import { View, Image } from "react-native";
import { AppCard } from "../../../components/primitives/AppCard";
import { AppText } from "../../../components/primitives/AppText";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import type { HomeCategoryItem } from "../domain/discovery-composer";

const TRUSTED_IMAGE_HOST_PREFIXES = ["https://"];

function isTrustedImageUrl(url: string | null): url is string {
  return Boolean(url) && TRUSTED_IMAGE_HOST_PREFIXES.some((prefix) => url!.startsWith(prefix));
}

export interface CategoryCardProps {
  category: HomeCategoryItem;
  onPress: (category: HomeCategoryItem) => void;
}

export function CategoryCard({ category, onPress }: CategoryCardProps) {
  const { theme } = useAppTheme();
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = isTrustedImageUrl(category.iconUrl) && !imageFailed;

  return (
    <AppCard
      variant="interactive"
      onPress={() => onPress(category)}
      accessibilityLabel={`${category.name}${category.offeringCount > 0 ? `, ${category.offeringCount} services available` : ""}`}
      style={{ flex: 1, minHeight: 96, alignItems: "center", justifyContent: "center", gap: theme.spacing[3] }}
    >
      <View style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center" }}>
        {showImage ? (
          <Image
            source={{ uri: category.iconUrl! }}
            style={{ width: 40, height: 40 }}
            resizeMode="contain"
            onError={() => setImageFailed(true)}
            accessibilityElementsHidden
          />
        ) : (
          <AppIcon name="home" size="lg" color="iconPrimary" />
        )}
      </View>
      <AppText variant="labelLarge" align="center" numberOfLines={2}>
        {category.name}
      </AppText>
    </AppCard>
  );
}

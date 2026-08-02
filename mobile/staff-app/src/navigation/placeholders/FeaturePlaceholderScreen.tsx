import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/themes";
import { Heading } from "../../design-system/components/typography/Heading";
import { AppText } from "../../design-system/components/typography/AppText";
import { Caption } from "../../design-system/components/typography/Label";
import { Icon, IconProps } from "../../design-system/components/Icon";

export interface FeaturePlaceholderScreenProps {
  title: string;
  note?: string;
  icon?: IconProps["name"];
}

/**
 * Marks an unbuilt feature screen during navigation-shell development
 * (spec section 11). Visibly labeled as a placeholder and renders no
 * operational data -- Phase E proves navigation reaches this screen, it
 * does not build the feature itself.
 */
export function FeaturePlaceholderScreen({ title, note, icon = "construct-outline" }: FeaturePlaceholderScreenProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary, alignItems: "center", justifyContent: "center", padding: theme.spacing.xl, gap: theme.spacing.sm }}>
      <Icon name={icon} size="feature" color={theme.colors.textTertiary} decorative />
      <Heading level="medium" align="center">{title}</Heading>
      <AppText color="secondary" align="center">
        {note ?? "This screen is not implemented yet -- navigation shell placeholder only."}
      </AppText>
      <View style={{ marginTop: theme.spacing.base, paddingHorizontal: theme.spacing.sm, paddingVertical: 4, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusNeutralSurface }}>
        <Caption color="tertiary">DEV PLACEHOLDER</Caption>
      </View>
    </View>
  );
}

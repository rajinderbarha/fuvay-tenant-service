import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";
import { resolveMediaUrl } from "../../domain/mediaUrl";

export interface TrustBenefitCardProps {
  label: string;
  icon: IconProps["name"];
  /** Illustration for this benefit. Falls back to the `icon` glyph when
   * absent so the row never renders an empty tile. */
  artworkUrl?: string | null;
}

/** Static marketing copy, not backend data -- see homeViewModels.ts. */
export function TrustBenefitCard({ label, icon, artworkUrl }: TrustBenefitCardProps) {
  const { theme } = useTheme();
  const uri = resolveMediaUrl(artworkUrl);
  return (
    <View
      style={{
        flex: 1, alignItems: "center", gap: theme.spacing.xs, paddingVertical: theme.spacing.base,
        paddingHorizontal: theme.spacing.xs,
        borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
      }}
    >
      {uri ? (
        <Image source={{ uri }} style={{ width: 44, height: 44 }} resizeMode="contain" accessibilityElementsHidden />
      ) : (
        <Icon name={icon} size="navigation" color={theme.colors.brandPrimaryStrong} decorative />
      )}
      <AppText variant="caption" align="center" numberOfLines={2}>{label}</AppText>
    </View>
  );
}

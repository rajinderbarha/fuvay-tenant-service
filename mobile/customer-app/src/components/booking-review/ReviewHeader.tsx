import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";

export interface ReviewHeaderProps {
  onBack: () => void;
  onClose: () => void;
}

export function ReviewHeader({ onBack, onClose }: ReviewHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.xs }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
        <Icon name="sparkles" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
        <View style={{ flex: 1 }}>
          <AppText variant="headingSmall" numberOfLines={1}>Review service request</AppText>
          <AppText variant="caption" color="tertiary">Check everything before confirming</AppText>
        </View>
        <AppIconButton name="close" onPress={onClose} accessibilityLabel="Close" />
      </View>
    </View>
  );
}

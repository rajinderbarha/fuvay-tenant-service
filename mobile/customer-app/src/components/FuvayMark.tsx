import React from "react";
import { View } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { Icon } from "./Icon";

/** Shared wordmark used on bootstrap/exceptional-state screens -- no image
 * asset dependency, built entirely from theme tokens so it renders
 * correctly before any asset bundle is available. */
export function FuvayMark() {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
      <Icon name="flash" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
      <AppText variant="headingMedium" style={{ letterSpacing: 1 }}>FUVAY</AppText>
    </View>
  );
}

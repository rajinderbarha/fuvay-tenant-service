import React from "react";
import { View, ActivityIndicator } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText } from "../../components";
import { FuvayMark } from "../../components/FuvayMark";

/**
 * Bootstrap screen (spec section 13 "Preparing experience"). Light
 * warm-white treatment, no tabs, no customer data, restrained orange
 * spinner -- matches the attached design's first frame exactly.
 */
export function PreparingExperienceScreen() {
  const { theme } = useTheme();
  return (
    <AppScreen style={{ alignItems: "center", justifyContent: "center" }}>
      <View style={{ marginBottom: theme.spacing.huge }}>
        <FuvayMark />
      </View>
      <AppText variant="headingMedium" align="center" accessibilityRole="header" style={{ marginBottom: theme.spacing.xs }}>
        Preparing your experience
      </AppText>
      <AppText variant="bodySmall" color="secondary" align="center" style={{ marginBottom: theme.spacing.xxl }}>
        Loading services available in your area
      </AppText>
      <ActivityIndicator
        size="large"
        color={theme.colors.brandPrimaryStrong}
        accessibilityLabel="Preparing your experience"
      />
    </AppScreen>
  );
}

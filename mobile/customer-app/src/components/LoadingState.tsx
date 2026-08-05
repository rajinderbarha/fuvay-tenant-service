import React from "react";
import { View, ActivityIndicator } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";

export function LoadingState({ label }: { label?: string }) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel={label ?? "Loading"}
      style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: theme.spacing.sm }}
    >
      <ActivityIndicator color={theme.colors.brandPrimaryStrong} size="large" />
      {label ? <AppText variant="bodySmall" color="secondary">{label}</AppText> : null}
    </View>
  );
}

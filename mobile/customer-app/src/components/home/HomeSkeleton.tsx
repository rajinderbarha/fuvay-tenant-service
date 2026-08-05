import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { LoadingSkeleton } from "../LoadingSkeleton";

export function HomeSkeleton() {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.lg }} accessibilityLabel="Loading your home screen" accessibilityRole="progressbar">
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <LoadingSkeleton width="60%" height={24} />
        <LoadingSkeleton width={40} height={40} radius={20} />
      </View>
      <LoadingSkeleton width="100%" height={48} radius={theme.radiusUsage.input} />
      <LoadingSkeleton width="100%" height={140} radius={theme.radiusUsage.card} />
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        <LoadingSkeleton width="48%" height={100} radius={theme.radiusUsage.card} />
        <LoadingSkeleton width="48%" height={100} radius={theme.radiusUsage.card} />
      </View>
    </View>
  );
}

import React from "react";
import { View } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { LoadingSkeleton } from "./LoadingSkeleton";
import { Icon } from "./Icon";

export interface ShellSectionSkeletonProps {
  title: string;
  rows?: number;
}

/** Neutral skeleton section used by the Phase E Home shell preview --
 * rows are placeholder shapes only, never real service/booking data (spec
 * section 8). */
export function ShellSectionSkeleton({ title, rows = 3 }: ShellSectionSkeletonProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        backgroundColor: theme.colors.surfaceDefault,
        borderRadius: theme.radiusUsage.card,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        padding: theme.layout.cardPadding,
      }}
    >
      <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>{title}</AppText>
      <View style={{ gap: theme.spacing.md }}>
        {Array.from({ length: rows }).map((_, i) => (
          <View key={i} style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
            <View
              style={{
                width: 40,
                height: 40,
                borderRadius: theme.radiusUsage.input,
                backgroundColor: theme.colors.surfaceInteractive,
              }}
            />
            <LoadingSkeleton width="70%" height={14} style={{ flex: 1 }} />
            <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
          </View>
        ))}
      </View>
    </View>
  );
}

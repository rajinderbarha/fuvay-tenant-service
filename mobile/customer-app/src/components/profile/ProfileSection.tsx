import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";

export function ProfileSection({ title, children }: { title: string; children: React.ReactNode }) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.xs }}>
      <AppText variant="labelStrong" color="secondary">{title}</AppText>
      <AppCard style={{ padding: 0, overflow: "hidden" }}>{children}</AppCard>
    </View>
  );
}

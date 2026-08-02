import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { NumericText } from "../typography/NumericText";
import { Card } from "../foundation/Layout";
import { Icon, IconProps } from "../Icon";

export interface MetricCardProps {
  label: string;
  value: string;
  icon?: IconProps["name"];
  tone?: "neutral" | "success" | "warning" | "danger";
}

export function MetricCard({ label, value, icon, tone = "neutral" }: MetricCardProps) {
  const { theme } = useTheme();
  const color = tone === "neutral" ? theme.colors.textPrimary
    : tone === "success" ? theme.colors.statusSuccess
    : tone === "warning" ? theme.colors.statusWarning
    : theme.colors.statusDanger;

  return (
    <Card style={{ flex: 1 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, marginBottom: theme.spacing.xs }}>
        {icon ? <Icon name={icon} size="compact" color={theme.colors.textTertiary} decorative /> : null}
        <AppText variant="label" color="tertiary">{label}</AppText>
      </View>
      <NumericText size="large" style={{ color }}>{value}</NumericText>
    </Card>
  );
}

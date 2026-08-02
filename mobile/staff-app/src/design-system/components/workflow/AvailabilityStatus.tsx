import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Switch } from "../forms/Switch";

export type AvailabilityValue = "available" | "busy" | "off_duty";

const LABEL: Record<AvailabilityValue, string> = { available: "Available", busy: "On a job", off_duty: "Off duty" };

export function AvailabilityStatus({ value, onToggleAvailable, disabled }: { value: AvailabilityValue; onToggleAvailable: (available: boolean) => void; disabled?: boolean }) {
  const { theme } = useTheme();
  const color = value === "available" ? theme.colors.statusSuccess : value === "busy" ? theme.colors.statusWarning : theme.colors.statusNeutral;

  return (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
        <AppText variant="bodyStrong">{LABEL[value]}</AppText>
      </View>
      <Switch value={value === "available"} onChange={onToggleAvailable} disabled={disabled || value === "busy"} accessibilityLabel="Toggle availability" />
    </View>
  );
}

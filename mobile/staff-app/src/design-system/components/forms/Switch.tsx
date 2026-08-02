import React from "react";
import { Switch as RNSwitch, View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";

export interface SwitchProps {
  label?: string;
  value: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  accessibilityLabel?: string;
}

export function Switch({ label, value, onChange, disabled, accessibilityLabel }: SwitchProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing.sm }}>
      {label ? <AppText variant="body" style={{ flex: 1 }}>{label}</AppText> : null}
      <RNSwitch
        value={value}
        onValueChange={onChange}
        disabled={disabled}
        accessibilityLabel={accessibilityLabel ?? label}
        trackColor={{ false: theme.colors.surfaceInteractive, true: theme.colors.brandPrimaryMuted }}
        thumbColor={value ? theme.colors.brandPrimary : theme.colors.surfaceRaised}
      />
    </View>
  );
}

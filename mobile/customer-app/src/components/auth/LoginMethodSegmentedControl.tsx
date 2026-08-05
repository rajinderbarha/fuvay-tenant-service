import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";

export type LoginMethod = "otp" | "password";

export interface LoginMethodSegmentedControlProps {
  value: LoginMethod;
  onChange: (method: LoginMethod) => void;
}

/** Exposes selected state via `accessibilityState.selected` (spec section
 * 22 "Segmented Login methods expose selected state") -- selection is
 * never conveyed by color alone (the selected segment also gets a
 * distinct background + bold weight). */
export function LoginMethodSegmentedControl({ value, onChange }: LoginMethodSegmentedControlProps) {
  const { theme } = useTheme();
  const options: { key: LoginMethod; label: string }[] = [
    { key: "otp", label: "Phone OTP" },
    { key: "password", label: "Password" },
  ];

  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: "row",
        backgroundColor: theme.colors.surfaceInteractive,
        borderRadius: theme.radiusUsage.input,
        padding: theme.spacing.xxs,
        gap: theme.spacing.xxs,
      }}
    >
      {options.map(opt => {
        const selected = opt.key === value;
        return (
          <Pressable
            key={opt.key}
            onPress={() => onChange(opt.key)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            style={{
              flex: 1,
              minHeight: theme.touchTargets.minimum - theme.spacing.sm,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: theme.radiusUsage.input,
              backgroundColor: selected ? theme.colors.surfaceDefault : "transparent",
              ...(selected ? theme.shadow.sm : null),
            }}
          >
            <AppText variant={selected ? "bodyStrong" : "body"} color={selected ? "primary" : "secondary"}>
              {opt.label}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

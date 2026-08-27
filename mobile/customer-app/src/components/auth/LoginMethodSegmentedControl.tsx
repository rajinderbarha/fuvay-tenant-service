import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";

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
  const options: { key: LoginMethod; label: string; icon: IconProps["name"] }[] = [
    { key: "otp", label: "Phone OTP", icon: "phone-portrait-outline" },
    { key: "password", label: "Password", icon: "lock-closed-outline" },
  ];

  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: "row",
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
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
              minHeight: theme.touchTargets.minimum,
              flexDirection: "row",
              gap: theme.spacing.sm,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: theme.radiusUsage.input,
              backgroundColor: selected ? theme.colors.brandPrimaryMuted : "transparent",
              borderBottomWidth: selected ? 2 : 0,
              borderBottomColor: theme.colors.brandPrimary,
            }}
          >
            <Icon name={opt.icon} size="compact" color={selected ? theme.colors.brandPrimaryStrong : theme.colors.iconDefault} decorative />
            <AppText variant={selected ? "bodyStrong" : "body"} color={selected ? "link" : "secondary"}>
              {opt.label}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

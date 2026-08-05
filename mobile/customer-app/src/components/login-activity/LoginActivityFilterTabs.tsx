import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { LoginActivityFilter } from "../../domain/customerSecurity";

const FILTERS: { key: LoginActivityFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "successful", label: "Successful" },
  { key: "needs_attention", label: "Needs attention" },
];

export interface LoginActivityFilterTabsProps {
  value: LoginActivityFilter;
  onChange: (filter: LoginActivityFilter) => void;
}

export function LoginActivityFilterTabs({ value, onChange }: LoginActivityFilterTabsProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.xs }} accessibilityRole="tablist">
      {FILTERS.map(f => {
        const selected = value === f.key;
        return (
          <Pressable
            key={f.key}
            onPress={() => onChange(f.key)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            accessibilityLabel={f.label}
            hitSlop={4}
            style={{
              minHeight: theme.touchTargets.minimum,
              paddingHorizontal: theme.spacing.sm,
              alignItems: "center", justifyContent: "center",
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: selected ? theme.colors.brandPrimary : theme.colors.surfaceInteractive,
            }}
          >
            <AppText variant="labelStrong" style={{ color: selected ? theme.colors.brandOnPrimary : theme.colors.textPrimary }}>
              {f.label}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

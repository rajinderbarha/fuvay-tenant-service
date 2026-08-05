import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { ThemePreference } from "../../design-system/theme/ThemeProvider";
import { AppText } from "../AppText";

const OPTIONS: Array<{ key: ThemePreference; label: string }> = [
  { key: "system", label: "System" },
  { key: "light", label: "Light" },
  { key: "dark", label: "Dark" },
];

export function AppearanceSelector({ selected, onSelect }: { selected: ThemePreference; onSelect: (p: ThemePreference) => void }) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: "row", borderRadius: theme.radiusUsage.statusPill,
        backgroundColor: theme.colors.surfaceInteractive, padding: 2,
      }}
    >
      {OPTIONS.map(opt => {
        const isSelected = selected === opt.key;
        return (
          <Pressable
            key={opt.key}
            onPress={() => onSelect(opt.key)}
            accessibilityRole="tab"
            accessibilityState={{ selected: isSelected }}
            accessibilityLabel={opt.label}
            style={{
              paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xxs,
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: isSelected ? theme.colors.brandPrimary : "transparent",
            }}
          >
            <AppText variant="labelStrong" style={{ color: isSelected ? theme.colors.brandOnPrimary : theme.colors.textPrimary }}>
              {opt.label}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

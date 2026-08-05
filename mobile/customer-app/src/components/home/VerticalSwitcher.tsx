import React from "react";
import { ScrollView, Pressable, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";
import { HomeVertical } from "../../domain/customerHome";
import { resolveVerticalIcon } from "../../domain/verticalIcon";

export interface VerticalSwitcherProps {
  /** Already backend-filtered to enabled verticals only (see
   * CustomerHomeService._get_enabled_verticals -- disabled verticals are
   * never included in the payload, so there is no client-side hiding
   * logic to get wrong). */
  verticals: HomeVertical[];
  selectedVerticalKey: string;
  onSelect: (vertical: HomeVertical) => void;
}

const FALLBACK_ICON: IconProps["name"] = "grid-outline";

export function VerticalSwitcher({ verticals, selectedVerticalKey, onSelect }: VerticalSwitcherProps) {
  const { theme } = useTheme();
  if (verticals.length === 0) return null;

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityRole="tablist">
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        {verticals.map(vertical => {
          const selected = vertical.key === selectedVerticalKey;
          return (
            <Pressable
              key={vertical.verticalId}
              onPress={() => onSelect(vertical)}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              accessibilityLabel={vertical.label}
              style={{
                flexDirection: "row", alignItems: "center", gap: theme.spacing.xs,
                minHeight: theme.touchTargets.minimum, paddingHorizontal: theme.spacing.base,
                borderRadius: theme.radiusUsage.statusPill,
                backgroundColor: selected ? theme.colors.brandPrimary : theme.colors.surfaceDefault,
                borderWidth: 1, borderColor: selected ? theme.colors.brandPrimary : theme.colors.borderSubtle,
              }}
            >
              <Icon
                name={resolveVerticalIcon(vertical.icon, FALLBACK_ICON)}
                size="compact"
                color={selected ? theme.colors.brandOnPrimary : theme.colors.iconDefault}
                decorative
              />
              <AppText variant="bodySmall" style={{ color: selected ? theme.colors.brandOnPrimary : theme.colors.textPrimary }}>
                {vertical.label}
              </AppText>
            </Pressable>
          );
        })}
      </View>
    </ScrollView>
  );
}

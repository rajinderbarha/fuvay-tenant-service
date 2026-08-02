import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { Icon } from "../Icon";
import { AppText } from "../typography/AppText";

export function Rating({ value, max = 5, showValue = true }: { value: number; max?: number; showValue?: boolean }) {
  const { theme } = useTheme();
  const rounded = Math.round(value);
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`Rating: ${value} out of ${max}`}
      style={{ flexDirection: "row", alignItems: "center", gap: 2 }}
    >
      {Array.from({ length: max }).map((_, i) => (
        <Icon key={i} name={i < rounded ? "star" : "star-outline"} size="compact" color={theme.colors.statusWarning} decorative />
      ))}
      {showValue ? <AppText variant="caption" color="tertiary" style={{ marginLeft: 4 }}>{value.toFixed(1)}</AppText> : null}
    </View>
  );
}

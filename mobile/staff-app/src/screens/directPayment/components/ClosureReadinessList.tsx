import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";

export interface ReadinessRow {
  label: string;
  complete: boolean;
}

/** Read-only gate summary -- the backend, not this list, decides
 * `can_finalize` (spec section 16). */
export function ClosureReadinessList({ rows }: { rows: ReadinessRow[] }) {
  const { theme } = useTheme();
  return (
    <View>
      {rows.map(row => (
        <View key={row.label} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: theme.spacing.sm, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
          <AppText variant="body">{row.label}</AppText>
          {row.complete ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
              <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
              <AppText variant="caption" color="success">Complete</AppText>
            </View>
          ) : (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
              <Icon name="time-outline" size="compact" color={theme.colors.statusWarning} decorative />
              <AppText variant="caption" color="warning">Pending</AppText>
            </View>
          )}
        </View>
      ))}
    </View>
  );
}

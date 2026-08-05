import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface ReviewStatusStripProps {
  zipcode: string | null;
}

/** Only rendered once the loading sequence has already succeeded (spec
 * section 6: "Show only after successful checks") -- the parent screen
 * controls when this mounts. */
export function ReviewStatusStrip({ zipcode }: ReviewStatusStripProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", justifyContent: "space-between",
        padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.statusSuccessSurface,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
        <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
        <AppText variant="labelStrong" style={{ color: theme.colors.statusSuccess }}>Details complete</AppText>
      </View>
      {zipcode ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <Icon name="location" size="compact" color={theme.colors.statusSuccess} decorative />
          <AppText variant="labelStrong" style={{ color: theme.colors.statusSuccess }}>Service available in {zipcode}</AppText>
        </View>
      ) : null}
    </View>
  );
}

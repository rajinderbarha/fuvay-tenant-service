import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";

export interface ThisDeviceRowProps {
  /** True only when the backend's own `is_current` flag (device_id
   * correlation) confirms this -- never assumed (spec section 9). */
  isCurrent: boolean;
}

/** Only "This device" renders this phase -- `Manage sessions` is hidden
 * (no functional destination exists yet, spec section 9). No invented
 * city/IP-location/device-model/browser/last-active copy. */
export function ThisDeviceRow({ isCurrent }: ThisDeviceRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.xs }}>
      <View style={{ width: 36, alignItems: "center" }}>
        <Icon name="phone-portrait-outline" size="standard" color={theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">This device</AppText>
        {isCurrent ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
            <View style={{ width: 6, height: 6, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.statusSuccess }} />
            <AppText variant="bodySmall" color="secondary">Active now</AppText>
          </View>
        ) : null}
      </View>
      <AppBadge label="Current" tone="info" />
    </View>
  );
}

import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { CustomerSession } from "../../domain/customerSecurity";
import { formatRelativeServerTime, ServerTimestamp } from "../../domain/dates";

export interface OtherSessionCardProps {
  session: CustomerSession;
  onSignOut: () => void;
  signingOut: boolean;
}

/** No city/IP/device-model/browser copy beyond what the backend actually
 * returns (spec section 7) -- this app has no geo-lookup capability, so
 * no approximate-location line renders here at all (honest gap, not a
 * fabricated one). */
export function OtherSessionCard({ session, onSignOut, signingOut }: OtherSessionCardProps) {
  const { theme } = useTheme();
  const lastActive = session.lastActiveAt ? formatRelativeServerTime(session.lastActiveAt as ServerTimestamp) : null;

  return (
    <AppCard
      style={{ gap: theme.spacing.sm }}
      accessible
      accessibilityLabel={`${session.deviceName ?? "Unknown device"}, ${session.channel}${lastActive ? `, last active ${lastActive}` : ""}`}
    >
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
        <View style={{ width: 44, height: 44, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center" }}>
          <Icon name="phone-portrait-outline" size="standard" color={theme.colors.textSecondary} decorative />
        </View>
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <AppText variant="bodyStrong">{session.deviceName ?? "Unknown device"}</AppText>
            <AppButton
              label="Sign out" tone="destructive" size="compact" onPress={onSignOut}
              loading={signingOut}
              accessibilityLabel={`Sign out ${session.deviceName ?? "this device"}`}
            />
          </View>
          <AppText variant="bodySmall" color="secondary">Fuvay app • {session.channel}</AppText>
          {lastActive ? <AppText variant="bodySmall" color="secondary">Last active {lastActive}</AppText> : null}
        </View>
      </View>
    </AppCard>
  );
}

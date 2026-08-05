import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { CustomerSession } from "../../domain/customerSecurity";
import { ServerTimestamp } from "../../domain/dates";

export interface CurrentSessionCardProps {
  session: CustomerSession;
}

/** No per-session Sign out button here -- ending the current session goes
 * through the established logout flow (secure credential cleanup +
 * navigation reset), never this screen's revoke mutation (spec section
 * 6). `Trusted` is never shown unless the backend's own `is_trusted` flag
 * says so. */
export function CurrentSessionCard({ session }: CurrentSessionCardProps) {
  const { theme } = useTheme();
  const signedInDate = session.createdAt ? new Date(session.createdAt as ServerTimestamp).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : null;

  return (
    <AppCard
      style={{ gap: theme.spacing.sm }}
      accessible
      accessibilityLabel={`This device, current session, active now`}
    >
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
        <View style={{ width: 44, height: 44, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center" }}>
          <Icon name="phone-portrait-outline" size="standard" color={theme.colors.textSecondary} decorative />
        </View>
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <AppText variant="bodyStrong">This device</AppText>
            <AppBadge label="Current" tone="info" />
          </View>
          <AppText variant="bodySmall" color="secondary">Fuvay app • {session.channel}</AppText>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
            <View style={{ width: 6, height: 6, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.statusSuccess }} />
            <AppText variant="bodySmall" color="secondary">Active now</AppText>
          </View>
        </View>
      </View>
      {signedInDate ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle, paddingTop: theme.spacing.sm }}>
          <Icon name="calendar-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary">Signed in {signedInDate}</AppText>
        </View>
      ) : null}
    </AppCard>
  );
}

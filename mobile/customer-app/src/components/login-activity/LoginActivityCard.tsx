import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon, IconProps } from "../Icon";
import { LoginActivityEvent } from "../../domain/customerSecurity";
import { ServerTimestamp } from "../../domain/dates";

export interface LoginActivityCardProps {
  event: LoginActivityEvent;
}

const OUTCOME_META: Record<LoginActivityEvent["outcome"], { icon: IconProps["name"]; colorKey: "statusSuccess" | "statusWarning" | "statusDanger" | "textSecondary" }> = {
  successful: { icon: "checkmark-circle", colorKey: "statusSuccess" },
  verification_required: { icon: "alert-circle", colorKey: "statusWarning" },
  blocked: { icon: "close-circle", colorKey: "statusDanger" },
  unknown: { icon: "help-circle-outline", colorKey: "textSecondary" },
};

/** No raw backend event_type, no failure reason, no IP, no geo (this
 * backend has no geo-lookup capability -- honestly omitted, spec section
 * 13's "Network location unavailable" copy is not shown either since
 * there is no location field to be unavailable). */
export function LoginActivityCard({ event }: LoginActivityCardProps) {
  const { theme } = useTheme();
  const meta = OUTCOME_META[event.outcome];
  const color = theme.colors[meta.colorKey];
  const time = new Date(event.occurredAt as ServerTimestamp).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  const absoluteLabel = new Date(event.occurredAt as ServerTimestamp).toLocaleString();

  return (
    <AppCard
      style={{ gap: theme.spacing.xs }}
      accessible
      accessibilityLabel={`${event.label}, ${event.deviceName ?? event.channel}, ${absoluteLabel}${event.isCurrentDevice ? ", current device" : ""}`}
    >
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
        <Icon name={meta.icon} size="standard" color={color} decorative />
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <AppText variant="bodyStrong">{event.label}</AppText>
            {event.isCurrentDevice ? <AppBadge label="Current device" tone="info" /> : null}
          </View>
          <AppText variant="bodySmall" color="secondary">
            {event.deviceName ? `${event.deviceName} • ` : ""}Fuvay app • {event.channel}
          </AppText>
          <AppText variant="bodySmall" color="secondary" accessibilityLabel={absoluteLabel}>{time}</AppText>
        </View>
      </View>
    </AppCard>
  );
}

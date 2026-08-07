import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { formatCreatedAt, ServerTimestamp } from "../../domain/dates";

export interface CurrentStatusCardProps {
  statusLabel: string;
  activityText: string | null;
  supportingText: string | null;
  createdAt?: ServerTimestamp | null;
}

/** Renders only truthful, backend-derived text -- `statusLabel` is
 * already a customer-safe mapped value (domain/bookingStatus.ts), never a
 * raw workflow enum.
 *
 * Real bug fixed here: the status pill was a HARDCODED "Request confirmed"
 * string, so a booking that had moved past that point (e.g. genuinely
 * on the way) still showed a stale label on this card. It now renders the
 * same `statusLabel` the rest of the app already computed.
 */
export function CurrentStatusCard({ statusLabel, activityText, supportingText, createdAt }: CurrentStatusCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", gap: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, flex: 1 }}>
          <View
            style={{
              width: 40, height: 40, borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.brandPrimaryMuted,
              alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
            <Icon name="sparkles" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1, minWidth: 0 }}>
            {/* When there is no distinct activity line, the pill on the
                right already says the status -- repeating it here as the
                title too would render the identical text twice on one
                card. "What's happening" falls back to the generic label
                only in that case. */}
            <AppText variant="bodyStrong">{activityText ?? "What's happening"}</AppText>
            {supportingText ? (
              <AppText variant="bodySmall" color="secondary" style={{ marginTop: 1 }}>{supportingText}</AppText>
            ) : null}
          </View>
        </View>
        <View style={{ alignItems: "flex-end", gap: theme.spacing.xxs }}>
          <View
            style={{
              paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill,
              borderWidth: 1, borderColor: theme.colors.statusSuccess,
              backgroundColor: theme.colors.statusSuccessSurface,
            }}
          >
            <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>{statusLabel}</AppText>
          </View>
          {createdAt ? (
            <AppText variant="caption" color="tertiary">{formatCreatedAt(createdAt)}</AppText>
          ) : null}
        </View>
      </View>
    </AppCard>
  );
}

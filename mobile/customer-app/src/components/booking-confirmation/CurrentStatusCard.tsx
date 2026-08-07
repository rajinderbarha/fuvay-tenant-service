import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { formatCreatedAt, ServerTimestamp } from "../../domain/dates";

export interface CurrentStatusCardProps {
  statusLabel: string;
  activityText: string | null;
  supportingText: string | null;
  createdAt?: ServerTimestamp | null;
}

const ICON_SIZE = 72;

/** Renders only truthful, backend-derived text -- `statusLabel` is
 * already a customer-safe mapped value (domain/bookingStatus.ts), never a
 * raw workflow enum.
 *
 * Real bug fixed here: the status pill was a HARDCODED "Request confirmed"
 * string, so a booking that had moved past that point (e.g. genuinely
 * on the way) still showed a stale label on this card. It now renders the
 * same `statusLabel` the rest of the app already computed.
 *
 * Centered hero layout per the design -- a full-bleed section rather than
 * a bordered card, with a layered icon badge. Colours are the app's own
 * existing brand tokens (brandPrimaryMuted/brandPrimaryStrong), not a new
 * accent introduced for this card. */
export function CurrentStatusCard({ statusLabel, activityText, supportingText, createdAt }: CurrentStatusCardProps) {
  const { theme } = useTheme();
  return (
    <View style={{ alignItems: "center" }}>
      <View style={{ width: ICON_SIZE, height: ICON_SIZE, alignItems: "center", justifyContent: "center" }}>
        {/* Two faint rings behind the solid icon circle -- purely
            decorative depth, same brand hue at falling opacity. */}
        <View
          style={{
            position: "absolute", width: ICON_SIZE, height: ICON_SIZE, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimaryMuted, opacity: 0.4,
          }}
        />
        <View
          style={{
            position: "absolute", width: ICON_SIZE * 0.78, height: ICON_SIZE * 0.78, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimaryMuted, opacity: 0.7,
          }}
        />
        <View
          style={{
            width: ICON_SIZE * 0.58, height: ICON_SIZE * 0.58, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimaryMuted,
            alignItems: "center", justifyContent: "center",
          }}
        >
          <Icon name="sparkles" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
        </View>
        {/* Small solid badge overlapping the ring, same brand colour as
            the pill below -- ties the icon to the status it represents. */}
        <View
          style={{
            position: "absolute", right: 2, bottom: 2,
            width: 18, height: 18, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimary,
            borderWidth: 2, borderColor: theme.colors.surfaceDefault,
          }}
        />
      </View>

      <AppText variant="headingSmall" align="center" style={{ marginTop: theme.spacing.sm }}>
        {/* When there is no distinct activity line, the pill below already
            says the status -- repeating it here as the title too would
            render the identical text twice on one screen. */}
        {activityText ?? "What's happening"}
      </AppText>
      {supportingText ? (
        <AppText variant="bodySmall" color="secondary" align="center" style={{ marginTop: theme.spacing.xxs, maxWidth: 280 }}>
          {supportingText}
        </AppText>
      ) : null}

      <View
        style={{
          marginTop: theme.spacing.sm,
          paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
          borderRadius: theme.radiusUsage.statusPill,
          borderWidth: 1, borderColor: theme.colors.statusSuccess,
          backgroundColor: theme.colors.statusSuccessSurface,
        }}
      >
        <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>{statusLabel}</AppText>
      </View>

      {createdAt ? (
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>
          {formatCreatedAt(createdAt)}
        </AppText>
      ) : null}
    </View>
  );
}

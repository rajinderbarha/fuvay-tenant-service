import React, { useEffect, useRef, useState } from "react";
import { View, Animated, AccessibilityInfo } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { FuvayIcon } from "../FuvayIcon";
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
 * Centered hero layout, but the icon itself is the SAME solid
 * branded Fuvay identity used everywhere else the app
 * represents its own automated matching/assistant activity
 * (AssistantHeader, TypingBubble) -- not a bespoke ringed badge invented
 * for this one card. A gentle pulse says "this is actively working",
 * matching TypingBubble's own animation approach: reduced-motion users
 * get the icon fully static, and the pulse is purely decorative -- it
 * never implies a specific ETA or step. */
export function CurrentStatusCard({ statusLabel, activityText, supportingText, createdAt }: CurrentStatusCardProps) {
  const { theme } = useTheme();
  const [reducedMotion, setReducedMotion] = useState(false);
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion).catch(() => {});
  }, []);

  useEffect(() => {
    if (reducedMotion) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.12, duration: 700, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 700, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reducedMotion, pulse]);

  return (
    <View style={{ alignItems: "center" }}>
      <Animated.View
        style={{
          width: ICON_SIZE, height: ICON_SIZE, borderRadius: theme.radius.radiusFull,
          backgroundColor: theme.colors.brandPrimaryMuted,
          alignItems: "center", justifyContent: "center",
          transform: [{ scale: reducedMotion ? 1 : pulse }],
        }}
      >
        <FuvayIcon size={42} accessibilityLabel="Fuvay assistant" />
      </Animated.View>

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

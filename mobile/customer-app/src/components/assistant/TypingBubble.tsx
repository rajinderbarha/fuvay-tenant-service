import React, { useEffect, useRef, useState } from "react";
import { Animated, View, AccessibilityInfo } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface TypingBubbleProps {
  /** A short, honest label for what's actually happening right now (e.g.
   * "Saving your answer", "Loading next question") -- sourced from the
   * controller's own real uiState, never a fabricated or unrelated word.
   * Per explicit feedback: a fixed rotating word cycle that showed the
   * same thing regardless of the real request in flight was worse than
   * useful, since it didn't reflect reality. Falls back to "Thinking" if
   * omitted. */
  label?: string;
}

/**
 * Inline chat "typing" indicator -- a normal, left-aligned assistant
 * bubble with three pulsing dots plus a short label describing the real
 * operation in flight. Renders as a regular transcript item (see
 * AssistantScreen's `transcriptItems`), never absolutely positioned above
 * the message list, so it appears exactly where a real "..." typing
 * indicator would in any chat app -- directly under the customer's own
 * message, at the bottom of the conversation.
 *
 * Reduced-motion users see static dots with the same label and
 * accessible announcement.
 */
export function TypingBubble({ label }: TypingBubbleProps) {
  const { theme } = useTheme();
  const [reducedMotion, setReducedMotion] = useState(false);
  const dot1 = useRef(new Animated.Value(0.3)).current;
  const dot2 = useRef(new Animated.Value(0.3)).current;
  const dot3 = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion).catch(() => {});
  }, []);

  useEffect(() => {
    if (reducedMotion) return;
    // Faster pulse (was 350ms/leg) -- per feedback that the indicator felt
    // like it lingered too long before the next question appeared.
    const pulse = (value: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(value, { toValue: 1, duration: 240, delay, useNativeDriver: true }),
          Animated.timing(value, { toValue: 0.3, duration: 240, useNativeDriver: true }),
        ]),
      );
    const loops = [pulse(dot1, 0), pulse(dot2, 110), pulse(dot3, 220)];
    loops.forEach(l => l.start());
    return () => loops.forEach(l => l.stop());
  }, [reducedMotion, dot1, dot2, dot3]);

  const displayLabel = label || "Thinking";

  return (
    <View
      accessibilityLabel="Assistant is responding"
      accessible
      style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, alignSelf: "flex-start" }}
    >
      <View
        style={{
          width: 24, height: 24, borderRadius: theme.radius.radiusFull,
          backgroundColor: theme.colors.brandPrimaryMuted,
          alignItems: "center", justifyContent: "center",
        }}
      >
        <Icon name="sparkles" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
      </View>
      <View
        style={{
          flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
          backgroundColor: theme.colors.surfaceInteractive,
          borderRadius: theme.radiusUsage.card,
          paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
        }}
      >
        <AppText variant="caption" color="tertiary">{displayLabel}</AppText>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
          {[dot1, dot2, dot3].map((v, i) => (
            <Animated.View
              key={i}
              style={{
                width: 6, height: 6, borderRadius: 3,
                backgroundColor: theme.colors.textTertiary,
                opacity: reducedMotion ? 0.6 : v,
              }}
            />
          ))}
        </View>
      </View>
    </View>
  );
}

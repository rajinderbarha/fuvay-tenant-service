import React, { useEffect, useRef } from "react";
import { View, Animated, Easing, AccessibilityInfo } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { AssistantActivityStage, resolveActivityLabel } from "../../domain/assistantActivity";

export interface AssistantActivityProps {
  stage: AssistantActivityStage;
  zipcode: string | null;
  fallbackOffered: boolean;
  onContinueWithGuidedFallback: () => void;
  onCancel?: () => void;
}

/**
 * Real-event-driven processing capsule (spec section 6). The label is
 * always one of the closed allowlist strings in domain/assistantActivity
 * -- this component never receives raw backend text, a model name, or a
 * fabricated percentage. `stage` is set by useAssistantController only in
 * response to actual request-lifecycle transitions, never a timer.
 */
export function AssistantActivity({ stage, zipcode, fallbackOffered, onContinueWithGuidedFallback, onCancel }: AssistantActivityProps) {
  const { theme } = useTheme();
  const pulse = useRef(new Animated.Value(0)).current;
  const [reducedMotion, setReducedMotion] = React.useState(false);
  // Cycling "." -> ".." -> "..." dots, like a chat "typing" indicator --
  // purely cosmetic (never affects the real label, which stays the closed
  // allowlist string from resolveActivityLabel), just a lightweight sense
  // of active work happening while waiting on a real request.
  const [dotCount, setDotCount] = React.useState(1);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion).catch(() => {});
  }, []);

  useEffect(() => {
    if (reducedMotion) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 900, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 900, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reducedMotion, pulse]);

  useEffect(() => {
    if (reducedMotion) return;
    const interval = setInterval(() => setDotCount(d => (d % 3) + 1), 450);
    return () => clearInterval(interval);
  }, [reducedMotion]);

  const dots = reducedMotion ? "…" : ".".repeat(dotCount);

  useEffect(() => {
    AccessibilityInfo.announceForAccessibility(resolveActivityLabel(stage, zipcode));
  }, [stage, zipcode]);

  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.15] });
  const opacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.55, 1] });

  return (
    <View
      accessibilityLabel={resolveActivityLabel(stage, zipcode)}
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        padding: theme.spacing.base, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.brandPrimaryMuted, borderWidth: 1, borderColor: theme.colors.borderSubtle,
      }}
    >
      <Animated.View
        style={{
          width: 32, height: 32, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.brandPrimary,
          alignItems: "center", justifyContent: "center",
          transform: reducedMotion ? undefined : [{ scale }],
          opacity: reducedMotion ? 1 : opacity,
        }}
      >
        <Icon name="sparkles" size="compact" color={theme.colors.brandOnPrimary} decorative />
      </Animated.View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">{resolveActivityLabel(stage, zipcode).replace(/…$/, "")}{dots}</AppText>
        <AppText variant="caption" color="tertiary">Your progress is safe</AppText>
        {fallbackOffered ? (
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginTop: theme.spacing.xs }}>
            <AppButton label="Continue with guided questions" size="compact" tone="secondary" onPress={onContinueWithGuidedFallback} />
            {onCancel ? <AppButton label="Cancel" size="compact" tone="tertiary" onPress={onCancel} /> : null}
          </View>
        ) : null}
      </View>
    </View>
  );
}

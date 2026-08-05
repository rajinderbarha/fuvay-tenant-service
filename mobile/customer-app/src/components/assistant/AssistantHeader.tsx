import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";

export interface AssistantHeaderProps {
  title: string;
  onClose: () => void;
  answeredCount: number;
  remainingCount: number;
  /** Discards the current conversation and starts a genuinely fresh
   * request for the same service -- the explicit "start again" escape
   * hatch for a conversation that has gone somewhere the customer didn't
   * intend. */
  onRestart?: () => void;
}

export function AssistantHeader({ title, onClose, answeredCount, remainingCount, onRestart }: AssistantHeaderProps) {
  const { theme } = useTheme();
  const total = answeredCount + remainingCount;
  // "Step X of Y" only reflects REAL backend progress (answeredCount/
  // remainingCount from the question-flow envelope) -- never a fabricated
  // step count. Hidden entirely until the backend has actually produced a
  // question, rather than showing "Step 1 of 0" or similar.
  const currentStep = Math.min(answeredCount + 1, Math.max(total, 1));

  return (
    <View style={{ gap: theme.spacing.xs }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
        <AppIconButton name="chevron-back" onPress={onClose} accessibilityLabel="Back" />
        <View
          style={{
            width: 28, height: 28, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimaryMuted,
            alignItems: "center", justifyContent: "center",
          }}
        >
          <Icon name="sparkles" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="headingSmall" numberOfLines={1}>{title}</AppText>
          <AppText variant="caption" color="tertiary">Saved automatically</AppText>
        </View>
        {total > 0 ? (
          <View style={{ alignItems: "flex-end", gap: theme.spacing.xxs }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
              <View
                style={{
                  paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xxs,
                  borderRadius: theme.radiusUsage.statusPill, borderWidth: 1, borderColor: theme.colors.borderSubtle,
                }}
              >
                {/* "Question X of Y" -- explicitly catalog-question
                    progress, never conflated with overall booking-stage
                    progress (address/schedule/review live on separate
                    screens with their own progress model). */}
                <AppText variant="labelStrong">Question {currentStep} of {total}</AppText>
              </View>
              {onRestart ? (
                <AppIconButton name="refresh" onPress={onRestart} accessibilityLabel="Start a new request" />
              ) : null}
              <AppIconButton name="close" onPress={onClose} accessibilityLabel="Close assistant" />
            </View>
            <View style={{ width: 100, height: 4, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.surfaceDisabled, overflow: "hidden" }}>
              <View
                style={{
                  width: `${Math.round((currentStep / total) * 100)}%`, height: "100%",
                  borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.brandPrimary,
                }}
              />
            </View>
          </View>
        ) : (
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
            {onRestart ? (
              <AppIconButton name="refresh" onPress={onRestart} accessibilityLabel="Start a new request" />
            ) : null}
            <AppIconButton name="close" onPress={onClose} accessibilityLabel="Close assistant" />
          </View>
        )}
      </View>
    </View>
  );
}

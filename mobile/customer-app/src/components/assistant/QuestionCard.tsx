import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { CurrentQuestion } from "../../domain/questionEnvelope";

export interface QuestionCardProps {
  question: CurrentQuestion;
  selectedOptionIds: string[];
  onSelectOption: (optionId: string) => void;
  disabled: boolean;
}

/** Renders exactly what the backend envelope says -- option order,
 * labels, required/optional state, and IDs sent back on selection are
 * never computed or reordered client-side (spec: "Send canonical option
 * IDs/codes; never calculate dependencies client-side").
 *
 * CUSTOMER-ASSISTANT-CHAT-03: renders as a plain assistant chat bubble
 * (same background/radius/alignment as `ChatBubble`, no border or
 * shadow) rather than a bordered `AppCard` -- a real product complaint
 * confirmed live: a bordered "frame" for the active question sitting
 * inside the same list as chat bubbles still read as a separate widget
 * bolted onto the chat, not "one single WhatsApp-level chat". */
export function QuestionCard({ question, selectedOptionIds, onSelectOption, disabled }: QuestionCardProps) {
  const { theme } = useTheme();
  const isMultiSelect = question.questionType === "multi_select";

  // CUSTOMER-ASSISTANT-UX-04 Part 8: an ACTIVE question owns the full
  // conversation width -- no `maxWidth`, no shrink-to-content. A short
  // option label ("LG") previously produced a tiny half-width control that
  // read as a disabled form field rather than a real, tappable choice.
  // Only historical chat bubbles stay narrow (they're conversation, not
  // interaction).
  return (
    <View
      style={{
        alignSelf: "stretch",
        backgroundColor: theme.colors.surfaceDefault,
        borderRadius: theme.radiusUsage.card,
        borderBottomLeftRadius: theme.radius.radiusSmall,
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
        paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, marginBottom: theme.spacing.xs }}>
        <AppBadge label={question.required ? "Required" : "Optional"} tone={question.required ? "warning" : "neutral"} />
      </View>
      <AppText variant="bodyStrong">{question.text}</AppText>
      {question.helpText ? (
        <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>{question.helpText}</AppText>
      ) : null}

      {question.options.length === 0 ? (
        <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.sm }}>
          Type your answer in the message box below.
        </AppText>
      ) : null}

      {question.options.length > 0 ? (
        <View style={{ marginTop: theme.spacing.sm, gap: theme.spacing.xs }}>
          {question.options.map(opt => {
            if (!opt.id) return null;
            const selected = selectedOptionIds.includes(opt.id);
            return (
              <Pressable
                key={opt.id}
                disabled={disabled}
                onPress={() => onSelectOption(opt.id as string)}
                accessibilityRole={isMultiSelect ? "checkbox" : "radio"}
                accessibilityState={{ selected, disabled }}
                accessibilityLabel={opt.label ?? opt.id}
                style={{
                  flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                  minHeight: 56, paddingHorizontal: theme.spacing.base,
                  borderRadius: theme.radiusUsage.input, borderWidth: 1,
                  borderColor: selected ? theme.colors.brandPrimary : theme.colors.borderDefault,
                  backgroundColor: selected ? theme.colors.brandPrimaryMuted : theme.colors.backgroundSecondary,
                  opacity: disabled ? theme.opacity.disabled : 1,
                }}
              >
                <AppText variant="body">{opt.label ?? opt.id}</AppText>
                {selected ? <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimaryStrong} decorative /> : null}
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

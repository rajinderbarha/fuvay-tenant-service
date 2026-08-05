import React, { useEffect, useRef, useState } from "react";
import { Animated, View, Pressable, AccessibilityInfo } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { AssistantMessage } from "../../domain/assistantSession";
import { TypingBubble } from "./TypingBubble";

export interface ChatBubbleProps {
  message: AssistantMessage;
  onQuickReply?: (value: string) => void;
  quickRepliesDisabled?: boolean;
  /** Single-active-question invariant: while a canonical catalog question
   * owns the interaction (QuestionCard is showing), a chat message's own
   * quick-replies must not render at all -- not merely disabled/greyed
   * out, genuinely absent -- so the customer is never shown two competing
   * actionable groups at once (confirmed live via a physical-device
   * screenshot: date quick-replies + a required cooling question rendered
   * simultaneously). */
  suppressQuickReplies?: boolean;
}

/** A single chat bubble that pops in on mount -- fades, slides up slightly,
 * and scales from 0.9 -> 1 with a gentle overshoot, like a real messaging
 * app "message arrived" animation -- runs once per message (new
 * AssistantMessage objects are only ever appended, never mutated in
 * place, so this naturally only animates genuinely new messages, not the
 * whole list re-rendering). Reduced-motion users get the same end state
 * with no animation. Real backend-sourced `quickReplies` (e.g. choosing
 * "AC Installation" vs "AC Service" before any draft exists) render as
 * tap buttons directly under the bubble -- per product decision, the
 * customer should never have to type when a real set of options exists;
 * free text is only for genuinely open-ended input. Tapping one is
 * equivalent to typing its value and sending it. */
export function ChatBubble({ message, onQuickReply, quickRepliesDisabled, suppressQuickReplies }: ChatBubbleProps) {
  const { theme } = useTheme();
  const progress = useRef(new Animated.Value(0)).current;
  const [used, setUsed] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion).catch(() => {});
  }, []);

  useEffect(() => {
    if (reducedMotion) {
      progress.setValue(1);
      return;
    }
    Animated.spring(progress, {
      toValue: 1,
      speed: 16,
      bounciness: 6,
      useNativeDriver: true,
    }).start();
  }, [progress, reducedMotion]);

  if (message.isTyping) {
    return <TypingBubble label={message.content} />;
  }

  const opacity = progress.interpolate({ inputRange: [0, 0.4, 1], outputRange: [0, 1, 1] });
  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [10, 0] });
  const scale = progress.interpolate({ inputRange: [0, 1], outputRange: [0.9, 1] });

  function handleTap(value: string) {
    if (used || quickRepliesDisabled) return;
    setUsed(true);
    onQuickReply?.(value);
  }

  return (
    <Animated.View
      style={{
        alignSelf: message.role === "user" ? "flex-end" : "flex-start",
        maxWidth: "85%",
        opacity,
        transform: [{ translateY }, { scale }],
        gap: theme.spacing.xs,
      }}
    >
      {/* WhatsApp-style asymmetric tail: the corner nearest the speaker is
          squared off so the two sides read as distinct voices at a glance,
          rather than two identical rounded blobs. Colours come from the
          Staff-aligned palette -- an assistant bubble sits on
          `surfaceDefault` (white) against the conversation's
          `backgroundPrimary`, which is a genuinely legible step; the old
          `surfaceInteractive`-on-`backgroundPrimary` pairing was a ~1.5%
          luminance difference, i.e. effectively invisible. */}
      <View
        style={{
          backgroundColor: message.role === "user" ? theme.colors.brandPrimaryMuted : theme.colors.surfaceDefault,
          borderRadius: theme.radiusUsage.card,
          borderBottomRightRadius: message.role === "user" ? theme.radius.radiusSmall : theme.radiusUsage.card,
          borderBottomLeftRadius: message.role === "user" ? theme.radiusUsage.card : theme.radius.radiusSmall,
          paddingHorizontal: theme.spacing.base,
          paddingVertical: theme.spacing.sm,
          borderWidth: message.role === "user" ? 0 : 1,
          borderColor: theme.colors.borderSubtle,
        }}
      >
        <AppText variant="body">{message.content}</AppText>
      </View>

      {message.quickReplies && message.quickReplies.length > 0 && !suppressQuickReplies ? (
        <View style={{ gap: theme.spacing.xs }}>
          {message.quickReplies.map(qr => (
            <Pressable
              key={qr.label}
              disabled={used || quickRepliesDisabled}
              onPress={() => handleTap(qr.value)}
              accessibilityRole="button"
              accessibilityLabel={qr.label}
              style={{
                flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                minHeight: theme.touchTargets.minimum, paddingHorizontal: theme.spacing.base,
                borderRadius: theme.radiusUsage.input, borderWidth: 1,
                borderColor: theme.colors.brandPrimary,
                backgroundColor: theme.colors.surfaceDefault,
                opacity: used || quickRepliesDisabled ? theme.opacity.disabled : 1,
              }}
            >
              <AppText variant="body">{qr.label}</AppText>
              <Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
            </Pressable>
          ))}
        </View>
      ) : null}
    </Animated.View>
  );
}

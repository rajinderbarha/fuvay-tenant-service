import React, { useState } from "react";
import { View, TextInput, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { Icon } from "../Icon";

export interface AssistantComposerProps {
  disabled: boolean;
  onSend: (text: string) => void;
  /** Short placeholder for a genuine active free-text question (spec:
   * "Add details…", not the longer explanatory sentence -- that belongs
   * in the question bubble itself, not the input field). Defaults to the
   * general-chat placeholder when no question is active. */
  placeholder?: string;
}

/** Free-text composer for the conversational part of the flow. Preserves
 * typed-but-unsent text across a recoverable failure -- it is only
 * cleared on a confirmed successful send (spec: "preserve unsent text
 * through recoverable failures"). */
export function AssistantComposer({ disabled, onSend, placeholder = "Type your answer" }: AssistantComposerProps) {
  const { theme } = useTheme();
  const [text, setText] = useState("");

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  const canSend = !disabled && !!text.trim();

  return (
    <View style={{ gap: theme.spacing.xxs }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <View
          style={{
            flex: 1, flexDirection: "row", alignItems: "center", gap: theme.spacing.xs,
            minHeight: theme.touchTargets.minimum, paddingHorizontal: theme.spacing.sm,
            borderRadius: theme.radius.radiusFull, borderWidth: 1, borderColor: theme.colors.borderDefault,
            backgroundColor: theme.colors.surfaceDefault,
          }}
        >
          <Pressable accessibilityRole="button" accessibilityLabel="Add attachment" hitSlop={8} disabled={disabled}>
            <Icon name="add-circle-outline" size="compact" color={theme.colors.textSecondary} decorative />
          </Pressable>
          <TextInput
            value={text}
            onChangeText={setText}
            // Explicit, never implicit: the keyboard opens only when the
            // customer taps this field themselves. This component is now
            // only ever mounted for a genuinely free-text interaction
            // (see AssistantScreen's composerAllowed) -- conditional
            // UNmounting, not hiding, is what keeps the keyboard from
            // reopening on a stale, still-focused instance underneath a
            // tap-only stage.
            autoFocus={false}
            // Fixed placeholder regardless of disabled state -- processing
            // feedback belongs in the inline assistant typing bubble, never
            // as literal "Please wait…" copy inside the input field itself.
            placeholder={placeholder}
            placeholderTextColor={theme.colors.textTertiary}
            editable={!disabled}
            multiline
            accessibilityLabel="Message to Fuvay Assistant"
            style={{ flex: 1, maxHeight: 96, paddingVertical: theme.spacing.xs, color: theme.colors.textPrimary, ...theme.typography.body }}
          />
          <Pressable accessibilityRole="button" accessibilityLabel="Voice input" hitSlop={8} disabled={disabled}>
            <Icon name="mic-outline" size="compact" color={theme.colors.textSecondary} decorative />
          </Pressable>
        </View>
        <Pressable
          onPress={handleSend}
          disabled={!canSend}
          accessibilityRole="button"
          accessibilityLabel="Send message"
          accessibilityState={{ disabled: !canSend }}
          style={{
            width: theme.touchTargets.iconButton, height: theme.touchTargets.iconButton,
            borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
            backgroundColor: canSend ? theme.colors.brandPrimary : theme.colors.surfaceDisabled,
          }}
        >
          <Icon name="send" size="compact" color={canSend ? theme.colors.brandOnPrimary : theme.colors.textDisabled} decorative />
        </Pressable>
      </View>
    </View>
  );
}

import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import type { AssistantLanguageOption } from "../../domain/assistantSession";

export interface LanguageChoiceCardProps {
  options: AssistantLanguageOption[];
  onSelect: (option: AssistantLanguageOption) => void;
  disabled: boolean;
}

/**
 * CUSTOMER-ASSISTANT-UX-04 Part 1: the FIRST interaction of every fresh
 * booking request -- "Choose your preferred language", rendered as
 * full-width, vertically stacked options inside the same conversation
 * feed as every other assistant turn (never a header-only selector, and
 * never three compressed buttons on one row).
 *
 * Every option comes from the backend's own ZIP-aware
 * `build_language_options`; this component never fabricates, reorders or
 * filters the list, and never offers "Regional"/"Automatic"/device
 * language. Each label is the language's own native endonym (English /
 * हिन्दी / ਪੰਜਾਬੀ) so a customer who reads only that language can
 * recognise their own option.
 *
 * This choice scopes the DeepSeek booking conversation only -- the rest
 * of the Customer App stays in its existing single UI language.
 */
export function LanguageChoiceCard({ options, onSelect, disabled }: LanguageChoiceCardProps) {
  const { theme } = useTheme();

  return (
    <View
      style={{
        alignSelf: "stretch",
        backgroundColor: theme.colors.surfaceDefault,
        borderRadius: theme.radiusUsage.card,
        borderBottomLeftRadius: theme.radius.radiusSmall,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        paddingHorizontal: theme.spacing.base,
        paddingVertical: theme.spacing.sm,
        gap: theme.spacing.xs,
      }}
    >
      {options.map(opt => (
        <Pressable
          key={opt.code}
          disabled={disabled}
          onPress={() => onSelect(opt)}
          accessibilityRole="button"
          accessibilityState={{ disabled }}
          accessibilityLabel={opt.label}
          style={({ pressed }) => ({
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
            // Spec: minimum 56pt touch height, full available width,
            // comfortable horizontal padding, never shrink-to-content.
            minHeight: 56,
            alignSelf: "stretch",
            paddingHorizontal: theme.spacing.base,
            borderRadius: theme.radiusUsage.input,
            borderWidth: 1,
            borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderDefault,
            backgroundColor: pressed ? theme.colors.brandPrimaryMuted : theme.colors.backgroundSecondary,
            opacity: disabled ? theme.opacity.disabled : 1,
          })}
        >
          <AppText variant="body">{opt.label}</AppText>
          <Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
        </Pressable>
      ))}
    </View>
  );
}

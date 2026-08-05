import React, { useState } from "react";
import { View, Pressable, Modal } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { ChatbotLanguageOption } from "../../domain/chatbotLanguage";

export interface LanguageSelectorProps {
  options: ChatbotLanguageOption[];
  selected: string;
  onChange: (code: string) => void;
}

/** Chatbot-language-only selector (never app UI language). Options come
 * exclusively from the backend session response -- never a hardcoded
 * ZIP-to-language table on the client. Renders nothing when the backend
 * hasn't returned any options yet, rather than guessing a default set. */
export function LanguageSelector({ options, selected, onChange }: LanguageSelectorProps) {
  const { theme } = useTheme();
  const [open, setOpen] = useState(false);
  if (options.length === 0) return null;
  const current = options.find(o => o.code === selected) ?? options[0];

  return (
    <>
      <Pressable
        onPress={() => setOpen(true)}
        accessibilityRole="button"
        accessibilityLabel={`Assistant language: ${current.label}. Change language.`}
        style={{
          flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
          paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xxs,
          borderRadius: theme.radiusUsage.statusPill, borderWidth: 1, borderColor: theme.colors.borderSubtle,
        }}
      >
        <Icon name="language" size="compact" color={theme.colors.textSecondary} decorative />
        <AppText variant="labelStrong">{current.label}</AppText>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable
          style={{ flex: 1, backgroundColor: theme.colors.backgroundOverlay, justifyContent: "flex-end" }}
          onPress={() => setOpen(false)}
        >
          <View style={{ backgroundColor: theme.colors.surfaceDefault, borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card, padding: theme.spacing.base, gap: theme.spacing.xxs }}>
            <AppText variant="headingSmall">Assistant language</AppText>
            {options.map(opt => (
              <Pressable
                key={opt.code}
                onPress={() => { onChange(opt.code); setOpen(false); }}
                accessibilityRole="button"
                accessibilityLabel={opt.label}
                style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: theme.spacing.sm }}
              >
                <AppText variant="body">{opt.label}</AppText>
                {opt.code === current.code ? <Icon name="checkmark" size="compact" color={theme.colors.brandPrimaryStrong} decorative /> : null}
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

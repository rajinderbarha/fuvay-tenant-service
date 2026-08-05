import React from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppIconButton } from "../../components/AppIconButton";

/**
 * Informational only -- not a language preference (the app UI stays
 * English; assistant conversation language is chosen inside each DeepSeek
 * conversation, unaffected by this phase, per scope restrictions).
 * Content is limited to what the audited backend actually proves:
 * assistant/chat messages are soft-deleted and their content replaced as
 * part of an approved account-deletion request (confirmed in
 * `ComplianceService.process_deletion` step 3), and
 * `ai_assistant_processing` is a real, customer-withdrawable consent type.
 * No system prompts, tool definitions, model parameters or provider
 * secrets are referenced here.
 */
export function AssistantDataInfoScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">Assistant conversations</AppText>
            <AppText variant="bodySmall" color="secondary">Learn how your messages are handled</AppText>
          </View>
        </View>

        <AppCard style={{ gap: theme.spacing.sm }}>
          <AppText variant="bodyStrong">How your messages are used</AppText>
          <AppText variant="bodySmall" color="secondary">
            Your conversations with the Fuvay Assistant are used to help with your service requests and may be reviewed for quality and safety.
          </AppText>
        </AppCard>

        <AppCard style={{ gap: theme.spacing.sm }}>
          <AppText variant="bodyStrong">Deletion</AppText>
          <AppText variant="bodySmall" color="secondary">
            If your account deletion request is approved, your assistant messages are removed and replaced with a placeholder as part of that process.
          </AppText>
        </AppCard>

        <AppCard style={{ gap: theme.spacing.sm }}>
          <AppText variant="bodyStrong">Consent</AppText>
          <AppText variant="bodySmall" color="secondary">
            You can review and withdraw your consent for assistant message processing from Privacy consent.
          </AppText>
        </AppCard>
      </View>
    </AppScreen>
  );
}

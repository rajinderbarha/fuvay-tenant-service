import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { TextField } from "../../design-system/components/forms/TextField";
import { TextArea } from "../../design-system/components/forms/TextArea";
import { Checkbox } from "../../design-system/components/forms/Checkbox";
import { SecondaryButton, PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import * as api from "../../services/support/supportApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "CreateSupportRequest">;

const ISSUE_AREAS: { key: string; label: string; category: string; impact: string; redirect?: keyof ProfileStackParamList }[] = [
  { key: "jobs", label: "Jobs", category: "dispatch", impact: "one_user_affected" },
  { key: "schedule", label: "Schedule", category: "bookings_jobs", impact: "one_user_affected" },
  { key: "employment", label: "Employment details", category: "onboarding", impact: "one_user_affected", redirect: "EmploymentDetails" },
  { key: "documents", label: "Documents", category: "profile_documents", impact: "one_user_affected" },
  { key: "account_security", label: "Account/security", category: "security", impact: "one_user_affected" },
  { key: "notifications", label: "Notifications", category: "notifications", impact: "one_user_affected" },
  { key: "privacy", label: "Privacy", category: "account_access", impact: "one_user_affected", redirect: "PrivacyAndData" },
  { key: "technical", label: "Technical problem", category: "technical", impact: "one_user_affected" },
  { key: "other", label: "Other", category: "other", impact: "question" },
];

/**
 * Create Support Request (Phase Y spec sections 9, 10). Routes specialized
 * issues to their OWN canonical workflows instead of creating a generic
 * ticket -- employment corrections go through Phase S's real
 * correction-request system, privacy issues through Phase X's real DPDP
 * request system. Everything else creates one real ticket in the existing
 * Tenant Help & Support engine.
 */
export function CreateSupportRequestScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const [areaKey, setAreaKey] = useState<string | null>(
    route.params?.intent === "technical" ? "technical" : null,
  );
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [declared, setDeclared] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<string | null>(null);

  const area = ISSUE_AREAS.find(a => a.key === areaKey);
  const canSubmit = !!area && subject.trim().length > 0 && description.trim().length >= 10 && declared;

  const handleAreaSelect = (key: string) => {
    const selected = ISSUE_AREAS.find(a => a.key === key);
    if (selected?.redirect) {
      navigation.replace(selected.redirect as any, undefined as any);
      return;
    }
    setAreaKey(key);
  };

  const handleSubmit = async () => {
    if (!canSubmit || !area) return;
    setBusy(true);
    setError(null);
    const result = await api.createSupportRequest({
      category: area.category, subject: subject.trim(), description: description.trim(), impact: area.impact,
    });
    setBusy(false);
    if (result.ok) setSubmitted(result.data.id);
    else setError(result.error.safeMessage);
  };

  if (submitted) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Request submitted" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="success" title="Request submitted" message="You'll be notified as it's reviewed and updated." />
          <View style={{ height: theme.spacing.base }} />
          <PrimaryButton label="View request" onPress={() => navigation.replace("SupportRequestDetail", { requestId: submitted })} fullWidth />
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Create support request" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>What's this about?</AppText>
          {ISSUE_AREAS.map(a => (
            <SecondaryButton key={a.key} label={areaKey === a.key ? `✓ ${a.label}` : a.label} onPress={() => handleAreaSelect(a.key)} style={{ marginBottom: theme.spacing.xs }} fullWidth />
          ))}
        </Section>

        {area ? (
          <>
            <Section>
              <TextField label="Subject" value={subject} onChangeText={setSubject} />
            </Section>
            <Section>
              <TextArea label="Description" value={description} onChangeText={setDescription} minLines={4} placeholder="What happened, and what did you expect instead?" />
            </Section>
            <Section>
              <Checkbox label="I've included what's needed to look into this, and no customer or private information" checked={declared} onChange={setDeclared} />
            </Section>
            {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't submit" message={error} /></View> : null}
            <PrimaryButton label="Submit request" onPress={handleSubmit} loading={busy} disabled={!canSubmit} fullWidth />
          </>
        ) : null}
      </ScrollView>
    </SafeAreaScreen>
  );
}

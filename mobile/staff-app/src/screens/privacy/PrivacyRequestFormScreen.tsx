import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { TextArea } from "../../design-system/components/forms/TextArea";
import { Checkbox } from "../../design-system/components/forms/Checkbox";
import { SecondaryButton, PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { usePrivacy } from "./usePrivacy";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { PrivacyRequestType } from "../../services/privacy/types";

type Props = NativeStackScreenProps<ProfileStackParamList, "PrivacyRequestForm">;

const REQUEST_TYPES: { value: PrivacyRequestType; label: string; description: string }[] = [
  { value: "data_correction", label: "Correction", description: "Fix inaccurate information Fuvay holds about you" },
  { value: "processing_objection", label: "Object to processing", description: "Object to a specific way your data is used" },
  { value: "consent_withdrawal", label: "Consent withdrawal", description: "Formally withdraw a consent-based purpose" },
  { value: "grievance", label: "Grievance", description: "Raise a privacy concern or complaint" },
];

/** Privacy Request Form (Phase X spec section 9). Subject is always the
 * authenticated technician -- never a client-supplied ID. Submission only
 * creates the request; discovery/impact-review/execution all happen
 * backend-side (spec section 9: "Do not directly edit, export or erase
 * data from the form handler"). */
export function PrivacyRequestFormScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { submitRequest } = usePrivacy();
  const [requestType, setRequestType] = useState<PrivacyRequestType | null>(route.params?.requestType ?? null);
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState("");
  const [declared, setDeclared] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedId, setSubmittedId] = useState<string | null>(null);

  const canSubmit = !!requestType && reason.trim().length > 0 && declared;

  const handleSubmit = async () => {
    if (!canSubmit || !requestType) return;
    setBusy(true);
    setError(null);
    const result = await submitRequest(requestType, reason.trim(), details.trim() || undefined);
    setBusy(false);
    if (result.ok) setSubmittedId(result.requestId);
    else setError(result.error.safeMessage);
  };

  if (submittedId) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Request submitted" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="success" title="Request submitted" message="It will be reviewed across every Fuvay category linked to your account. You'll be notified as it progresses." />
          <View style={{ height: theme.spacing.base }} />
          <PrimaryButton label="Track request" onPress={() => navigation.replace("PrivacyRequestDetail", { requestId: submittedId })} fullWidth />
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Privacy request" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>What would you like to request?</AppText>
          {REQUEST_TYPES.map(t => (
            <SecondaryButton
              key={t.value}
              label={requestType === t.value ? `✓ ${t.label}` : t.label}
              onPress={() => setRequestType(t.value)}
              style={{ marginBottom: theme.spacing.xs }}
              fullWidth
            />
          ))}
        </Section>

        {requestType ? (
          <>
            <Section>
              <TextArea label="Request summary" value={reason} onChangeText={setReason} minLines={3} placeholder="Briefly describe what you need" />
            </Section>
            <Section>
              <TextArea label="Additional details (optional)" value={details} onChangeText={setDetails} minLines={2} />
            </Section>
            <Section>
              <Checkbox label="I confirm this request is about my own Fuvay account" checked={declared} onChange={setDeclared} />
            </Section>
            {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't submit" message={error} /></View> : null}
            <PrimaryButton label="Submit request" onPress={handleSubmit} loading={busy} disabled={!canSubmit} fullWidth />
          </>
        ) : null}
      </ScrollView>
    </SafeAreaScreen>
  );
}

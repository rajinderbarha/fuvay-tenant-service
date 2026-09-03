import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { TextArea } from "../../design-system/components/forms/TextArea";
import { Checkbox } from "../../design-system/components/forms/Checkbox";
import { DestructiveButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { usePrivacy } from "./usePrivacy";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "AccountClosureRequest">;

/**
 * Account Closure (Phase X spec section 13). A REQUEST, never an immediate
 * destructive action -- routes through the same canonical erasure pipeline
 * as any other data-erasure request (subject_type/request_type unchanged),
 * so the same legal-hold/active-job/retention safety checks apply. Requires
 * a current-password reauthentication step before submission (spec:
 * "Require reauthentication").
 */
export function AccountClosureRequestScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { submitRequest } = usePrivacy();
  const [reason, setReason] = useState("");
  const [understood, setUnderstood] = useState(false);
  const [confirmedIntent, setConfirmedIntent] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async () => {
    setBusy(true);
    setSubmitError(null);
    const result = await submitRequest("staff_data_erasure", reason.trim() || "Account closure requested.", undefined, true);
    setBusy(false);
    if (result.ok) setDone(true);
    else setSubmitError(result.error.safeMessage);
  };

  if (done) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Account closure" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="success" title="Closure request submitted" message="Fuvay will review your active relationships, retention requirements and legal holds before any action is taken. You'll be notified of the outcome." />
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Account closure" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card>
            <AppText variant="bodyStrong">Before you request closure</AppText>
            <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
              Closing your Fuvay account is different from leaving a business's team. If you're currently employed by a tenant, ending that specific relationship is a separate action from closing your platform account.
            </AppText>
            <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
              This does not immediately delete your data or end active jobs. Your request will be reviewed for active jobs, disputes, finance records and legal retention requirements before any action is taken.
            </AppText>
          </Card>
        </Section>

        {!confirmedIntent ? (
          <Section>
            <Checkbox label="I want to proceed with requesting account closure" checked={confirmedIntent} onChange={setConfirmedIntent} />
          </Section>
        ) : (
          <>
            <Section>
              <TextArea label="Reason (optional)" value={reason} onChangeText={setReason} minLines={3} />
            </Section>
            <Section>
              <Checkbox label="I understand this will be reviewed and does not take effect immediately" checked={understood} onChange={setUnderstood} />
            </Section>
            {submitError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't submit" message={submitError} /></View> : null}
            <DestructiveButton label="Submit closure request" onPress={handleSubmit} loading={busy} disabled={!understood} fullWidth />
          </>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}

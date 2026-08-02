import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { DestructiveButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { ConfirmationDialog } from "../../design-system/components/overlays/ConfirmationDialog";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import * as securityApi from "../../services/auth/securityApi";
import { useSecurity } from "./useSecurity";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "TrustedDevice">;

const formatDateTime = (iso: string | null) => iso ? new Date(iso).toLocaleString() : "—";

/**
 * Trusted Device (Phase V spec section 10). Trust is granted only at login
 * (remember-device) and is session/device scoped, never a client boolean --
 * this screen only surfaces the real UserSession.is_trusted state and lets
 * the user remove it, which takes effect immediately server-side.
 */
export function TrustedDeviceScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { data, isLoading, invalidate } = useSecurity();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [removed, setRemoved] = useState(false);

  const handleRemoveTrust = async () => {
    if (!data?.current_device.session_id) return;
    setBusy(true);
    setError(null);
    const result = await securityApi.removeDeviceTrust(data.current_device.session_id);
    setBusy(false);
    setConfirmOpen(false);
    if (result.ok) {
      setRemoved(true);
      invalidate();
    } else {
      setError(result.error.safeMessage);
    }
  };

  if (isLoading || !data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Trusted device" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={200} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  const trusted = removed ? false : data.current_device.trusted;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Trusted device" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {removed ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="success" message="Trust removed. You may be asked to verify with a code more often on this device." /></View> : null}
        {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't remove trust" message={error} /></View> : null}

        <Section>
          <Card>
            <KeyValueList items={[
              { label: "Device", value: data.current_device.device_name ?? "This device" },
              { label: "Trusted", value: trusted ? "Yes" : "No" },
              { label: "Last active", value: formatDateTime(data.current_device.last_active_at) },
            ]} />
          </Card>
        </Section>

        <AppText variant="bodySmall" color="tertiary" style={{ marginBottom: theme.spacing.base }}>
          A trusted device may reduce how often you're asked for a two-step code, but never bypasses sign-in authorization.
        </AppText>

        {trusted ? (
          <DestructiveButton label="Remove trust" onPress={() => setConfirmOpen(true)} fullWidth />
        ) : null}
      </ScrollView>

      <ConfirmationDialog
        visible={confirmOpen}
        title="Remove trust from this device?"
        message="You may be asked to verify with a two-step code more often afterward."
        confirmLabel="Remove trust"
        destructive
        loading={busy}
        onConfirm={handleRemoveTrust}
        onCancel={() => setConfirmOpen(false)}
      />
    </SafeAreaScreen>
  );
}

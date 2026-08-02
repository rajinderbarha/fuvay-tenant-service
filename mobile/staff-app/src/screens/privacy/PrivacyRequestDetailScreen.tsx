import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { DestructiveButton, PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { ConfirmationDialog } from "../../design-system/components/overlays/ConfirmationDialog";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import * as api from "../../services/privacy/privacyApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "PrivacyRequestDetail">;

const formatDateTime = (iso: string | null) => iso ? new Date(iso).toLocaleString() : "—";
const AUDIT_LABEL: Record<string, string> = {
  "request.created": "Request created", "compliance.staff_request_created": "Request submitted",
  "request.identity_verified": "Identity verified", "request.approved": "Approved",
  "request.partially_approved": "Partially approved", "request.rejected": "Rejected",
  "request.processed": "Processing", "request.completed": "Completed",
};

/** Privacy Request Detail (Phase X spec section 10). Renders ONLY the
 * backend's real lifecycle stage/audit trail -- no second state machine. */
export function PrivacyRequestDetailScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { requestId } = route.params;
  const queryClient = useQueryClient();
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["privacy-request", requestId],
    queryFn: async () => {
      const result = await api.getRequestDetail(requestId);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const canWithdraw = query.data && ["submitted", "identity_verification_pending"].includes(query.data.status);
  const canGenerateExport = query.data && query.data.request_type === "staff_data_export" && ["approved", "completed"].includes(query.data.status);

  const handleWithdraw = async () => {
    setBusy(true);
    setError(null);
    const result = await api.withdrawRequest(requestId);
    setBusy(false);
    setConfirmWithdraw(false);
    if (result.ok) {
      queryClient.invalidateQueries({ queryKey: ["privacy-request", requestId] });
      queryClient.invalidateQueries({ queryKey: ["privacy-requests"] });
      queryClient.invalidateQueries({ queryKey: ["privacy-summary"] });
    } else {
      setError(result.error.safeMessage);
    }
  };

  const handleGenerateExport = async () => {
    setBusy(true);
    setError(null);
    const result = await api.generateExport(requestId);
    setBusy(false);
    if (result.ok) queryClient.invalidateQueries({ queryKey: ["privacy-request", requestId] });
    else setError(result.error.safeMessage);
  };

  if (query.isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Request detail" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={300} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (query.isError || !query.data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Request detail" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load request" message="Please try again." actionLabel="Retry" onAction={() => query.refetch()} />
      </SafeAreaScreen>
    );
  }

  const req = query.data;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title={req.request_number} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete action" message={error} /></View> : null}

        <Section>
          <Card>
            <AppText variant="bodyStrong">{req.request_type.replace(/_/g, " ")}</AppText>
            <View style={{ marginTop: theme.spacing.xs, alignSelf: "flex-start", paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusWarningSurface }}>
              <AppText variant="labelStrong" color="warning">{req.status_label}</AppText>
            </View>
            {req.reason ? <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.sm }}>{req.reason}</AppText> : null}
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Details" />
          <Card>
            <KeyValueList items={[
              { label: "Submitted", value: formatDateTime(req.submitted_at) },
              { label: "Due", value: formatDateTime(req.due_at) },
              { label: "Completed", value: formatDateTime(req.completed_at) },
            ]} />
            {req.rejection_reason ? <AppText variant="bodySmall" color="danger" style={{ marginTop: theme.spacing.sm }}>{req.rejection_reason}</AppText> : null}
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Timeline" />
          <Card padding="base">
            {req.audit_trail.length === 0 ? (
              <AppText variant="bodySmall" color="tertiary">No updates yet.</AppText>
            ) : req.audit_trail.map((event, idx) => (
              <View key={`${event.action}-${idx}`} style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.xs }}>
                <Icon name="ellipse" size="compact" color={theme.colors.brandPrimary} decorative />
                <View style={{ flex: 1 }}>
                  <AppText variant="bodySmall">{AUDIT_LABEL[event.action] ?? event.action}</AppText>
                  <AppText variant="caption" color="tertiary">{formatDateTime(event.created_at)}</AppText>
                </View>
              </View>
            ))}
          </Card>
        </Section>

        {req.export ? (
          <Section>
            <SectionHeader title="Export" />
            <Card>
              <AppText variant="bodySmall">Status: {req.export.status}</AppText>
              {req.export.expires_at ? <AppText variant="caption" color="tertiary">Expires {formatDateTime(req.export.expires_at)}</AppText> : null}
              {req.export.is_expired ? <AppText variant="caption" color="danger">This export has expired. Request a new one.</AppText> : null}
            </Card>
          </Section>
        ) : null}

        {canGenerateExport ? (
          <PrimaryButton label="Generate export" onPress={handleGenerateExport} loading={busy} fullWidth />
        ) : null}
        {canWithdraw ? (
          <View style={{ marginTop: theme.spacing.sm }}>
            <DestructiveButton label="Withdraw request" onPress={() => setConfirmWithdraw(true)} fullWidth />
          </View>
        ) : null}
      </ScrollView>

      <ConfirmationDialog
        visible={confirmWithdraw}
        title="Withdraw this request?"
        message="You can submit a new request later if you change your mind."
        confirmLabel="Withdraw"
        destructive
        loading={busy}
        onConfirm={handleWithdraw}
        onCancel={() => setConfirmWithdraw(false)}
      />
    </SafeAreaScreen>
  );
}

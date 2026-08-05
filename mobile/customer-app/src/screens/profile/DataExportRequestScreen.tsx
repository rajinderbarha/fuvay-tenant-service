import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { Icon } from "../../components/Icon";
import { ExportInfoPanel } from "../../components/privacy/ExportInfoPanel";
import { ExportStepsList } from "../../components/privacy/ExportStepsList";
import { DeletionInfoRow } from "../../components/privacy/DeletionInfoRow";
import { usePrivacyRequestsQuery, useCreatePrivacyRequestMutation } from "../../api/privacyData/usePrivacyDataQueries";
import { getOrCreateIdempotencyKey, clearIdempotencyKey } from "../../api/idempotency/idempotencyStore";
import { PrivacyRequest } from "../../domain/privacyData";
import { isOffline } from "../../api/networkState";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { DomainError } from "../../domain/errors";

const IDEMPOTENCY_SCOPE = "privacy-request-create:data_export";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "DataExportRequest">;

const OPEN_STATUSES = new Set(["submitted", "identity_verification_pending", "under_review", "approved", "processing"]);

function findActiveExport(requests: PrivacyRequest[]): { request: PrivacyRequest; label: string } | null {
  const inProgress = requests.find(r => r.requestType === "data_export" && OPEN_STATUSES.has(r.status));
  if (inProgress) return { request: inProgress, label: "Your export is being prepared" };

  const readyOrDownloaded = requests.find(r =>
    r.requestType === "data_export" && r.status === "completed" &&
    r.export && !r.export.isExpired && (r.export.status === "ready" || r.export.status === "downloaded"));
  if (readyOrDownloaded) return { request: readyOrDownloaded, label: "Your export is ready" };

  return null;
}

/**
 * Opened from Privacy & Data -> "Download your data". Submits a real
 * request through `POST /v1/me/compliance/requests`
 * (request_type=data_export) -- never assembles or simulates export
 * content locally. The audited backend has no export manifest field on
 * either the create or detail response, so "Your export may include"
 * below uses the spec-mandated generic fallback copy rather than
 * inventing specific categories. Generation is real but currently
 * requires manual admin processing (no automated worker exists in the
 * audited engine) -- disclosed in the phase report, not implied here via
 * ETA or guaranteed-delivery language.
 */
export function DataExportRequestScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const requestsQuery = usePrivacyRequestsQuery(1);
  const createMutation = useCreatePrivacyRequestMutation();
  const [error, setError] = useState<string | null>(null);
  const offline = isOffline();

  if (requestsQuery.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Checking your export eligibility…" />
      </AppScreen>
    );
  }

  const active = findActiveExport(requestsQuery.data?.requests ?? []);

  async function handleSubmit() {
    if (offline) {
      setError("Connect to the internet to request your data.");
      return;
    }
    setError(null);
    try {
      // Reused across a retry of THIS submission attempt (network retry,
      // timeout, backgrounding) -- the backend returns the original
      // request instead of creating a duplicate for the same key (Data
      // Export Request phase). Only cleared below on a definitive outcome
      // (success or a non-retryable failure), never before.
      const idempotencyKey = await getOrCreateIdempotencyKey(IDEMPOTENCY_SCOPE);
      const res = await createMutation.mutateAsync({
        request_type: "data_export", confirm_understanding: true, idempotency_key: idempotencyKey,
      });
      await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
      // `replace` (not `navigate`/`goBack`) so a device-back press cannot
      // land the customer back on this form and resubmit (spec section 2).
      navigation.replace("PrivacyRequestSubmitted", { requestId: res.data.request_id });
    } catch (err) {
      if (err instanceof DomainError) {
        const existingRequestId = err.telemetryMeta?.existingRequestId;
        if (typeof existingRequestId === "string") {
          await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
          navigation.replace("PrivacyRequestDetails", { requestId: existingRequestId });
          return;
        }
        // Network/offline/timeout errors leave the key in place so a retry
        // reconciles onto the same attempt; only a definitive rejection
        // clears it.
        if (err.category !== "NETWORK_UNAVAILABLE" && err.category !== "TIMEOUT" && err.category !== "BACKEND_UNAVAILABLE") {
          await clearIdempotencyKey(IDEMPOTENCY_SCOPE);
        }
        setError(err.diagnostic);
      } else {
        setError("Couldn't submit your export request.");
      }
    }
  }

  if (active) {
    return (
      <AppScreen scroll edges={["top", "bottom"]}>
        <View style={{ gap: theme.spacing.base }}>
          <Header onBack={() => navigation.goBack()} />
          <AppCard style={{ gap: theme.spacing.sm, alignItems: "center" }}>
            <Icon name="download-outline" size="feature" color={theme.colors.textSecondary} decorative />
            <AppText variant="bodyStrong" align="center">{active.label}</AppText>
            <AppText variant="bodySmall" color="secondary" align="center">{active.request.statusLabel}</AppText>
            <AppButton
              label="View request" tone="primary" fullWidth
              onPress={() => navigation.replace("PrivacyRequestDetails", { requestId: active.request.id })}
            />
          </AppCard>
        </View>
      </AppScreen>
    );
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <Header onBack={() => navigation.goBack()} />
        <ExportInfoPanel />

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Your export may include</AppText>
          <AppCard style={{ gap: theme.spacing.xs }}>
            <AppText variant="bodySmall" color="secondary">
              Your export contains the customer information available under the platform's export policy.
            </AppText>
          </AppCard>
          <AppText variant="caption" color="tertiary">Included data depends on availability and retention rules.</AppText>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">How it works</AppText>
          <ExportStepsList />
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Important to know</AppText>
          <AppCard style={{ gap: theme.spacing.xs }}>
            <DeletionInfoRow
              icon="lock-closed-outline" title="Only you can access it"
              subtitle="Your identity and active session protect the request."
            />
            <DeletionInfoRow
              icon="time-outline" title="Downloads may expire"
              subtitle="Use the availability shown with the finished export."
            />
          </AppCard>
        </View>

        {error ? <AppText variant="bodySmall" color="danger">{error}</AppText> : null}
        {offline ? <AppText variant="bodySmall" color="secondary">Connect to the internet to request your data.</AppText> : null}

        <View style={{ gap: theme.spacing.sm }}>
          <AppButton
            label="Request data export" tone="primary" onPress={handleSubmit}
            loading={createMutation.isPending} disabled={offline} fullWidth
          />
          <AppButton label="Not now" tone="secondary" onPress={() => navigation.goBack()} disabled={createMutation.isPending} fullWidth />
        </View>

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: theme.spacing.xxs }}>
          <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary" align="center">Your request is linked to this account.</AppText>
        </View>
      </View>
    </AppScreen>
  );
}

function Header({ onBack }: { onBack: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">Download your data</AppText>
        <AppText variant="bodySmall" color="secondary">Request a secure copy</AppText>
      </View>
    </View>
  );
}

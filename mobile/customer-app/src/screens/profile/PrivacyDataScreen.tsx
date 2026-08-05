import React, { useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { PrivacyHeader } from "../../components/privacy/PrivacyHeader";
import { PrivacyInfoPanel } from "../../components/privacy/PrivacyInfoPanel";
import { PrivacyActionRow } from "../../components/privacy/PrivacyActionRow";
import { PrivacyRequestCard } from "../../components/privacy/PrivacyRequestCard";
import { PrivacyRequestsEmptyState } from "../../components/privacy/PrivacyRequestsEmptyState";
import {
  usePrivacyRequestsQuery, useCancelPrivacyRequestMutation, useDownloadExportMutation,
} from "../../api/privacyData/usePrivacyDataQueries";
import { resolvePrivacyCapabilities } from "../../domain/privacyCapabilities";
import { isOffline } from "../../api/networkState";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { DomainError } from "../../domain/errors";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "PrivacyData">;

const OPEN_STATUSES = new Set(["submitted", "identity_verification_pending", "under_review", "approved", "processing"]);

/**
 * Opened from Profile -> "Privacy & data". Every action here calls the
 * real, canonical DPDP compliance engine (`app/engines/compliance/
 * customer_router.py`) -- no local request history, no fake export file,
 * no second deletion workflow.
 */
export function PrivacyDataScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [page, setPage] = useState(1);
  const requestsQuery = usePrivacyRequestsQuery(page);
  const cancelMutation = useCancelPrivacyRequestMutation();
  const downloadMutation = useDownloadExportMutation();
  const capabilities = resolvePrivacyCapabilities();

  const [error, setError] = useState<string | null>(null);

  if (requestsQuery.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Checking privacy controls…" />
      </AppScreen>
    );
  }

  if (requestsQuery.isError && !requestsQuery.data) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your privacy controls." actionLabel="Try again" onAction={() => requestsQuery.refetch()} />
      </AppScreen>
    );
  }

  const allRequests = requestsQuery.data?.requests ?? [];
  const activeRequests = allRequests.filter(r => OPEN_STATUSES.has(r.status));
  const visibleRequests = activeRequests;
  const hasActiveErasure = activeRequests.some(r => r.requestType === "right_to_erasure");
  const hasActiveExport = activeRequests.some(r => r.requestType === "data_export");

  function handleCancelRequest(requestId: string) {
    Alert.alert("Withdraw this request?", "This request will be withdrawn.", [
      { text: "Keep request", style: "cancel" },
      { text: "Withdraw", style: "destructive", onPress: () => cancelMutation.mutate(requestId) },
    ]);
  }

  async function handleDownload(exportId: string, requestId: string) {
    try {
      const res = await downloadMutation.mutateAsync({ exportId, requestId });
      if (!res.data.download_url) {
        setError("This export isn't available for download right now.");
      }
    } catch (err) {
      setError(err instanceof DomainError ? err.diagnostic : "Couldn't download this export.");
    }
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      {isOffline() && requestsQuery.data ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.base }}>
        <PrivacyHeader onBack={() => navigation.goBack()} />
        <PrivacyInfoPanel />

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Your data</AppText>
          <AppCard style={{ gap: theme.spacing.xs }}>
            {capabilities.canRequestExport ? (
              <PrivacyActionRow
                icon="download-outline" title="Download your data"
                subtitle="Request a copy of your Fuvay information"
                actionLabel="Request" onPress={() => navigation.navigate("DataExportRequest")}
                disabled={hasActiveExport}
              />
            ) : null}
            {capabilities.canRequestCorrection ? (
              <PrivacyActionRow
                icon="create-outline" title="Correct my data"
                subtitle="Report inaccurate information"
                actionLabel="Request" onPress={() => navigation.navigate("DataCorrectionRequest")}
              />
            ) : null}
            {capabilities.canRequestErasure ? (
              <PrivacyActionRow
                icon="person-remove-outline" title="Delete your account"
                subtitle="Submit an account deletion request"
                actionLabel="Start" destructive
                onPress={() => navigation.navigate("AccountDeletionRequest")}
                disabled={hasActiveErasure}
              />
            ) : null}
          </AppCard>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Consent & permissions</AppText>
          <AppCard style={{ gap: theme.spacing.xs }}>
            {capabilities.canManageConsent ? (
              <PrivacyActionRow
                icon="checkmark-done-outline" title="Privacy consent"
                subtitle="Review your current consent choices"
                actionLabel="View" onPress={() => navigation.navigate("PrivacyConsent")}
              />
            ) : null}
            <PrivacyActionRow
              icon="chatbubble-ellipses-outline" title="Assistant conversations"
              subtitle="Learn how your messages are handled"
              actionLabel="View" onPress={() => navigation.navigate("AssistantDataInfo")}
            />
          </AppCard>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Privacy requests</AppText>
          {visibleRequests.length === 0 ? (
            <PrivacyRequestsEmptyState />
          ) : (
            <View style={{ gap: theme.spacing.sm }}>
              {visibleRequests.map(request => (
                <PrivacyRequestCard
                  key={request.id}
                  request={request}
                  onPress={() => navigation.navigate("PrivacyRequestDetails", { requestId: request.id })}
                  onCancel={capabilities.canCancelRequest && OPEN_STATUSES.has(request.status) ? () => handleCancelRequest(request.id) : undefined}
                  onDownload={capabilities.canDownloadExport && request.export ? () => handleDownload(request.export!.exportId, request.id) : undefined}
                />
              ))}
            </View>
          )}
          {capabilities.canViewRequestHistory ? (
            <AppText
              variant="labelStrong" color="link" onPress={() => navigation.navigate("PrivacyRequests")}
              accessibilityRole="button" accessibilityLabel="View all privacy requests"
            >
              View all requests
            </AppText>
          ) : null}
        </View>

        {error ? <AppText variant="bodySmall" color="danger">{error}</AppText> : null}

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive }}>
          <AppText variant="bodyStrong">Account deletion is reviewed</AppText>
        </View>
        <AppText variant="bodySmall" color="secondary">Eligible personal data is anonymized after your request is approved.</AppText>

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: theme.spacing.xxs }}>
          <AppText variant="caption" color="tertiary" align="center">Fuvay keeps required records only according to its retention policy.</AppText>
        </View>
      </View>
    </AppScreen>
  );
}

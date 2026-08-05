import React, { useState } from "react";
import { View, ScrollView, RefreshControl, Alert } from "react-native";
import { useRoute, RouteProp, useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { Icon, IconProps } from "../../components/Icon";
import { PrivacyRequestStatusCard } from "../../components/privacy/PrivacyRequestStatusCard";
import { PrivacyRequestProgress } from "../../components/privacy/PrivacyRequestProgress";
import { PrivacyRequestDetailsCard } from "../../components/privacy/PrivacyRequestDetailsCard";
import { PrivacyRequestExportSection } from "../../components/privacy/PrivacyRequestExportSection";
import {
  usePrivacyRequestDetailQuery, useCancelPrivacyRequestMutation, useDownloadExportMutation,
} from "../../api/privacyData/usePrivacyDataQueries";
import { resolvePrivacyRequestPresentation } from "../../domain/privacyRequestPresentation";
import { isOffline } from "../../api/networkState";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { DomainError } from "../../domain/errors";

type Route = RouteProp<CustomerAppStackParamList, "PrivacyRequestDetails">;
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "PrivacyRequestDetails">;

/**
 * One reusable, backend-driven detail screen for every customer privacy
 * request type (deletion, export, and any future type the backend adds) --
 * never a per-type hardcoded screen (spec section "Screen and navigation").
 * All display data is resolved from `requestId` alone via
 * `usePrivacyRequestDetailQuery`; the route param never carries a full
 * request object.
 */
export function PrivacyRequestDetailsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { requestId } = route.params;
  const query = usePrivacyRequestDetailQuery(requestId);
  const cancelMutation = useCancelPrivacyRequestMutation();
  const downloadMutation = useDownloadExportMutation();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [withdrawError, setWithdrawError] = useState<string | null>(null);
  const offline = isOffline();

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your request…" />
      </AppScreen>
    );
  }

  if (offline && !query.data) {
    return (
      <AppScreen>
        <OfflineBanner />
        <ErrorState title="You're offline" message="Reconnect to see this request." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  if (query.isError && !query.data) {
    return (
      <AppScreen>
        <ErrorState title="Something went wrong" message="We couldn't load this request." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  if (query.data?.kind !== "found") {
    return (
      <AppScreen>
        <ErrorState
          title="This privacy request is unavailable."
          actionLabel="Back to Privacy & data"
          onAction={() => navigation.goBack()}
        />
      </AppScreen>
    );
  }

  const request = query.data.request;
  const presentation = resolvePrivacyRequestPresentation(request);

  async function handleWithdraw() {
    setWithdrawError(null);
    Alert.alert(
      `Withdraw this ${presentation.typeLabel.toLowerCase()} request?`,
      "This request will be withdrawn and no further action will be taken on it.",
      [
        { text: "Keep request", style: "cancel" },
        {
          text: "Withdraw", style: "destructive",
          onPress: async () => {
            try {
              await cancelMutation.mutateAsync(requestId);
              await query.refetch();
            } catch (err) {
              // Approval-vs-withdrawal race: server re-validates state on
              // every call, so a race just surfaces as INVALID_STATE here
              // -- refetch to show whatever the authoritative status is now.
              setWithdrawError(err instanceof DomainError ? err.diagnostic : "Couldn't withdraw this request.");
              await query.refetch();
            }
          },
        },
      ],
    );
  }

  async function handleDownload() {
    if (!request.export) return;
    setDownloadError(null);
    try {
      const res = await downloadMutation.mutateAsync({ exportId: request.export.exportId, requestId });
      if (!res.data.download_url) {
        setDownloadError("This export isn't available for download right now.");
      }
    } catch (err) {
      setDownloadError(err instanceof DomainError ? err.diagnostic : "Couldn't download this export.");
    }
  }

  return (
    <AppScreen edges={["top", "bottom"]}>
      <ScrollView
        contentContainerStyle={{ padding: theme.layout.screenHorizontalPadding, gap: theme.spacing.base }}
        refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => query.refetch()} />}
      >
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">Privacy request</AppText>
            <AppText variant="bodySmall" color="secondary">Track your request status</AppText>
          </View>
        </View>

        {offline ? <OfflineBanner /> : null}
        {query.isError ? (
          <AppText variant="bodySmall" color="danger">We couldn't refresh this request. Showing the last known status.</AppText>
        ) : null}

        <PrivacyRequestStatusCard presentation={presentation} />

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Request progress</AppText>
          <PrivacyRequestProgress request={request} />
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Request details</AppText>
          <PrivacyRequestDetailsCard request={request} typeLabel={presentation.typeLabel} />
        </View>

        {request.requestType === "right_to_erasure" && !presentation.isTerminal ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">While your request is reviewed</AppText>
            <View style={{ gap: theme.spacing.sm }}>
              <InfoRow icon="shield-outline" title="You can continue using Fuvay" subtitle="Your account remains active." />
              <InfoRow icon="document-lock-outline" title="Some records may be retained" subtitle="Booking, financial and audit records follow retention policy." />
            </View>
          </View>
        ) : null}

        {request.requestType === "data_export" && request.export ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">Your export</AppText>
            <PrivacyRequestExportSection
              exportInfo={request.export}
              onDownload={handleDownload}
              downloadPending={downloadMutation.isPending}
              downloadError={downloadError}
              offline={offline}
            />
          </View>
        ) : null}

        {presentation.canWithdraw ? (
          <View style={{ gap: theme.spacing.xs }}>
            {withdrawError ? <AppText variant="bodySmall" color="danger">{withdrawError}</AppText> : null}
            <AppButton
              label="Withdraw request" tone="destructive" onPress={handleWithdraw}
              loading={cancelMutation.isPending} disabled={offline} fullWidth
            />
          </View>
        ) : null}

        <AppButton label="Back to Privacy & data" tone="secondary" onPress={() => navigation.goBack()} fullWidth />

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: theme.spacing.xxs }}>
          <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary" align="center">Only you can view this request.</AppText>
        </View>
      </ScrollView>
    </AppScreen>
  );
}

function InfoRow({ icon, title, subtitle }: { icon: IconProps["name"]; title: string; subtitle: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
      <Icon name={icon} size="standard" color={theme.colors.textSecondary} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">{title}</AppText>
        <AppText variant="bodySmall" color="secondary">{subtitle}</AppText>
      </View>
    </View>
  );
}

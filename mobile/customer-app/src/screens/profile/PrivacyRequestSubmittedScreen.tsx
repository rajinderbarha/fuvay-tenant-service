import React, { useEffect } from "react";
import { View, AccessibilityInfo } from "react-native";
import { useRoute, RouteProp, useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppBadge } from "../../components/AppBadge";
import { AppIconButton } from "../../components/AppIconButton";
import { Icon } from "../../components/Icon";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { usePrivacyRequestDetailQuery } from "../../api/privacyData/usePrivacyDataQueries";
import {
  resolvePrivacyRequestType, resolvePrivacyRequestStatus, resolvePrivacyReceiptNextSteps,
  resolvePrivacyReceiptSupportingMessage, resolvePrivacyReceiptSessionMessage,
} from "../../domain/privacyRequestPresentation";
import { ServerTimestamp, toDisplayDate } from "../../domain/dates";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";

type Route = RouteProp<CustomerAppStackParamList, "PrivacyRequestSubmitted">;
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "PrivacyRequestSubmitted">;

function formatDateTime(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

/**
 * Reusable privacy-request confirmation receipt (spec section 7) -- loads
 * the real, authenticated request by `requestId` alone via the same
 * `usePrivacyRequestDetailQuery` the details screen already uses, never a
 * navigation param carrying a mutable request object. Confirms the
 * request was CREATED, never that the underlying privacy work (or an
 * export artifact) is complete.
 */
export function PrivacyRequestSubmittedScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { requestId } = route.params;
  const query = usePrivacyRequestDetailQuery(requestId);

  useEffect(() => {
    AccessibilityInfo.announceForAccessibility("Privacy request submitted");
  }, []);

  function close() {
    navigation.goBack();
  }

  function viewRequest() {
    navigation.replace("PrivacyRequestDetails", { requestId });
  }

  if (query.isPending) {
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header onClose={close} />
        <LoadingState label="Confirming your request…" />
      </AppScreen>
    );
  }

  if (query.data?.kind !== "found") {
    // Creation already succeeded (this screen is only reached after a real
    // 201) -- a delayed/failed detail read is not a failed submission. The
    // acknowledgment stays honest without inventing detail fields.
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header onClose={close} />
        <View style={{ alignItems: "center", padding: theme.spacing.xl, gap: theme.spacing.sm }}>
          <Icon name="checkmark-circle-outline" size="emptyState" color={theme.colors.brandPrimaryStrong} decorative />
          <AppText variant="title" align="center">Your request is in</AppText>
          <AppText variant="bodySmall" color="secondary" align="center">
            We couldn't load the full details just now, but your request was submitted.
          </AppText>
          <AppButton label="Try again" tone="secondary" onPress={() => { void query.refetch(); }} />
        </View>
        <View style={{ gap: theme.spacing.sm, padding: theme.layout.screenHorizontalPadding }}>
          <AppButton label="Back to Privacy & data" tone="primary" onPress={close} fullWidth />
        </View>
      </AppScreen>
    );
  }

  const request = query.data.request;
  const typeLabel = resolvePrivacyRequestType(request.requestType);
  const status = resolvePrivacyRequestStatus(request.status);
  const nextSteps = resolvePrivacyReceiptNextSteps({ requestType: request.requestType, status: request.status });
  const submitted = request.submittedAt ?? request.createdAt;
  const sessionMessage = resolvePrivacyReceiptSessionMessage(request.requestType);

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <Header onClose={close} />

        <View style={{ alignItems: "center", gap: theme.spacing.sm }}>
          <View
            style={{
              width: 72, height: 72, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
              backgroundColor: theme.colors.brandPrimaryMuted,
            }}
          >
            <Icon name="shield-checkmark-outline" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <AppText variant="title" align="center" accessibilityRole="header">Your request is in</AppText>
          <AppText variant="bodySmall" color="secondary" align="center">
            {resolvePrivacyReceiptSupportingMessage(request.requestType)}
          </AppText>
          <AppBadge label={status.title} tone={status.tone} />
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Request summary</AppText>
          <AppCard style={{ gap: 0 }}>
            <SummaryRow icon="document-text-outline" label="Request type" value={typeLabel} />
            {request.requestNumber ? (
              <SummaryRow icon="pricetag-outline" label="Reference" value={request.requestNumber} />
            ) : null}
            {submitted ? (
              <SummaryRow icon="calendar-outline" label="Submitted" value={formatDateTime(submitted)} />
            ) : null}
            <SummaryRow icon="checkmark-circle-outline" label="Current status" value={status.title} last />
          </AppCard>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">What happens next</AppText>
          <View style={{ gap: theme.spacing.sm }}>
            {nextSteps.map((step, i) => (
              <View key={step} style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
                <View
                  style={{
                    width: 24, height: 24, borderRadius: theme.radius.radiusFull, borderWidth: 1, borderColor: theme.colors.brandPrimary,
                    alignItems: "center", justifyContent: "center",
                  }}
                >
                  <AppText variant="caption" style={{ color: theme.colors.brandPrimaryStrong }}>{i + 1}</AppText>
                </View>
                <AppText variant="bodySmall" style={{ flex: 1 }}>{step}</AppText>
              </View>
            ))}
          </View>
        </View>

        {sessionMessage ? (
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.statusSuccessSurface }}>
            <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.statusSuccess} decorative />
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong" style={{ color: theme.colors.statusSuccess }}>{sessionMessage.title}</AppText>
              <AppText variant="bodySmall" color="secondary">{sessionMessage.description}</AppText>
            </View>
          </View>
        ) : null}

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive }}>
          <Icon name="information-circle-outline" size="standard" color={theme.colors.textSecondary} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">No need to stay on this screen</AppText>
            <AppText variant="bodySmall" color="secondary">You can return later and check the latest status.</AppText>
          </View>
        </View>

        <View style={{ gap: theme.spacing.sm }}>
          <AppButton label="View request" tone="primary" onPress={viewRequest} fullWidth />
          <AppButton label="Back to Privacy & data" tone="secondary" onPress={close} fullWidth />
        </View>
      </View>
    </AppScreen>
  );
}

function Header({ onClose }: { onClose: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm }}>
      <View style={{ flex: 1 }} />
      <AppText variant="headingSmall" accessibilityRole="header">Request submitted</AppText>
      <View style={{ flex: 1, alignItems: "flex-end" }}>
        <AppIconButton name="close" onPress={onClose} accessibilityLabel="Close" />
      </View>
    </View>
  );
}

function SummaryRow({
  icon, label, value, last,
}: { icon: React.ComponentProps<typeof Icon>["name"]; label: string; value: string; last?: boolean }) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.sm,
        borderBottomWidth: last ? 0 : 1, borderBottomColor: theme.colors.borderSubtle,
      }}
    >
      <Icon name={icon} size="compact" color={theme.colors.textSecondary} decorative />
      <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>{label}</AppText>
      <AppText variant="bodyStrong">{value}</AppText>
    </View>
  );
}

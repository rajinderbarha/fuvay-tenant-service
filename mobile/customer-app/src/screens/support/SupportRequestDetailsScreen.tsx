import React, { useState } from "react";
import { View, ScrollView, RefreshControl, Alert } from "react-native";
import { useRoute, RouteProp, useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppBadge } from "../../components/AppBadge";
import { AppInput } from "../../components/AppInput";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import {
  useSupportRequestDetailQuery, useCancelSupportRequestMutation,
  useSupportRequestMessagesQuery, useAddSupportRequestMessageMutation,
} from "../../api/supportRequests/useSupportRequestsQueries";
import { useCustomerBookingsListQuery } from "../../api/customerBookings/useCustomerBookingsListQuery";
import {
  resolveSupportRequestPresentation, canCancelSupportRequest,
  resolveHeroKind, resolvedHeroHeadline, isConversationReadOnly,
} from "../../domain/supportRequestPresentation";
import { Icon } from "../../components/Icon";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { isOffline } from "../../api/networkState";
import { DomainError } from "../../domain/errors";
import { ServerTimestamp, toDisplayDate } from "../../domain/dates";

type Route = RouteProp<CustomerAppStackParamList, "SupportRequestDetails">;
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "SupportRequestDetails">;

function formatDateTime(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

/** Real detail + real message thread from `app/engines/complaints/
 * customer_router.py` -- no fabricated agent identity, resolution time or
 * live-chat availability (spec section 8). Messages are fetched via
 * focus-refresh, never claimed as real-time/WebSocket delivery. */
export function SupportRequestDetailsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { requestId } = route.params;
  const query = useSupportRequestDetailQuery(requestId);
  const messagesQuery = useSupportRequestMessagesQuery(requestId);
  const cancelMutation = useCancelSupportRequestMutation();
  const addMessageMutation = useAddSupportRequestMessageMutation(requestId);
  // Only fetched to resolve a safe service name + booking reference for the
  // linked-booking card, same pattern as the create-request wizard's Review
  // screen -- never renders raw provider/tenant/workflow data.
  const bookingsQuery = useCustomerBookingsListQuery("all");
  const [messageText, setMessageText] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);
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
        <ErrorState title="This request is unavailable." actionLabel="Go back" onAction={() => navigation.goBack()} />
      </AppScreen>
    );
  }

  const request = query.data.request;
  const presentation = resolveSupportRequestPresentation(request);
  const canCancel = canCancelSupportRequest(request.status);
  const heroKind = resolveHeroKind(request.status);
  const readOnly = isConversationReadOnly(request.status);
  const linkedBooking = request.bookingId
    ? bookingsQuery.items.find(b => b.bookingId === request.bookingId) ?? null
    : null;

  function handleCancel() {
    setCancelError(null);
    Alert.alert("Cancel this request?", "This request will be cancelled.", [
      { text: "Keep request", style: "cancel" },
      {
        text: "Cancel request", style: "destructive",
        onPress: async () => {
          try {
            await cancelMutation.mutateAsync({ requestId, reason: "Cancelled by customer" });
          } catch (err) {
            setCancelError(err instanceof DomainError ? err.diagnostic : "Couldn't cancel this request.");
          }
        },
      },
    ]);
  }

  async function handleSendMessage() {
    if (!messageText.trim()) return;
    try {
      await addMessageMutation.mutateAsync(messageText.trim());
      setMessageText("");
    } catch {
      // Recoverable -- the composed text is preserved so the customer can retry.
    }
  }

  return (
    <AppScreen edges={["top", "bottom"]}>
      <ScrollView
        contentContainerStyle={{ padding: theme.layout.screenHorizontalPadding, gap: theme.spacing.base }}
        refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => { query.refetch(); messagesQuery.refetch(); }} />}
      >
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">{presentation.typeLabel}</AppText>
            <AppText variant="bodySmall" color="secondary">Request {request.complaintNumber}</AppText>
          </View>
        </View>

        {offline ? <OfflineBanner /> : null}

        {heroKind ? (
          <AppCard style={{ gap: theme.spacing.xs }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
              <Icon
                name={heroKind === "resolved" ? "checkmark-circle" : "checkmark-done-circle-outline"}
                size="feature" color={theme.colors.statusSuccess} decorative
              />
              <AppBadge label={presentation.statusLabel} tone={presentation.tone} />
            </View>
            <AppText variant="title" accessibilityRole="header">{resolvedHeroHeadline(heroKind)}</AppText>
            {(heroKind === "resolved" ? request.resolvedAt : request.closedAt) ? (
              <AppText variant="bodySmall" color="secondary">
                {heroKind === "resolved" ? "Resolved on " : "Closed on "}
                {formatDateTime((heroKind === "resolved" ? request.resolvedAt : request.closedAt) as ServerTimestamp)}
              </AppText>
            ) : null}
          </AppCard>
        ) : (
          <AppCard style={{ gap: theme.spacing.xs }}>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
              <AppText variant="bodyStrong">Status</AppText>
              <AppBadge label={presentation.statusLabel} tone={presentation.tone} />
            </View>
          </AppCard>
        )}

        {heroKind ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">Resolution</AppText>
            <AppCard style={{ gap: theme.spacing.xxs }}>
              <AppText variant="bodySmall">
                {request.customerVisibleSummary
                  ? request.customerVisibleSummary
                  : "This request has been marked as resolved."}
              </AppText>
              <AppText variant="caption" color="tertiary">Updated by Fuvay Support</AppText>
            </AppCard>
          </View>
        ) : null}

        {linkedBooking ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">Linked booking</AppText>
            <AppCard style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
              <Icon name="briefcase-outline" size="feature" color={theme.colors.textSecondary} decorative />
              <View style={{ flex: 1 }}>
                <AppText variant="bodyStrong">{linkedBooking.serviceName ?? "Service"}</AppText>
                {linkedBooking.bookingNumber ? (
                  <AppText variant="caption" color="secondary">Booking {linkedBooking.bookingNumber}</AppText>
                ) : null}
              </View>
              <AppText
                variant="labelStrong" color="link" accessibilityRole="button"
                accessibilityLabel="View booking"
                onPress={() => navigation.navigate("BookingDetails", { bookingId: request.bookingId as string })}
              >
                View booking
              </AppText>
            </AppCard>
          </View>
        ) : null}

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Description</AppText>
          <AppCard><AppText variant="bodySmall">{request.description}</AppText></AppCard>
        </View>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Conversation history</AppText>
          {messagesQuery.isPending ? (
            <LoadingState label="Loading messages…" />
          ) : (messagesQuery.data ?? []).length === 0 ? (
            <AppText variant="bodySmall" color="secondary">No messages yet.</AppText>
          ) : (
            <View style={{ gap: theme.spacing.sm }}>
              {(messagesQuery.data ?? []).map(m => (
                <AppCard key={m.id} style={{ gap: theme.spacing.xxs }}>
                  <AppText variant="labelStrong" color="secondary">{m.senderType === "customer" ? "You" : "Support"}</AppText>
                  <AppText variant="bodySmall">{m.messageText}</AppText>
                  <AppText variant="caption" color="tertiary">{formatDateTime(m.createdAt)}</AppText>
                </AppCard>
              ))}
            </View>
          )}
          {readOnly ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
              <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
              <AppText variant="caption" color="tertiary">This conversation is now read-only.</AppText>
            </View>
          ) : (
            <View style={{ gap: theme.spacing.xs }}>
              <AppInput
                label="Add a message" value={messageText} onChangeText={setMessageText}
                accessibilityLabel="Add a message" multiline editable={!addMessageMutation.isPending && !offline}
              />
              <AppButton
                label="Send" tone="secondary" onPress={handleSendMessage}
                loading={addMessageMutation.isPending} disabled={!messageText.trim() || offline}
              />
            </View>
          )}
        </View>

        {cancelError ? <AppText variant="bodySmall" color="danger">{cancelError}</AppText> : null}

        {canCancel ? (
          <AppButton
            label="Cancel request" tone="destructive" onPress={handleCancel}
            loading={cancelMutation.isPending} disabled={offline} fullWidth
          />
        ) : null}

        {heroKind ? (
          <View style={{ gap: theme.spacing.sm }}>
            <AppButton
              label="Back to support" tone="primary" fullWidth
              onPress={() => navigation.navigate("SupportRequests")}
            />
            {linkedBooking ? (
              <AppText
                variant="labelStrong" color="link" align="center" accessibilityRole="button"
                accessibilityLabel="View booking"
                onPress={() => navigation.navigate("BookingDetails", { bookingId: request.bookingId as string })}
              >
                View booking
              </AppText>
            ) : null}
          </View>
        ) : null}
      </ScrollView>
    </AppScreen>
  );
}
